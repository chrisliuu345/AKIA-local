"""姿态估计 — MediaPipe Tasks API（主路径）+ OpenCV 运动特征（降级路径）。

MediaPipe 1.0 起已移除旧 `mp.solutions` API，本模块使用 Tasks API 与
外部 `pose_landmarker_lite.task` 模型（经 model_store 校验/按需下载）；
模型或依赖缺失时自动降级为运动特征，不影响会话可用性。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from analysis.vision import mediapipe_available
from analysis.vision.camera import require_cv2
from analysis.vision.model_store import pose_model_path, verify_pose_model
from analysis.vision.processor import ProcessedFrame

# MediaPipe Pose 关键点索引
_WRISTS = (15, 16)
_SHOULDERS = (11, 12)
_HIPS = (23, 24)


@dataclass
class PoseFrame:
    ts_ms: float
    person_present: bool
    backend: str
    landmarks: list[tuple[float, float, float, float]] = field(default_factory=list)
    bbox: tuple[float, float, float, float] | None = None   # x, y, w, h（像素）
    centroid: tuple[float, float] | None = None
    motion_energy: float = 0.0
    activity_energy: float = 0.0
    speed_px_s: float = 0.0
    arm_swing: float = 0.0
    wrists_low: bool = False


class PoseEstimator:
    backend = "none"

    def estimate(self, processed: ProcessedFrame) -> PoseFrame:
        raise NotImplementedError

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


class MotionFallbackPoseEstimator(PoseEstimator):
    """OpenCV 运动特征路径：仅用前景掩码/质心/速度，无骨架关键点。"""

    backend = "opencv-motion"

    def __init__(self, min_motion: float = 0.0015, hold_ms: float = 2000.0):
        self.min_motion = float(min_motion)
        self.hold_ms = float(hold_ms)
        self._last_seen: float | None = None

    def estimate(self, processed: ProcessedFrame) -> PoseFrame:
        visible = (processed.bbox is not None
                   and processed.motion_energy >= self.min_motion)
        if visible:
            self._last_seen = processed.ts_ms
        present = visible or (
            self._last_seen is not None
            and processed.ts_ms - self._last_seen <= self.hold_ms)
        return PoseFrame(ts_ms=processed.ts_ms, person_present=present,
                         backend=self.backend, bbox=processed.bbox,
                         centroid=processed.centroid,
                         motion_energy=processed.motion_energy,
                         activity_energy=processed.activity_energy,
                         speed_px_s=processed.speed_px_s)


class MediaPipePoseEstimator(PoseEstimator):
    """MediaPipe Tasks PoseLandmarker（VIDEO 模式，33 关键点）。"""

    backend = "mediapipe"

    def __init__(self, model_path: str | Path | None = None,
                 min_visibility: float = 0.5, num_poses: int = 1):
        self.model_path = Path(model_path) if model_path else pose_model_path()
        self.min_visibility = float(min_visibility)
        self.num_poses = int(num_poses)
        self._landmarker = None
        self._mp_image = None
        self._image_format = None
        self._last_ts = -1
        self._prev_wrists: tuple[float, float] | None = None
        self._arm_swing = 0.0

    def _ensure_ready(self):
        if self._landmarker is not None:
            return
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision as mp_vision

        if not self.model_path.is_file():
            raise FileNotFoundError(f"姿态模型不存在: {self.model_path}")
        options = mp_vision.PoseLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=str(self.model_path)),
            running_mode=mp_vision.RunningMode.VIDEO,
            num_poses=self.num_poses,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5)
        self._landmarker = mp_vision.PoseLandmarker.create_from_options(options)
        self._mp_image = mp.Image
        self._image_format = mp.ImageFormat.SRGB

    def estimate(self, processed: ProcessedFrame) -> PoseFrame:
        self._ensure_ready()
        cv2 = require_cv2()
        rgb = cv2.cvtColor(processed.frame, cv2.COLOR_BGR2RGB)
        rgb = np.ascontiguousarray(rgb)
        image = self._mp_image(image_format=self._image_format, data=rgb)
        ts = int(max(processed.ts_ms, self._last_ts + 1))
        self._last_ts = ts
        result = self._landmarker.detect_for_video(image, ts)
        if not result.pose_landmarks:
            self._arm_swing *= 0.6
            return PoseFrame(ts_ms=processed.ts_ms, person_present=False,
                             backend=self.backend,
                             motion_energy=processed.motion_energy,
                             activity_energy=processed.activity_energy,
                             speed_px_s=processed.speed_px_s,
                             arm_swing=self._arm_swing)
        landmarks = result.pose_landmarks[0]
        height, width = processed.frame.shape[:2]
        points = [(float(lm.x), float(lm.y), float(lm.z),
                   float(getattr(lm, "visibility", 1.0))) for lm in landmarks]
        visible = [(x, y) for x, y, _z, v in points if v >= self.min_visibility]
        if len(visible) < 4:
            return PoseFrame(ts_ms=processed.ts_ms, person_present=False,
                             backend=self.backend, landmarks=points,
                             motion_energy=processed.motion_energy,
                             activity_energy=processed.activity_energy,
                             speed_px_s=processed.speed_px_s)
        xs = [p[0] * width for p in visible]
        ys = [p[1] * height for p in visible]
        bbox = (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
        centroid = (float(np.mean(xs)), float(np.mean(ys)))
        self._update_arm_metrics(points, width, height)
        return PoseFrame(ts_ms=processed.ts_ms, person_present=True,
                         backend=self.backend, landmarks=points, bbox=bbox,
                         centroid=centroid,
                         motion_energy=processed.motion_energy,
                         activity_energy=processed.activity_energy,
                         speed_px_s=processed.speed_px_s,
                         arm_swing=self._arm_swing,
                         wrists_low=self._wrists_low(points, height))

    def _update_arm_metrics(self, points, width: float, height: float):
        wrists = [points[i] for i in _WRISTS if points[i][3] >= self.min_visibility]
        if not wrists:
            self._arm_swing *= 0.7
            self._prev_wrists = None
            return
        current = (float(np.mean([w[0] * width for w in wrists])),
                   float(np.mean([w[1] * height for w in wrists])))
        torso = self._torso_length(points, width, height)
        if self._prev_wrists is not None and torso > 1.0:
            moved = float(np.hypot(current[0] - self._prev_wrists[0],
                                   current[1] - self._prev_wrists[1]))
            self._arm_swing = min(3.0, 0.4 * self._arm_swing + 0.6 * (moved / torso))
        self._prev_wrists = current

    def _torso_length(self, points, width: float, height: float) -> float:
        try:
            shoulder = np.mean([[points[i][0] * width, points[i][1] * height]
                                for i in _SHOULDERS], axis=0)
            hip = np.mean([[points[i][0] * width, points[i][1] * height]
                           for i in _HIPS], axis=0)
            return float(np.hypot(shoulder[0] - hip[0], shoulder[1] - hip[1]))
        except Exception:
            return 0.0

    @staticmethod
    def _wrists_low(points, height: float) -> bool:
        wrists = [points[i] for i in _WRISTS]
        if any(w[3] < 0.3 for w in wrists):
            return False
        hip_y = float(np.mean([points[i][1] * height for i in _HIPS]))
        return all(w[1] * height >= hip_y - 0.05 * height for w in wrists)

    def close(self):
        if self._landmarker is not None:
            try:
                self._landmarker.close()
            except Exception:
                pass
            self._landmarker = None


def create_pose_estimator(prefer_mediapipe: bool = True,
                          model_path: str | Path | None = None,
                          min_visibility: float = 0.5):
    """返回 (estimator, backend, warnings)；MediaPipe 不可用时降级。"""
    warnings: list[str] = []
    if prefer_mediapipe:
        if not mediapipe_available():
            warnings.append("未安装 mediapipe（可选）— 已降级为 OpenCV 运动特征")
        else:
            path = Path(model_path) if model_path else pose_model_path()
            if not path.is_file():
                warnings.append("未找到姿态模型（可在设置中下载）— "
                                "已降级为 OpenCV 运动特征")
            elif not verify_pose_model(path):
                warnings.append("姿态模型校验失败 — 已降级为 OpenCV 运动特征")
            else:
                try:
                    estimator = MediaPipePoseEstimator(path, min_visibility=min_visibility)
                    estimator._ensure_ready()
                    return estimator, estimator.backend, warnings
                except Exception as e:
                    warnings.append(f"MediaPipe 初始化失败（{e}）— "
                                    "已降级为 OpenCV 运动特征")
    return MotionFallbackPoseEstimator(), "opencv-motion", warnings
