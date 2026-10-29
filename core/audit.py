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


def audit(action: str, operator: str, detail: str = "") -> str:
    """写入一条审计记录。内部吞异常，不影响主流程；失败计入 write_failures()。

    返回尝试写入的那一行（不含换行）。写失败时仍返回该行，调用方可以把
    它留在内存结果上，和本机操作日志对照。
    """
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {operator}: {action} {detail}"
    try:
        _migrate_legacy_log()
        _rotate_if_needed()
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as e:  # 审计失败不得中断业务操作
        _stats["write_failures"] += 1
        logger.warning("审计写入失败（累计 %d 次）: %s", _stats["write_failures"], e)
    return line


# 模型调度审计：复用上面的操作日志，不另建配置或日志文件。
MODEL_CALL_ACTION = "model_call"
_INPUT_LIMIT = 240
# 与 LLMClient.config_summary() 对齐，只留可解释字段；key 是掩码后的密钥，不入库。
_TRACE_CONFIG_KEYS = ("provider", "label", "protocol", "model", "api_base", "available")


class ModelCallAudit:
    """一次模型调度的追溯结果：输入、模型、配置，以及操作日志中的那一行。"""

    def __init__(self, *, input: str, model: str, config: dict, outcome: str, line: str):
        self.input = input
        self.model = model
        self.config = dict(config)
        self.outcome = outcome
        self.line = line


def _public_base(url: str) -> str:
    """去掉 query，避免接口地址把密钥带进操作日志。"""
    return str(url or "").split("?", 1)[0]


def _trace_config(config: dict | None, model: str) -> dict:
    raw = dict(config or {})
    safe: dict = {}
    for key in _TRACE_CONFIG_KEYS:
        if key not in raw:
            continue
        value = raw[key]
        if key == "api_base":
            value = _public_base(str(value or ""))
        safe[key] = value
    if model and not safe.get("model"):
        safe["model"] = model
    return safe


def _fmt(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.1f}"
    if isinstance(value, int):
        return str(value)
    text = " ".join(str(value).split())
    return repr(text)


def record_model_call(operator: str, *, question: str, model: str,
                      config: dict | None = None, outcome: str = "",
                      elapsed_ms: float | None = None,
                      tools: list[str] | None = None) -> ModelCallAudit:
    """把一次已发生的模型调度写成操作日志，并返回可附在结果上的追溯记录。"""
    text = " ".join((question or "").split())
    if len(text) > _INPUT_LIMIT:
        text = text[:_INPUT_LIMIT] + "…"
    model_name = str(model or "")
    safe = _trace_config(config, model_name)
    if not model_name:
        model_name = str(safe.get("model") or "")
    parts = [f"input={_fmt(text)}", f"model={_fmt(model_name)}"]
    for key in ("provider", "label", "protocol", "api_base", "available"):
        if key in safe:
            parts.append(f"{key}={_fmt(safe[key])}")
    if outcome:
        parts.append(f"outcome={_fmt(outcome)}")
    if elapsed_ms is not None:
        parts.append(f"elapsed_ms={_fmt(float(elapsed_ms))}")
    if tools:
        parts.append(f"tools={_fmt(','.join(tools))}")
    detail = " ".join(parts)
    line = audit(MODEL_CALL_ACTION, operator or "user", detail)
    return ModelCallAudit(input=text, model=model_name, config=safe,
                          outcome=outcome, line=line)


def _line_action(line: str) -> str:
    body = line.split("] ", 1)[-1]
    if ": " not in body:
        return ""
    rest = body.split(": ", 1)[1]
    return rest.split(" ", 1)[0].strip()


def read_log(limit: int = 200, action: str | None = None) -> list[str]:
    """读取操作日志（旧→新）。文件缺失或不可读时返回空列表，不抛异常。"""
    try:
        with open(LOG_FILE, encoding="utf-8") as handle:
            raw_lines = handle.readlines()
    except Exception:
        return []
    lines = []
    for raw_line in raw_lines:
        line = raw_line.rstrip("\n")
        if not line.strip():
            continue
        if action is not None and _line_action(line) != action:
            continue
        lines.append(line)
    if limit <= 0:
        return []
    return lines[-int(limit):]
