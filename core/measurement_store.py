"""MeasurementStore v1 — 项目内测量事件集合（v4.3.0 B2）。

- 内存集合按 ``event_id`` 幂等去重，超过 ``max_events`` 时 FIFO 截断；
- JSONL 序列化与账本同款容错：写入中崩溃留下的半行在读取时丢弃；
- 随 `.qap` 1.9 的 ``measurements.jsonl`` 段持久化（B2）。

本模块无 Qt、无 ui 依赖（core 分层守卫）。
"""

from __future__ import annotations

import contextlib
import json
from pathlib import Path

from core.measurement_event import MeasurementEvent

MEASUREMENT_STORE_SCHEMA_VERSION = "1"
DEFAULT_MAX_EVENTS = 2000


class MeasurementStore:
    """测量事件集合（默认最多 2000 条，防止长时采集撑大项目文件）。"""

    def __init__(self, events=None, max_events: int = DEFAULT_MAX_EVENTS):
        self.max_events = int(max_events or 0)
        self.events: list[MeasurementEvent] = []
        self.load_errors: list[str] = []
        self.recovered_truncation = False
        self.event_sink = None      # Callable[[MeasurementEvent], None] | None
        self.extend(events or [])

    # ------------------------------------------------------------ 写入
    @staticmethod
    def _normalize(event) -> MeasurementEvent:
        if isinstance(event, MeasurementEvent):
            return event
        return MeasurementEvent.from_dict(event)

    def add(self, event) -> MeasurementEvent:
        """按 event_id 幂等写入（重复 ID 覆盖旧值），返回规范化事件。"""
        normalized = self._normalize(event)
        for index, existing in enumerate(self.events):
            if existing.event_id == normalized.event_id:
                self.events[index] = normalized
                return normalized
        self.events.append(normalized)
        self._trim()
        if callable(self.event_sink):
            with contextlib.suppress(Exception):  # 记账失败不得阻断测量写入
                self.event_sink(normalized)
        return normalized

    def extend(self, events) -> list[MeasurementEvent]:
        return [self.add(event) for event in events or []]

    def _trim(self) -> None:
        if self.max_events and len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]

    def clear(self) -> None:
        self.events = []

    # ------------------------------------------------------------ 查询
    def __len__(self) -> int:
        return len(self.events)

    def __iter__(self):
        return iter(self.events)

    def get(self, event_id: str) -> MeasurementEvent | None:
        target = str(event_id or "").strip()
        return next((e for e in self.events if e.event_id == target), None)

    def by_ids(self, event_ids) -> list[MeasurementEvent]:
        wanted = [str(item) for item in event_ids or []]
        index = {event.event_id: event for event in self.events}
        return [index[item] for item in wanted if item in index]

    def to_dicts(self) -> list[dict]:
        return [event.to_dict() for event in self.events]

    # ------------------------------------------------------------ 序列化
    def to_jsonl(self) -> str:
        return "".join(json.dumps(event.to_dict(), ensure_ascii=False,
                                  separators=(",", ":")) + "\n"
                       for event in self.events)

    def to_bytes(self) -> bytes:
        return self.to_jsonl().encode("utf-8")

    @classmethod
    def from_jsonl(cls, text: str, *, max_events: int = DEFAULT_MAX_EVENTS) -> MeasurementStore:
        raw = str(text or "")
        recovered = bool(raw) and not raw.endswith("\n")
        lines = raw.splitlines()
        if recovered and lines:
            lines = lines[:-1]
        store = cls(max_events=max_events)
        for index, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                store.add(json.loads(stripped))
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                store.load_errors.append(f"第 {index} 行: {exc}")
        store.recovered_truncation = recovered
        return store

    @classmethod
    def from_bytes(cls, data: bytes | str, *,
                   max_events: int = DEFAULT_MAX_EVENTS) -> MeasurementStore:
        text = data.decode("utf-8") if isinstance(data, bytes) else str(data or "")
        return cls.from_jsonl(text, max_events=max_events)

    def save_file(self, path: str | Path) -> str:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.to_jsonl(), encoding="utf-8")
        return str(target)

    @classmethod
    def load_file(cls, path: str | Path) -> MeasurementStore:
        target = Path(path)
        if not target.exists():
            return cls()
        store = cls.from_jsonl(target.read_text(encoding="utf-8"))
        if store.recovered_truncation and not store.load_errors:
            target.write_text(store.to_jsonl(), encoding="utf-8")
        return store
