"""告警自动立案 8D — 编排层（v4.4.0 B1）。

职责边界:
- critical 告警 → 8D 草稿 + ImprovementCase（D1 默认值 / D2 由快照与项目上下文
  生成 / D3、D4 留空待填）；快照进案例基线步骤，`alert_case_opened` 进证据账本；
- 去重与冷却：同一 ``rule_key``（设备+通道）在冷却窗口内（默认 30 分钟）合并为
  同案步骤，跨窗口新开案例；一案一号（`AlertCaseLink` 记录 alert→case 映射）；
- 纯逻辑层：不依赖 Qt、不依赖 ui（告警对象按属性/字典鸭子类型读取），
  案例创建通过 ``create_case`` 回调完成（主窗口负责注册与持久化）。

工作流编排（CaseWorkflow）与统计判定仍由既有引擎承担；本模块只决定
"何时立案、案怎么建、证据怎么留"。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, fields
from datetime import datetime
from typing import Any
from collections.abc import Callable, Iterable

from core.streaming.alert_journal import severity_rank
from core.time_utils import epoch_to_iso, now_iso, parse_iso

ALERT_CASE_SCHEMA_VERSION = "1"

#: 立案动作
ALERT_CASE_ACTIONS = ("opened", "merged", "ignored")
#: 严重度等级
ALERT_SEVERITIES = ("info", "warning", "critical")
#: 8D 草稿报告 ID 前缀（按告警 ID 稳定生成 → 重复触发幂等）
ALERT_REPORT_PREFIX = "8D-AUTO-"


def new_link_id() -> str:
    """链接 ID（本地时区时间 + 4 位随机后缀）。"""
    stamp = datetime.now().astimezone().strftime("%Y%m%d%H%M%S")
    return f"LNK-{stamp}-{uuid.uuid4().hex[:4]}"


def _attr(source: Any, name: str, default: Any = None) -> Any:
    """鸭子类型读取：对象属性或字典键。"""
    if isinstance(source, dict):
        return source.get(name, default)
    return getattr(source, name, default)


@dataclass(frozen=True)
class AlertSnapshot:
    """告警事实快照（立案基线的最小证据）。"""

    alert_id: str
    rule_key: str
    device: str
    channel: str
    kind: str
    value: float
    desc: str
    severity: str
    ts: str
    usl: float | None = None
    lsl: float | None = None
    rule_version: str = "alert-engine@1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "rule_key": self.rule_key,
            "device": self.device,
            "channel": self.channel,
            "kind": self.kind,
            "value": self.value,
            "desc": self.desc,
            "severity": self.severity,
            "ts": self.ts,
            "usl": self.usl,
            "lsl": self.lsl,
            "rule_version": self.rule_version,
        }

    @classmethod
    def from_event(cls, alert: Any) -> AlertSnapshot:
        """从 AlertEvent（或同构对象/字典）构建快照；时间统一为带时区 ISO-8601。"""
        device = str(_attr(alert, "device", "") or "").strip()
        channel = str(_attr(alert, "channel", "") or "").strip()
        if not device and not channel:
            raise ValueError("告警缺少设备/通道，无法立案")
        ts = _attr(alert, "ts", None)
        if isinstance(ts, (int, float)) and ts > 0:
            ts_iso = epoch_to_iso(float(ts))
        else:
            ts_iso = parse_iso(str(ts or ""), "ts", allow_naive=True).isoformat(
                timespec="seconds") if ts else now_iso()
        severity = str(_attr(alert, "severity", "warning") or "warning").strip().lower()
        if severity not in ALERT_SEVERITIES:
            raise ValueError(
                f"非法告警等级: {severity!r}（可选 {list(ALERT_SEVERITIES)}）")
        usl = _attr(alert, "usl", None)
        lsl = _attr(alert, "lsl", None)
        return cls(
            alert_id=str(_attr(alert, "id", "") or "").strip() or f"ALERT-{uuid.uuid4().hex[:8]}",
            rule_key=f"{device}|{channel}",
            device=device,
            channel=channel,
            kind=str(_attr(alert, "kind", "") or "").strip(),
            value=float(_attr(alert, "value", 0.0) or 0.0),
            desc=str(_attr(alert, "desc", "") or "").strip(),
            severity=severity,
            ts=ts_iso,
            usl=None if usl is None else float(usl),
            lsl=None if lsl is None else float(lsl),
            rule_version=str(_attr(alert, "rule_version", "") or "alert-engine@1"),
        )


@dataclass
class AlertCaseLink:
    """alert → case 映射（一案一号；同案合并的多条告警各留一条链接）。"""

    alert_id: str
    case_id: str
    rule_key: str
    severity: str
    at: str
    snapshot: dict[str, Any] = field(default_factory=dict)
    link_id: str = field(default_factory=new_link_id)
    schema_version: str = ALERT_CASE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != ALERT_CASE_SCHEMA_VERSION:
            raise ValueError(f"不支持的立案链接 schema 版本: {self.schema_version}")
        self.alert_id = str(self.alert_id or "").strip()
        self.case_id = str(self.case_id or "").strip()
        if not self.alert_id or not self.case_id:
            raise ValueError("立案链接必须同时提供 alert_id 与 case_id")
        self.rule_key = str(self.rule_key or "").strip()
        self.severity = str(self.severity or "").strip().lower()
        if self.severity not in ALERT_SEVERITIES:
            raise ValueError(f"非法告警等级: {self.severity!r}")
        self.at = parse_iso(self.at or now_iso(), "at").isoformat(timespec="seconds")
        if not isinstance(self.snapshot, dict):
            raise ValueError("立案链接 snapshot 必须为 dict")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "link_id": self.link_id,
            "alert_id": self.alert_id,
            "case_id": self.case_id,
            "rule_key": self.rule_key,
            "severity": self.severity,
            "at": self.at,
            "snapshot": dict(self.snapshot),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AlertCaseLink:
        if not isinstance(data, dict):
            raise ValueError("立案链接必须为 dict")
        schema = str(data.get("schema_version") or ALERT_CASE_SCHEMA_VERSION)
        if schema != ALERT_CASE_SCHEMA_VERSION:
            raise ValueError(f"不支持的立案链接 schema 版本: {schema}")
        allowed = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in allowed})


@dataclass
class AlertCasePolicy:
    """立案策略（默认值即 PLAN_v4.4.0 §8 决策 2/4）。"""

    severity_threshold: str = "critical"   # 达到或高于该等级才立案
    cooldown_s: float = 1800.0             # 同 rule_key 合并窗口（30 分钟）

    def __post_init__(self) -> None:
        self.severity_threshold = str(
            self.severity_threshold or "critical").strip().lower()
        if self.severity_threshold not in ALERT_SEVERITIES:
            raise ValueError(
                f"非法立案阈值等级: {self.severity_threshold!r}"
                f"（可选 {list(ALERT_SEVERITIES)}）")
        self.cooldown_s = float(self.cooldown_s)
        if self.cooldown_s < 0:
            raise ValueError(f"冷却窗口不能为负: {self.cooldown_s}")

    def admits(self, severity: str) -> bool:
        return severity_rank(str(severity or "")) >= severity_rank(
            self.severity_threshold)


@dataclass
class AlertCaseDecision:
    """一次立案评估结果（handle 的返回）。"""

    action: str
    case_id: str = ""
    title: str = ""
    rule_key: str = ""
    reason: str = ""
    link: AlertCaseLink | None = None

    def __post_init__(self) -> None:
        self.action = str(self.action or "").strip().lower()
        if self.action not in ALERT_CASE_ACTIONS:
            raise ValueError(
                f"非法立案动作: {self.action!r}（可选 {list(ALERT_CASE_ACTIONS)}）")
        self.case_id = str(self.case_id or "").strip()
        self.title = str(self.title or "").strip()
        self.rule_key = str(self.rule_key or "").strip()
        self.reason = str(self.reason or "").strip()


def _fmea_summary(item: Any) -> dict[str, str]:
    """FMEA 条目 → 摘要字典（对象属性或字典输入均可）。"""

    def pick(*names: str) -> str:
        for name in names:
            value = _attr(item, name, None)
            if value not in (None, ""):
                return str(value)
        return ""

    if isinstance(item, dict):
        return {str(k): str(v) for k, v in item.items()
                if isinstance(v, (str, int, float))}
    return {
        "function": pick("function", "功能"),
        "failure_mode": pick("failure_mode", "失效模式"),
        "effect": pick("effect", "影响", "后果"),
        "cause": pick("cause", "原因", "失效原因"),
    }


def _fmea_texts(item: Any) -> list[str]:
    if isinstance(item, dict):
        return [str(v) for v in item.values() if isinstance(v, (str, int, float))]
    return [str(getattr(item, name, "") or "")
            for name in ("function", "failure_mode", "effect", "cause",
                         "recommended_action")]


def collect_context_evidence(context: Any, snapshot: AlertSnapshot) -> dict[str, Any]:
    """从 ProjectContext 抓取相关质量特性与 FMEA 条目（匹配通道/设备名，均可为空）。"""
    evidence: dict[str, Any] = {"characteristic": None, "fmea_items": []}
    if context is None:
        return evidence
    token = snapshot.channel or snapshot.device
    for qc in list(getattr(context, "characteristics", []) or []):
        names = {str(getattr(qc, "id", "") or ""), str(getattr(qc, "name", "") or "")}
        if token and token in names:
            evidence["characteristic"] = {
                "id": str(getattr(qc, "id", "") or ""),
                "name": str(getattr(qc, "name", "") or ""),
                "usl": getattr(qc, "usl", None),
                "lsl": getattr(qc, "lsl", None),
                "target": getattr(qc, "target", None),
                "process": str(getattr(qc, "process", "") or ""),
            }
            break
    needles = [item for item in
               (token, (evidence["characteristic"] or {}).get("name")) if item]
    for item in list(getattr(context, "fmea_items", []) or []):
        texts = _fmea_texts(item)
        if any(needle and needle in text for needle in needles for text in texts):
            evidence["fmea_items"].append(_fmea_summary(item))
    return evidence


def build_8d_draft(snapshot: AlertSnapshot, evidence: dict[str, Any],
                   *, case_id: str) -> dict[str, Any]:
    """生成 8D 草稿（D1 默认值 + D2 快照/上下文生成；D3/D4 留空待填）。

    形状与 ``analysis.quality.eight_d_engine.EightDReport.to_dict()`` 对齐，
    额外携带 ``id`` / ``auto`` / ``case_id`` 供 8D Tab 与案例双向定位。
    """
    qc = evidence.get("characteristic") or {}
    specs = []
    if snapshot.usl is not None or qc.get("usl") is not None:
        specs.append(f"USL={snapshot.usl if snapshot.usl is not None else qc.get('usl')}")
    if snapshot.lsl is not None or qc.get("lsl") is not None:
        specs.append(f"LSL={snapshot.lsl if snapshot.lsl is not None else qc.get('lsl')}")
    spec_text = "，".join(specs)
    problem = (f"{snapshot.kind}: {snapshot.desc}；当前值 {snapshot.value:g}"
               + (f"；{spec_text}" if spec_text else ""))
    if qc.get("name"):
        problem += f"（特性: {qc['name']}）"
    fmea_hint = ""
    if evidence.get("fmea_items"):
        hints = [item.get("failure_mode") or item.get("cause") or ""
                 for item in evidence["fmea_items"][:3]]
        fmea_hint = "；相关 FMEA: " + "、".join(h for h in hints if h)
    return {
        "id": f"{ALERT_REPORT_PREFIX}{snapshot.alert_id}",
        "auto": True,
        "case_id": str(case_id),
        "title": f"自动立案：{snapshot.device}/{snapshot.channel} {snapshot.kind} 告警 8D",
        "product": str(qc.get("name") or qc.get("process") or ""),
        "customer": "",
        "created_at": snapshot.ts[:16].replace("T", " "),
        "steps": {
            "D1": {"team_leader": "", "members": "",
                   "date_started": snapshot.ts[:10]},
            "D2": {"problem_statement": problem + fmea_hint,
                   "what": snapshot.desc or snapshot.kind,
                   "where": f"{snapshot.device}/{snapshot.channel}",
                   "when": snapshot.ts,
                   "who": "", "why": "", "how": "",
                   "how_many": f"当前值 {snapshot.value:g}"},
            "D3": {"ica_description": "", "implementation_date": "",
                   "verified": False},
            "D4": {"fishbone_data": None, "five_why": "", "root_cause": ""},
            "D5": {"pca_items": [], "verification_method": ""},
            "D6": {"implementation_notes": "", "validation_result": "",
                   "validated_date": ""},
            "D7": {"preventive_actions": "", "standards_updated": "",
                   "training_completed": False},
            "D8": {"recognition_notes": "", "closure_date": ""},
        },
    }


class AlertCaseOrchestrator:
    """告警立案编排器（无 Qt；案例创建经 ``create_case`` 回调）。"""

    def __init__(self, *, ledger=None, context=None,
                 create_case: Callable[..., Any] | None = None,
                 case_lookup: Callable[[str], Any | None] | None = None,
                 policy: AlertCasePolicy | None = None,
                 clock: Callable[[], datetime] | None = None):
        self.ledger = ledger
        self.context = context
        self.create_case = create_case
        self.case_lookup = case_lookup
        self.policy = policy or AlertCasePolicy()
        self.links: list[AlertCaseLink] = []
        self._sessions: dict[str, tuple[str, datetime]] = {}
        self._clock = clock or (lambda: datetime.now().astimezone())

    # ------------------------------------------------------------ 查询
    def case_for_alert(self, alert_id: str) -> str | None:
        target = str(alert_id or "").strip()
        for link in reversed(self.links):
            if link.alert_id == target:
                return link.case_id
        return None

    def case_for_rule(self, rule_key: str) -> str | None:
        session = self._sessions.get(str(rule_key or "").strip())
        return session[0] if session else None

    def rebuild(self, workflows: Iterable[Any]) -> int:
        """从已加载案例重建会话与链接（应用重启后去重仍生效）。

        仅扫描带 ``auto_alert`` 标签的案例；步骤 ``result.alert`` 提供
        rule_key / alert_id / ts。返回重建的会话数。
        """
        restored = 0
        for workflow in workflows or []:
            case = getattr(workflow, "case", None)
            if case is None or "auto_alert" not in (case.tags or []):
                continue
            for step in case.steps or []:
                payload = (step.get("result") or {}).get("alert")
                if not isinstance(payload, dict):
                    continue
                rule_key = str(payload.get("rule_key") or "").strip()
                at = str(payload.get("ts") or step.get("at") or "")
                if not rule_key or not at:
                    continue
                try:
                    moment = parse_iso(at, "ts", allow_naive=True)
                except ValueError:
                    continue
                current = self._sessions.get(rule_key)
                if current is None or moment > current[1]:
                    self._sessions[rule_key] = (case.id, moment)
                self.links.append(AlertCaseLink(
                    alert_id=str(payload.get("alert_id") or step.get("at") or ""),
                    case_id=case.id, rule_key=rule_key,
                    severity=str(payload.get("severity") or "warning"),
                    at=moment.isoformat(timespec="seconds"),
                    snapshot=dict(payload)))
                restored += 1
        return restored

    # ------------------------------------------------------------ 编排
    def handle(self, alert: Any) -> AlertCaseDecision:
        """评估一条告警：立案 / 合并 / 忽略（确定性，可由时钟注入驱动测试）。"""
        snapshot = AlertSnapshot.from_event(alert)
        if not self.policy.admits(snapshot.severity):
            return AlertCaseDecision(
                "ignored", rule_key=snapshot.rule_key,
                reason=f"等级 {snapshot.severity} 未达立案阈值 "
                       f"{self.policy.severity_threshold}")
        now = self._clock()
        session = self._sessions.get(snapshot.rule_key)
        if session is not None:
            case_id, last_at = session
            if (now - last_at).total_seconds() <= self.policy.cooldown_s:
                workflow = self._lookup(case_id)
                if workflow is not None:
                    return self._merge(workflow, snapshot, now)
        return self._open(snapshot, now)

    # ------------------------------------------------------------ 内部
    def _lookup(self, case_id: str):
        if callable(self.case_lookup):
            try:
                return self.case_lookup(case_id)
            except Exception:  # 取数失败按"找不到"处理 → 新开案例
                return None
        return None

    def _merge(self, workflow, snapshot: AlertSnapshot,
               now: datetime) -> AlertCaseDecision:
        case = workflow.case
        step = workflow.record_step(
            "analyse",
            {"alert": snapshot.to_dict(), "merged": True},
            data_ref=f"alert:{snapshot.alert_id}",
            note=f"同类告警续报（{snapshot.device}/{snapshot.channel} "
                 f"{snapshot.kind}）：{snapshot.desc}")
        link = AlertCaseLink(
            alert_id=snapshot.alert_id, case_id=case.id,
            rule_key=snapshot.rule_key, severity=snapshot.severity,
            at=snapshot.ts, snapshot=snapshot.to_dict())
        self.links.append(link)
        self._sessions[snapshot.rule_key] = (case.id, parse_iso(snapshot.ts))
        return AlertCaseDecision("merged", case_id=case.id, title=case.title,
                                 rule_key=snapshot.rule_key,
                                 reason=f"并入现有案例（冷却窗口内）· 步骤 {step['phase']}",
                                 link=link)

    def _open(self, snapshot: AlertSnapshot, now: datetime) -> AlertCaseDecision:
        if not callable(self.create_case):
            raise RuntimeError("未配置 create_case 回调，无法自动立案")
        evidence = collect_context_evidence(self.context, snapshot)
        title = f"[自动立案] {snapshot.device}/{snapshot.channel} {snapshot.kind} 异常"
        workflow = self.create_case(title, product="", owner="")
        case = workflow.case
        for tag in ("auto_alert", f"alert:{snapshot.rule_key}"):
            if tag not in case.tags:
                case.tags.append(tag)
        case.evidence_required = True
        workflow.record_step(
            "baseline",
            {"alert": snapshot.to_dict(), "context": evidence},
            data_ref=f"alert:{snapshot.alert_id}",
            note="系统自动立案：告警快照进基线（D1–D3 见 8D 草稿）")
        report = build_8d_draft(snapshot, evidence, case_id=case.id)
        report_id = str(report["id"])
        if report_id not in case.report_refs:
            case.report_refs.append(report_id)
        if self.context is not None and hasattr(self.context, "upsert_eight_d_report"):
            self.context.upsert_eight_d_report(report, report_id=report_id)
        link = AlertCaseLink(
            alert_id=snapshot.alert_id, case_id=case.id,
            rule_key=snapshot.rule_key, severity=snapshot.severity,
            at=snapshot.ts, snapshot=snapshot.to_dict())
        self.links.append(link)
        self._sessions[snapshot.rule_key] = (case.id, parse_iso(snapshot.ts))
        self._emit_opened(snapshot, case.id, report_id)
        return AlertCaseDecision("opened", case_id=case.id, title=title,
                                 rule_key=snapshot.rule_key,
                                 reason="自动立案成功", link=link)

    def _emit_opened(self, snapshot: AlertSnapshot, case_id: str,
                     report_id: str) -> None:
        append = getattr(self.ledger, "append", None)
        if not callable(append):
            return
        append(
            "alert_case_opened", actor="system",
            object_refs=[f"case:{case_id}", f"alert:{snapshot.alert_id}",
                         f"report:{report_id}"],
            payload={"rule_key": snapshot.rule_key,
                     "severity": snapshot.severity,
                     "device": snapshot.device,
                     "channel": snapshot.channel,
                     "kind": snapshot.kind,
                     "snapshot": snapshot.to_dict()})


__all__ = [
    "ALERT_CASE_SCHEMA_VERSION",
    "ALERT_CASE_ACTIONS",
    "ALERT_SEVERITIES",
    "ALERT_REPORT_PREFIX",
    "AlertSnapshot",
    "AlertCaseLink",
    "AlertCasePolicy",
    "AlertCaseDecision",
    "AlertCaseOrchestrator",
    "build_8d_draft",
    "collect_context_evidence",
    "new_link_id",
]
