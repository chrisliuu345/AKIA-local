"""
审计日志 — 公共入口
格式: [YYYY-MM-DD HH:MM:SS] operator: action detail
与 core/auth.py 内部 _audit 写入同一文件 (~/.qa_tool_audit.log)，格式保持一致。
"""

import os
from datetime import datetime

LOG_FILE = os.path.join(os.path.expanduser("~"), ".qa_tool_audit.log")


def audit(action: str, operator: str, detail: str = ""):
    """写入一条审计记录。内部吞异常，不影响主流程。"""
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {operator}: {action} {detail}\n")
    except Exception:
        pass
