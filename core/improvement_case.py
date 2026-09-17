"""改善案例 schema v0 — 案例脊柱的第一版契约（v4.2.0 P0）。

完整生命周期对象（阶段引用、证据账本联动）在 v4.3.0 B1 扩展；
本版只定义最小可用字段与校验，保证 `.qap` 1.7 案例段可读写、可回放。
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from datetime import datetime
from typing import Any

CASE_SCHEMA_VERSION = "0"
CASE_STATUSES = ("draft", "active", "closed")
CASE_PHASES = ("baseline", "analyse", "improve", "re_measure", "verify", "standardise")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class ImprovementCase:
    """改善案例 v0 — 测量 → 分析 → 改善 → 复测 → 验证 → 标准的最小骨架。"""

    id: str
    title: str = ""
    status: str = "active"
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    baseline_refs: list[str] = field(default_factory=list)
    conclusion_refs: list[str] = field(default_factory=list)
    standard_draft: str = ""
    steps: list[dict[str, Any]] = field(default_factory=list)
    schema_version: str = CASE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not str(self.id or "").strip():
            raise ValueError("案例 id 不能为空")
        if self.status not in CASE_STATUSES:
            raise ValueError(f"非法案例状态: {self.status}（可选 {CASE_STATUSES}）")
        for name in ("baseline_refs", "conclusion_refs"):
            refs = getattr(self, name)
            if not isinstance(refs, list) or any(not isinstance(r, str) for r in refs):
                raise ValueError(f"{name} 必须为字符串列表")
        if not isinstance(self.steps, list):
            raise ValueError("steps 必须为列表")
        if self.schema_version != CASE_SCHEMA_VERSION:
            raise ValueError(f"不支持的案例 schema 版本: {self.schema_version}")
        self.id = str(self.id)

    def add_step(self, phase: str, ref: str = "", note: str = "") -> dict[str, Any]:
        """追加一个案例步骤并刷新时间戳；phase 建议取 ``CASE_PHASES``。"""
        if not str(phase or "").strip():
            raise ValueError("步骤 phase 不能为空")
        step = {"phase": str(phase), "ref": str(ref), "note": str(note), "at": _now()}
        self.steps.append(step)
        self.updated_at = step["at"]
        return step

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "baseline_refs": list(self.baseline_refs),
            "conclusion_refs": list(self.conclusion_refs),
            "standard_draft": self.standard_draft,
            "steps": [dict(step) for step in self.steps],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ImprovementCase:
        if not isinstance(d, dict):
            raise ValueError("案例必须为 dict")
        if not str(d.get("id") or "").strip():
            raise ValueError("案例缺少必填字段: id")
        schema = str(d.get("schema_version") or CASE_SCHEMA_VERSION)
        if schema != CASE_SCHEMA_VERSION:
            raise ValueError(f"不支持的案例 schema 版本: {schema}")
        allowed = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in allowed})
