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
from collections import deque
from collections.abc import Callable, Iterable

from core.streaming.live_spc import LiveSPC, LiveFrame

from core.evidence import _jsonable
from core.time_utils import now_iso, parse_iso

GAUGE_SCHEMA_VERSION = "1"

#: 量具健康状态
GAUGE_STATES = ("ok", "watch", "drift")
#: 漂移规则支持的键（均为可选；未配置的规则不参与判定）
DRIFT_RULE_KEYS = ("ucl", "lcl", "cusum_h", "bias_limit")

# ---------------------------------------------------------------- 在线监控（B2）
#: 健康分权重（覆盖率 / 偏倚 / 稳定性；合计 1.0，可按现场调整）
HEALTH_WEIGHTS = {"coverage": 0.2, "bias": 0.5, "stability": 0.3}
#: 偏倚序列 MPC 控制图滚动窗口
MPC_WINDOW = 30
#: MPC 最少预热点数（窗口过小时控制限不稳，只做偏倚限判定）
MPC_MIN_POINTS = 10
#: 漂移提示冷却（秒）——避免"重做研究"提示轰炸
PROMPT_COOLDOWN_S = 3600.0
#: watch 阈值：健康分低于该值或偏倚超过容忍限的 70%
WATCH_HEALTH_THRESHOLD = 70.0
WATCH_BIAS_RATIO = 0.7
#: 偏倚历史保留条数 / 每量具保留的事件引用数
MAX_BIAS_HISTORY = 500
MAX_EVENT_REFS = 100


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


def compute_health(*, n: int, window_n: int, bias: float, sigma: float,
                   bias_history: list[dict[str, Any]] | None,
                   bias_limit: float | None) -> float:
    """量具健康分 0–100（加权：覆盖率 / 偏倚 / 稳定性，权重见 HEALTH_WEIGHTS）。

    - 覆盖率：窗口内累计点数 / ``window_n``；
    - 偏倚：相对容忍限（``bias_limit``，未配置时取 3σ 重复性）线性衰减，
      |偏倚| 达 3× 容忍限记 0 分；
    - 稳定性：当次偏倚与历史偏倚（≥5 点历史）离散度的偏离，
      偏离达 3× 历史标准差记 0 分；历史不足时为满分（不惩罚冷启动）。
    """
    coverage = min(1.0, (int(n) / int(window_n)) if window_n else 0.0)
    limit = float(bias_limit) if bias_limit else (3.0 * sigma if sigma > 0 else None)
    if limit is None:
        bias_score = 1.0
    else:
        bias_score = max(0.0, min(1.0, 1.0 - abs(float(bias)) / (3.0 * limit)))
    history = [float(item.get("bias", 0.0)) for item in (bias_history or [])[:-1]
               if isinstance(item, dict)]
    if len(history) >= 5:
        mean = sum(history) / len(history)
        variance = sum((v - mean) ** 2 for v in history) / (len(history) - 1)
        sd = math.sqrt(variance)
        deviation = abs(float(bias) - mean)
        stability = 1.0 if sd <= 0 else max(
            0.0, min(1.0, 1.0 - deviation / (3.0 * sd)))
    else:
        stability = 1.0
    score = 100.0 * (HEALTH_WEIGHTS["coverage"] * coverage
                     + HEALTH_WEIGHTS["bias"] * bias_score
                     + HEALTH_WEIGHTS["stability"] * stability)
    return round(score, 1)


@dataclass
class GaugeOutcome:
    """一次监控推进的结果（``GaugeMonitor.ingest_*`` 的返回）。"""

    gauge_id: str
    n: int
    repeatability_sigma: float
    bias: float
    health_score: float
    state: str
    drift_reasons: list[str] = field(default_factory=list)
    prompt: bool = False
    event_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "gauge_id": self.gauge_id,
            "n": self.n,
            "repeatability_sigma": self.repeatability_sigma,
            "bias": self.bias,
            "health_score": self.health_score,
            "state": self.state,
            "drift_reasons": list(self.drift_reasons),
            "prompt": self.prompt,
            "event_id": self.event_id,
        }


class GaugeMonitor:
    """标准件测量滚动监控（无 Qt）。

    MeasurementEvent（四通道统一入口）→ 命中 ``GaugeStudyPolicy`` 的量具 →
    滚动窗口重复性/偏倚 → 偏倚序列接 ``LiveSPC``（I-MR，MPC 图）→ 健康分与
    漂移状态；漂移提示带冷却，避免轰炸。

    持久化：``to_dict()/from_dict()`` 对应 ``.qap`` 的 ``gauge_studies.json``
    （studies=策略列表、states=滚动状态列表）；重载时按偏倚历史重放 MPC 图，
    判定链延续。窗口内原始测量值不持久化（重启后重新累积），摘要与历史保留。
    """

    def __init__(self, policies: Iterable[GaugeStudyPolicy] | None = None,
                 states: Iterable[GaugeRollingState] | None = None, *,
                 prompt_cooldown_s: float = PROMPT_COOLDOWN_S,
                 clock: Callable[[], datetime] | None = None):
        self.policies: dict[str, GaugeStudyPolicy] = {}
        self.states: dict[str, GaugeRollingState] = {}
        self.prompt_cooldown_s = float(prompt_cooldown_s)
        self._clock = clock or (lambda: datetime.now().astimezone())
        self._spc: dict[str, LiveSPC] = {}
        self._frames: dict[str, LiveFrame] = {}
        self._windows: dict[str, deque] = {}
        self._event_ids: dict[str, deque] = {}
        for policy in policies or []:
            self.set_policy(policy)
        for state in states or []:
            self._restore_state(state)

    # ------------------------------------------------------------ 配置
    def set_policy(self, policy: GaugeStudyPolicy) -> GaugeStudyPolicy:
        if not isinstance(policy, GaugeStudyPolicy):
            raise TypeError("set_policy 仅接受 GaugeStudyPolicy")
        self.policies[policy.gauge_id] = policy
        existing = self._windows.get(policy.gauge_id)
        if existing is None or existing.maxlen != policy.window_n:
            self._windows[policy.gauge_id] = deque(
                existing or [], maxlen=policy.window_n)
        self._ensure_spc(policy)
        return policy

    def remove_policy(self, gauge_id: str, *, drop_state: bool = True) -> bool:
        target = str(gauge_id or "").strip()
        existed = self.policies.pop(target, None) is not None
        self._windows.pop(target, None)
        self._spc.pop(target, None)
        self._frames.pop(target, None)
        self._event_ids.pop(target, None)
        if drop_state:
            self.states.pop(target, None)
        return existed

    def _ensure_spc(self, policy: GaugeStudyPolicy) -> LiveSPC:
        spc = self._spc.get(policy.gauge_id)
        if spc is None:
            spc = LiveSPC(policy.gauge_id, mode="imr", window=MPC_WINDOW,
                          usl=policy.drift_rule.get("ucl"),
                          lsl=policy.drift_rule.get("lcl"))
            self._spc[policy.gauge_id] = spc
        else:
            spc.usl = policy.drift_rule.get("ucl")
            spc.lsl = policy.drift_rule.get("lcl")
        return spc

    def _restore_state(self, state: GaugeRollingState) -> None:
        self.states[state.gauge_id] = state
        spc = self._spc.get(state.gauge_id)
        if spc is None:
            policy = self.policies.get(state.gauge_id)
            spc = (self._ensure_spc(policy) if policy is not None
                   else self._spc.setdefault(state.gauge_id, LiveSPC(
                       state.gauge_id, mode="imr", window=MPC_WINDOW)))
        else:
            spc.reset()
        history = [float(item.get("bias", 0.0)) for item in state.bias_history
                   if isinstance(item, dict)]
        if history:
            self._frames[state.gauge_id] = spc.feed(history)

    # ------------------------------------------------------------ 匹配与摄入
    def match_gauge(self, event) -> str | None:
        """MeasurementEvent → 命中的量具 id（device:channel / characteristic_id / channel）。"""
        device = str(getattr(event, "device", "") or "").strip()
        channel = str(getattr(event, "channel", "") or "").strip()
        candidates = []
        if device and channel:
            candidates.append(f"{device}:{channel}")
        candidates.extend([
            str(getattr(event, "characteristic_id", "") or "").strip(),
            channel, device,
        ])
        for candidate in candidates:
            if candidate and candidate in self.policies:
                return candidate
        return None

    def ingest_event(self, event) -> GaugeOutcome | None:
        """事件命中量具策略时推进监控；未命中 / 无内联值 / 无效事件返回 None。"""
        gauge_id = self.match_gauge(event)
        if gauge_id is None:
            return None
        if str(getattr(event, "validity", "valid") or "valid") == "invalid":
            return None
        values = [float(v) for v in (getattr(event, "values", None) or [])]
        if not values:
            return None
        return self.ingest_values(
            gauge_id, values,
            at=str(getattr(event, "recorded_at", "") or ""),
            event_id=str(getattr(event, "event_id", "") or ""))

    def ingest_values(self, gauge_id: str, values, *, at: str = "",
                      event_id: str = "") -> GaugeOutcome:
        """向指定量具喂入一批重复测量值，返回滚动监控结果。"""
        target = str(gauge_id or "").strip()
        policy = self.policies.get(target)
        if policy is None:
            raise ValueError(f"未知量具策略: {target}（请先配置 gauge_id）")
        if not policy.enabled:
            raise ValueError(f"量具策略已禁用: {target}")
        numbers = [float(v) for v in values]
        if not numbers:
            raise ValueError("测量值不能为空")
        window = self._windows.setdefault(target, deque(maxlen=policy.window_n))
        window.extend(numbers)
        samples = list(window)
        sigma = compute_repeatability(samples)
        bias = compute_bias(samples, policy.expected_value)
        spc = self._ensure_spc(policy)
        frame = spc.feed([bias])
        self._frames[target] = frame
        state = self.states.get(target)
        if state is None:
            state = GaugeRollingState(gauge_id=target)
        stamp = parse_iso(at or now_iso(), "at").isoformat(timespec="seconds")
        state.n = len(samples)
        state.repeatability_sigma = round(sigma, 8)
        state.bias = round(bias, 8)
        state.bias_history.append({"at": stamp, "bias": state.bias,
                                   "sigma": state.repeatability_sigma,
                                   "n": state.n})
        if len(state.bias_history) > MAX_BIAS_HISTORY:
            del state.bias_history[:-MAX_BIAS_HISTORY]
        reasons: list[str] = []
        if frame.point_index >= MPC_MIN_POINTS and frame.events:
            for item in frame.events[:5]:
                reasons.append(f"MPC {item.kind}: {item.desc}")
        bias_limit = policy.drift_rule.get("bias_limit")
        if bias_limit is not None and abs(bias) > float(bias_limit):
            reasons.append(f"偏倚 {bias:.4g} 超限（|偏倚| > {float(bias_limit):g}）")
        health = compute_health(n=state.n, window_n=policy.window_n, bias=bias,
                                sigma=sigma, bias_history=state.bias_history,
                                bias_limit=bias_limit)
        if reasons:
            next_state = "drift"
        elif (health < WATCH_HEALTH_THRESHOLD
              or (bias_limit is not None
                  and abs(bias) > WATCH_BIAS_RATIO * float(bias_limit))):
            next_state = "watch"
        else:
            next_state = "ok"
        state.health_score = health
        state.state = next_state
        state.updated_at = stamp
        self.states[target] = state
        if event_id:
            refs = self._event_ids.setdefault(target, deque(maxlen=MAX_EVENT_REFS))
            refs.append(event_id)
        now = self._clock()
        prompt = (next_state == "drift"
                  and not state.prompt_cooldown_active(
                      self.prompt_cooldown_s, now=now))
        return GaugeOutcome(gauge_id=target, n=state.n,
                            repeatability_sigma=state.repeatability_sigma,
                            bias=state.bias, health_score=health,
                            state=next_state, drift_reasons=reasons,
                            prompt=prompt, event_id=event_id)

    def note_prompted(self, gauge_id: str, *, at: str = "") -> None:
        """记录一次"重做研究"提示（进入冷却窗口）。"""
        state = self.states.get(str(gauge_id or "").strip())
        if state is None:
            return
        stamp = at or self._clock().isoformat(timespec="seconds")
        state.last_prompt_at = parse_iso(stamp, "at").isoformat(timespec="seconds")

    # ------------------------------------------------------------ 查询
    def event_ids_for(self, gauge_id: str, limit: int = 20) -> list[str]:
        refs = self._event_ids.get(str(gauge_id or "").strip())
        return list(refs)[-int(limit):] if refs else []

    def frame_for(self, gauge_id: str) -> LiveFrame | None:
        return self._frames.get(str(gauge_id or "").strip())

    def snapshot(self) -> list[dict[str, Any]]:
        """界面用状态快照（策略 + 滚动状态 + MPC 控制限）。"""
        rows: list[dict[str, Any]] = []
        for gauge_id, policy in sorted(self.policies.items()):
            state = self.states.get(gauge_id)
            frame = self._frames.get(gauge_id)
            rows.append({
                "gauge_id": gauge_id,
                "expected_value": policy.expected_value,
                "window_n": policy.window_n,
                "enabled": policy.enabled,
                "n": state.n if state else 0,
                "repeatability_sigma": state.repeatability_sigma if state else 0.0,
                "bias": state.bias if state else 0.0,
                "health_score": state.health_score if state else 100.0,
                "state": state.state if state else "ok",
                "cl": getattr(frame, "cl", None) if frame else None,
                "ucl": getattr(frame, "ucl", None) if frame else None,
                "lcl": getattr(frame, "lcl", None) if frame else None,
                "spec_ucl": policy.drift_rule.get("ucl"),
                "spec_lcl": policy.drift_rule.get("lcl"),
                "bias_limit": policy.drift_rule.get("bias_limit"),
                "last_prompt_at": state.last_prompt_at if state else "",
            })
        return rows

    # ------------------------------------------------------------ 序列化
    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": GAUGE_SCHEMA_VERSION,
            "studies": [policy.to_dict() for policy in self.policies.values()],
            "states": [state.to_dict() for state in self.states.values()],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> GaugeMonitor:
        if data is None:
            return cls()
        if not isinstance(data, dict):
            raise ValueError("量具监控载荷必须为 dict")
        schema = str(data.get("schema_version") or GAUGE_SCHEMA_VERSION)
        if schema != GAUGE_SCHEMA_VERSION:
            raise ValueError(f"不支持的量具监控 schema 版本: {schema}")
        raw_studies = data.get("studies")
        raw_states = data.get("states")
        if raw_studies is None:
            raw_studies = []
        if raw_states is None:
            raw_states = []
        if not isinstance(raw_studies, list) or not isinstance(raw_states, list):
            raise ValueError("量具监控 studies/states 必须为列表")
        policies = [GaugeStudyPolicy.from_dict(item) for item in raw_studies]
        states = [GaugeRollingState.from_dict(item) for item in raw_states]
        return cls(policies, states)


__all__ = [
    "GAUGE_SCHEMA_VERSION",
    "GAUGE_STATES",
    "DRIFT_RULE_KEYS",
    "HEALTH_WEIGHTS",
    "MPC_WINDOW",
    "MPC_MIN_POINTS",
    "PROMPT_COOLDOWN_S",
    "WATCH_HEALTH_THRESHOLD",
    "WATCH_BIAS_RATIO",
    "GaugeStudyPolicy",
    "GaugeRollingState",
    "GaugeOutcome",
    "GaugeMonitor",
    "compute_bias",
    "compute_health",
    "compute_repeatability",
]
