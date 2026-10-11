"""StandardRecord v1 — 标准版本记录（v4.3.0 B0/B3 契约）。

覆盖路线图约定的五类标准对象：规格限 / 控制限 / 标准工时 / 作业组合票 / 控制计划条目。
每条记录带生效区间（valid_from / valid_to）、变更原因与来源，注册表保证同一对象
时间区间不重叠，并支持按时间点还原当时标准（as-of）。

本模块无 Qt、无 ui 依赖（core 分层守卫）。
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, fields
from datetime import datetime, timedelta
from typing import Any

from core.evidence import _jsonable
from core.time_utils import now_iso, parse_iso

STANDARD_SCHEMA_VERSION = "1"
OBJECT_TYPES = ("spec_limit", "control_limit", "standard_time",
                "work_combination", "control_plan_row")
ORIGINS = ("manual", "migration", "case")


def new_record_id() -> str:
    """生成标准版本记录 ID：STD-<本地时间>-<4 位随机>。"""
    stamp = datetime.now().astimezone().strftime("%Y%m%d%H%M%S")
    return f"STD-{stamp}-{uuid.uuid4().hex[:4]}"


def _fingerprint(object_type: str, object_ref: str, payload: dict[str, Any],
                 valid_from: str, valid_to: str | None) -> str:
    canonical = json.dumps(
        {"object_type": object_type, "object_ref": object_ref, "payload": _jsonable(payload),
         "valid_from": valid_from, "valid_to": valid_to},
        sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"std-hash-v1:{digest}"


@dataclass
class StandardRecord:
    """一条标准版本记录（append-only；关闭旧记录 = 设置 valid_to）。"""

    record_id: str
    object_type: str
    object_ref: str
    payload: dict[str, Any]
    valid_from: str
    valid_to: str | None = None
    change_reason: str = ""
    changed_by: str = ""
    recorded_at: str = ""
    supersedes: str = ""
    source_case_id: str = ""
    origin: str = "manual"
    fingerprint: str = ""
    schema_version: str = STANDARD_SCHEMA_VERSION

    def __post_init__(self) -> None:
        self.record_id = str(self.record_id or "").strip()
        self.object_type = str(self.object_type or "").strip().lower()
        self.object_ref = str(self.object_ref or "").strip()
        self.change_reason = str(self.change_reason or "").strip()
        self.changed_by = str(self.changed_by or "").strip()
        self.supersedes = str(self.supersedes or "").strip()
        self.source_case_id = str(self.source_case_id or "").strip()
        self.origin = str(self.origin or "manual").strip().lower()

        if self.schema_version != STANDARD_SCHEMA_VERSION:
            raise ValueError(f"不支持的标准记录 schema 版本: {self.schema_version}")
        if not self.record_id:
            raise ValueError("标准记录 record_id 不能为空")
        if self.object_type not in OBJECT_TYPES:
            raise ValueError(f"未知标准对象类型: {self.object_type!r}（可选 {list(OBJECT_TYPES)}）")
        if not self.object_ref:
            raise ValueError("标准记录 object_ref 不能为空")
        if not isinstance(self.payload, dict) or not self.payload:
            raise ValueError("标准记录 payload 必须为非空 dict")
        if self.origin not in ORIGINS:
            raise ValueError(f"未知标准来源 origin: {self.origin!r}（可选 {list(ORIGINS)}）")
        if self.origin == "migration" and not self.change_reason:
            self.change_reason = "历史数据迁移"
        if not self.change_reason:
            raise ValueError("标准变更必须填写 change_reason")

        self.valid_from = parse_iso(self.valid_from, "valid_from").isoformat(timespec="milliseconds")
        if self.valid_to:
            self.valid_to = parse_iso(self.valid_to, "valid_to").isoformat(timespec="milliseconds")
            if parse_iso(self.valid_to) <= parse_iso(self.valid_from):
                raise ValueError("valid_to 必须晚于 valid_from")
        else:
            self.valid_to = None
        self.recorded_at = parse_iso(
            self.recorded_at or now_iso(), "recorded_at").isoformat(timespec="milliseconds")
        self.payload = _jsonable(self.payload)
        if not self.fingerprint:
            self.fingerprint = _fingerprint(
                self.object_type, self.object_ref, self.payload,
                self.valid_from, self.valid_to)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "record_id": self.record_id,
            "object_type": self.object_type,
            "object_ref": self.object_ref,
            "payload": dict(self.payload),
            "valid_from": self.valid_from,
            "valid_to": self.valid_to,
            "change_reason": self.change_reason,
            "changed_by": self.changed_by,
            "recorded_at": self.recorded_at,
            "supersedes": self.supersedes,
            "source_case_id": self.source_case_id,
            "origin": self.origin,
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StandardRecord:
        if not isinstance(data, dict):
            raise ValueError("标准记录必须为 dict")
        schema = str(data.get("schema_version") or STANDARD_SCHEMA_VERSION)
        if schema != STANDARD_SCHEMA_VERSION:
            raise ValueError(f"不支持的标准记录 schema 版本: {schema}")
        allowed = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in allowed})

    def is_open(self) -> bool:
        return self.valid_to is None

    def covers(self, ts: str) -> bool:
        """时间点是否落在 [valid_from, valid_to) 区间内。"""
        moment = parse_iso(ts, "时间点")
        start = parse_iso(self.valid_from)
        if moment < start:
            return False
        if self.valid_to is None:
            return True
        return moment < parse_iso(self.valid_to)


class StandardRegistry:
    """标准版本注册表 — append-only + 区间不重叠 + as-of 还原。"""

    def __init__(self, records: list[StandardRecord] | None = None):
        self.records: list[StandardRecord] = []
        for record in records or []:
            self._insert(record)

    # ------------------------------------------------------------ 写入
    def append(self, record: StandardRecord) -> StandardRecord:
        """追加新版本：自动关闭同一对象的开放记录；区间重叠则拒绝。

        全部校验先于任何状态变更（原子性）：失败时现行版本保持开放，
        不会出现"旧版本已关闭、新版本未加入"的损坏注册表状态。
        """
        if not isinstance(record, StandardRecord):
            raise TypeError("append 仅接受 StandardRecord")
        previous = self.current(record.object_ref)
        if previous is not None:
            if previous.object_type != record.object_type:
                raise ValueError(
                    f"对象 {record.object_ref} 已有类型 {previous.object_type}，"
                    f"不能改记为 {record.object_type}")
            new_start = parse_iso(record.valid_from)
            previous_start = parse_iso(previous.valid_from)
            if new_start <= previous_start:
                raise ValueError(
                    f"新版本 valid_from ({record.valid_from}) 必须晚于现行版本 "
                    f"({previous.valid_from})")
        self._assert_no_overlap(record, replaces=previous)
        if previous is not None:
            previous.valid_to = record.valid_from
            record.supersedes = record.supersedes or previous.record_id
        self.records.append(record)
        return record

    def _insert(self, record: StandardRecord) -> None:
        if not isinstance(record, StandardRecord):
            raise TypeError("records 仅接受 StandardRecord")
        self._assert_no_overlap(record)
        self.records.append(record)

    def _assert_no_overlap(self, record: StandardRecord, *,
                           replaces: StandardRecord | None = None) -> None:
        """区间冲突校验；``replaces`` 为即将被本条记录关闭的现行版本，
        其有效区间按"在 ``record.valid_from`` 关闭"参与比较（不实际改写）。"""
        start = parse_iso(record.valid_from)
        end = parse_iso(record.valid_to) if record.valid_to else None
        if any(existing.record_id == record.record_id for existing in self.records):
            raise ValueError(f"记录 ID 重复: {record.record_id}")
        for existing in self.records:
            if existing.object_ref != record.object_ref:
                continue
            if existing.object_type != record.object_type:
                raise ValueError(
                    f"对象 {record.object_ref} 类型冲突: "
                    f"{existing.object_type} vs {record.object_type}")
            ex_start = parse_iso(existing.valid_from)
            if existing is replaces:
                ex_end = start
            else:
                ex_end = parse_iso(existing.valid_to) if existing.valid_to else None
            overlaps = (end is None or ex_start < end) and (ex_end is None or start < ex_end)
            if overlaps:
                raise ValueError(
                    f"标准区间重叠: {record.object_ref} 新旧版本在 "
                    f"[{record.valid_from}, {record.valid_to or '现在'}) 相交")

    # ------------------------------------------------------------ 查询
    def current(self, object_ref: str) -> StandardRecord | None:
        ref = str(object_ref or "").strip()
        open_records = [r for r in self.records if r.object_ref == ref and r.is_open()]
        if not open_records:
            return None
        return max(open_records, key=lambda r: r.valid_from)

    def as_of(self, object_ref: str, ts: str) -> StandardRecord | None:
        """还原某时间点生效的标准；边界 valid_to 为开区间。"""
        ref = str(object_ref or "").strip()
        matches = [r for r in self.records if r.object_ref == ref and r.covers(ts)]
        if not matches:
            return None
        return max(matches, key=lambda r: r.valid_from)

    def history(self, object_ref: str) -> list[StandardRecord]:
        ref = str(object_ref or "").strip()
        return sorted((r for r in self.records if r.object_ref == ref),
                      key=lambda r: r.valid_from)

    def refs(self) -> list[str]:
        return sorted({r.object_ref for r in self.records})

    def record_change(self, object_type: str, object_ref: str,
                      payload: dict[str, Any], *, change_reason: str,
                      changed_by: str = "", source_case_id: str = "",
                      origin: str = "manual", valid_from: str = "",
                      recorded_at: str = "") -> StandardRecord:
        """记录一次标准变更；与现行版本内容一致时幂等返回（不产生新版本）。

        旧版本由 ``append`` 自动关闭（``valid_to = 新版本 valid_from``）。
        """
        if not str(change_reason or "").strip() and origin != "migration":
            raise ValueError("标准变更必须填写 change_reason")
        normalized = _jsonable(payload)
        current = self.current(object_ref)
        if (current is not None and current.object_type == object_type
                and current.payload == normalized):
            return current
        explicit_start = str(valid_from or "").strip()
        start = parse_iso(explicit_start, "valid_from") if explicit_start else parse_iso(now_iso())
        if current is not None:
            current_start = parse_iso(current.valid_from)
            if start < current_start and explicit_start:
                raise ValueError(
                    f"新版本 valid_from ({start.isoformat(timespec='milliseconds')}) "
                    f"早于现行版本 ({current.valid_from})")
            if start <= current_start:
                # 同一毫秒内连续变更：单调后移 1ms，保证版本区间非零且可 as-of 还原
                start = current_start + timedelta(milliseconds=1)
        record = StandardRecord(
            record_id=new_record_id(),
            object_type=object_type,
            object_ref=str(object_ref),
            payload=normalized,
            valid_from=start.isoformat(timespec="milliseconds"),
            change_reason=change_reason,
            changed_by=changed_by,
            recorded_at=recorded_at or now_iso(),
            source_case_id=source_case_id,
            origin=origin,
        )
        return self.append(record)

    def __len__(self) -> int:
        return len(self.records)

    # ------------------------------------------------------------ 序列化
    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": STANDARD_SCHEMA_VERSION,
            "records": [r.to_dict() for r in self.records],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> StandardRegistry:
        if data is None:
            return cls()
        if not isinstance(data, dict):
            raise ValueError("标准注册表必须为 dict")
        schema = str(data.get("schema_version") or STANDARD_SCHEMA_VERSION)
        if schema != STANDARD_SCHEMA_VERSION:
            raise ValueError(f"不支持的标准注册表 schema 版本: {schema}")
        raw_records = data.get("records") or []
        if not isinstance(raw_records, list):
            raise ValueError("标准注册表 records 必须为列表")
        return cls([StandardRecord.from_dict(item) for item in raw_records])

    @staticmethod
    def diff(left: StandardRecord, right: StandardRecord) -> dict[str, Any]:
        """逐字段比较两个版本，返回变化项（无变化返回空 dict）。"""
        if not isinstance(left, StandardRecord) or not isinstance(right, StandardRecord):
            raise TypeError("diff 需要两个 StandardRecord")
        changes: dict[str, Any] = {}
        for key in ("object_type", "object_ref", "valid_from", "valid_to"):
            old, new = getattr(left, key), getattr(right, key)
            if old != new:
                changes[key] = {"old": old, "new": new}
        for key in sorted(set(left.payload) | set(right.payload)):
            old, new = left.payload.get(key), right.payload.get(key)
            if old != new:
                changes.setdefault("payload", {})[key] = {"old": old, "new": new}
        return changes


def resolve_standard_context(registry: StandardRegistry | None, refs,
                             ts: str = "") -> dict[str, Any]:
    """按候选引用解析标准上下文（当前或 ``ts`` 时刻生效版本）。

    候选引用可以是对象引用（特性 ID / 列名 / 工序号）或记录 ID；
    返回可直接并入判定凭证 params 的字段（无匹配返回空 dict）。
    """
    if registry is None:
        return {}
    for raw in refs or []:
        target = str(raw or "").strip()
        if not target:
            continue
        if ts:
            record = registry.as_of(target, ts)
        else:
            record = registry.current(target)
            if record is None:
                record = registry.as_of(target, now_iso())
        if record is None:
            record = next((r for r in registry.records if r.record_id == target), None)
        if record is not None:
            return {
                "standard_ref": record.record_id,
                "standard_object_ref": record.object_ref,
                "standard_as_of": record.valid_from,
                "standard_fingerprint": record.fingerprint,
            }
    return {}


def migrate_legacy_context(context: dict[str, Any], *,
                           recorded_at: str = "") -> StandardRegistry:
    """把旧项目上下文中的规格限转为首版 ``spec_limit`` 记录（origin=migration）。"""
    registry = StandardRegistry()
    if not isinstance(context, dict):
        return registry
    try:
        valid_from = parse_iso(
            str(context.get("created_at") or recorded_at or now_iso()),
            "created_at", allow_naive=True).isoformat(timespec="seconds")
    except ValueError:
        valid_from = (parse_iso(recorded_at, "recorded_at", allow_naive=True)
                      .isoformat(timespec="seconds") if recorded_at else now_iso())
    stamp = now_iso() if not recorded_at else parse_iso(
        recorded_at, "recorded_at", allow_naive=True).isoformat(timespec="seconds")
    for qc in context.get("characteristics") or []:
        if not isinstance(qc, dict):
            continue
        if all(qc.get(key) is None for key in ("usl", "lsl", "target")):
            continue
        ref = str(qc.get("id") or qc.get("name") or "").strip()
        if not ref:
            continue
        registry.append(StandardRecord(
            record_id=f"STD-MIG-{ref}",
            object_type="spec_limit",
            object_ref=ref,
            payload={"usl": qc.get("usl"), "lsl": qc.get("lsl"),
                     "target": qc.get("target"), "unit": qc.get("unit", ""),
                     "name": qc.get("name", ""), "process": qc.get("process", "")},
            valid_from=valid_from,
            change_reason="历史数据迁移",
            changed_by="system",
            recorded_at=stamp,
            origin="migration",
        ))
    return registry
