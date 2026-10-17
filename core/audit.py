"""
审计日志 — 公共入口
格式: [YYYY-MM-DD HH:MM:SS] operator: action detail

设计: 审计写入**不得**中断业务操作（导入/导出/告警确认），因此失败时吞异常；
但"审计失败"本身必须可观测 —— 计入 ``write_failures()`` 并写 warning 日志。
"""

import logging
import os
from datetime import datetime

from core.legacy import legacy_home_dir, migrate_legacy_file

logger = logging.getLogger(__name__)

_DEFAULT_LOG_FILE = os.path.join(os.path.expanduser("~"), ".akia_audit.log")
LOG_FILE = _DEFAULT_LOG_FILE
_MAX_LOG_SIZE = 5 * 1024 * 1024

# 写入失败计数（不做 global 声明，避免跨模块状态误用）
_stats = {"write_failures": 0}
_legacy_migrated = False


def _migrate_legacy_log() -> None:
    """首次写入前把旧版审计日志复制过来（保留旧文件）。"""
    global _legacy_migrated
    if _legacy_migrated:
        return
    _legacy_migrated = True
    if LOG_FILE != _DEFAULT_LOG_FILE:   # 测试/自定义路径不做旧日志搬迁
        return
    migrate_legacy_file(legacy_home_dir("audit.log"), LOG_FILE)


def write_failures() -> int:
    """审计写入失败累计次数（供自检/状态展示；>0 表示审计链有缺口）"""
    return _stats["write_failures"]


def _rotate_if_needed():
    """日志超过 _MAX_LOG_SIZE 时轮转归档（W05）"""
    try:
        if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > _MAX_LOG_SIZE:
            backup = LOG_FILE + ".1"
            if os.path.exists(backup):
                os.remove(backup)
            os.rename(LOG_FILE, backup)
    except Exception as e:  # 轮转失败不阻断审计写入（下次再试）
        logger.warning("审计日志轮转失败: %s", e)


def audit(action: str, operator: str, detail: str = ""):
    """写入一条审计记录。内部吞异常，不影响主流程；失败计入 write_failures()。"""
    try:
        _migrate_legacy_log()
        _rotate_if_needed()
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {operator}: {action} {detail}\n")
    except Exception as e:  # 审计失败不得中断业务操作
        _stats["write_failures"] += 1
        logger.warning("审计写入失败（累计 %d 次）: %s", _stats["write_failures"], e)
