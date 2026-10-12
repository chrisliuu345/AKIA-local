"""测量系统在线域契约 v1 — 量具研究策略与滚动状态（v4.4.0 B0）。

覆盖 PLAN_v4.4.0 §3.3 冻结的两类对象：

- ``GaugeStudyPolicy``：标准件测量与漂移判定的配置（期望值 / 窗口 / 规则 / 开关）；
- ``GaugeRollingState``：滚动重复性、偏倚及其历史、健康分与提示冷却状态。

B2 在此契约上实现滚动计算与控制图接线；本模块先冻结字段语义、校验与序列化，
并提供两个纯计算辅助（组内标准差 / 偏倚），避免 B2 重复造轮子。
本模块无 Qt、无 ui 依赖（core 分层守卫）。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, fields
from datetime import datetime
from typing import Any
from collections.abc import Iterable

from core.evidence import _jsonable
from core.time_utils import now_iso, parse_iso

GAUGE_SCHEMA_VERSION = "1"

#: 量具健康状态
GAUGE_STATES = ("ok", "watch", "drift")
#: 漂移规则支持的键（均为可选；未配置的规则不参与判定）
DRIFT_RULE_KEYS = ("ucl", "lcl", "cusum_h", "bias_limit")


def compute_repeatability(values: Iterable[float]) -> float:
    """组内重复性（样本标准差，ddof=1）；不足两点返回 0.0。"""
    clean = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    if len(clean) < 2:
        return 0.0
    mean = sum(clean) / len(clean)
    variance = sum((v - mean) ** 2 for v in clean) / (len(clean) - 1)
    return math.sqrt(variance)


def compute_bias(values: Iterable[float], expected_value: float) -> float:
    """偏倚 = 均值 − 期望值；无有效值返回 0.0。"""
    clean = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    if not clean:
        return 0.0
    return sum(clean) / len(clean) - float(expected_value)


@dataclass
class GaugeStudyPolicy:
    """一台量具（设备:通道）的在线研究策略。"""

    gauge_id: str
    standard_ref: str = ""           # 标准件规格（StandardRecord ID）
    expected_value: float = 0.0      # 标准件参考值
    window_n: int = 10               # 滚动窗口重复测量次数
    drift_rule: dict[str, float] = field(default_factory=dict)
    enabled: bool = True
    updated_at: str = ""
    schema_version: str = GAUGE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != GAUGE_SCHEMA_VERSION:
            raise ValueError(f"不支持的量具策略 schema 版本: {self.schema_version}")
        self.gauge_id = str(self.gauge_id or "").strip()
        if not self.gauge_id:
            raise ValueError("量具策略必须提供 gauge_id（设备:通道）")
        self.standard_ref = str(self.standard_ref or "").strip()
        self.expected_value = float(self.expected_value)
        if not math.isfinite(self.expected_value):
            raise ValueError(f"标准件参考值必须为有限数: {self.expected_value}")
        self.window_n = int(self.window_n or 0)
        if self.window_n < 2:
            raise ValueError(f"滚动窗口至少 2 次重复测量: {self.window_n}")
        if not isinstance(self.drift_rule, dict):
            raise ValueError("drift_rule 必须为 dict")
        normalized: dict[str, float] = {}
        for key, value in self.drift_rule.items():
            if key not in DRIFT_RULE_KEYS:
                raise ValueError(
                    f"未知漂移规则键: {key!r}（可选 {list(DRIFT_RULE_KEYS)}）")
            number = float(value)
            if not math.isfinite(number):
                raise ValueError(f"漂移规则 {key} 必须为有限数: {value}")
            normalized[key] = number
        if ("ucl" in normalized) != ("lcl" in normalized):
            raise ValueError("漂移规则 ucl/lcl 必须成对配置")
        self.drift_rule = normalized
        self.enabled = bool(self.enabled)
        self.updated_at = parse_iso(
            self.updated_at or now_iso(), "updated_at").isoformat(timespec="seconds")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "gauge_id": self.gauge_id,
            "standard_ref": self.standard_ref,
            "expected_value": self.expected_value,
            "window_n": self.window_n,
            "drift_rule": dict(self.drift_rule),
            "enabled": self.enabled,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GaugeStudyPolicy:
        if not isinstance(data, dict):
            raise ValueError("量具策略必须为 dict")
        schema = str(data.get("schema_version") or GAUGE_SCHEMA_VERSION)
        if schema != GAUGE_SCHEMA_VERSION:
            raise ValueError(f"不支持的量具策略 schema 版本: {schema}")
        allowed = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in allowed})


@dataclass
class GaugeRollingState:
    """量具滚动状态（B2 由标准件测量事件推进）。"""

    gauge_id: str
    n: int = 0
    repeatability_sigma: float = 0.0
    bias: float = 0.0
    bias_history: list[dict[str, Any]] = field(default_factory=list)
    health_score: float = 100.0
    state: str = "ok"
    last_prompt_at: str = ""
    updated_at: str = ""
    schema_version: str = GAUGE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != GAUGE_SCHEMA_VERSION:
            raise ValueError(f"不支持的量具状态 schema 版本: {self.schema_version}")
        self.gauge_id = str(self.gauge_id or "").strip()
        if not self.gauge_id:
            raise ValueError("量具状态必须提供 gauge_id")
        self.n = int(self.n or 0)
        if self.n < 0:
            raise ValueError(f"量具状态计数不能为负: {self.n}")
        self.repeatability_sigma = float(self.repeatability_sigma or 0.0)
        self.bias = float(self.bias or 0.0)
        if not math.isfinite(self.repeatability_sigma) or not math.isfinite(self.bias):
            raise ValueError("量具状态统计量必须为有限数")
        self.health_score = float(self.health_score)
        if not 0.0 <= self.health_score <= 100.0:
            raise ValueError(f"健康分必须在 0~100: {self.health_score}")
        self.state = str(self.state or "ok").strip().lower()
        if self.state not in GAUGE_STATES:
            raise ValueError(f"非法量具状态: {self.state!r}（可选 {list(GAUGE_STATES)}）")
        history: list[dict[str, Any]] = []
        for item in self.bias_history or []:
            if not isinstance(item, dict):
                raise ValueError("偏倚历史条目必须为 dict")
            history.append(_jsonable(item))
        self.bias_history = history
        self.last_prompt_at = str(self.last_prompt_at or "").strip()
        if self.last_prompt_at:
            self.last_prompt_at = parse_iso(
                self.last_prompt_at, "last_prompt_at").isoformat(timespec="seconds")
        self.updated_at = parse_iso(
            self.updated_at or now_iso(), "updated_at").isoformat(timespec="seconds")

    def prompt_cooldown_active(self, cooldown_s: float,
                               now: datetime | None = None) -> bool:
        """提示冷却是否生效（B2 用于避免"重做研究"提示轰炸）。"""
        if not self.last_prompt_at:
            return False
        last = parse_iso(self.last_prompt_at, "last_prompt_at")
        moment = now or datetime.now().astimezone()
        return (moment - last).total_seconds() < float(cooldown_s)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "gauge_id": self.gauge_id,
            "n": self.n,
            "repeatability_sigma": self.repeatability_sigma,
            "bias": self.bias,
            "bias_history": [dict(item) for item in self.bias_history],
            "health_score": self.health_score,
            "state": self.state,
            "last_prompt_at": self.last_prompt_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GaugeRollingState:
        if not isinstance(data, dict):
            raise ValueError("量具状态必须为 dict")
        schema = str(data.get("schema_version") or GAUGE_SCHEMA_VERSION)
        if schema != GAUGE_SCHEMA_VERSION:
            raise ValueError(f"不支持的量具状态 schema 版本: {schema}")
        allowed = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in allowed})


__all__ = [
    "GAUGE_SCHEMA_VERSION",
    "GAUGE_STATES",
    "DRIFT_RULE_KEYS",
    "GaugeStudyPolicy",
    "GaugeRollingState",
    "compute_bias",
    "compute_repeatability",
]
