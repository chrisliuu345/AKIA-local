"""
审计日志 — 公共入口
格式: [YYYY-MM-DD HH:MM:SS] operator: action detail
core/auth.py 通过此模块写入审计记录（W04 统一实现）。
"""

import os
from datetime import datetime

LOG_FILE = os.path.join(os.path.expanduser("~"), ".qa_tool_audit.log")
_MAX_LOG_SIZE = 5 * 1024 * 1024  # 5MB


def _rotate_if_needed():
    """日志超过 _MAX_LOG_SIZE 时轮转归档（W05）"""
    try:
        if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > _MAX_LOG_SIZE:
            backup = LOG_FILE + ".1"
            if os.path.exists(backup):
                os.remove(backup)
            os.rename(LOG_FILE, backup)
    except Exception:
        pass


def audit(action: str, operator: str, detail: str = ""):
    """写入一条审计记录。内部吞异常，不影响主流程。"""
    try:
        _rotate_if_needed()
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {operator}: {action} {detail}\n")
    except Exception:
        pass
