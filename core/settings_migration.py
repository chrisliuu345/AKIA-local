"""QSettings 品牌迁移 — 把旧组织（QA-Tool）下的设置复制到新组织（AKIA）。

涉及的组: MainWindow（窗口布局）/ RecentProjects / Dashboard / DBConnections /
Formulas / LLM。迁移只在新组尚无数据时进行，避免覆盖 AKIA 已有配置。
"""
from __future__ import annotations

import logging

from PySide6.QtCore import QSettings

from config.settings import APP_NAME, LEGACY_APP_NAME

logger = logging.getLogger(f"{APP_NAME}.SettingsMigration")

_FLAG = "brand_migration_done"

#: 旧版本使用过的全部 QSettings 组
LEGACY_GROUPS = (
    "MainWindow",
    "RecentProjects",
    "Dashboard",
    "DBConnections",
    "Formulas",
    "LLM",
)


def migrate_legacy_qsettings(groups: tuple[str, ...] | None = None) -> int:
    """把旧组织的键值复制到新组织，返回发生迁移的组数。"""
    migrated = 0
    for group in (groups or LEGACY_GROUPS):
        current = QSettings(APP_NAME, group)
        if current.value(_FLAG, False, type=bool):
            continue
        legacy = QSettings(LEGACY_APP_NAME, group)
        keys = legacy.allKeys()
        if keys and not current.allKeys():
            for key in keys:
                current.setValue(key, legacy.value(key))
            migrated += 1
            logger.info("已迁移旧版设置组 %s（%d 项）", group, len(keys))
        current.setValue(_FLAG, True)
        current.sync()
    return migrated
