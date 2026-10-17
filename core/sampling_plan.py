"""抽样域契约 v1 — 检验批 / 抽样决定 / 转移状态（v4.4.0 B0）。

覆盖四类冻结对象：

- ``LotRecord``：一次检验批的事实（数量/检验数/不合格数/判定/严重标记）；
- ``SamplingDecision``：一次抽样决定（方法/种子/样本量/方案引用/样本行指纹）；
- ``TransferState``：按供应商·产品线的转移状态与历史（append 由 B3 编排）；
- ``TransferDecision``：转移评估结果（纯函数输出，含触发依据）。

本模块无 Qt、无 ui 依赖（core 分层守卫）；时间戳一律走 ``core/time_utils``
（带时区 ISO-8601），未知 schema 版本拒读并给结构化中文错误。
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field, fields
from typing import Any

from core.evidence import _jsonable
from core.time_utils import now_iso, parse_iso

SAMPLING_SCHEMA_VERSION = "1"

#: 检验批判定
LOT_DECISIONS = ("pending", "accept", "reject")
#: 抽样方法（与 SamplingEngine 的既有实现对齐）
SAMPLING_METHODS = ("random", "stratified", "systematic", "sequential",
                    "measurement", "c0")
#: 检验严格度状态
TRANSFER_STATES = ("normal", "tightened", "reduced")


def new_decision_id() -> str:
    """抽样决定 ID：本地时区时间 + 4 位随机后缀。"""
    from datetime import datetime

    stamp = datetime.now().astimezone().strftime("%Y%m%d%H%M%S")
    return f"SAM-{stamp}-{uuid.uuid4().hex[:4]}"


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


@dataclass
class LotRecord:
    """一次检验批的事实记录（判定的最小输入）。"""

    lot_id: str
    supplier: str = ""
    product: str = ""
    line: str = ""
    qty: int = 0
    inspected: int = 0
    defects: int = 0
    decision: str = "pending"
    serious: bool = False            # 严重不合格标记（触发立即加严）
    plan_ref: str = ""               # 生效抽样方案（StandardRecord ID）
    at: str = ""                     # 判定时间（带时区 ISO-8601）
    actor: str = ""
    raw_ref: str = ""
    schema_version: str = SAMPLING_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SAMPLING_SCHEMA_VERSION:
            raise ValueError(f"不支持的检验批 schema 版本: {self.schema_version}")
        self.lot_id = _clean_text(self.lot_id)
        if not self.lot_id:
            raise ValueError("检验批 lot_id 不能为空")
        for name in ("supplier", "product", "line", "plan_ref", "actor", "raw_ref"):
            setattr(self, name, _clean_text(getattr(self, name)))
        for name in ("qty", "inspected", "defects"):
            value = int(getattr(self, name) or 0)
            if value < 0:
                raise ValueError(f"检验批 {name} 不能为负: {value}")
            setattr(self, name, value)
        if self.inspected > self.qty:
            raise ValueError(f"检验数 ({self.inspected}) 不能超过批量 ({self.qty})")
        if self.defects > self.inspected:
            raise ValueError(f"不合格数 ({self.defects}) 不能超过检验数 ({self.inspected})")
        self.decision = _clean_text(self.decision).lower() or "pending"
        if self.decision not in LOT_DECISIONS:
            raise ValueError(f"非法检验批判定: {self.decision!r}（可选 {list(LOT_DECISIONS)}）")
        self.serious = bool(self.serious)
        self.at = parse_iso(self.at or now_iso(), "at").isoformat(timespec="seconds")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "lot_id": self.lot_id,
            "supplier": self.supplier,
            "product": self.product,
            "line": self.line,
            "qty": self.qty,
            "inspected": self.inspected,
            "defects": self.defects,
            "decision": self.decision,
            "serious": self.serious,
            "plan_ref": self.plan_ref,
            "at": self.at,
            "actor": self.actor,
            "raw_ref": self.raw_ref,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LotRecord:
        if not isinstance(data, dict):
            raise ValueError("检验批必须为 dict")
        schema = str(data.get("schema_version") or SAMPLING_SCHEMA_VERSION)
        if schema != SAMPLING_SCHEMA_VERSION:
            raise ValueError(f"不支持的检验批 schema 版本: {schema}")
        allowed = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in allowed})


@dataclass
class SamplingDecision:
    """一次抽样决定（可复现：种子 + 样本行指纹）。"""

    decision_id: str = field(default_factory=new_decision_id)
    scope_key: str = ""              # 供应商·产品线（转移状态作用域）
    method: str = "random"
    seed: int | None = None
    n: int = 0
    aql: float | None = None
    level: str = ""
    plan_ref: str = ""               # 抽样方案（StandardRecord ID）
    row_fingerprint: str = ""        # 抽样结果行指纹（pd-hash-v1）
    sampled_at: str = ""
    actor: str = ""
    source_ref: str = ""
    note: str = ""                   # 抽样说明（展示层透明化统一字段）
    schema_version: str = SAMPLING_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SAMPLING_SCHEMA_VERSION:
            raise ValueError(f"不支持的抽样决定 schema 版本: {self.schema_version}")
        self.decision_id = _clean_text(self.decision_id) or new_decision_id()
        self.scope_key = _clean_text(self.scope_key)
        self.method = _clean_text(self.method).lower()
        if self.method not in SAMPLING_METHODS:
            raise ValueError(
                f"非法抽样方法: {self.method!r}（可选 {list(SAMPLING_METHODS)}）")
        if self.seed is not None:
            self.seed = int(self.seed)
        self.n = int(self.n or 0)
        if self.n < 1:
            raise ValueError(f"样本量必须 ≥ 1: {self.n}")
        if self.aql is not None:
            self.aql = float(self.aql)
        for name in ("level", "plan_ref", "row_fingerprint", "actor",
                     "source_ref", "note"):
            setattr(self, name, _clean_text(getattr(self, name)))
        self.sampled_at = parse_iso(
            self.sampled_at or now_iso(), "sampled_at").isoformat(timespec="seconds")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "decision_id": self.decision_id,
            "scope_key": self.scope_key,
            "method": self.method,
            "seed": self.seed,
            "n": self.n,
            "aql": self.aql,
            "level": self.level,
            "plan_ref": self.plan_ref,
            "row_fingerprint": self.row_fingerprint,
            "sampled_at": self.sampled_at,
            "actor": self.actor,
            "source_ref": self.source_ref,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SamplingDecision:
        if not isinstance(data, dict):
            raise ValueError("抽样决定必须为 dict")
        schema = str(data.get("schema_version") or SAMPLING_SCHEMA_VERSION)
        if schema != SAMPLING_SCHEMA_VERSION:
            raise ValueError(f"不支持的抽样决定 schema 版本: {schema}")
        allowed = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in allowed})


@dataclass
class TransferDecision:
    """一次转移评估的结果（``SamplingEngine.evaluate_transfer`` 的返回）。"""

    scope_key: str
    from_state: str
    to_state: str
    rule: str = ""
    reason: str = ""
    triggering_lots: list[str] = field(default_factory=list)
    evaluated_at: str = ""

    def __post_init__(self) -> None:
        self.scope_key = _clean_text(self.scope_key)
        self.from_state = _clean_text(self.from_state).lower()
        self.to_state = _clean_text(self.to_state).lower()
        for name in ("from_state", "to_state"):
            if getattr(self, name) not in TRANSFER_STATES:
                raise ValueError(
                    f"非法转移状态 {name}: {getattr(self, name)!r}"
                    f"（可选 {list(TRANSFER_STATES)}）")
        self.rule = _clean_text(self.rule)
        self.reason = _clean_text(self.reason)
        self.triggering_lots = [str(item) for item in (self.triggering_lots or [])]
        self.evaluated_at = parse_iso(
            self.evaluated_at or now_iso(), "evaluated_at").isoformat(timespec="seconds")

    @property
    def changed(self) -> bool:
        return self.from_state != self.to_state

    def to_dict(self) -> dict[str, Any]:
        return {
            "scope_key": self.scope_key,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "changed": self.changed,
            "rule": self.rule,
            "reason": self.reason,
            "triggering_lots": list(self.triggering_lots),
            "evaluated_at": self.evaluated_at,
        }


@dataclass
class TransferState:
    """按供应商·产品线的转移状态（append-only 历史在 ``history``）。"""

    scope_key: str
    state: str = "normal"
    history: list[dict[str, Any]] = field(default_factory=list)
    override_reason: str = ""
    updated_at: str = ""
    schema_version: str = SAMPLING_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SAMPLING_SCHEMA_VERSION:
            raise ValueError(f"不支持的转移状态 schema 版本: {self.schema_version}")
        self.scope_key = _clean_text(self.scope_key)
        if not self.scope_key:
            raise ValueError("转移状态必须提供 scope_key（供应商·产品线）")
        self.state = _clean_text(self.state).lower() or "normal"
        if self.state not in TRANSFER_STATES:
            raise ValueError(
                f"非法检验状态: {self.state!r}（可选 {list(TRANSFER_STATES)}）")
        self.override_reason = _clean_text(self.override_reason)
        normalized: list[dict[str, Any]] = []
        for item in self.history or []:
            if not isinstance(item, dict):
                raise ValueError("转移历史条目必须为 dict")
            normalized.append(_jsonable(item))
        self.history = normalized
        self.updated_at = parse_iso(
            self.updated_at or now_iso(), "updated_at").isoformat(timespec="seconds")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "scope_key": self.scope_key,
            "state": self.state,
            "history": [dict(item) for item in self.history],
            "override_reason": self.override_reason,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TransferState:
        if not isinstance(data, dict):
            raise ValueError("转移状态必须为 dict")
        schema = str(data.get("schema_version") or SAMPLING_SCHEMA_VERSION)
        if schema != SAMPLING_SCHEMA_VERSION:
            raise ValueError(f"不支持的转移状态 schema 版本: {schema}")
        allowed = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in allowed})


def scope_key_for(supplier: str, product: str) -> str:
    """转移状态作用域键（供应商·产品线；空值归一为 ``-``）。"""
    left = _clean_text(supplier) or "-"
    right = _clean_text(product) or "-"
    return f"{left}|{right}"


def fingerprint_from_frames(frames) -> str:
    """抽样结果行指纹。

    单表直接复用 ``pd-hash-v1`` 口径；多表（多批/多子集）用
    ``pd-hash-v1-group:`` 前缀对各自指纹的规范串再哈希，保证确定性。
    """
    from core.evidence import fingerprint_dataframe

    items = list(frames) if isinstance(frames, (list, tuple)) else [frames]
    if not items:
        return ""
    if len(items) == 1:
        return fingerprint_dataframe(items[0]) if items[0] is not None else ""
    parts = ["none" if frame is None else fingerprint_dataframe(frame)
             for frame in items]
    digest = hashlib.sha256(_canonical_json(parts).encode("utf-8")).hexdigest()
    return f"pd-hash-v1-group:{digest}"


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), default=str)


__all__ = [
    "SAMPLING_SCHEMA_VERSION",
    "LOT_DECISIONS",
    "SAMPLING_METHODS",
    "TRANSFER_STATES",
    "LotRecord",
    "SamplingDecision",
    "TransferDecision",
    "TransferState",
    "fingerprint_from_frames",
    "new_decision_id",
    "scope_key_for",
]
