"""技能域契约 v1 — 技能矩阵与排班计划（v4.4.0 B0）。

覆盖两类冻结对象：

- ``SkillMatrix``：人员 × 工序 → 熟练度（1~5 级）；
- ``SchedulePlan``：技能约束下的排班结果（含平衡率前后对比与不可行明细）。

B5 在此契约上实现约束求解与案例模板接线；本模块先冻结字段语义、校验与序列化。
本模块无 Qt、无 ui 依赖（core 分层守卫）。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, fields
from typing import Any

from core.time_utils import now_iso, parse_iso

SKILL_SCHEMA_VERSION = "1"

MIN_SKILL_LEVEL = 1
MAX_SKILL_LEVEL = 5


@dataclass
class ProcessSkillReq:
    """工序技能要求（PLAN §3.5：并入线平衡约束面板）。"""

    process_id: str
    min_level: int = 1
    schema_version: str = SKILL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SKILL_SCHEMA_VERSION:
            raise ValueError(f"不支持的工序技能要求 schema 版本: {self.schema_version}")
        self.process_id = str(self.process_id or "").strip()
        if not self.process_id:
            raise ValueError("工序技能要求必须提供 process_id")
        self.min_level = int(self.min_level)
        if not MIN_SKILL_LEVEL <= self.min_level <= MAX_SKILL_LEVEL:
            raise ValueError(
                f"最低技能等级必须为 {MIN_SKILL_LEVEL}~{MAX_SKILL_LEVEL}: "
                f"{self.min_level}")

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": self.schema_version,
                "process_id": self.process_id, "min_level": self.min_level}

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ProcessSkillReq | None:
        if data is None:
            return None
        if not isinstance(data, dict):
            raise ValueError("工序技能要求必须为 dict")
        schema = str(data.get("schema_version") or SKILL_SCHEMA_VERSION)
        if schema != SKILL_SCHEMA_VERSION:
            raise ValueError(f"不支持的工序技能要求 schema 版本: {schema}")
        allowed = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in allowed})


@dataclass
class SkillMatrix:
    """技能矩阵（同一 (人员, 工序) 只允许一条记录）+ 工序技能要求。"""

    entries: list[dict[str, Any]] = field(default_factory=list)
    requirements: list[dict[str, Any]] = field(default_factory=list)
    updated_at: str = ""
    schema_version: str = SKILL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SKILL_SCHEMA_VERSION:
            raise ValueError(f"不支持的技能矩阵 schema 版本: {self.schema_version}")
        normalized: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for index, item in enumerate(self.entries or [], start=1):
            if not isinstance(item, dict):
                raise ValueError(f"第 {index} 条技能记录必须为 dict")
            operator = str(item.get("operator") or "").strip()
            process_id = str(item.get("process_id") or "").strip()
            if not operator or not process_id:
                raise ValueError(f"第 {index} 条技能记录缺少 operator / process_id")
            key = (operator, process_id)
            if key in seen:
                raise ValueError(f"技能记录重复: {operator} × {process_id}")
            seen.add(key)
            try:
                level = int(item.get("level"))
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"技能等级必须为 {MIN_SKILL_LEVEL}~{MAX_SKILL_LEVEL} 整数: "
                    f"{item.get('level')!r}") from exc
            if not MIN_SKILL_LEVEL <= level <= MAX_SKILL_LEVEL:
                raise ValueError(
                    f"技能等级必须为 {MIN_SKILL_LEVEL}~{MAX_SKILL_LEVEL}: {level}")
            updated = str(item.get("updated_at") or "").strip()
            if updated:
                updated = parse_iso(updated, "updated_at").isoformat(timespec="seconds")
            normalized.append({"operator": operator, "process_id": process_id,
                               "level": level, "updated_at": updated})
        self.entries = normalized
        normalized_reqs: list[dict[str, Any]] = []
        seen_reqs: set[str] = set()
        for index, item in enumerate(self.requirements or [], start=1):
            if not isinstance(item, dict):
                raise ValueError(f"第 {index} 条工序技能要求必须为 dict")
            req = ProcessSkillReq(
                process_id=item.get("process_id", ""),
                min_level=item.get("min_level", 1))
            if req.process_id in seen_reqs:
                raise ValueError(f"工序技能要求重复: {req.process_id}")
            seen_reqs.add(req.process_id)
            normalized_reqs.append(req.to_dict())
        self.requirements = normalized_reqs
        self.updated_at = parse_iso(
            self.updated_at or now_iso(), "updated_at").isoformat(timespec="seconds")

    # ------------------------------------------------------------ 查询
    def level_of(self, operator: str, process_id: str) -> int | None:
        target = (str(operator or "").strip(), str(process_id or "").strip())
        for item in self.entries:
            if (item["operator"], item["process_id"]) == target:
                return int(item["level"])
        return None

    def operators_for(self, process_id: str, min_level: int = MIN_SKILL_LEVEL
                      ) -> list[str]:
        target = str(process_id or "").strip()
        floor = int(min_level)
        return [item["operator"] for item in self.entries
                if item["process_id"] == target and int(item["level"]) >= floor]

    def processes_for(self, operator: str) -> list[str]:
        target = str(operator or "").strip()
        return [item["process_id"] for item in self.entries
                if item["operator"] == target]

    def min_level_for(self, process_id: str) -> int | None:
        """工序最低技能等级；未设置返回 None。"""
        target = str(process_id or "").strip()
        for item in self.requirements:
            if item["process_id"] == target:
                return int(item["min_level"])
        return None

    def fingerprint(self) -> str:
        """技能矩阵指纹（凭证参数用）：entries + requirements 的稳定哈希。"""
        canonical = json.dumps(
            {"entries": self.entries, "requirements": self.requirements},
            sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return f"skill-hash-v1:{digest}"

    def __len__(self) -> int:
        return len(self.entries)

    # ------------------------------------------------------------ 序列化
    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "entries": [dict(item) for item in self.entries],
            "requirements": [dict(item) for item in self.requirements],
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> SkillMatrix:
        if data is None:
            return cls()
        if not isinstance(data, dict):
            raise ValueError("技能矩阵必须为 dict")
        schema = str(data.get("schema_version") or SKILL_SCHEMA_VERSION)
        if schema != SKILL_SCHEMA_VERSION:
            raise ValueError(f"不支持的技能矩阵 schema 版本: {schema}")
        allowed = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in allowed})


@dataclass
class SchedulePlan:
    """技能约束下的排班结果（B5 产出；不可行时给出 unmet 明细）。"""

    assignments: list[dict[str, Any]] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)
    balance_rate_before: float | None = None
    balance_rate_after: float | None = None
    unmet: list[str] = field(default_factory=list)
    plan_ref: str = ""
    created_at: str = ""
    schema_version: str = SKILL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SKILL_SCHEMA_VERSION:
            raise ValueError(f"不支持的排班计划 schema 版本: {self.schema_version}")
        normalized: list[dict[str, Any]] = []
        for index, item in enumerate(self.assignments or [], start=1):
            if not isinstance(item, dict):
                raise ValueError(f"第 {index} 条排班记录必须为 dict")
            process_id = str(item.get("process_id") or "").strip()
            operator = str(item.get("operator") or "").strip()
            if not process_id or not operator:
                raise ValueError(f"第 {index} 条排班记录缺少 process_id / operator")
            start_s = float(item.get("start_s") or 0.0)
            end_s = float(item.get("end_s") or 0.0)
            if end_s < start_s:
                raise ValueError(
                    f"第 {index} 条排班结束时间早于开始时间: "
                    f"{operator}@{process_id}")
            normalized.append({"process_id": process_id, "operator": operator,
                               "start_s": start_s, "end_s": end_s})
        self.assignments = normalized
        if not isinstance(self.constraints, dict):
            raise ValueError("排班约束 constraints 必须为 dict")
        for name in ("balance_rate_before", "balance_rate_after"):
            value = getattr(self, name)
            if value is not None:
                setattr(self, name, float(value))
        if not isinstance(self.unmet, (list, tuple)):
            raise ValueError("unmet 必须为字符串列表")
        self.unmet = [str(item) for item in self.unmet if str(item)]
        self.plan_ref = str(self.plan_ref or "").strip()
        self.created_at = parse_iso(
            self.created_at or now_iso(), "created_at").isoformat(timespec="seconds")

    @property
    def feasible(self) -> bool:
        return not self.unmet

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "assignments": [dict(item) for item in self.assignments],
            "constraints": dict(self.constraints),
            "balance_rate_before": self.balance_rate_before,
            "balance_rate_after": self.balance_rate_after,
            "unmet": list(self.unmet),
            "plan_ref": self.plan_ref,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> SchedulePlan | None:
        if data is None:
            return None
        if not isinstance(data, dict):
            raise ValueError("排班计划必须为 dict")
        schema = str(data.get("schema_version") or SKILL_SCHEMA_VERSION)
        if schema != SKILL_SCHEMA_VERSION:
            raise ValueError(f"不支持的排班计划 schema 版本: {schema}")
        allowed = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in allowed})


__all__ = [
    "SKILL_SCHEMA_VERSION",
    "MIN_SKILL_LEVEL",
    "MAX_SKILL_LEVEL",
    "ProcessSkillReq",
    "SkillMatrix",
    "SchedulePlan",
]
