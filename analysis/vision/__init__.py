"""Vision 能力包（v3.8.0 P3）— 无 Qt，OpenCV/MediaPipe 均为可选依赖。

设计:
  - 主程序与 Agent 核心不依赖本包；未安装可选依赖时能力探测返回不可用，
    各入口给出安装指引而非 ImportError 崩溃。
  - 重依赖（cv2 / mediapipe）只在类初始化或函数内延迟导入，
    `import analysis.vision` 本身永远可用。
  - 无摄像头环境（CI/沙箱）走文件源或合成源，便于自动化测试。
"""
from __future__ import annotations

__all__ = [
    "VisionDependencyError",
    "INSTALL_HINT",
    "cv2_available",
    "mediapipe_available",
    "vision_available",
    "backend_info",
]

INSTALL_HINT = "pip install -r requirements-vision.txt"


class VisionDependencyError(RuntimeError):
    """可选依赖缺失 — 消息包含可执行的安装指引。"""


def cv2_available() -> bool:
    try:
        import cv2  # noqa: F401
        return True
    except Exception:
        return False


def mediapipe_available() -> bool:
    try:
        import mediapipe  # noqa: F401
        return True
    except Exception:
        return False


def vision_available() -> bool:
    """Vision 最低要求：OpenCV（MediaPipe 缺失时降级运动特征）。"""
    return cv2_available()


def backend_info() -> dict:
    """能力探测（供 UI/Agent 工具展示，不触发重初始化）。"""
    cv2_ok = cv2_available()
    mp_ok = mediapipe_available()
    model_ok = False
    model_path = ""
    if mp_ok:
        try:
            from analysis.vision.model_store import pose_model_path, verify_pose_model
            path = pose_model_path()
            model_path = str(path)
            model_ok = path.exists() and verify_pose_model(path)
        except Exception:
            model_ok = False
    if not cv2_ok:
        backend = "unavailable"
    elif mp_ok and model_ok:
        backend = "mediapipe"
    else:
        backend = "opencv-motion"
    return {
        "available": cv2_ok,
        "cv2": cv2_ok,
        "mediapipe": mp_ok,
        "pose_model": model_ok,
        "pose_model_path": model_path,
        "backend": backend,
        "install_hint": INSTALL_HINT if not cv2_ok else "",
    }
