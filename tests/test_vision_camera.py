"""Vision 视频源测试 — 合成源/解析（无依赖路径）+ 文件源（OpenCV 路径）。"""
from pathlib import Path

import numpy as np
import pytest

from analysis.vision.camera import (
    FileVideoSource,
    FrameSource,
    SyntheticSource,
    USBCameraSource,
    open_source,
)


def test_synthetic_source_frames_and_timestamps():
    src = SyntheticSource(width=160, height=120, fps=25.0, duration_s=0.4)
    with src:
        assert src.is_open
        ok, frame, ts = src.read()
        assert ok and frame.shape == (120, 160, 3)
        assert ts == 0.0
        timestamps = [ts]
        while True:
            ok, _frame, ts = src.read()
            if not ok:
                break
            timestamps.append(ts)
        assert len(timestamps) == 10                       # 25fps × 0.4s
        assert timestamps == sorted(timestamps)
        assert timestamps[-1] == pytest.approx(360.0)
    assert not src.is_open


def test_synthetic_patterns_move_differently():
    def center_x(pattern):
        src = SyntheticSource(width=200, height=100, fps=10.0,
                              duration_s=1.0, pattern=pattern)
        xs = []
        with src:
            while True:
                ok, frame, _ts = src.read()
                if not ok:
                    break
                col = frame.mean(axis=(0, 2))
                xs.append(int(np.argmax(col)))
        return xs

    moving = center_x("moving_square")
    static = center_x("static_square")
    assert max(moving) - min(moving) > 50
    assert max(static) - min(static) <= 2


def test_open_source_dispatch():
    assert isinstance(open_source("synthetic"), SyntheticSource)
    assert isinstance(open_source(0), USBCameraSource)
    assert isinstance(open_source("2"), USBCameraSource)
    with pytest.raises(FileNotFoundError):
        open_source("/tmp/definitely-missing-video-file.mp4")


def test_frame_source_context_requires_open(tmp_path):
    class _NeverOpen(FrameSource):
        kind = "never"

        def open(self):
            return False

        def read(self):
            return False, None, 0.0

    with pytest.raises(RuntimeError):
        with _NeverOpen(str(tmp_path)):
            pass


def test_file_video_source_reads_written_mp4(tmp_path):
    cv2 = pytest.importorskip("cv2")
    path = tmp_path / "clip.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"),
                             10.0, (160, 120))
    assert writer.isOpened()
    for i in range(20):
        frame = np.full((120, 160, 3), 20, dtype=np.uint8)
        frame[40:80, 10 + i * 5:50 + i * 5] = 230
        writer.write(frame)
    writer.release()

    src = FileVideoSource(str(path))
    with src:
        count = 0
        last_ts = -1.0
        while True:
            ok, frame, ts = src.read()
            if not ok:
                break
            assert frame is not None
            assert ts > last_ts
            last_ts = ts
            count += 1
    assert count == 20
    assert src.info.width == 160
    assert src.info.height == 120
    assert Path(str(path)).exists()
