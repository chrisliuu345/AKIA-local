"""帧处理流水线测试 — 前景/质心/位移/延迟统计（OpenCV 路径）。"""
import numpy as np
import pytest

pytest.importorskip("cv2")

from analysis.vision.camera import SyntheticSource
from analysis.vision.processor import FramePipeline, LatencyMeter


def _frames(pattern: str, count: int = 40, size=(120, 160)):
    src = SyntheticSource(width=size[1], height=size[0], fps=10.0,
                          duration_s=count / 10.0, pattern=pattern)
    frames = []
    with src:
        while True:
            ok, frame, ts = src.read()
            if not ok:
                break
            frames.append((frame, ts))
    return frames


def _run(pattern: str, count: int = 40):
    pipeline = FramePipeline(width=0)
    out = [pipeline.process(frame, ts)
           for frame, ts in _frames(pattern, count=count)]
    return out


def test_moving_foreground_has_centroid_bbox_and_speed():
    processed = _run("moving_square")
    active = [p for p in processed if p.bbox is not None]
    assert active, "移动方块应有前景"
    assert processed[-1].speed_px_s > 0
    assert any(p.displacement_px > 0 for p in processed)


def test_moving_square_motion_beats_static_after_warmup():
    moving = _run("moving_square", count=80)[-20:]
    static = _run("static_square", count=80)[-20:]
    moving_energy = float(np.mean([p.motion_energy for p in moving]))
    static_energy = float(np.mean([p.motion_energy for p in static]))
    assert moving_energy > static_energy + 0.002
    assert moving_energy > 0.005


def test_roi_crops_frame_and_resize_limits_width():
    frame = np.full((120, 320, 3), 30, dtype=np.uint8)
    processed = FramePipeline(width=160).process(frame, 0.0)
    assert processed.frame.shape[1] == 160
    assert processed.frame.shape[0] == 60
    cropped = FramePipeline(width=0, roi=(10, 10, 100, 80)).process(frame, 0.0)
    assert cropped.frame.shape[1] == 100
    assert cropped.frame.shape[0] == 80
    assert cropped.mask is not None


def test_pipeline_reset_clears_state():
    pipeline = FramePipeline(width=0)
    frame, ts = _frames("moving_square", count=5)[-1]
    pipeline.process(frame, ts)
    assert pipeline._prev is not None
    pipeline.reset()
    assert pipeline._prev is None
    assert pipeline._subtractor is None


def test_activity_energy_detects_in_place_motion():
    """原地尺寸变化（模拟作业手部动作）: 质心几乎不动，但帧差活性高。"""
    pipeline = FramePipeline(width=0)
    out = []
    for i in range(60):
        frame = np.full((240, 320, 3), 28, dtype=np.uint8)
        size = int(42 + 12 * np.sin(i / 4.0))
        x, y = 160 - size // 2, 120 - size // 2
        frame[y:y + size, x:x + size] = 235
        out.append(pipeline.process(frame, i * 100.0))
    tail = out[-20:]
    activity = float(np.mean([p.activity_energy for p in tail]))
    speed = float(np.mean([p.speed_px_s for p in tail]))
    assert activity >= 0.0015
    assert speed < 40.0


def test_latency_meter_stats():
    meter = LatencyMeter(window=10)
    assert meter.stats()["count"] == 0
    for value in range(1, 11):
        meter.add(value)
    stats = meter.stats()
    assert stats["count"] == 10
    assert stats["avg_ms"] == 5.5
    assert stats["max_ms"] == 10.0
    assert 9.0 <= stats["p95_ms"] <= 10.0
