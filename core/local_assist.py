"""用户主动启用的本机评分与异常辅助。

只引用已经算好的 SPC / 能力结果和未确认告警：不重算等级、不改判定、
不确认告警，也不调用外部模型。未启用时什么都不写进操作日志。
"""
from __future__ import annotations

from core.audit import record_local_run
from core.kpi_extractor import extract_metrics

LOCAL_METHOD = "local:spc-alerts"
_NOTE_LIMIT = 5


class AssistResult:
    """一次辅助的结果。confirmed 恒为 False：确认只能由人来做。"""

    def __init__(self, *, enabled: bool, text: str, input: str, model: str,
                 config: dict, audit_record: str, judgements: list | None = None):
        self.enabled = enabled
        self.text = text
        self.input = input
        self.model = model
        self.config = dict(config)
        self.audit_record = audit_record
        self.judgements = list(judgements or [])
        self.advisory = True
        self.confirmed = False

    def trace(self) -> dict:
        """阶段 1 的追溯形状。未调用外部模型时 model 是本机方法或空字符串。"""
        return {"input": self.input, "model": self.model,
                "config": dict(self.config), "audit_record": self.audit_record}


def _iter_analyses(analyses) -> list:
    if not analyses:
        return []
    if isinstance(analyses, dict):
        return [analyses[key] for key in sorted(analyses, key=str)]
    return [item for item in analyses if isinstance(item, dict)]


def _violation_notes(result: dict) -> list[str]:
    """抄已有判异描述，不另判规则。"""
    notes: list[str] = []
    groups = []
    for key, value in result.items():
        if key.endswith("_chart") and isinstance(value, dict):
            groups.append(value.get("violations"))
    top = result.get("violations")
    if isinstance(top, (list, tuple)):
        groups.append(top)
    for group in groups:
        if not isinstance(group, (list, tuple)):
            continue
        for item in group:
            if len(notes) >= _NOTE_LIMIT:
                return notes
            if isinstance(item, dict):
                desc = str(item.get("desc") or item.get("rule") or "").strip()
                point = item.get("point", "")
                if desc or point != "":
                    notes.append(f"第 {point} 点 {desc}".strip())
            elif item:
                notes.append(str(item))
    return notes


def _quote(entry: dict) -> dict | None:
    result = entry.get("result") if isinstance(entry.get("result"), dict) else {}
    atype = str(entry.get("analysis_type") or "analysis")
    metrics = extract_metrics({0: entry}).get(atype, {})
    quoted: dict = {"analysis_type": atype}
    for key in ("cpk", "ppk", "grade", "violations"):
        if metrics.get(key) is not None:
            quoted[key] = metrics[key]
    notes = _violation_notes(result)
    if notes:
        quoted["notes"] = notes
    if len(quoted) == 1:
        return None
    return quoted


def _alert_unacked(alert) -> bool:
    if isinstance(alert, dict):
        return not bool(alert.get("ack"))
    return not bool(getattr(alert, "ack", False))


def _alert_line(alert) -> str:
    summary = getattr(alert, "summary", None)
    if callable(summary):
        return str(summary())
    if isinstance(alert, dict):
        desc = alert.get("desc") or alert.get("kind") or "告警"
        where = "/".join(part for part in (alert.get("device"), alert.get("channel")) if part)
        prefix = f"{where} " if where else ""
        return f"{prefix}{desc}（未确认）"
    return str(alert)


def _format_quote(quoted: dict) -> str:
    bits = [str(quoted.get("analysis_type") or "分析")]
    if quoted.get("cpk") is not None:
        bits.append(f"Cpk={quoted['cpk']}")
    if quoted.get("ppk") is not None:
        bits.append(f"Ppk={quoted['ppk']}")
    if quoted.get("grade"):
        bits.append(f"等级 {quoted['grade']}")
    if quoted.get("violations") is not None:
        bits.append(f"判异点 {quoted['violations']} 个")
    line = "；".join(bits)
    notes = quoted.get("notes") or []
    if notes:
        line += "。" + "；".join(notes)
    return line


def advise(*, enabled: bool, analyses=None, alerts=None, question: str = "") -> AssistResult:
    """启用时给出建议并写入操作日志；关闭时不记录、不改输入数据。"""
    if not enabled:
        return AssistResult(
            enabled=False,
            text="辅助未启用。统计判定和告警确认保持原样。",
            input="",
            model="",
            config={"enabled": False, "external_model": False, "method": LOCAL_METHOD},
            audit_record="",
        )

    items = _iter_analyses(analyses)
    quotes = [quoted for entry in items if (quoted := _quote(entry)) is not None]
    pending = [alert for alert in (alerts or []) if _alert_unacked(alert)]
    violations = sum(int(item.get("violations") or 0) for item in quotes)

    lines = [
        "本机辅助（local:spc-alerts），不调用外部模型。以下内容只供参考。",
        "",
        "统计判定（原文，未改写）：",
    ]
    if quotes:
        lines.extend(f"- {_format_quote(item)}" for item in quotes)
    else:
        lines.append("- 当前没有已记录的 SPC 或能力结果，未另作评分。")
    other = len(items) - len(quotes)
    if other:
        lines.append(f"- 另有 {other} 项当前分析不含 SPC 或能力指标，未另作评分。")
    lines.append("")
    lines.append("未确认告警（仍须人工确认）：")
    if pending:
        lines.extend(f"- {_alert_line(alert)}" for alert in pending[:_NOTE_LIMIT])
    else:
        lines.append("- 无未确认告警。")
    lines.append("")
    lines.append("建议：")
    if violations:
        lines.append("- 请人工复核上述判异点，先确认测量系统和数据录入，再决定处置。")
    else:
        lines.append("- 统计结果未要求改判。请以分析页上的判定为准。")
    if pending:
        lines.append("- 告警请在告警中心确认。本辅助不会代为确认。")
    lines.append("- 能力等级以分析页已经给出的统计结果为准，这里不重新评级。")
    lines.append("")
    lines.append("辅助不替代统计判定，也不代替人工确认。")
    text = "\n".join(lines)

    question_text = question.strip() or (
        f"当前分析 {len(items)} 项，未确认告警 {len(pending)} 条")
    config = {
        "method": LOCAL_METHOD,
        "external_model": False,
        "enabled": True,
        "advisory": True,
        "sources": "current_analysis,alerts",
        "analysis_count": len(items),
        "alert_count": len(pending),
        "violations": violations,
    }
    recorded = record_local_run(
        "user", question=question_text, method=LOCAL_METHOD,
        config=config, outcome="advisory")
    return AssistResult(
        enabled=True,
        text=text,
        input=recorded.input,
        model=recorded.method,
        config=dict(recorded.config),
        audit_record=recorded.line,
        judgements=quotes,
    )
