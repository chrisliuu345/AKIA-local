"""运行期数据目录 — 源码与冻结安装包统一解析。

AppImage 和 Program Files 均可能只读；用户数据必须落在平台用户目录，
不能把仓库内的 ``data/`` 布局原样带入安装后的写入路径。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from core.legacy import migrate_legacy_file

_PACKAGED_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def packaged_data_path(filename: str) -> Path:
    """旧版安装目录中的数据路径，仅用于迁移。"""
    return _PACKAGED_DATA_DIR / filename


def default_data_dir() -> Path:
    """返回可写数据目录；环境变量用于便携部署与测试隔离。"""
    override = (os.environ.get("AKIA_DATA_DIR")
                or os.environ.get("QA_TOOL_DATA_DIR"))
    if override:
        return Path(override).expanduser()
    if not getattr(sys, "frozen", False):
        return _PACKAGED_DATA_DIR
    if sys.platform == "win32":
        base = (os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
                or str(Path.home() / "AppData" / "Local"))
        return Path(base) / "AKIA"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "AKIA"
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "AKIA"


def default_data_path(filename: str) -> Path:
    """返回用户数据文件路径，并在首次升级时保留旧安装目录中的文件。"""
    if Path(filename).name != filename:
        raise ValueError("运行期数据文件名不能包含目录")
    target = default_data_dir() / filename
    legacy = packaged_data_path(filename)
    if target != legacy:
        migrate_legacy_file(legacy, target)
    return target
