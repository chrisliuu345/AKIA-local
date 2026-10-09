"""EvidenceEvent v1 + 哈希链账本（v4.3.0 B0/B4 契约）。

设计要点（与 `PLAN_v4.3.0.md` 第 3.4 节一致）:
- append-only JSONL，每条事件带 ``prev_hash`` 与 ``hash``，篡改可定位到首个断点；
- 账本只存引用与摘要，不复制原始数据；原始数据按 ``object_refs`` / ``raw_ref`` 回指；
- 文件模式支持"尾行截断恢复"（写入过程中崩溃留下的半行 JSON 会被丢弃并重写）；
- 本模块无 Qt、无 ui 依赖（core 分层守卫）。
"""

from __future__ import annotations

import hashlib
import json
import threading
import uuid
from dataclasses import dataclass, field, fields
from datetime import datetime
from pathlib import Path
from typing import Any

from core.evidence import _jsonable
from core.time_utils import now_iso, parse_iso

EVIDENCE_SCHEMA_VERSION = "1"
GENESIS_HASH = "0" * 64
EVENT_TYPES = (
    "data_imported",
    "measurement_recorded",
    "standard_changed",
    "analysis_run",
    "case_created",
    "case_step",
    "case_status_changed",
    "case_closed",
    "case_reopened",
    "report_exported",
    "evidence_pack_exported",
    "alert_ack",
    "data_edited",
    "share_pack_exported",
)


def new_event_id() -> str:
    stamp = datetime.now().astimezone().strftime("%Y%m%d%H%M%S")
    return f"EVT-{stamp}-{uuid.uuid4().hex[:4]}"


def canonical_json(payload: Any) -> str:
    """稳定 JSON 序列化（键排序 + 紧凑分隔符 + numpy 安全）。"""
    return json.dumps(_jsonable(payload), sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), default=str)


@dataclass
class EvidenceEvent:
    """一条账本事件。``type`` 在序列化层使用该名称，内部字段为 ``event_type``。"""

    seq: int
    event_type: str = ""
    prev_hash: str = GENESIS_HASH
    event_hash: str = ""
    event_id: str = field(default_factory=new_event_id)
    at: str = field(default_factory=now_iso)
    actor: str = "system"
    object_refs: list[str] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)
    schema_version: str = EVIDENCE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != EVIDENCE_SCHEMA_VERSION:
            raise ValueError(f"不支持的证据事件 schema 版本: {self.schema_version}")
        self.seq = int(self.seq)
        if self.seq < 1:
            raise ValueError("证据事件 seq 必须从 1 开始")
        self.event_type = str(self.event_type or "").strip()
        if self.event_type not in EVENT_TYPES:
            raise ValueError(f"未知证据事件类型: {self.event_type!r}（可选 {list(EVENT_TYPES)}）")
        self.event_id = str(self.event_id or "").strip() or new_event_id()
        self.at = parse_iso(self.at, "at").isoformat(timespec="seconds")
        self.actor = str(self.actor or "system").strip() or "system"
        if not isinstance(self.object_refs, (list, tuple)):
            raise ValueError("object_refs 必须为字符串列表")
        self.object_refs = [str(item) for item in self.object_refs if str(item)]
        if not isinstance(self.payload, dict):
            raise ValueError("payload 必须为 dict")
        self.payload = _jsonable(self.payload)
        self.prev_hash = str(self.prev_hash or GENESIS_HASH)
        if not self.event_hash:
            self.event_hash = self.compute_hash()

    def _hash_source(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "seq": self.seq,
            "event_id": self.event_id,
            "at": self.at,
            "type": self.event_type,
            "actor": self.actor,
            "object_refs": list(self.object_refs),
            "payload": self.payload,
            "prev_hash": self.prev_hash,
        }

    def compute_hash(self) -> str:
        digest = hashlib.sha256()
        digest.update(self.prev_hash.encode("utf-8"))
        digest.update(canonical_json(self._hash_source()).encode("utf-8"))
        return digest.hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "seq": self.seq,
            "event_id": self.event_id,
            "at": self.at,
            "type": self.event_type,
            "actor": self.actor,
            "object_refs": list(self.object_refs),
            "payload": dict(self.payload),
            "prev_hash": self.prev_hash,
            "hash": self.event_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvidenceEvent:
        if not isinstance(data, dict):
            raise ValueError("证据事件必须为 dict")
        schema = str(data.get("schema_version") or EVIDENCE_SCHEMA_VERSION)
        if schema != EVIDENCE_SCHEMA_VERSION:
            raise ValueError(f"不支持的证据事件 schema 版本: {schema}")
        normalized = dict(data)
        if "type" in normalized and "event_type" not in normalized:
            normalized["event_type"] = normalized.pop("type")
        if "hash" in normalized:
            normalized["event_hash"] = normalized.pop("hash")
        allowed = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in normalized.items() if k in allowed})


def verify_chain(events) -> dict[str, Any]:
    """校验事件序列的序号、prev_hash 链接与内容哈希。

    返回 ``{"ok", "count", "last_hash", "broken_at", "reason"}``；
    ``broken_at`` 为首个断点的 seq（1 基），无断点为 None。
    """
    previous = GENESIS_HASH
    items = list(events or [])
    for index, item in enumerate(items, start=1):
        try:
            event = item if isinstance(item, EvidenceEvent) else EvidenceEvent.from_dict(item)
        except (ValueError, TypeError) as exc:
            return {"ok": False, "count": len(items), "last_hash": previous,
                    "broken_at": index, "reason": f"第 {index} 条事件无法解析: {exc}"}
        if event.seq != index:
            return {"ok": False, "count": len(items), "last_hash": previous,
                    "broken_at": event.seq,
                    "reason": f"序号断点: 期望 {index}，实际 {event.seq}"}
        if event.prev_hash != previous:
            return {"ok": False, "count": len(items), "last_hash": previous,
                    "broken_at": event.seq,
                    "reason": f"prev_hash 不匹配: 期望 {previous[:12]}…，"
                              f"实际 {event.prev_hash[:12]}…"}
        if event.event_hash != event.compute_hash():
            return {"ok": False, "count": len(items), "last_hash": previous,
                    "broken_at": event.seq, "reason": "内容哈希不匹配（事件被篡改）"}
        previous = event.event_hash
    return {"ok": True, "count": len(items), "last_hash": previous,
            "broken_at": None, "reason": ""}


class EvidenceLedger:
    """项目内 append-only 证据账本（内存 + 可选 JSONL 文件）。"""

    def __init__(self, events: list[EvidenceEvent] | None = None, path: str = ""):
        self.events: list[EvidenceEvent] = list(events or [])
        self.path = str(path or "")
        self.load_errors: list[str] = []
        self.recovered_truncation = False
        self._lock = threading.RLock()

    # ------------------------------------------------------------ 读取
    @classmethod
    def from_events(cls, events) -> EvidenceLedger:
        return cls([item if isinstance(item, EvidenceEvent)
                    else EvidenceEvent.from_dict(item) for item in events or []])

    @classmethod
    def from_jsonl(cls, text: str, path: str = "") -> EvidenceLedger:
        raw = str(text or "")
        recovered = bool(raw) and not raw.endswith("\n")
        lines = raw.splitlines()
        if recovered and lines:
            lines = lines[:-1]
        events: list[EvidenceEvent] = []
        errors: list[str] = []
        for index, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                events.append(EvidenceEvent.from_dict(json.loads(stripped)))
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                errors.append(f"第 {index} 行: {exc}")
        ledger = cls(events, path=path)
        ledger.load_errors = errors
        ledger.recovered_truncation = recovered
        return ledger

    @classmethod
    def from_bytes(cls, data: bytes | str, path: str = "") -> EvidenceLedger:
        text = data.decode("utf-8") if isinstance(data, bytes) else str(data or "")
        return cls.from_jsonl(text, path=path)

    @classmethod
    def load_file(cls, path: str | Path) -> EvidenceLedger:
        target = Path(path)
        if not target.exists():
            ledger = cls(path=str(target))
            return ledger
        ledger = cls.from_jsonl(target.read_text(encoding="utf-8"), path=str(target))
        if ledger.recovered_truncation and not ledger.load_errors:
            # 崩溃遗留的半行 JSON 已在内存中丢弃，同步重写干净文件
            target.write_text(ledger.to_jsonl(), encoding="utf-8")
        return ledger

    # ------------------------------------------------------------ 写入
    def append(self, event_type: str, *, actor: str = "system",
               object_refs: list[str] | None = None,
               payload: dict[str, Any] | None = None,
               at: str = "", event_id: str = "") -> EvidenceEvent:
        with self._lock:
            if self.load_errors:
                raise RuntimeError(
                    "账本存在解析错误，拒绝追加（先修复或导出取证）: "
                    + "；".join(self.load_errors[:3]))
            previous = self.events[-1].event_hash if self.events else GENESIS_HASH
            event = EvidenceEvent(
                seq=len(self.events) + 1,
                event_type=event_type,
                prev_hash=previous,
                event_id=event_id or new_event_id(),
                at=at or now_iso(),
                actor=actor,
                object_refs=list(object_refs or []),
                payload=dict(payload or {}),
            )
            self.events.append(event)
            if self.path:
                self._append_line(event)
            return event

    def _append_line(self, event: EvidenceEvent) -> None:
        path = Path(self.path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.to_dict(), ensure_ascii=False,
                                    separators=(",", ":")) + "\n")
            handle.flush()

    # ------------------------------------------------------------ 查询/导出
    def __len__(self) -> int:
        return len(self.events)

    def iter_events(self):
        return iter(self.events)

    def events_for(self, ref: str) -> list[EvidenceEvent]:
        target = str(ref or "").strip()
        if not target:
            return []
        matches = []
        for event in self.events:
            if target in event.object_refs:
                matches.append(event)
                continue
            if any(isinstance(v, str) and v == target for v in event.payload.values()):
                matches.append(event)
        return matches

    def verify(self) -> dict[str, Any]:
        result = verify_chain(self.events)
        if result["ok"] and self.load_errors:
            return {"ok": False, "count": len(self.events),
                    "last_hash": result["last_hash"], "broken_at": None,
                    "reason": "；".join(self.load_errors[:3])}
        return result

    def to_jsonl(self) -> str:
        return "".join(json.dumps(event.to_dict(), ensure_ascii=False,
                                  separators=(",", ":")) + "\n"
                       for event in self.events)

    def to_bytes(self) -> bytes:
        return self.to_jsonl().encode("utf-8")

    def save_file(self, path: str | Path) -> str:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.to_jsonl(), encoding="utf-8")
        self.path = str(target)
        return self.path

    def export_manifest(self) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for event in self.events:
            counts[event.event_type] = counts.get(event.event_type, 0) + 1
        chain = self.verify()
        return {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "event_count": len(self.events),
            "last_hash": chain.get("last_hash", GENESIS_HASH),
            "chain_ok": bool(chain.get("ok")),
            "types": counts,
            "first_at": self.events[0].at if self.events else "",
            "last_at": self.events[-1].at if self.events else "",
            "generated_at": now_iso(),
        }


def file_sha256(path: str | Path) -> str:
    """文件内容 SHA-256（证据包 manifest 用）。"""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


__all__ = [
    "EVIDENCE_SCHEMA_VERSION",
    "GENESIS_HASH",
    "EVENT_TYPES",
    "EvidenceEvent",
    "EvidenceLedger",
    "canonical_json",
    "file_sha256",
    "new_event_id",
    "verify_chain",
]
