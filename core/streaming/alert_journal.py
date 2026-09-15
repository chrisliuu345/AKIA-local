"""告警日志（Journal）— 等级 / 确认（ack）/ 审计留存（v3.8.0-③）。

JSONL 追加存储（每行一条），进程内写锁 + 原子追加，供桌面告警中心与
看板读取；确认操作回写 `ack/ack_by/ack_ts` 字段并记入审计日志。
纯 stdlib，无 Qt 依赖（analysis/core 层可复用）。
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

SEVERITY_INFO = "info"
SEVERITY_WARNING = "warning"
SEVERITY_CRITICAL = "critical"

SEVERITY_ORDER = {SEVERITY_INFO: 1, SEVERITY_WARNING: 2, SEVERITY_CRITICAL: 3}

SEVERITY_LABELS = {
    SEVERITY_INFO: "预告",
    SEVERITY_WARNING: "警告",
    SEVERITY_CRITICAL: "严重",
}

SEVERITY_COLORS = {
    SEVERITY_INFO: "#4aa8ff",
    SEVERITY_WARNING: "#f39c12",
    SEVERITY_CRITICAL: "#e74c3c",
}


def severity_label(severity: str) -> str:
    return SEVERITY_LABELS.get(severity, severity or "警告")


def severity_rank(severity: str) -> int:
    return SEVERITY_ORDER.get(severity, 0)


@dataclass
class JournalEntry:
    id: str
    ts: float
    device: str
    channel: str
    kind: str
    severity: str = SEVERITY_WARNING
    desc: str = ""
    value: float = 0.0
    ack: bool = False
    ack_by: str = ""
    ack_ts: float = 0.0
    note: str = ""
    extra: dict = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict) -> JournalEntry:
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})

    def summary(self) -> str:
        label = severity_label(self.severity)
        state = "已确认" if self.ack else "未确认"
        when = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.ts))
        return (f"[{label}·{state}] {when} {self.device}/{self.channel} "
                f"{self.desc} 值={self.value:.3f}")


def default_journal_path() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "data" / "alerts.jsonl"


class AlertJournal:
    """告警留存 — 追加写 JSONL，确认信息叠加写回。"""

    def __init__(self, path: str | Path | None = None, max_entries: int = 2000):
        self.path = Path(path) if path else default_journal_path()
        self.max_entries = max(1, int(max_entries))
        self._lock = threading.Lock()
        self._entries: list[JournalEntry] = []
        self._load()

    # ---------- 读写 ----------
    def _load(self) -> None:
        if not self.path.exists():
            return
        entries: list[JournalEntry] = []
        try:
            with open(self.path, encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    try:
                        entries.append(JournalEntry.from_dict(json.loads(stripped)))
                    except (json.JSONDecodeError, TypeError):
                        continue
        except OSError:
            return
        self._entries = entries[-self.max_entries:]

    def record(self, entry: JournalEntry) -> JournalEntry:
        """追加一条告警（含去重上限裁剪）。"""
        with self._lock:
            self._entries.append(entry)
            if len(self._entries) > self.max_entries:
                self._entries = self._entries[-self.max_entries:]
            self._append_line(entry.to_json())
        return entry

    def _append_line(self, line: str) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass  # 留存失败不影响告警主流程

    def _rewrite(self) -> None:
        """确认状态变更后整体重写（文件通常远小于 5MB，代价可接受）。"""
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(self.path.suffix + ".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                for entry in self._entries:
                    f.write(entry.to_json() + "\n")
            tmp.replace(self.path)
        except OSError:
            pass

    # ---------- 查询 ----------
    def entries(self, limit: int | None = None, severity: str | None = None,
                unacked_only: bool = False, device: str | None = None
                ) -> list[JournalEntry]:
        """倒序返回（最新在前）。"""
        with self._lock:
            items = list(reversed(self._entries))
        if severity:
            rank = severity_rank(severity)
            items = [e for e in items if severity_rank(e.severity) >= rank]
        if unacked_only:
            items = [e for e in items if not e.ack]
        if device:
            items = [e for e in items if e.device == device]
        return items[:limit] if limit else items

    def get(self, entry_id: str) -> JournalEntry | None:
        with self._lock:
            return next((e for e in self._entries if e.id == entry_id), None)

    def unacked_count(self, severity: str | None = None) -> int:
        return len(self.entries(severity=severity, unacked_only=True))

    # ---------- 确认 ----------
    def ack(self, entry_id: str, operator: str = "user", note: str = "") -> bool:
        """确认一条告警 — 写回 JSONL 并记审计。返回是否命中。"""
        with self._lock:
            entry = next((e for e in self._entries if e.id == entry_id), None)
            if entry is None or entry.ack:
                return False
            entry.ack = True
            entry.ack_by = operator
            entry.ack_ts = time.time()
            entry.note = note
            self._rewrite()
        from core.audit import audit
        audit("alert_ack", operator,
              f"{entry.device}/{entry.channel} {entry.kind} id={entry.id} {note}")
        return True

    def ack_all(self, operator: str = "user", severity: str | None = None) -> int:
        targets = [e.id for e in self.entries(severity=severity, unacked_only=True)]
        return sum(1 for tid in targets if self.ack(tid, operator, note="批量确认"))

    def clear(self) -> None:
        with self._lock:
            self._entries = []
            self._rewrite()


def entry_from_event(event) -> JournalEntry:
    """AlertEvent → JournalEntry（保持 core.streaming.alerts 单向依赖）。"""
    return JournalEntry(
        id=getattr(event, "id", "") or f"{time.time():.6f}",
        ts=float(getattr(event, "ts", time.time())),
        device=getattr(event, "device", ""),
        channel=getattr(event, "channel", ""),
        kind=getattr(event, "kind", ""),
        severity=getattr(event, "severity", SEVERITY_WARNING),
        desc=getattr(event, "desc", ""),
        value=float(getattr(event, "value", 0.0)),
    )
