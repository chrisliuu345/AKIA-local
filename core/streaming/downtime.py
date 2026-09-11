"""停机事件追踪（v3.8.0-⑤）— 原因码 / 时长统计 / 班次窗口汇总。

实时 OEE 的可用率损失与成本损失均以本模块为准: 产线停机（start/end）按
时间区间记录，可查询窗口内总时长、当前原因与原因码分布。
纯 stdlib，无 Qt 依赖。
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass

# 缺省停机原因码（可由 user_config `downtime_reason_codes` 覆盖）
DEFAULT_REASON_CODES = ("换型", "故障", "缺料", "保养", "质量停线", "其他")


@dataclass
class DowntimeRecord:
    line: str
    reason: str = "其他"
    device: str = ""
    start_ts: float = 0.0
    end_ts: float | None = None
    note: str = ""

    def duration(self, now: float | None = None) -> float:
        end = self.end_ts if self.end_ts is not None else (now or time.time())
        return max(0.0, end - self.start_ts)

    def overlap(self, window_start: float, window_end: float) -> float:
        """与 [window_start, window_end] 的重叠时长。"""
        end = self.end_ts if self.end_ts is not None else window_end
        lo = max(self.start_ts, window_start)
        hi = min(end, window_end)
        return max(0.0, hi - lo)


class DowntimeTracker:
    """停机记录器 — 每产线同时只有一段进行中的停机。"""

    def __init__(self, reason_codes: tuple[str, ...] | list[str] | None = None,
                 max_records: int = 2000):
        self.reason_codes = tuple(reason_codes or DEFAULT_REASON_CODES)
        self.max_records = max(10, int(max_records))
        self._records: list[DowntimeRecord] = []
        self._lock = threading.Lock()

    # ---------- 记录 ----------
    def start(self, line: str, reason: str = "其他", device: str = "",
              ts: float | None = None) -> DowntimeRecord:
        """开始一段停机；已在停机中则原样返回进行中的记录。"""
        with self._lock:
            current = self._current(line)
            if current is not None:
                return current
            rec = DowntimeRecord(line=line, reason=self.normalize_reason(reason),
                                 device=device, start_ts=ts or time.time())
            self._records.append(rec)
            if len(self._records) > self.max_records:
                self._records = self._records[-self.max_records:]
            return rec

    def end(self, line: str, ts: float | None = None) -> DowntimeRecord | None:
        with self._lock:
            current = self._current(line)
            if current is None:
                return None
            current.end_ts = ts or time.time()
            return current

    def _current(self, line: str) -> DowntimeRecord | None:
        for rec in reversed(self._records):
            if rec.line == line and rec.end_ts is None:
                return rec
        return None

    def normalize_reason(self, reason: str) -> str:
        """未知原因码归入「其他」（保留原始描述到 note 由调用方处理）。"""
        text = str(reason or "").strip()
        if text in self.reason_codes:
            return text
        return "其他" if "其他" in self.reason_codes else (text or "其他")

    # ---------- 查询 ----------
    def is_down(self, line: str) -> bool:
        with self._lock:
            return self._current(line) is not None

    def current(self, line: str) -> DowntimeRecord | None:
        with self._lock:
            return self._current(line)

    def records(self, line: str | None = None, limit: int | None = None
                ) -> list[DowntimeRecord]:
        with self._lock:
            items = [r for r in self._records if line is None or r.line == line]
        return items[-limit:] if limit else items

    def downtime_seconds(self, line: str, window_s: float | None = None,
                         now: float | None = None) -> float:
        now = now or time.time()
        window_start = 0.0 if window_s is None else now - float(window_s)
        with self._lock:
            items = [r for r in self._records if r.line == line]
        return sum(r.overlap(window_start, now) for r in items)

    def breakdown(self, window_s: float | None = None, now: float | None = None
                  ) -> dict[str, dict[str, float]]:
        """产线 → 原因码 → 停机时长（秒）。"""
        now = now or time.time()
        window_start = 0.0 if window_s is None else now - float(window_s)
        out: dict[str, dict[str, float]] = {}
        for rec in self.records():
            overlap = rec.overlap(window_start, now)
            if overlap <= 0:
                continue
            out.setdefault(rec.line, {})
            out[rec.line][rec.reason] = out[rec.line].get(rec.reason, 0.0) + overlap
        return out

    def snapshot(self, window_s: float | None = None,
                 now: float | None = None) -> dict[str, dict]:
        now = now or time.time()
        breakdown = self.breakdown(window_s, now)
        out: dict[str, dict] = {}
        lines = {r.line for r in self.records()} | set(breakdown)
        for line in lines:
            current = self.current(line)
            out[line] = {
                "down": current is not None,
                "reason": current.reason if current is not None else "",
                "downtime_s": round(self.downtime_seconds(line, window_s, now), 2),
                "breakdown": {k: round(v, 1) for k, v in
                              (breakdown.get(line) or {}).items()},
            }
        return out

    def clear(self) -> None:
        with self._lock:
            self._records = []
