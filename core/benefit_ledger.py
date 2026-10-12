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
import json
import re
import uuid
from dataclasses import dataclass, field, fields
from datetime import datetime
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
                     category: str = "") -> str:
    """防重复计入键：案例 + 月份 + 计量口径（标准引用/单位/单价）的稳定哈希。"""
    payload = {
        "case_id": str(case_id or "").strip(),
        "month": str(month or "").strip(),
        "category": str(category or "").strip(),
        "standard_ref": str((basis or {}).get("standard_ref") or ""),
        "standard_as_of": str((basis or {}).get("standard_as_of") or ""),
        "unit": str((basis or {}).get("unit") or ""),
        "unit_cost": (basis or {}).get("unit_cost"),
    }
    text = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


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
                                        self.category)
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

    def summary(self) -> dict[str, Any]:
        """汇总（仅置信门槛内的记录）：改善收益 / COPQ 分区、待完善清单。"""
        improvement = 0.0
        copq = 0.0
        pending: list[str] = []
        for record in self.records:
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
            "count": len(self.records),
        }

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
    "new_benefit_id",
]
