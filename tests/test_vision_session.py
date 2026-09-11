"""Vision 会话端到端测试 — 合成视频 → 动作段 → 周期/占比 → 时间研究与工作抽样。"""
import json

import numpy as np
import pytest

pytest.importorskip("cv2")

from analysis.ie.work_sampling import WorkSamplingEngine
from analysis.vision.action import VISION_STATUSES
from analysis.vision.camera import FrameSource, SourceInfo
from analysis.vision.session import VisionConfig, run_vision_session


class _PhaseSource(FrameSource):
    """三阶段合成源: 原地运动(工作) → 匀速移动(走动) → 空场(离岗)。"""

    kind = "phase-test"

    def __init__(self, fps: float = 10.0):
        super().__init__("phase-test")
        self.fps = fps
        self.phases = ((0.0, 2.5, "pulse"), (2.5, 5.0, "move"),
                       (5.0, 7.0, "empty"))
        self.total = int(self.phases[-1][1] * fps)
        self.index = 0
        self.width, self.height = 320, 240

    def open(self) -> bool:
        self.index = 0
        self.info = SourceInfo(kind=self.kind, uri=self.uri, width=self.width,
                               height=self.height, fps=self.fps,
                               frames=self.total)
        self._opened = True
        return True

    def read(self):
        if not self._opened or self.index >= self.total:
            return False, None, self.index / self.fps * 1000.0
        t = self.index / self.fps
        ts = t * 1000.0
        frame = np.full((self.height, self.width, 3), 28, dtype=np.uint8)
        if t < 2.5:
            # 原地尺寸变化（作业动作）: 质心稳定、帧差活性持续
            size = int(42 + 12 * np.sin(self.index / 4.0))
            x, y = 160 - size // 2, 120 - size // 2
            frame[max(0, y):y + size, max(0, x):x + size] = 235
        elif t < 5.0:
            # 匀速移动：伴随帧差边缘，质心速度足够触发走动
            ratio = (t - 2.5) / 2.5
            x = 10 + int((300 - 40 - 10) * ratio)
            frame[100:140, x:x + 40] = 235
        else:
            pass
        self.index += 1
        return True, frame, ts


def _config():
    return VisionConfig(sample_fps=10.0, width=0, min_dwell_ms=300.0,
                        min_cycle_s=0.5, merge_gap_s=0.5,
                        prefer_mediapipe=False, process_id="P-视频",
                        operator="OP-视频")


def test_session_end_to_end_and_time_observations():
    progress = []
    result = run_vision_session(_PhaseSource(), _config(),
                                progress=progress.append)
    assert result.frames >= 60
    assert result.backend == "opencv-motion"
    assert result.model_ready is False
    assert result.ratios
    assert 95.0 <= sum(result.ratios.values()) <= 100.5
    assert result.ratios.get("working", 0) > 20
    assert result.ratios.get("walking", 0) > 10
    assert result.cycles, "应至少切出一个工作周期"
    assert result.cycles[0].duration_s >= 0.5
    assert progress

    observations = result.to_time_observations()
    assert observations
    assert observations[0].process_id == "P-视频"
    assert observations[0].operator == "OP-视频"
    assert observations[0].observation_time > 0
    assert [o.cycle for o in observations] == list(range(1, len(observations) + 1))


def test_session_work_sampling_and_json():
    result = run_vision_session(_PhaseSource(), _config())
    labels = result.to_work_sampling_labels(per_second=2.0)
    assert labels
    assert set(labels) <= {"工作", "空闲", "走动", "搬运", "离岗"}
    ratios = WorkSamplingEngine.calculate_ratios(labels, statuses=VISION_STATUSES)
    assert ratios["_total"] == len(labels)
    assert ratios["ratios"]["working"]["count"] > 0
    assert ratios["ratios"]["working"]["label"] == "工作"
    payload = json.dumps(result.to_dict(), ensure_ascii=False)
    assert "segments" in payload and "cycles" in payload


def test_session_truncates_at_max_seconds():
    config = _config()
    config.max_seconds = 1.0
    result = run_vision_session(_PhaseSource(), config)
    assert result.truncated is True
    assert result.duration_s <= 1.2
