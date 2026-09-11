"""相机 / 视频源抽象 — 文件 · USB · RTSP · MJPEG · 合成源。

纯 Python + 可选 OpenCV（惰性导入）；无 Qt，可在 analysis 层与 CI 直接使用。
时间戳约定:
  - 文件/合成源使用帧序号换算（可复现，便于测试）
  - USB/RTSP/MJPEG 使用墙钟（实时流无固定帧率）
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

import numpy as np

from analysis.vision import INSTALL_HINT, VisionDependencyError

VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".m4v",
              ".mpg", ".mpeg", ".wmv", ".flv", ".ts"}


def require_cv2():
    """返回 cv2；未安装时抛带安装指引的异常。"""
    try:
        import cv2
    except ImportError as e:
        raise VisionDependencyError(
            f"Vision 需要 OpenCV（{INSTALL_HINT}）") from e
    return cv2


@dataclass
class SourceInfo:
    kind: str
    uri: str
    width: int = 0
    height: int = 0
    fps: float = 0.0
    frames: int = 0

    def to_dict(self) -> dict:
        return {"kind": self.kind, "uri": self.uri, "width": self.width,
                "height": self.height, "fps": round(self.fps, 3),
                "frames": self.frames}


class FrameSource:
    """视频源接口 — open/read/close + 上下文管理。"""

    kind = "source"

    def __init__(self, uri: Any = ""):
        self.uri = uri
        self._opened = False
        self.info = SourceInfo(kind=self.kind, uri=str(uri))

    @property
    def is_open(self) -> bool:
        return self._opened

    def open(self) -> bool:
        raise NotImplementedError

    def read(self) -> tuple[bool, np.ndarray | None, float]:
        """返回 (ok, frame_bgr, timestamp_ms)。"""
        raise NotImplementedError

    def close(self):
        self._opened = False

    def describe(self) -> str:
        info = self.info
        size = f"{info.width}x{info.height}" if info.width else "未知分辨率"
        return f"{self.kind}: {self.uri}（{size}）"

    def __enter__(self):
        if not self.open():
            raise RuntimeError(f"无法打开视频源: {self.uri}")
        return self

    def __exit__(self, *exc):
        self.close()
        return False


class OpenCVFrameSource(FrameSource):
    """OpenCV VideoCapture 通用实现（文件/设备/网络流共用）。"""

    kind = "opencv"

    def __init__(self, uri: Any, *, width: int | None = None,
                 height: int | None = None, fps: float | None = None,
                 loop: bool = False, wall_clock: bool = False):
        super().__init__(uri)
        self._cap = None
        self._index = 0
        self._t0 = 0.0
        self._declared = {"width": width, "height": height, "fps": fps}
        self._loop = loop
        self._wall_clock = wall_clock

    def open(self) -> bool:
        cv2 = require_cv2()
        target = self.uri
        if isinstance(target, str) and target.isdigit():
            target = int(target)
        cap = cv2.VideoCapture(target)
        if not cap.isOpened():
            cap.release()
            return False
        if self._declared["width"]:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, float(self._declared["width"]))
        if self._declared["height"]:
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, float(self._declared["height"]))
        if self._declared["fps"]:
            cap.set(cv2.CAP_PROP_FPS, float(self._declared["fps"]))
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        self.info = SourceInfo(
            kind=self.kind, uri=str(self.uri),
            width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0),
            height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0),
            fps=fps,
            frames=int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0),
        )
        self._cap = cap
        self._t0 = time.monotonic()
        self._index = 0
        self._opened = True
        return True

    def read(self) -> tuple[bool, np.ndarray | None, float]:
        if not self._opened or self._cap is None:
            return False, None, 0.0
        ok, frame = self._cap.read()
        if not ok and self._loop:
            cv2 = require_cv2()
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = self._cap.read()
        if not ok:
            return False, None, self._timestamp()
        ts = self._timestamp()
        self._index += 1
        return True, frame, ts

    def _timestamp(self) -> float:
        if self._wall_clock or self.info.fps <= 0:
            return (time.monotonic() - self._t0) * 1000.0
        return self._index / self.info.fps * 1000.0

    def close(self):
        if self._cap is not None:
            self._cap.release()
        self._cap = None
        super().close()


class FileVideoSource(OpenCVFrameSource):
    kind = "file"

    def __init__(self, path: str, *, loop: bool = False, **kwargs):
        super().__init__(path, loop=loop, wall_clock=False, **kwargs)


class USBCameraSource(OpenCVFrameSource):
    kind = "usb"

    def __init__(self, index: int = 0, **kwargs):
        super().__init__(int(index), wall_clock=True, **kwargs)


class RTSPVideoSource(OpenCVFrameSource):
    kind = "rtsp"

    def __init__(self, url: str, **kwargs):
        super().__init__(url, wall_clock=True, **kwargs)


class MJPEGSource(OpenCVFrameSource):
    kind = "mjpeg"

    def __init__(self, url: str, **kwargs):
        super().__init__(url, wall_clock=True, **kwargs)


class SyntheticSource(FrameSource):
    """合成视频源 — 无 OpenCV 也可生成，用于 CI/演示/性能基准。

    pattern: moving_square（匀速移动 → 走动）·
             static_square（静止 → 空闲/工作）·
             pulse_square（原地小幅运动 → 工作）
    """

    kind = "synthetic"

    def __init__(self, width: int = 320, height: int = 240,
                 fps: float = 25.0, duration_s: float = 5.0,
                 pattern: str = "moving_square", square: int = 40,
                 amplitude: int = 6):
        super().__init__(f"synthetic:{pattern}")
        self.width, self.height = int(width), int(height)
        self.fps = float(fps)
        self.duration_s = float(duration_s)
        self.pattern = pattern
        self.square = int(square)
        self.amplitude = int(amplitude)
        self._total = max(1, int(self.fps * self.duration_s))
        self._index = 0

    def open(self) -> bool:
        self._index = 0
        self.info = SourceInfo(kind=self.kind, uri=str(self.uri),
                               width=self.width, height=self.height,
                               fps=self.fps, frames=self._total)
        self._opened = True
        return True

    def read(self) -> tuple[bool, np.ndarray | None, float]:
        if not self._opened or self._index >= self._total:
            return False, None, self._index / self.fps * 1000.0 if self.fps else 0.0
        frame = self._render(self._index)
        ts = self._index / self.fps * 1000.0
        self._index += 1
        return True, frame, ts

    def _render(self, idx: int) -> np.ndarray:
        frame = np.full((self.height, self.width, 3), 28, dtype=np.uint8)
        s = min(self.square, self.height, self.width)
        y = max(0, (self.height - s) // 2)
        span = max(1, self.width - s - 2)
        if self.pattern == "moving_square":
            x = 2 + int(span * (idx / max(1, self._total - 1)))
        elif self.pattern == "pulse_square":
            x = 2 + span // 2 + int(self.amplitude * np.sin(idx / 3.0))
        else:                                   # static_square
            x = 2 + span // 2
        x = max(0, min(self.width - s, x))
        frame[y:y + s, x:x + s] = 235
        return frame

    def close(self):
        super().close()


def open_source(spec: Any, **kwargs) -> FrameSource:
    """按规格创建视频源（不自动 open，便于调用方处理失败）。"""
    if isinstance(spec, FrameSource):
        return spec
    if isinstance(spec, int):
        return USBCameraSource(spec, **kwargs)
    text = str(spec or "").strip()
    low = text.lower()
    if low in ("synthetic", "demo"):
        return SyntheticSource(**kwargs)
    if text.isdigit() and len(text) <= 2:
        return USBCameraSource(int(text), **kwargs)
    if low.startswith("rtsp://"):
        return RTSPVideoSource(text, **kwargs)
    if low.startswith(("http://", "https://")):
        return MJPEGSource(text, **kwargs)
    if os.path.isfile(text):
        return FileVideoSource(text, **kwargs)
    raise FileNotFoundError(f"视频源不存在: {text}")
