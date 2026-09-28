"""
审计日志 — 公共入口
格式: [YYYY-MM-DD HH:MM:SS] operator: action detail

设计: 审计写入**不得**中断业务操作（导入/导出/告警确认），因此失败时吞异常；
但"审计失败"本身必须可观测 —— 计入 ``write_failures()`` 并写 warning 日志。
"""

import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

LOG_FILE = os.path.join(os.path.expanduser("~"), ".qa_tool_audit.log")
_MAX_LOG_SIZE = 5 * 1024 * 1024

# 写入失败计数（不做 global 声明，避免跨模块状态误用）
_stats = {"write_failures": 0}


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
        _rotate_if_needed()
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {operator}: {action} {detail}\n")
    except Exception as e:  # 审计失败不得中断业务操作
        _stats["write_failures"] += 1
        logger.warning("审计写入失败（累计 %d 次）: %s", _stats["write_failures"], e)
