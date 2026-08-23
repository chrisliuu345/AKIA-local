"""
pytest 批量运行拦截器
防止 `pytest tests/` 全量执行导致系统死机（PySide6+scipy+numpy 并发初始化冲突）
"""
import os
import sys
import pytest


def pytest_collection_modifyitems(config, items):
    """检测目录批量运行并强制中断"""
    if os.environ.get("QA_TOOL_ALLOW_BATCH") == "1":
        return

    if len(items) <= 30:
        return

    # 检查命令行是否有显式文件参数（如 pytest tests/test_xxx.py）
    # sys.argv[1:] 中如果包含 .py 文件，说明是显式指定，不拦截
    argv = sys.argv[1:]
    has_file_args = any(arg.endswith('.py') for arg in argv)
    if has_file_args:
        return

    # 无显式文件参数 + 超过阈值 = 目录批量运行 → 拦截
    msg = (
        f"\n⛔ 批量运行检测：{len(items)} 个测试\n"
        f"   此项目批量运行 pytest tests/ 曾导致系统死机。\n"
        f"   原因：PySide6 + scipy + numpy 并发初始化在 Windows 下死锁\n"
        f"\n"
        f"   正确用法：\n"
        f"     pytest tests/test_xxx.py          # 单文件\n"
        f"     pytest tests/test_a.py tests/test_b.py  # 指定多个文件\n"
        f"\n"
        f"   如确需批量运行，设置环境变量：\n"
        f"     $env:QA_TOOL_ALLOW_BATCH=1; pytest tests/\n"
    )
    pytest.exit(msg, returncode=1)
