"""姿态估计与模型管理测试 — 降级路径必测；MediaPipe 真模型存在时才跑推理。"""
import hashlib
import os
from pathlib import Path

import numpy as np
import pytest

from analysis.vision import backend_info, mediapipe_available, vision_available
from analysis.vision import model_store
from analysis.vision.pose import (
    MediaPipePoseEstimator,
    MotionFallbackPoseEstimator,
    create_pose_estimator,
)
from analysis.vision.processor import ProcessedFrame


def _processed(ts=0.0, energy=0.02, bbox=(10, 10, 30, 40), speed=5.0):
    frame = np.zeros((120, 160, 3), dtype=np.uint8)
    gray = np.zeros((120, 160), dtype=np.uint8)
    mask = np.zeros((120, 160), dtype=np.uint8)
    mask[10:50, 10:40] = 255
    return ProcessedFrame(ts_ms=ts, frame=frame, gray=gray, mask=mask,
                          diff_mask=mask.copy(), motion_energy=energy,
                          activity_energy=energy, centroid=(25.0, 30.0),
                          bbox=bbox, displacement_px=1.0, speed_px_s=speed)


def test_motion_fallback_reports_presence_with_hold():
    estimator = MotionFallbackPoseEstimator(min_motion=0.001, hold_ms=2000)
    first = estimator.estimate(_processed(ts=0.0))
    assert first.person_present is True
    assert first.backend == "opencv-motion"
    empty = _processed(ts=1000.0, energy=0.0, bbox=None)
    empty.centroid = None
    assert estimator.estimate(empty).person_present is True     # 保持窗口内
    assert estimator.estimate(_processed(ts=2500.0, energy=0.0,
                                         bbox=None)).person_present is False


def test_create_estimator_falls_back_without_model(monkeypatch, tmp_path):
    monkeypatch.setenv("QA_TOOL_POSE_MODEL", str(tmp_path / "missing.task"))
    estimator, backend, warnings = create_pose_estimator(prefer_mediapipe=True)
    assert backend == "opencv-motion"
    assert isinstance(estimator, MotionFallbackPoseEstimator)
    assert warnings


def test_create_estimator_can_force_fallback():
    estimator, backend, warnings = create_pose_estimator(prefer_mediapipe=False)
    assert backend == "opencv-motion"
    assert warnings == []


def test_model_store_env_overrides(monkeypatch, tmp_path):
    monkeypatch.setenv("QA_TOOL_MODELS_DIR", str(tmp_path / "models"))
    assert model_store.models_dir() == tmp_path / "models"
    assert model_store.pose_model_path() == tmp_path / "models" / model_store.MODEL_FILENAME
    custom = tmp_path / "custom.task"
    monkeypatch.setenv("QA_TOOL_POSE_MODEL", str(custom))
    assert model_store.pose_model_path() == custom


def test_model_verify_rejects_corrupt_file(tmp_path):
    bad = tmp_path / "bad.task"
    bad.write_bytes(b"x" * 2_000_000)
    assert model_store.verify_pose_model(bad) is False
    assert model_store.sha256_file(bad) == hashlib.sha256(bad.read_bytes()).hexdigest()


def test_backend_info_shape():
    info = backend_info()
    assert set(info) >= {"available", "cv2", "mediapipe", "pose_model",
                         "backend", "install_hint"}
    assert vision_available() == info["cv2"]
    assert isinstance(mediapipe_available(), bool)


MODEL_CANDIDATES = [
    Path(os.environ.get("QA_TOOL_POSE_MODEL", "")),
    Path.home() / ".qa_tool_models" / model_store.MODEL_FILENAME,
    Path("/tmp") / model_store.MODEL_FILENAME,
]


@pytest.mark.skipif(not mediapipe_available(), reason="mediapipe 未安装")
@pytest.mark.skipif(not any(p.is_file() and model_store.verify_pose_model(p)
                            for p in MODEL_CANDIDATES if str(p)),
                    reason="本机无姿态模型（可选下载）")
def test_mediapipe_estimator_runs_on_synthetic_frame():
    model = next(p for p in MODEL_CANDIDATES if str(p) and p.is_file()
                 and model_store.verify_pose_model(p))
    estimator = MediaPipePoseEstimator(model)
    try:
        result = estimator.estimate(_processed(ts=0.0))
        assert result.backend == "mediapipe"
        assert isinstance(result.person_present, bool)
    finally:
        estimator.close()
