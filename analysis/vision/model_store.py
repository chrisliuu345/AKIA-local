"""MediaPipe 姿态模型管理 — 按需下载 + SHA256 校验（v3.8.0 P3）。

模型（pose_landmarker_lite，约 5.6MB）不进入主安装包与仓库：
  - 默认位置 `~/.qa_tool_models/pose_landmarker_lite.task`
  - 可设 `QA_TOOL_MODELS_DIR` 覆盖目录，或 `QA_TOOL_POSE_MODEL` 直接指定文件
  - 离线环境手动放置亦可，校验失败视为不可用并降级 OpenCV 路径
下载始终由显式调用触发（UI 按钮/工具），不会静默联网。
"""
from __future__ import annotations

import hashlib
import os
import urllib.request
from pathlib import Path
from typing import Callable

MODEL_FILENAME = "pose_landmarker_lite.task"
MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
             "pose_landmarker_lite/float16/latest/pose_landmarker_lite.task")
MODEL_SHA256 = "59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a"


def models_dir() -> Path:
    override = os.environ.get("QA_TOOL_MODELS_DIR", "").strip()
    base = Path(override) if override else Path.home() / ".qa_tool_models"
    return base


def pose_model_path() -> Path:
    override = os.environ.get("QA_TOOL_POSE_MODEL", "").strip()
    if override:
        return Path(override)
    return models_dir() / MODEL_FILENAME


def sha256_file(path: Path | str, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def verify_pose_model(path: Path | str | None = None) -> bool:
    """文件存在且 SHA256 与官方 lite 模型一致。"""
    target = Path(path) if path else pose_model_path()
    try:
        if not target.is_file() or target.stat().st_size < 1_000_000:
            return False
        return sha256_file(target) == MODEL_SHA256
    except OSError:
        return False


def download_pose_model(dest: Path | str | None = None,
                        progress: Callable[[int, int], None] | None = None,
                        url: str | None = None,
                        timeout: float = 60.0) -> Path:
    """下载并校验模型；失败清理半成品并抛 RuntimeError。"""
    target = Path(dest) if dest else pose_model_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_suffix(target.suffix + ".part")
    source = url or MODEL_URL
    try:
        with urllib.request.urlopen(source, timeout=timeout) as resp:
            total = int(resp.headers.get("Content-Length") or 0)
            done = 0
            with open(part, "wb") as out:
                while True:
                    chunk = resp.read(256 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
                    done += len(chunk)
                    if progress:
                        progress(done, total)
    except Exception as e:
        part.unlink(missing_ok=True)
        raise RuntimeError(f"姿态模型下载失败: {e}") from e
    if not verify_pose_model(part):
        part.unlink(missing_ok=True)
        raise RuntimeError("姿态模型校验失败（SHA256 不匹配），请重试或手动放置模型文件")
    part.replace(target)
    return target
