"""动作分类（工作/空闲/走动/搬运/离岗）— 规则状态机 + 迟滞，无需训练数据。

输入 PoseFrame 的运动/姿态特征，输出带最短驻留（迟滞）的状态段，
避免抖动把一次作业切成碎片；阈值集中在 ActionConfig，可按现场校准。
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, replace
from enum import Enum

from analysis.vision.pose import PoseFrame


class ActionState(str, Enum):
    WORKING = "working"
    IDLE = "idle"
    WALKING = "walking"
    CARRYING = "carrying"
    AWAY = "away"
    UNKNOWN = "unknown"


ACTION_LABELS: dict[ActionState, str] = {
    ActionState.WORKING: "工作",
    ActionState.IDLE: "空闲",
    ActionState.WALKING: "走动",
    ActionState.CARRYING: "搬运",
    ActionState.AWAY: "离岗",
    ActionState.UNKNOWN: "未知",
}

ACTION_COLORS: dict[ActionState, str] = {
    ActionState.WORKING: "#4CAF50",
    ActionState.IDLE: "#FF9800",
    ActionState.WALKING: "#2196F3",
    ActionState.CARRYING: "#3F51B5",
    ActionState.AWAY: "#F44336",
    ActionState.UNKNOWN: "#9E9E9E",
}

# 工作抽样自定义状态表（标签为 Vision 语义，可直接交给 WorkSamplingEngine）
VISION_STATUSES = OrderedDict([
    ("working", {"label": "工作", "color": ACTION_COLORS[ActionState.WORKING],
                 "productive": True}),
    ("idle", {"label": "空闲", "color": ACTION_COLORS[ActionState.IDLE],
              "productive": False}),
    ("walking", {"label": "走动", "color": ACTION_COLORS[ActionState.WALKING],
                 "productive": False}),
    ("carrying", {"label": "搬运", "color": ACTION_COLORS[ActionState.CARRYING],
                  "productive": True}),
    ("away", {"label": "离岗", "color": ACTION_COLORS[ActionState.AWAY],
              "productive": False}),
])


@dataclass
class ActionConfig:
    walk_speed_px_s: float = 40.0       # 质心速度 ≥ 此值 → 走动/搬运
    carry_speed_px_s: float = 8.0       # 低于走动但有搬运姿态 → 搬运
    work_motion_energy: float = 0.015   # 前景占比 ≥ 此值 → 工作
    work_activity: float = 0.0015       # 帧差占比 ≥ 此值（原地动作）→ 工作
    work_arm_swing: float = 0.08        # 手腕摆动 ≥ 此值 → 工作
    carry_arm_swing_max: float = 0.06   # 搬运时手臂摆动较小的判据
    min_dwell_ms: float = 700.0         # 状态切换最短驻留（迟滞）

    def merged(self, **overrides) -> "ActionConfig":
        valid = {k: v for k, v in overrides.items()
                 if v is not None and k in self.__dataclass_fields__}
        return replace(self, **valid) if valid else self


@dataclass
class ActionSegment:
    start_ms: float
    end_ms: float
    state: ActionState
    frames: int = 0

    @property
    def duration_s(self) -> float:
        return max(0.0, (self.end_ms - self.start_ms) / 1000.0)

    def to_dict(self) -> dict:
        return {"start_ms": round(self.start_ms, 1),
                "end_ms": round(self.end_ms, 1),
                "state": self.state.value,
                "label": ACTION_LABELS[self.state],
                "duration_s": round(self.duration_s, 3),
                "frames": self.frames}


def classify_pose(pose: PoseFrame, config: ActionConfig | None = None) -> ActionState:
    """单帧规则判定（无迟滞）。"""
    cfg = config or ActionConfig()
    if not pose.person_present:
        return ActionState.AWAY
    speed = float(pose.speed_px_s or 0.0)
    has_pose = bool(pose.landmarks)
    carry_posture = has_pose and pose.wrists_low and pose.arm_swing <= cfg.carry_arm_swing_max
    if speed >= cfg.walk_speed_px_s:
        return ActionState.CARRYING if carry_posture else ActionState.WALKING
    if speed >= cfg.carry_speed_px_s and carry_posture:
        return ActionState.CARRYING
    if (pose.activity_energy >= cfg.work_activity
            or pose.motion_energy >= cfg.work_motion_energy
            or pose.arm_swing >= cfg.work_arm_swing):
        return ActionState.WORKING
    return ActionState.IDLE


class ActionClassifier:
    """带迟滞的状态机：候选状态持续 min_dwell 才切换并生成状态段。"""

    def __init__(self, config: ActionConfig | None = None):
        self.config = config or ActionConfig()
        self._segments: list[ActionSegment] = []
        self.reset()

    def reset(self):
        self._segments = []
        self._state = ActionState.UNKNOWN
        self._state_start: float | None = None
        self._state_frames = 0
        self._candidate: ActionState | None = None
        self._candidate_since: float | None = None
        self._last_ts: float | None = None

    def update(self, pose: PoseFrame) -> ActionState:
        raw = classify_pose(pose, self.config)
        ts = float(pose.ts_ms)
        if self._state_start is None:
            self._state, self._state_start = raw, ts
            self._state_frames = 1
            self._last_ts = ts
            return raw
        if raw == self._state:
            self._state_frames += 1
            self._candidate = None
        else:
            if self._candidate != raw:
                self._candidate = raw
                self._candidate_since = ts
            elif (self._candidate_since is not None
                  and ts - self._candidate_since >= self.config.min_dwell_ms):
                self._close_segment(self._candidate_since)
                self._state = raw
                self._state_start = self._candidate_since
                self._state_frames = 1
                self._candidate = None
        self._last_ts = ts
        return self._state

    @property
    def state(self) -> ActionState:
        return self._state

    def finish(self, ts_ms: float | None = None):
        end = ts_ms if ts_ms is not None else self._last_ts
        if end is not None:
            self._close_segment(end)
        self._state = ActionState.UNKNOWN
        self._state_start = None

    def _close_segment(self, end_ms: float):
        if (self._state == ActionState.UNKNOWN or self._state_start is None
                or end_ms <= self._state_start):
            return
        self._segments.append(ActionSegment(
            start_ms=self._state_start, end_ms=end_ms,
            state=self._state, frames=self._state_frames))

    def segments(self) -> list[ActionSegment]:
        return list(self._segments)


def duration_by_state(segments: list[ActionSegment]) -> dict[str, float]:
    out: dict[str, float] = {}
    for seg in segments:
        out[seg.state.value] = out.get(seg.state.value, 0.0) + seg.duration_s
    return out


def ratio_by_state(segments: list[ActionSegment]) -> dict[str, float]:
    """各状态时长占比（%，已知状态之和为 100）。"""
    durations = duration_by_state(segments)
    total = sum(durations.values())
    if total <= 0:
        return {}
    return {state: round(seconds / total * 100.0, 2)
            for state, seconds in durations.items()}
