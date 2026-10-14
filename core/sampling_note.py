"""展示/分析层抽样决定 v1（v4.4.0 B6）——隐式抽稀统一记录与标注。

覆盖三类此前"隐式抽样"的入口，统一产出可复现的 ``SamplingNote``：

- ``chart``：控制图 300 点智能系统抽样（判异点强制保留）；
- ``trend``：趋势图 1000 点等距抽稀（端点 / 极值保留）；
- ``profiler``：数据画像大样本正态检验的固定种子抽样。

原则：抽样方法 / 源规模 / 样本规模 / 种子 / 强制保留点数全部记录；
等距抽稀本身确定（可复现），随机抽样必须带固定种子；界面上的说明文本
由 ``SamplingNote.label()`` 统一生成——**不存在未标注的抽样**。

本模块无 Qt、无 ui 依赖（core 分层守卫）。
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any
from collections.abc import Iterable

import numpy as np

SAMPLING_NOTE_SCHEMA_VERSION = "1"

#: 允许的抽样层（新增层 = schema 变更，需评审）
NOTE_LAYERS = ("chart", "trend", "profiler")
#: 允许的抽样方法（head = 前 N 行截断，确定性）
NOTE_METHODS = ("systematic", "stride", "seeded_random", "head", "none")


@dataclass
class SamplingNote:
    """一条抽样决定（数据侧的留痕记录）。"""

    layer: str
    method: str
    source_count: int
    sampled_count: int
    seed: int | None = None
    reproducible: bool = True
    kept_count: int = 0
    detail: str = ""
    schema_version: str = SAMPLING_NOTE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SAMPLING_NOTE_SCHEMA_VERSION:
            raise ValueError(f"不支持的抽样决定 schema 版本: {self.schema_version}")
        self.layer = str(self.layer or "").strip().lower()
        if self.layer not in NOTE_LAYERS:
            raise ValueError(
                f"未知抽样层: {self.layer!r}（可选 {list(NOTE_LAYERS)}）")
        self.method = str(self.method or "").strip().lower()
        if self.method not in NOTE_METHODS:
            raise ValueError(
                f"未知抽样方法: {self.method!r}（可选 {list(NOTE_METHODS)}）")
        self.source_count = int(self.source_count)
        self.sampled_count = int(self.sampled_count)
        if self.source_count < 0 or self.sampled_count < 0:
            raise ValueError("抽样计数不能为负")
        if self.sampled_count > self.source_count:
            raise ValueError(
                f"样本数 ({self.sampled_count}) 不能超过源规模 "
                f"({self.source_count})")
        if self.seed is not None:
            self.seed = int(self.seed)
        self.reproducible = bool(self.reproducible)
        self.kept_count = int(self.kept_count)
        if self.kept_count < 0:
            raise ValueError("强制保留点数不能为负")
        self.detail = str(self.detail or "").strip()

    # ------------------------------------------------------------ 展示
    def label(self) -> str:
        """界面/图面说明文本；未发生抽样（method=none 或样本=全量）返回空串。"""
        if self.method == "none" or self.sampled_count >= self.source_count:
            return ""
        parts = [f"原始 {self.source_count} 点", f"抽样至 {self.sampled_count} 点"]
        if self.kept_count:
            parts.append(f"强制保留 {self.kept_count} 点")
        if self.seed is not None:
            parts.append(f"种子 {self.seed}（可复现）")
        elif self.reproducible:
            parts.append("可复现")
        if self.detail:
            parts.insert(0, self.detail)
        return "（" + "，".join(parts) + "）"

    # ------------------------------------------------------------ 序列化
    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "layer": self.layer,
            "method": self.method,
            "source_count": self.source_count,
            "sampled_count": self.sampled_count,
            "seed": self.seed,
            "reproducible": self.reproducible,
            "kept_count": self.kept_count,
            "detail": self.detail,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SamplingNote:
        if not isinstance(data, dict):
            raise ValueError("抽样决定必须为 dict")
        schema = str(data.get("schema_version") or SAMPLING_NOTE_SCHEMA_VERSION)
        if schema != SAMPLING_NOTE_SCHEMA_VERSION:
            raise ValueError(f"不支持的抽样决定 schema 版本: {schema}")
        allowed = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in allowed})


def _nearest_slot(sampled: list[int], target: int) -> int:
    return min(range(len(sampled)), key=lambda j: abs(sampled[j] - target))


def thin_indices(count: int, max_points: int, *, keep: Iterable[int] = (),
                 layer: str = "chart", method: str = "systematic",
                 detail: str = "") -> tuple[list[int], SamplingNote]:
    """等距抽稀索引（确定性）；``keep`` 索引强制保留（映射到最近槽位）。

    返回 (索引列表, SamplingNote)；未超上限时返回全量索引与 method="none"。
    """
    total = int(count)
    limit = int(max_points)
    if total < 0 or limit < 0:
        raise ValueError("计数不能为负")
    if limit == 0 or total <= limit:
        note = SamplingNote(layer=layer, method="none", source_count=total,
                            sampled_count=total)
        return list(range(total)), note
    keep_indices = sorted({int(item) for item in keep if 0 <= int(item) < total})
    step = total / limit
    sampled = [int(i * step) for i in range(limit)]
    kept = 0
    for target in keep_indices:
        if target in sampled:
            kept += 1
            continue
        sampled[_nearest_slot(sampled, target)] = target
        kept += 1
    sampled = sorted(set(sampled))
    note = SamplingNote(layer=layer, method=method, source_count=total,
                        sampled_count=len(sampled), kept_count=kept,
                        detail=detail)
    return sampled, note


def seeded_sample_indices(count: int, n: int, *, seed: int,
                          layer: str = "profiler",
                          detail: str = "") -> tuple[list[int], SamplingNote]:
    """固定种子随机抽样索引（无放回）；n≥count 时全量。"""
    total = int(count)
    size = int(n)
    if total < 0 or size < 0:
        raise ValueError("计数不能为负")
    if size == 0 or total <= size:
        note = SamplingNote(layer=layer, method="none", source_count=total,
                            sampled_count=total)
        return list(range(total)), note
    rng = np.random.default_rng(int(seed))
    indices = sorted(int(i) for i in rng.choice(total, size=size, replace=False))
    note = SamplingNote(layer=layer, method="seeded_random", source_count=total,
                        sampled_count=len(indices), seed=int(seed),
                        detail=detail)
    return indices, note


__all__ = [
    "SAMPLING_NOTE_SCHEMA_VERSION",
    "NOTE_LAYERS",
    "NOTE_METHODS",
    "SamplingNote",
    "seeded_sample_indices",
    "thin_indices",
]
