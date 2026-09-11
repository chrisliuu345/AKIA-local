"""帧处理流水线 — 缩放 / ROI / 前景检测 / 运动特征 / 延迟统计（可选 OpenCV）。"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import numpy as np

from analysis.vision.camera import require_cv2


@dataclass
class ProcessedFrame:
    ts_ms: float
    frame: np.ndarray                      # 缩放/裁剪后的 BGR 帧
    gray: np.ndarray
    mask: np.ndarray | None                # 前景掩码（MOG2 ∪ 帧差，255=前景）
    diff_mask: np.ndarray | None           # 帧差掩码（原地动作敏感）
    motion_energy: float                   # 前景像素占比 0..1
    activity_energy: float                 # 帧差像素占比 0..1（=0 表示静态）
    centroid: tuple[float, float] | None   # 前景质心（像素）
    bbox: tuple[int, int, int, int] | None  # x, y, w, h
    displacement_px: float
    speed_px_s: float


class LatencyMeter:
    """滑动窗口延迟统计（毫秒）。"""

    def __init__(self, window: int = 300):
        self._samples: deque[float] = deque(maxlen=max(10, int(window)))

    def add(self, ms: float):
        self._samples.append(float(ms))

    @property
    def count(self) -> int:
        return len(self._samples)

    def stats(self) -> dict:
        if not self._samples:
            return {"avg_ms": 0.0, "p95_ms": 0.0, "max_ms": 0.0, "count": 0}
        values = sorted(self._samples)
        idx = min(len(values) - 1, int(round(0.95 * (len(values) - 1))))
        return {
            "avg_ms": round(float(np.mean(values)), 2),
            "p95_ms": round(float(values[idx]), 2),
            "max_ms": round(float(values[-1]), 2),
            "count": len(values),
        }


class FramePipeline:
    """把原始帧转成运动特征：前景掩码 → 质心/包围盒 → 位移/速度。"""

    def __init__(self, width: int = 640, roi: tuple[int, int, int, int] | None = None,
                 history: int = 120, var_threshold: float = 16.0,
                 min_area_ratio: float = 0.0008, detect_shadows: bool = False,
                 morph: bool = True):
        self.width = int(width or 0)
        self.roi = roi
        self.history = int(history)
        self.var_threshold = float(var_threshold)
        self.min_area_ratio = float(min_area_ratio)
        self.detect_shadows = bool(detect_shadows)
        self.morph = bool(morph)
        self._subtractor = None
        self._prev_gray: np.ndarray | None = None
        self._prev: tuple[float, float] | None = None
        self._prev_ts: float | None = None

    def reset(self):
        self._subtractor = None
        self._prev_gray = None
        self._prev = None
        self._prev_ts = None

    def process(self, frame: np.ndarray, ts_ms: float) -> ProcessedFrame:
        cv2 = require_cv2()
        if self._subtractor is None:
            self._subtractor = cv2.createBackgroundSubtractorMOG2(
                history=self.history, varThreshold=self.var_threshold,
                detectShadows=self.detect_shadows)
        img = self._resize(frame)
        img = self._crop(img)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        mask = self._subtractor.apply(gray)
        if self.detect_shadows:
            _, mask = cv2.threshold(mask, 200, 255, cv2.THRESH_BINARY)
        if self._prev_gray is None:
            diff_mask = np.zeros_like(gray)
        else:
            diff = cv2.absdiff(gray, self._prev_gray)
            _, diff_mask = cv2.threshold(diff, 12, 255, cv2.THRESH_BINARY)
        self._prev_gray = gray
        combined = cv2.bitwise_or(mask, diff_mask)
        if self.morph:
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            combined = cv2.morphologyEx(combined, cv2.MORPH_OPEN, kernel)
            combined = cv2.dilate(combined, None, iterations=1)

        motion_energy = float(np.count_nonzero(combined)) / float(combined.size)
        activity_energy = float(np.count_nonzero(diff_mask)) / float(diff_mask.size)
        bbox, centroid = self._largest_blob(cv2, combined)
        displacement = 0.0
        speed = 0.0
        if centroid is not None and self._prev is not None and self._prev_ts is not None:
            dt = max(1e-6, (ts_ms - self._prev_ts) / 1000.0)
            displacement = float(np.hypot(centroid[0] - self._prev[0],
                                          centroid[1] - self._prev[1]))
            speed = displacement / dt
        if centroid is not None:
            self._prev = centroid
            self._prev_ts = ts_ms
        return ProcessedFrame(ts_ms=ts_ms, frame=img, gray=gray, mask=combined,
                              diff_mask=diff_mask,
                              motion_energy=motion_energy,
                              activity_energy=activity_energy,
                              centroid=centroid,
                              bbox=bbox, displacement_px=displacement,
                              speed_px_s=speed)

    def _resize(self, frame: np.ndarray) -> np.ndarray:
        if not self.width or frame.shape[1] <= self.width:
            return frame
        cv2 = require_cv2()
        scale = self.width / float(frame.shape[1])
        size = (self.width, max(1, int(round(frame.shape[0] * scale))))
        return cv2.resize(frame, size, interpolation=cv2.INTER_AREA)

    def _crop(self, frame: np.ndarray) -> np.ndarray:
        if not self.roi:
            return frame
        x, y, w, h = self.roi
        height, width = frame.shape[:2]
        x0, y0 = max(0, int(x)), max(0, int(y))
        x1, y1 = min(width, x0 + int(w)), min(height, y0 + int(h))
        if x1 - x0 < 8 or y1 - y0 < 8:
            return frame
        return frame[y0:y1, x0:x1]

    def _largest_blob(self, cv2, mask: np.ndarray):
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None, None
        area_threshold = self.min_area_ratio * float(mask.size)
        best = None
        best_area = 0.0
        for contour in contours:
            area = float(cv2.contourArea(contour))
            if area >= area_threshold and area > best_area:
                best, best_area = contour, area
        if best is None:
            return None, None
        x, y, w, h = cv2.boundingRect(best)
        moments = cv2.moments(best)
        if moments["m00"] > 0:
            centroid = (moments["m10"] / moments["m00"], moments["m01"] / moments["m00"])
        else:
            centroid = (x + w / 2.0, y + h / 2.0)
        return (int(x), int(y), int(w), int(h)), (float(centroid[0]), float(centroid[1]))
