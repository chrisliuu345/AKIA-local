"""收益账本与 COPQ 契约 v1 — 改善收益记录与集合（v4.4.0 B0）。

覆盖 PLAN_v4.4.0 §3.4 冻结的 ``BenefitRecord``：

- 口径锁定当时标准版本（``basis.standard_ref`` / ``standard_as_of``），
  月度复算不追溯改写历史月（B4 编排）；
- 防重复计入：``double_count_key = sha256(case|month|口径)[:16]``，同键二次入账拒绝；
- 置信门禁：仅 A / A- / B 计入汇总，C 级留在"待完善"清单（``admits_to_summary``）；
- 改善与鉴定/损失分区（``ledger_kind``），考核视图与改善视图分开统计。

本模块无 Qt、无 ui 依赖（core 分层守卫）。
"""

from __future__ import annotations

import hashlib
import contextlib
import json
import re
import uuid
from dataclasses import dataclass, field, fields
from datetime import datetime, timedelta
from typing import Any

from core.evidence import _jsonable
from core.time_utils import now_iso, parse_iso

BENEFIT_SCHEMA_VERSION = "1"

#: 账本分区：改善收益 / 质量成本（COPQ）
LEDGER_KINDS = ("improvement", "cost_of_quality")
#: COPQ 四类 + 改善收益
BENEFIT_CATEGORIES = ("预防", "鉴定", "内部失败", "外部失败", "改善收益")
#: 置信分级（A/A-/B 可入账汇总；C 只登记）
CONFIDENCE_LEVELS = ("A", "A-", "B", "C")
SUMMARY_CONFIDENCE = ("A", "A-", "B")
#: 记录来源
BENEFIT_SOURCES = ("case_close", "monthly_recompute", "manual")

_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def new_benefit_id() -> str:
    """收益记录 ID：本地时区时间 + 4 位随机后缀。"""
    stamp = datetime.now().astimezone().strftime("%Y%m%d%H%M%S")
    return f"BEN-{stamp}-{uuid.uuid4().hex[:4]}"


def _to_float(value: Any, name: str) -> float:
    try:
        number = float(value or 0.0)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} 必须为数值: {value!r}") from exc
    return number


def double_count_key(case_id: str, month: str, basis: dict[str, Any],
                     category: str = "", ledger_kind: str = "") -> str:
    """防重复计入键：案例 + 月份 + 类别/分区 + 计量口径（单位/单价）的稳定哈希。

    v4.4.0 B4 语义加固：**不含标准版本字段**——标准升版不得打开第二条入账窗口
    （防"换口径重复计入"）；同案同月同类别同单位单价一律视为重复。
    """
    payload = {
        "case_id": str(case_id or "").strip(),
        "month": str(month or "").strip(),
        "category": str(category or "").strip(),
        "ledger_kind": str(ledger_kind or "").strip(),
        "unit": str((basis or {}).get("unit") or ""),
        "unit_cost": (basis or {}).get("unit_cost"),
    }
    text = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def month_bounds(month: str) -> tuple[datetime, datetime]:
    """``YYYY-MM`` → (月初, 月末) 本地时区 aware datetime。"""
    text = str(month or "").strip()
    match = _MONTH_RE.match(text)
    if not match:
        raise ValueError(f"月份格式必须为 YYYY-MM: {month!r}")
    start = datetime(int(text[:4]), int(text[5:7]), 1).astimezone()
    if int(text[5:7]) == 12:
        following = datetime(int(text[:4]) + 1, 1, 1).astimezone()
    else:
        following = datetime(int(text[:4]), int(text[5:7]) + 1, 1).astimezone()
    return start, following - timedelta(seconds=1)


def resolve_standard_basis(registry, refs, at: str = "") -> dict[str, str]:
    """从案例标准引用解析入账口径的 (standard_ref, standard_as_of)。

    候选引用可为对象引用或记录 ID；取 ``at``（默认现在）时刻生效版本，
    无匹配返回空 dict（入账仍可进行，只是不携带标准口径）。
    """
    if registry is None:
        return {}
    moment = str(at or "").strip() or now_iso()
    for raw in refs or []:
        target = str(raw or "").strip()
        if not target:
            continue
        record = None
        as_of = getattr(registry, "as_of", None)
        current = getattr(registry, "current", None)
        if callable(as_of):
            record = as_of(target, moment)
        if record is None and callable(current):
            record = current(target)
        if record is None:
            record = next((item for item in getattr(registry, "records", [])
                           if getattr(item, "record_id", "") == target), None)
        if record is not None:
            return {
                "standard_ref": str(getattr(record, "record_id", "")),
                "standard_as_of": str(getattr(record, "valid_from", "")),
                "standard_object_ref": str(getattr(record, "object_ref", "")),
            }
    return {}


@dataclass
class BenefitRecord:
    """一条收益/成本记录（月度、按当时标准口径）。"""

    record_id: str = field(default_factory=new_benefit_id)
    case_id: str = ""
    month: str = ""
    ledger_kind: str = "improvement"
    category: str = "改善收益"
    basis: dict[str, Any] = field(default_factory=dict)
    confidence: str = "B"
    evidence_refs: list[str] = field(default_factory=list)
    double_count_key: str = ""
    computed_at: str = ""
    source: str = "manual"
    note: str = ""
    schema_version: str = BENEFIT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != BENEFIT_SCHEMA_VERSION:
            raise ValueError(f"不支持的收益记录 schema 版本: {self.schema_version}")
        self.record_id = str(self.record_id or "").strip() or new_benefit_id()
        self.case_id = str(self.case_id or "").strip()
        if not self.case_id:
            raise ValueError("收益记录必须关联案例（case_id）")
        self.month = str(self.month or "").strip()
        if not _MONTH_RE.match(self.month):
            raise ValueError(f"月份格式必须为 YYYY-MM: {self.month!r}")
        self.ledger_kind = str(self.ledger_kind or "").strip().lower()
        if self.ledger_kind not in LEDGER_KINDS:
            raise ValueError(
                f"非法账本分区: {self.ledger_kind!r}（可选 {list(LEDGER_KINDS)}）")
        self.category = str(self.category or "").strip()
        if self.category not in BENEFIT_CATEGORIES:
            raise ValueError(
                f"非法收益类别: {self.category!r}（可选 {list(BENEFIT_CATEGORIES)}）")
        if not isinstance(self.basis, dict):
            raise ValueError("收益口径 basis 必须为 dict")
        self.basis = _jsonable(self.basis)
        self.confidence = str(self.confidence or "C").strip()
        if self.confidence not in CONFIDENCE_LEVELS:
            raise ValueError(
                f"非法置信分级: {self.confidence!r}（可选 {list(CONFIDENCE_LEVELS)}）")
        if not isinstance(self.evidence_refs, (list, tuple)):
            raise ValueError("evidence_refs 必须为字符串列表")
        self.evidence_refs = [str(item) for item in self.evidence_refs if str(item)]
        self.source = str(self.source or "manual").strip().lower()
        if self.source not in BENEFIT_SOURCES:
            raise ValueError(
                f"非法收益来源: {self.source!r}（可选 {list(BENEFIT_SOURCES)}）")
        self.note = str(self.note or "").strip()
        self.computed_at = parse_iso(
            self.computed_at or now_iso(), "computed_at").isoformat(timespec="seconds")
        expected_key = double_count_key(self.case_id, self.month, self.basis,
                                        self.category, self.ledger_kind)
        if self.double_count_key and self.double_count_key != expected_key:
            raise ValueError("double_count_key 与口径不一致（请留空由系统计算）")
        self.double_count_key = expected_key

    # ------------------------------------------------------------ 计算
    @property
    def amount(self) -> float:
        """金额（防重复计入之外的量值口径）。

        - improvement（改善收益）：(基线 − 新值) × 数量 × 单价（负值代表恶化，保留符号）；
        - cost_of_quality（COPQ）：数量 × 单价（损失/投入，恒为非负方向记录）。
        """
        basis = self.basis
        quantity = _to_float(basis.get("quantity"), "quantity")
        unit_cost = _to_float(basis.get("unit_cost"), "unit_cost")
        if self.ledger_kind == "improvement":
            baseline = _to_float(basis.get("baseline_value"), "baseline_value")
            new_value = _to_float(basis.get("new_value"), "new_value")
            return (baseline - new_value) * quantity * unit_cost
        return quantity * unit_cost

    @property
    def admits_to_summary(self) -> bool:
        """是否计入汇总（置信门禁：仅 A/A-/B）。"""
        return self.confidence in SUMMARY_CONFIDENCE

    # ------------------------------------------------------------ 序列化
    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "record_id": self.record_id,
            "case_id": self.case_id,
            "month": self.month,
            "ledger_kind": self.ledger_kind,
            "category": self.category,
            "basis": dict(self.basis),
            "confidence": self.confidence,
            "evidence_refs": list(self.evidence_refs),
            "double_count_key": self.double_count_key,
            "computed_at": self.computed_at,
            "source": self.source,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BenefitRecord:
        if not isinstance(data, dict):
            raise ValueError("收益记录必须为 dict")
        schema = str(data.get("schema_version") or BENEFIT_SCHEMA_VERSION)
        if schema != BENEFIT_SCHEMA_VERSION:
            raise ValueError(f"不支持的收益记录 schema 版本: {schema}")
        allowed = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in allowed})


class BenefitLedger:
    """收益记录集合（按 double_count_key 防重复；月度/分区查询）。"""

    def __init__(self, records: list[BenefitRecord] | None = None):
        self.records: list[BenefitRecord] = []
        for record in records or []:
            self.add(record)

    @staticmethod
    def _normalize(record) -> BenefitRecord:
        if isinstance(record, BenefitRecord):
            return record
        return BenefitRecord.from_dict(record)

    def add(self, record) -> BenefitRecord:
        """入账；同 double_count_key 拒绝（防重复计入）。"""
        normalized = self._normalize(record)
        for existing in self.records:
            if existing.double_count_key == normalized.double_count_key:
                raise ValueError(
                    f"重复计入被拒绝：案例 {normalized.case_id} 在 "
                    f"{normalized.month} 的口径已存在记录 {existing.record_id}")
        self.records.append(normalized)
        return normalized

    def __len__(self) -> int:
        return len(self.records)

    def __iter__(self):
        return iter(self.records)

    def for_case(self, case_id: str) -> list[BenefitRecord]:
        target = str(case_id or "").strip()
        return [r for r in self.records if r.case_id == target]

    def for_month(self, month: str) -> list[BenefitRecord]:
        target = str(month or "").strip()
        return [r for r in self.records if r.month == target]

    def cost_breakdown(self, month: str = "") -> dict[str, float]:
        """COPQ 四类分项（仅置信门槛内的记录）；``month`` 为空统计全部。"""
        breakdown = dict.fromkeys(("预防", "鉴定", "内部失败", "外部失败"), 0.0)
        target = str(month or "").strip()
        for record in self.records:
            if target and record.month != target:
                continue
            if record.ledger_kind != "cost_of_quality":
                continue
            if not record.admits_to_summary:
                continue
            if record.category in breakdown:
                breakdown[record.category] += record.amount
        return breakdown

    def summary(self, month: str = "") -> dict[str, Any]:
        """汇总（仅置信门槛内的记录）：改善收益 / COPQ 分区、待完善清单。"""
        improvement = 0.0
        copq = 0.0
        pending: list[str] = []
        target = str(month or "").strip()
        count = 0
        for record in self.records:
            if target and record.month != target:
                continue
            count += 1
            if not record.admits_to_summary:
                pending.append(record.record_id)
                continue
            if record.ledger_kind == "improvement":
                improvement += record.amount
            else:
                copq += record.amount
        return {
            "improvement_total": improvement,
            "copq_total": copq,
            "roi": (improvement / copq) if copq > 0 else None,
            "pending_records": pending,
            "pending_count": len(pending),
            "copq_breakdown": self.cost_breakdown(target),
            "count": count,
        }

    # ------------------------------------------------------------ 月度复算（B4-1）
    def recompute_month(self, month: str, *, standards=None, now: str = "",
                        event_sink=None) -> dict[str, Any]:
        """按当时标准版本复算指定月（历史月冻结，当月口径前移）。

        - **历史月不追溯改写**：`month` 早于当前月直接返回
          ``frozen=True``，记录与金额保持不变（复算只做快照）；
        - **当月复算**：对每条记录按"现在生效"的标准版本刷新
          ``basis.standard_as_of/standard_ref``（金额由案例测量口径给出，
          不因版本变化改数），并回传 ``benefit_recomputed`` 事件供账本留痕；
        - 返回 {month, frozen, updates, summary}。
        """
        target = str(month or "").strip()
        month_bounds(target)  # 格式校验
        # "现在"取真实毫秒精度：同一秒内的标准升版（valid_from +1ms 位移）
        # 也能被覆盖（now_iso 只有秒级精度，补零会落在新版生效点之前）
        if str(now or "").strip():
            moment = parse_iso(str(now).strip(), "now").isoformat(
                timespec="milliseconds")
        else:
            moment = datetime.now().astimezone().isoformat(
                timespec="milliseconds")
        current_month = parse_iso(moment, "now").strftime("%Y-%m")
        frozen = target < current_month
        updates: list[dict[str, Any]] = []
        if not frozen:
            for record in self.for_month(target):
                ref = str(record.basis.get("standard_ref") or "")
                if standards is None or not ref:
                    continue
                anchor = next((item for item in getattr(standards, "records", [])
                               if getattr(item, "record_id", "") == ref), None)
                if anchor is None:
                    continue
                effective = None
                as_of = getattr(standards, "as_of", None)
                current = getattr(standards, "current", None)
                if callable(as_of):
                    effective = as_of(str(anchor.object_ref), moment)
                if effective is None and callable(current):
                    effective = current(str(anchor.object_ref))
                if (effective is None
                        or effective.valid_from == record.basis.get("standard_as_of")):
                    continue
                old_as_of = str(record.basis.get("standard_as_of") or "")
                record.basis["standard_as_of"] = effective.valid_from
                record.basis["standard_ref"] = effective.record_id
                record.computed_at = parse_iso(
                    moment, "now").isoformat(timespec="seconds")
                update = {
                    "record_id": record.record_id, "case_id": record.case_id,
                    "old_as_of": old_as_of, "new_as_of": effective.valid_from,
                    "standard_ref": effective.record_id, "amount": record.amount,
                }
                updates.append(update)
                if callable(event_sink):
                    with contextlib.suppress(Exception):  # 记账失败不阻断复算
                        event_sink(
                            "benefit_recomputed",
                            [f"benefit:{record.record_id}",
                             f"case:{record.case_id}"],
                            {"month": target, **update,
                             "confidence": record.confidence,
                             "category": record.category})
        return {"month": target, "frozen": frozen, "updates": updates,
                "summary": self.summary(target)}

    def to_dicts(self) -> list[dict[str, Any]]:
        return [record.to_dict() for record in self.records]

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": BENEFIT_SCHEMA_VERSION,
                "records": self.to_dicts()}

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> BenefitLedger:
        if data is None:
            return cls()
        if not isinstance(data, dict):
            raise ValueError("收益账本必须为 dict")
        schema = str(data.get("schema_version") or BENEFIT_SCHEMA_VERSION)
        if schema != BENEFIT_SCHEMA_VERSION:
            raise ValueError(f"不支持的收益账本 schema 版本: {schema}")
        raw = data.get("records") or []
        if not isinstance(raw, list):
            raise ValueError("收益账本 records 必须为列表")
        return cls([BenefitRecord.from_dict(item) for item in raw])


def record_case_benefit(ledger: BenefitLedger, case, *, month: str,
                        baseline_value: float = 0.0, new_value: float = 0.0,
                        quantity: float = 0.0, unit_cost: float = 0.0,
                        category: str = "改善收益",
                        ledger_kind: str = "improvement",
                        confidence: str = "B", unit: str = "",
                        currency: str = "", note: str = "",
                        source: str = "case_close", standards=None,
                        evidence_refs=None, event_sink=None) -> BenefitRecord:
    """案例收益入账（B4-4）：自动携带案例标准引用解析出的口径版本。

    ``case`` 接受 ``ImprovementCase``（读取 ``id`` / ``standard_refs``）；
    入账即写 ``benefit_recorded`` 事件（经 ``event_sink`` 注入账本）。
    """
    case_id = str(getattr(case, "id", "") or "").strip()
    if not case_id:
        raise ValueError("案例缺少 id，无法入账收益")
    basis = {
        "baseline_value": float(baseline_value),
        "new_value": float(new_value),
        "quantity": float(quantity),
        "unit_cost": float(unit_cost),
        "unit": str(unit or ""),
        "currency": str(currency or ""),
    }
    basis.update(resolve_standard_basis(
        standards, getattr(case, "standard_refs", []) or []))
    refs = [str(item) for item in (evidence_refs or []) if str(item)]
    if f"case:{case_id}" not in refs:
        refs.insert(0, f"case:{case_id}")
    record = ledger.add(BenefitRecord(
        case_id=case_id, month=month, ledger_kind=ledger_kind,
        category=category, basis=basis, confidence=confidence,
        evidence_refs=refs, source=source, note=note))
    if callable(event_sink):
        with contextlib.suppress(Exception):  # 记账失败不阻断入账
            event_sink(
                "benefit_recorded",
                [f"case:{case_id}", f"benefit:{record.record_id}"],
                {"month": month, "category": category,
                 "ledger_kind": ledger_kind, "confidence": confidence,
                 "amount": record.amount,
                 "standard_ref": basis.get("standard_ref", ""),
                 "standard_as_of": basis.get("standard_as_of", ""),
                 "double_count_key": record.double_count_key})
    return record


__all__ = [
    "BENEFIT_SCHEMA_VERSION",
    "LEDGER_KINDS",
    "BENEFIT_CATEGORIES",
    "CONFIDENCE_LEVELS",
    "SUMMARY_CONFIDENCE",
    "BENEFIT_SOURCES",
    "BenefitRecord",
    "BenefitLedger",
    "double_count_key",
    "month_bounds",
    "new_benefit_id",
    "record_case_benefit",
    "resolve_standard_basis",
]
