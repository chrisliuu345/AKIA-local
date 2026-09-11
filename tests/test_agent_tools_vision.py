"""QAM Harness Vision 工具测试 — 注册完整性 / 视频分析 / 时间研究 / 工作抽样。"""
import numpy as np
import pytest

pytest.importorskip("cv2")

from core.agent.tools import AgentContext, build_default_registry
from analysis.vision.camera import FrameSource, SourceInfo


class _PhaseSource(FrameSource):
    """原地作业(工作) → 匀速移动(走动) → 空场(离岗)，与界面引擎同源验证。"""

    kind = "phase-tool-test"

    def __init__(self, fps: float = 10.0, duration_s: float = 4.0):
        super().__init__("phase-tool-test")
        self.fps = fps
        self.total = int(fps * duration_s)
        self.index = 0
        self.width, self.height = 320, 240

    def open(self) -> bool:
        self.index = 0
        self.info = SourceInfo(kind=self.kind, uri=self.uri, width=self.width,
                               height=self.height, fps=self.fps, frames=self.total)
        self._opened = True
        return True

    def read(self):
        if not self._opened or self.index >= self.total:
            return False, None, self.index / self.fps * 1000.0
        t = self.index / self.fps
        ts = t * 1000.0
        frame = np.full((self.height, self.width, 3), 28, dtype=np.uint8)
        if t < 2.0:
            size = int(42 + 12 * np.sin(self.index / 4.0))
            x, y = 160 - size // 2, 120 - size // 2
            frame[y:y + size, x:x + size] = 235
        elif t < 3.0:
            x = 10 + int((300 - 40 - 10) * ((t - 2.0) / 1.0))
            frame[100:140, x:x + 40] = 235
        self.index += 1
        return True, frame, ts


@pytest.fixture
def registry():
    ctx = AgentContext(data_frames={})
    return build_default_registry(ctx), ctx


def test_vision_tools_registered(registry):
    reg, _ctx = registry
    for name in ("vision_status", "vision_analyze_video",
                 "vision_time_study", "vision_work_sampling"):
        assert name in reg
    assert len(reg) >= 34
    vision_specs = [s for s in reg.specs() if s.name.startswith("vision_")]
    assert len(vision_specs) == 4
    assert all(s.category == "视觉" for s in vision_specs)


def test_vision_status_tool(registry):
    reg, ctx = registry
    result = reg.call("vision_status", {}, ctx)
    assert result.ok is True
    assert result.data["backend"] in ("mediapipe", "opencv-motion")
    assert "后端" in result.text


def test_vision_analyze_video_tool(registry):
    reg, ctx = registry
    result = reg.call("vision_analyze_video",
                      {"path": _PhaseSource(), "sample_fps": 10.0,
                       "max_seconds": 10.0}, ctx)
    assert result.ok is True, result.error
    assert result.data["frames"] >= 35
    assert result.data["ratios"].get("working", 0) > 20
    assert result.data["cycles"]
    assert "状态占比" in result.text


def test_vision_time_study_tool(registry):
    reg, ctx = registry
    result = reg.call("vision_time_study",
                      {"path": _PhaseSource(), "sample_fps": 10.0,
                       "rating": 1.1, "allowance_pct": 10.0}, ctx)
    assert result.ok is True, result.error
    row = result.data["time_study"]["results"][0]
    assert row["avg_time"] > 0
    assert row["normal_time"] > row["avg_time"]
    assert row["standard_time"] > row["normal_time"]
    assert "标准" in result.text


def test_vision_work_sampling_tool(registry):
    reg, ctx = registry
    result = reg.call("vision_work_sampling",
                      {"path": _PhaseSource(), "sample_fps": 10.0,
                       "confidence": 0.95}, ctx)
    assert result.ok is True, result.error
    assert result.data["ratios"]["_total"] > 0
    assert result.data["utilization"]["productive_pct"] >= 0
    assert "利用率" in result.text


def test_missing_file_is_reported(registry):
    reg, ctx = registry
    result = reg.call("vision_analyze_video",
                      {"path": "/tmp/definitely-missing-vision.mp4"}, ctx)
    assert result.ok is False
    assert "不存在" in result.error


def test_status_reports_install_hint_without_cv2(registry, monkeypatch):
    import analysis.vision as vision_pkg

    monkeypatch.setattr(vision_pkg, "cv2_available", lambda: False)
    reg, ctx = registry
    result = reg.call("vision_status", {}, ctx)
    assert result.ok is False
    assert "requirements-vision" in result.error


def test_analysis_dependency_error_is_actionable(registry, monkeypatch):
    import analysis.vision.processor as processor_mod
    from analysis.vision import VisionDependencyError

    def _boom():
        raise VisionDependencyError("Vision 需要 OpenCV（pip install -r requirements-vision.txt）")

    monkeypatch.setattr(processor_mod, "require_cv2", _boom)
    reg, ctx = registry
    result = reg.call("vision_analyze_video",
                      {"path": "synthetic", "sample_fps": 5.0}, ctx)
    assert result.ok is False
    assert "requirements-vision" in result.error


def test_offline_router_extracts_video_path(registry):
    from core.agent.engine import AgentEngine

    reg, ctx = registry
    engine = AgentEngine(reg, context=ctx)
    reply = engine.respond("分析视频 /tmp/demo-clip.mp4 的动作")
    assert reply.tool_calls[0].name == "vision_analyze_video"
    assert reply.tool_calls[0].args["path"] == "/tmp/demo-clip.mp4"


def test_offline_router_runs_synthetic_demo(registry):
    from core.agent.engine import AgentEngine

    reg, ctx = registry
    engine = AgentEngine(reg, context=ctx)
    reply = engine.respond("用视频动作分析 synthetic 演示源")
    assert reply.tool_calls[0].name == "vision_analyze_video"
    assert reply.tool_calls[0].args["path"] == "synthetic"
    assert reply.tool_calls[0].ok is True
    assert "状态占比" in reply.text
