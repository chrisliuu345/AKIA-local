"""连接器健康度与重连退避（v3.8.0-⑦）。

对标 Kepware 连接树: 每个数据源维护 状态 / 最近错误 / 连续失败次数 /
下次重试时间；失败后按指数退避（base × factor^(n-1)，上限 max）重连，
恢复后自动清零。纯 stdlib，采集线程与 UI 均直接读取快照。
"""
from __future__ import annotations

import threading
import time
from dataclasses import asdict, dataclass, field

STATUS_UNKNOWN = "unknown"
STATUS_ONLINE = "online"
STATUS_DEGRADED = "degraded"     # 曾失败但尚未到重试时间
STATUS_ERROR = "error"           # 连续失败达到阈值
STATUS_STOPPED = "stopped"

STATUS_LABELS = {
    STATUS_UNKNOWN: "未连接",
    STATUS_ONLINE: "在线",
    STATUS_DEGRADED: "重连中",
    STATUS_ERROR: "异常",
    STATUS_STOPPED: "已停止",
}

STATUS_COLORS = {
    STATUS_UNKNOWN: "#9aa4b2",
    STATUS_ONLINE: "#27ae60",
    STATUS_DEGRADED: "#f39c12",
    STATUS_ERROR: "#e74c3c",
    STATUS_STOPPED: "#6e7080",
}


@dataclass
class ConnectorHealth:
    name: str
    kind: str = "connector"          # connector / device
    status: str = STATUS_UNKNOWN
    consecutive_errors: int = 0
    total_errors: int = 0
    total_ok: int = 0
    last_ok_ts: float = 0.0
    last_error: str = ""
    last_error_ts: float = 0.0
    next_retry_ts: float = 0.0
    backoff_s: float = 0.0
    samples: int = 0
    extra: dict = field(default_factory=dict)

    def status_label(self) -> str:
        return STATUS_LABELS.get(self.status, self.status)

    def as_dict(self) -> dict:
        data = asdict(self)
        data["status_label"] = self.status_label()
        return data


class HealthRegistry:
    """连接健康度注册表 — 线程安全，供采集线程写、UI 读。"""

    def __init__(self, base_backoff_s: float = 1.0, max_backoff_s: float = 60.0,
                 factor: float = 2.0, error_threshold: int = 3, clock=None):
        self.base_backoff_s = float(base_backoff_s)
        self.max_backoff_s = float(max_backoff_s)
        self.factor = float(factor)
        self.error_threshold = max(1, int(error_threshold))
        self._clock = clock or time.time
        self._states: dict[str, ConnectorHealth] = {}
        self._lock = threading.Lock()

    # ---------- 注册 / 查询 ----------
    def register(self, name: str, kind: str = "connector",
                 **extra) -> ConnectorHealth:
        with self._lock:
            state = self._states.get(name)
            if state is None:
                state = ConnectorHealth(name=name, kind=kind,
                                        extra=dict(extra or {}))
                self._states[name] = state
            elif extra:
                state.extra.update(extra)
            return state

    def get(self, name: str) -> ConnectorHealth | None:
        with self._lock:
            return self._states.get(name)

    def names(self) -> list[str]:
        with self._lock:
            return sorted(self._states)

    def snapshot(self) -> dict[str, dict]:
        with self._lock:
            return {name: state.as_dict() for name, state in self._states.items()}

    def clear(self) -> None:
        with self._lock:
            self._states.clear()

    # ---------- 状态迁移 ----------
    def mark_ok(self, name: str, samples: int = 0) -> ConnectorHealth:
        with self._lock:
            state = self._states.setdefault(name, ConnectorHealth(name=name))
            now = self._clock()
            state.status = STATUS_ONLINE
            state.consecutive_errors = 0
            state.backoff_s = 0.0
            state.next_retry_ts = 0.0
            state.last_ok_ts = now
            state.samples += int(samples or 0)
            state.total_ok += 1
            state.last_error = ""
            return state

    def mark_error(self, name: str, error: str = "") -> ConnectorHealth:
        with self._lock:
            state = self._states.setdefault(name, ConnectorHealth(name=name))
            now = self._clock()
            state.consecutive_errors += 1
            state.total_errors += 1
            state.last_error = str(error)[:300]
            state.last_error_ts = now
            state.backoff_s = self.backoff_for(state.consecutive_errors)
            state.next_retry_ts = now + state.backoff_s
            state.status = (STATUS_ERROR
                            if state.consecutive_errors >= self.error_threshold
                            else STATUS_DEGRADED)
            return state

    def backoff_for(self, consecutive_errors: int) -> float:
        """第 n 次连续失败的等待秒数 = base × factor^(n-1)，上限 max。"""
        n = max(1, int(consecutive_errors))
        delay = self.base_backoff_s * (self.factor ** (n - 1))
        return float(min(self.max_backoff_s, delay))

    def should_poll(self, name: str) -> bool:
        with self._lock:
            state = self._states.get(name)
            if state is None:
                return True
            return self._clock() >= state.next_retry_ts

    def retry_in(self, name: str) -> float:
        state = self.get(name)
        if state is None:
            return 0.0
        return max(0.0, state.next_retry_ts - self._clock())

    def mark_stopped(self, name: str) -> None:
        with self._lock:
            state = self._states.setdefault(name, ConnectorHealth(name=name))
            state.status = STATUS_STOPPED
            state.next_retry_ts = 0.0

    def reset(self, name: str) -> None:
        """手动重连前的复位 — 立即允许下一次轮询。"""
        with self._lock:
            state = self._states.get(name)
            if state is None:
                return
            state.consecutive_errors = 0
            state.backoff_s = 0.0
            state.next_retry_ts = 0.0
            state.status = STATUS_UNKNOWN
