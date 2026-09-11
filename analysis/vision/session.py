"""Vision 会话编排 — 视频源 → 帧处理 → 姿态 → 动作状态 → 时间研究/工作抽样。"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from analysis.vision.action import (
    ACTION_LABELS,
    VISION_STATUSES,
    ActionClassifier,
    ActionConfig,
    ActionSegment,
    ActionState,
    duration_by_state,
    ratio_by_state,
)
from analysis.vision.camera import FrameSource, open_source
from analysis.vision.pose import create_pose_estimator
from analysis.vision.processor import FramePipeline, LatencyMeter


@dataclass
class VisionConfig:
    sample_fps: float = 5.0
    width: int = 640
    roi: tuple[int, int, int, int] | None = None
    min_dwell_ms: float = 700.0
    min_cycle_s: float = 0.5
    merge_gap_s: float = 1.0
    max_seconds: float = 600.0
    process_id: str = "视频工序"
    operator: str = "视频观测"
    prefer_mediapipe: bool = True
    model_path: str | None = None
    action: ActionConfig = field(default_factory=ActionConfig)

    def action_config(self) -> ActionConfig:
        return self.action.merged(min_dwell_ms=self.min_dwell_ms)


@dataclass
class CycleSegment:
    index: int
    start_ms: float
    end_ms: float

    @property
    def duration_s(self) -> float:
        return max(0.0, (self.end_ms - self.start_ms) / 1000.0)

    def to_dict(self) -> dict:
        return {"index": self.index, "start_ms": round(self.start_ms, 1),
                "end_ms": round(self.end_ms, 1),
                "duration_s": round(self.duration_s, 3)}


@dataclass
class VisionResult:
    source: str
    backend: str
    frames: int
    duration_s: float
    processed_fps: float
    latency: dict
    segments: list[ActionSegment]
    ratios: dict[str, float]
    durations: dict[str, float]
    cycles: list[CycleSegment]
    warnings: list[str] = field(default_factory=list)
    model_ready: bool = False
    truncated: bool = False
    process_id: str = "视频工序"
    operator: str = "视频观测"

    @property
    def ratios_labeled(self) -> dict[str, float]:
        return {ACTION_LABELS[ActionState(k)]: v for k, v in self.ratios.items()}

    def to_dict(self) -> dict:
        return {
            "source": self.source, "backend": self.backend,
            "frames": self.frames, "duration_s": round(self.duration_s, 3),
            "processed_fps": round(self.processed_fps, 2),
            "latency": self.latency, "model_ready": self.model_ready,
            "truncated": self.truncated, "warnings": list(self.warnings),
            "ratios": self.ratios,
            "ratios_labeled": self.ratios_labeled,
            "durations_s": {k: round(v, 3) for k, v in self.durations.items()},
            "segments": [s.to_dict() for s in self.segments],
            "cycles": [c.to_dict() for c in self.cycles],
        }

    def to_time_observations(self) -> list:
        """周期时长 → TimeObservation（可直接进 TimeStudyEngine）。"""
        from core.data_objects import TimeObservation

        return [TimeObservation(process_id=self.process_id,
                                operator=self.operator,
                                cycle=cycle.index,
                                observation_time=round(cycle.duration_s, 3))
                for cycle in self.cycles]

    def to_work_sampling_labels(self, per_second: float = 1.0,
                                max_labels: int = 20000) -> list[str]:
        """把状态段展开成工作抽样标签序列（默认每秒 1 个样本）。"""
        labels: list[str] = []
        for seg in self.segments:
            label = ACTION_LABELS.get(seg.state)
            if not label:
                continue
            count = max(1, int(round(seg.duration_s * per_second)))
            labels.extend([label] * count)
            if len(labels) >= max_labels:
                return labels[:max_labels]
        return labels


def extract_cycles(segments: list[ActionSegment], config: VisionConfig) -> list[CycleSegment]:
    """工作段 → 作业周期（合并小间隔、过滤过短片段、重新编号）。"""
    working = [s for s in segments if s.state == ActionState.WORKING]
    merged: list[list[float]] = []
    for seg in working:
        if merged and (seg.start_ms - merged[-1][1]) <= config.merge_gap_s * 1000.0:
            merged[-1][1] = max(merged[-1][1], seg.end_ms)
        else:
            merged.append([seg.start_ms, seg.end_ms])
    cycles = [CycleSegment(index=i + 1, start_ms=a, end_ms=b)
              for i, (a, b) in enumerate(merged)
              if (b - a) / 1000.0 >= config.min_cycle_s]
    return cycles


def run_vision_session(source_spec, config: VisionConfig | None = None,
                       progress=None, should_stop=None,
                       frame_callback=None) -> VisionResult:
    """执行一次完整视频分析（同步；UI 层放入工作线程调用）。"""
    cfg = config or VisionConfig()
    source: FrameSource = (source_spec if isinstance(source_spec, FrameSource)
                           else open_source(source_spec))
    if not source.open():
        raise RuntimeError(f"无法打开视频源: {source_spec}")

    pipeline = FramePipeline(width=cfg.width, roi=cfg.roi)
    estimator, backend, warnings = create_pose_estimator(
        prefer_mediapipe=cfg.prefer_mediapipe, model_path=cfg.model_path)
    model_ready = backend == "mediapipe"
    classifier = ActionClassifier(cfg.action_config())
    meter = LatencyMeter()

    interval_ms = 1000.0 / max(0.1, float(cfg.sample_fps))
    next_sample = 0.0
    frames = 0
    first_ts: float | None = None
    last_ts = 0.0
    truncated = False
    try:
        while True:
            if should_stop and should_stop():
                truncated = True
                break
            ok, frame, ts = source.read()
            if not ok or frame is None:
                break
            last_ts = ts
            if ts + 1e-6 < next_sample:      # 固定采样节拍，容忍文件时间戳浮点误差
                continue
            next_sample += interval_ms
            started = time.perf_counter()
            processed = pipeline.process(frame, ts)
            pose = estimator.estimate(processed)
            state = classifier.update(pose)
            meter.add((time.perf_counter() - started) * 1000.0)
            frames += 1
            if first_ts is None:
                first_ts = ts
            if frame_callback:
                frame_callback(processed, pose, state)
            if progress and frames % 10 == 0:
                progress({"frames": frames, "ts_ms": ts,
                          "state": classifier.state.value})
            if cfg.max_seconds and ts >= cfg.max_seconds * 1000.0:
                truncated = True
                break
    finally:
        estimator.close()
        source.close()

    classifier.finish(last_ts if frames else None)
    segments = classifier.segments()
    durations = duration_by_state(segments)
    ratios = ratio_by_state(segments)
    cycles = extract_cycles(segments, cfg)
    duration_s = ((last_ts - first_ts) / 1000.0) if first_ts is not None else 0.0
    if duration_s <= 0 and frames:
        duration_s = frames / max(0.1, float(cfg.sample_fps))
    return VisionResult(
        source=source.describe(), backend=backend, frames=frames,
        duration_s=duration_s,
        processed_fps=(frames / duration_s) if duration_s > 0 else 0.0,
        latency=meter.stats(), segments=segments, ratios=ratios,
        durations=durations, cycles=cycles, warnings=list(warnings),
        model_ready=model_ready, truncated=truncated,
        process_id=cfg.process_id, operator=cfg.operator)

__all__ = [
    "VisionConfig", "VisionResult", "CycleSegment",
    "run_vision_session", "extract_cycles", "VISION_STATUSES",
]
