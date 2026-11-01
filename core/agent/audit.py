"""本地模型调用审计 — 有界 JSONL 存储，无 Qt、无外发。

审计保存问题、模型配置、工具调用和回答；原始提示词只保留长度与哈希，
避免把整段对话历史和知识库内容反复写入磁盘。API Key 永远不进入记录。
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import logging
import math
import numbers
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from core.runtime_paths import default_data_path

logger = logging.getLogger("AKIA.ModelAudit")

MODEL_AUDIT_SCHEMA_VERSION = "1.0"


def prompt_digest(prompt: str) -> str:
    return hashlib.sha256((prompt or "").encode("utf-8")).hexdigest()


def _safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, numbers.Integral):
        return int(value)
    if isinstance(value, numbers.Real):
        number = float(value)
        return number if math.isfinite(number) else None
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return _safe(dataclasses.asdict(value))
    if isinstance(value, dict):
        return {str(key): _safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_safe(item) for item in value]
    if hasattr(value, "to_dict"):
        return _safe(value.to_dict())
    return str(value)


def bounded_payload(value: Any, max_chars: int = 12_000) -> Any:
    """限制单个分析结果体积，防止嵌套图表数据淹没调用审计。"""
    safe = _safe(value)
    text = json.dumps(safe, ensure_ascii=False, default=str)
    if len(text) <= max_chars:
        return safe
    return {"truncated": True, "json_chars": len(text),
            "preview": text[:max_chars]}


class ModelCallAudit:
    """进程内加锁的本地审计库；写入失败不阻断模型主流程。"""

    def __init__(self, path: str | Path | None = None, max_records: int = 500):
        self.path = Path(path) if path else default_data_path("model_calls.jsonl")
        self.max_records = max(1, int(max_records))
        self._lock = threading.Lock()
        self._records: list[dict[str, Any]] = []
        self._errors: list[str] = []
        self.write_failures = 0
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            with self.path.open(encoding="utf-8") as handle:
                for line in handle:
                    try:
                        item = json.loads(line)
                        if isinstance(item, dict) and item.get("record_id"):
                            self._records.append(item)
                    except (json.JSONDecodeError, TypeError):
                        self._errors.append("跳过损坏的模型审计行")
        except OSError as exc:
            self._errors.append(str(exc))
        self._records = self._records[-self.max_records:]

    def record(self, payload: dict[str, Any]) -> dict[str, Any]:
        item = _safe(dict(payload or {}))
        item.update({
            "schema_version": MODEL_AUDIT_SCHEMA_VERSION,
            "record_id": str(item.get("record_id") or f"MCA-{uuid.uuid4().hex}"),
            "created_at": str(item.get("created_at") or time.strftime(
                "%Y-%m-%dT%H:%M:%S%z")),
        })
        with self._lock:
            self._records.append(item)
            self._records = self._records[-self.max_records:]
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                if len(self._records) >= self.max_records:
                    self._rewrite_locked()
                else:
                    with self.path.open("a", encoding="utf-8") as handle:
                        handle.write(json.dumps(
                            item, ensure_ascii=False, allow_nan=False) + "\n")
            except (OSError, TypeError, ValueError) as exc:
                self.write_failures += 1
                logger.warning("模型调用审计写入失败（累计 %d 次）: %s",
                               self.write_failures, exc)
        return item

    def _rewrite_locked(self) -> None:
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            for item in self._records:
                handle.write(json.dumps(item, ensure_ascii=False,
                                        allow_nan=False) + "\n")
        temporary.replace(self.path)

    def records(self, limit: int = 100, *, kind: str = "") -> list[dict[str, Any]]:
        with self._lock:
            items = [item for item in self._records
                     if not kind or item.get("kind") == kind]
        return list(reversed(items[-max(1, int(limit)):]))

    def get(self, record_id: str) -> dict[str, Any] | None:
        with self._lock:
            return next((item for item in self._records
                         if item.get("record_id") == record_id), None)

    def export(self, path: str | Path) -> Path:
        target = Path(path)
        with self._lock:
            payload = {
                "schema_version": MODEL_AUDIT_SCHEMA_VERSION,
                "exported_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "record_count": len(self._records),
                "records": self._records,
            }
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2,
                                     allow_nan=False) + "\n", encoding="utf-8")
        return target


_default_audit: ModelCallAudit | None = None
_default_lock = threading.Lock()


def get_model_audit() -> ModelCallAudit:
    global _default_audit
    with _default_lock:
        if _default_audit is None:
            _default_audit = ModelCallAudit()
        return _default_audit


__all__ = [
    "MODEL_AUDIT_SCHEMA_VERSION", "ModelCallAudit", "bounded_payload",
    "get_model_audit", "prompt_digest",
]
