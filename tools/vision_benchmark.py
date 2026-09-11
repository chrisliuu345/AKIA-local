"""视频动作识别基准 — 与人工标注对比计算时长加权一致率（v3.8.0 P3 验收）。

用法:
  python tools/vision_benchmark.py --video clip.mp4 --labels labels.csv \
      --sample-fps 10 [--model PATH] [--json out.json] [--min-accuracy 0.85]
  python tools/vision_benchmark.py --demo            # 合成片段自检（CI 可用）

标签 CSV 列: start_ms,end_ms,state
  state 支持 working/idle/walking/carrying/away 或中文 工作/空闲/走动/搬运/离岗
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analysis.vision.action import ACTION_LABELS, ActionState  # noqa: E402
from analysis.vision.camera import FrameSource, SourceInfo  # noqa: E402
from analysis.vision.session import VisionConfig, run_vision_session  # noqa: E402

LABEL_TO_STATE = {state.value: state for state in ActionState}
LABEL_TO_STATE.update({label: state for state, label in ACTION_LABELS.items()})


@dataclass
class LabelInterval:
    start_ms: float
    end_ms: float
    state: ActionState

    @property
    def duration_s(self) -> float:
        return max(0.0, (self.end_ms - self.start_ms) / 1000.0)


def load_labels(path: str | Path) -> list[LabelInterval]:
    labels: list[LabelInterval] = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            raw = str(row.get("state") or row.get("状态") or "").strip().lower()
            state = LABEL_TO_STATE.get(raw)
            if state is None:
                raise ValueError(f"未知状态: {raw!r}（行 {row}）")
            labels.append(LabelInterval(float(row["start_ms"]), float(row["end_ms"]),
                                        state))
    if not labels:
        raise ValueError("标签文件为空")
    return labels


def evaluate(labels: list[LabelInterval], segments) -> dict:
    """时长加权一致率 + 混淆统计。"""
    total_ms = sum(lab.duration_s for lab in labels) * 1000.0
    correct_ms = 0.0
    confusion: dict[str, float] = {}
    per_state: dict[str, dict] = {}
    for lab in labels:
        entry = per_state.setdefault(lab.state.value,
                                     {"label": ACTION_LABELS[lab.state],
                                      "total_s": 0.0, "correct_s": 0.0})
        entry["total_s"] += lab.duration_s
        for seg in segments:
            overlap = (min(lab.end_ms, seg.end_ms)
                       - max(lab.start_ms, seg.start_ms))
            if overlap <= 0:
                continue
            if seg.state == lab.state:
                correct_ms += overlap
                entry["correct_s"] += overlap / 1000.0
            else:
                key = f"{lab.state.value}→{seg.state.value}"
                confusion[key] = confusion.get(key, 0.0) + overlap / 1000.0
    accuracy = (correct_ms / total_ms) if total_ms > 0 else 0.0
    for entry in per_state.values():
        entry["accuracy"] = round(
            entry["correct_s"] / entry["total_s"], 4) if entry["total_s"] else 0.0
        entry["total_s"] = round(entry["total_s"], 3)
        entry["correct_s"] = round(entry["correct_s"], 3)
    return {
        "accuracy": round(accuracy, 4),
        "total_labeled_s": round(total_ms / 1000.0, 3),
        "correct_s": round(correct_ms / 1000.0, 3),
        "per_state": per_state,
        "confusion_s": {k: round(v, 3) for k, v in
                        sorted(confusion.items(), key=lambda kv: -kv[1])},
    }


class _DemoSource(FrameSource):
    """演示片段: 原地作业 0-2.5s → 匀速走动 2.5-5s → 空场 5-9s。"""

    kind = "benchmark-demo"
    DURATION_S = 9.0
    FPS = 15.0

    def __init__(self):
        super().__init__("benchmark-demo")
        self.index = 0
        self.width, self.height = 320, 240
        self.total = int(self.FPS * self.DURATION_S)

    def open(self) -> bool:
        self.index = 0
        self.info = SourceInfo(kind=self.kind, uri=self.uri, width=self.width,
                               height=self.height, fps=self.FPS, frames=self.total)
        self._opened = True
        return True

    def read(self):
        if not self._opened or self.index >= self.total:
            return False, None, self.index / self.FPS * 1000.0
        t = self.index / self.FPS
        frame = np.full((self.height, self.width, 3), 28, dtype=np.uint8)
        if t < 2.5:
            size = int(42 + 12 * np.sin(self.index / 4.0))
            x, y = 160 - size // 2, 120 - size // 2
            frame[y:y + size, x:x + size] = 235
        elif t < 5.0:
            x = 10 + int((300 - 40 - 10) * ((t - 2.5) / 2.5))
            frame[100:140, x:x + 40] = 235
        self.index += 1
        return True, frame, t * 1000.0


def demo_labels() -> list[LabelInterval]:
    return [LabelInterval(0, 2400, ActionState.WORKING),
            LabelInterval(2600, 5000, ActionState.WALKING),
            LabelInterval(7200, 9000, ActionState.AWAY)]


def run_demo_benchmark(sample_fps: float = 10.0) -> dict:
    config = VisionConfig(sample_fps=sample_fps, width=0,
                          prefer_mediapipe=False)
    result = run_vision_session(_DemoSource(), config)
    report = evaluate(demo_labels(), result.segments)
    report["source"] = "synthetic-demo"
    report["backend"] = result.backend
    return report


def _format_report(report: dict) -> str:
    lines = [f"动作识别一致率: {report['accuracy'] * 100:.1f}%"
             f"（标注 {report['total_labeled_s']:.1f}s，正确 "
             f"{report['correct_s']:.1f}s）"]
    for _key, entry in sorted(report.get("per_state", {}).items()):
        lines.append(f"  {entry['label']}: {entry['accuracy'] * 100:.1f}%"
                     f"（{entry['correct_s']:.1f}/{entry['total_s']:.1f}s）")
    if report.get("confusion_s"):
        lines.append("混淆(秒): " + " · ".join(
            f"{k} {v}" for k, v in list(report["confusion_s"].items())[:5]))
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Vision 动作识别基准")
    parser.add_argument("--video", help="本地视频文件")
    parser.add_argument("--labels", help="标签 CSV（start_ms,end_ms,state）")
    parser.add_argument("--demo", action="store_true", help="用合成片段自检")
    parser.add_argument("--sample-fps", type=float, default=10.0)
    parser.add_argument("--max-seconds", type=float, default=1800.0)
    parser.add_argument("--model", default="", help="姿态模型路径（可选）")
    parser.add_argument("--no-mediapipe", action="store_true")
    parser.add_argument("--json", default="", help="报告输出 JSON 路径")
    parser.add_argument("--min-accuracy", type=float, default=0.0,
                        help="低于该一致率时返回非零退出码")
    args = parser.parse_args(argv)

    if args.demo:
        report = run_demo_benchmark(args.sample_fps)
    else:
        if not args.video or not args.labels:
            parser.error("需要 --video 与 --labels（或使用 --demo）")
        config = VisionConfig(sample_fps=args.sample_fps, width=640,
                              max_seconds=args.max_seconds,
                              prefer_mediapipe=not args.no_mediapipe,
                              model_path=args.model or None)
        result = run_vision_session(args.video, config)
        report = evaluate(load_labels(args.labels), result.segments)
        report.update({"source": args.video, "backend": result.backend,
                       "frames": result.frames})
    print(_format_report(report))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"报告已写入 {args.json}")
    return 0 if report["accuracy"] >= args.min_accuracy else 1


if __name__ == "__main__":
    raise SystemExit(main())
