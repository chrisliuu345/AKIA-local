"""旧版数据兼容助手 — 仅用于一次性数据迁移，勿在新代码引用旧名。

旧版本的配置目录 / 会话 / 审计日志 / 插件目录仍可能存在于用户机器上。
这里集中放置"读旧、写新"的迁移逻辑，保证老用户升级后不丢数据。
"""
from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

from config.settings import APP_NAME

logger = logging.getLogger(f"{APP_NAME}.Legacy")

LEGACY_HOME_PREFIX = ".qa_tool_"


def env_first(new_name: str, legacy_name: str, default: str = "") -> str:
    """读取环境变量：新名优先，旧名回退（兼容 ``QA_TOOL_*`` 写法）。"""
    value = os.environ.get(new_name, "").strip()
    if value:
        return value
    return os.environ.get(legacy_name, "").strip() or default


def migrate_legacy_file(legacy: Path | str, target: Path | str) -> bool:
    """旧文件存在且新文件缺失时复制过去（保留旧文件，便于回退旧版）。"""
    legacy_path, target_path = Path(legacy), Path(target)
    if target_path.exists() or not legacy_path.exists():
        return False
    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(legacy_path, target_path)
        logger.info("已迁移旧版数据: %s → %s", legacy_path, target_path)
        return True
    except OSError as e:  # 迁移失败不阻断启动，但必须留痕
        logger.warning("旧版数据迁移失败（%s → %s）: %s", legacy_path, target_path, e)
        return False


def migrate_legacy_dir(legacy: Path | str, target: Path | str) -> bool:
    """旧目录存在且新目录缺失时整体复制过去（保留旧目录）。"""
    legacy_path, target_path = Path(legacy), Path(target)
    if target_path.exists() or not legacy_path.is_dir():
        return False
    try:
        shutil.copytree(legacy_path, target_path)
        logger.info("已迁移旧版数据目录: %s → %s", legacy_path, target_path)
        return True
    except OSError as e:  # 迁移失败不阻断启动，但必须留痕
        logger.warning("旧版数据目录迁移失败（%s → %s）: %s",
                       legacy_path, target_path, e)
        return False


def legacy_home_dir(name: str) -> Path:
    """旧版家目录数据路径，例如 ``legacy_home_dir("sessions")``。"""
    return Path.home() / f"{LEGACY_HOME_PREFIX}{name}"
