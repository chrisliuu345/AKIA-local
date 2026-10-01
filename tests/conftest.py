"""
pytest 批量运行拦截器
防止 `pytest tests/` 全量执行导致系统死机（PySide6+scipy+numpy 并发初始化冲突）
"""
import os
import sys
from functools import lru_cache

import pytest

# 必须先于任何 PySide6 导入设置，确保无显示环境可用离屏平台
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session", autouse=True)
def _qt_application():
    """会话级 QApplication — 任何直接构造 QWidget 的测试都需要它，
    缺失时 PySide6 会 qFatal(SIGABRT) 终止整个 Python 进程"""
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        yield None
        return
    app = QApplication.instance() or QApplication([])
    yield app


@lru_cache(maxsize=1)
def _socket_available() -> bool:
    """能否绑定本地回环端口（受限沙箱 / 容器可能不允许）。"""
    import socket

    try:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
        return True
    except OSError:
        return False


@lru_cache(maxsize=1)
def _keyring_available() -> bool:
    """是否存在可用密钥环后端（加密→解密往返探测）。"""
    try:
        from core.secret_store import decrypt_secret, encrypt_secret

        token = encrypt_secret("akia-probe")
        return decrypt_secret(token) == "akia-probe"
    except Exception:
        return False


@lru_cache(maxsize=1)
def _server_available() -> bool:
    """是否安装可选实时看板依赖（FastAPI / uvicorn）。"""
    import importlib.util

    return (importlib.util.find_spec("fastapi") is not None
            and importlib.util.find_spec("uvicorn") is not None)


_CAPABILITY_MARKERS = {
    "requires_socket": (_socket_available,
                        "环境不允许本地 socket 绑定（受限沙箱 / 容器）"),
    "requires_keyring": (_keyring_available,
                         "无可用密钥环后端：可安装 keyrings.alt 或 gnome-keyring"),
    "requires_server": (_server_available,
                        "缺少可选依赖：pip install -r requirements-server.txt"),
}


def pytest_collection_modifyitems(config, items):
    """1) 按环境能力自动跳过标记用例；2) 拦截批量运行（多文件 / 目录）。"""
    for item in items:
        for marker_name, (check, reason) in _CAPABILITY_MARKERS.items():
            if item.get_closest_marker(marker_name) and not check():
                item.add_marker(pytest.mark.skip(reason=reason))

    if (os.environ.get("AKIA_ALLOW_BATCH") == "1"
            or os.environ.get("QA_TOOL_ALLOW_BATCH") == "1"):
        return

    # 只允许"显式指定单个文件"（如 pytest tests/test_xxx.py）
    file_args = [arg for arg in sys.argv[1:] if arg.endswith(".py")]
    if len(file_args) > 1:
        pytest.exit(
            f"\n⛔ 一次传入了 {len(file_args)} 个测试文件：PySide6 + scipy + numpy 在同一进程"
            "内并发初始化会死锁甚至 OOM（2026-09-22 实测）。\n"
            "   正确用法：逐文件执行，或用封装脚本 python tools/run_tests.py\n"
            "   如确需合并运行：AKIA_ALLOW_BATCH=1 pytest ...\n"
            "   （旧变量 QA_TOOL_ALLOW_BATCH=1 仍兼容）\n",
            returncode=1,
        )
    if file_args:
        return

    # 无显式文件参数 + 超过阈值 = 目录批量运行 → 拦截
    msg = (
        f"\n⛔ 批量运行检测：{len(items)} 个测试\n"
        f"   此项目批量运行 pytest tests/ 曾导致系统死机。\n"
        f"   原因：PySide6 + scipy + numpy 并发初始化在 Windows 下死锁\n"
        f"\n"
        f"   正确用法：\n"
        f"     pytest tests/test_xxx.py          # 单文件\n"
        f"     python tools/run_tests.py         # 逐文件全量（推荐）\n"
        f"\n"
        f"   如确需批量运行，设置环境变量：\n"
        f"     $env:AKIA_ALLOW_BATCH=1; pytest tests/\n"
        f"     # 旧变量 QA_TOOL_ALLOW_BATCH=1 仍兼容\n"
    )
    pytest.exit(msg, returncode=1)
