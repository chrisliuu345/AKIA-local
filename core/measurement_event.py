"""MeasurementEvent v1 — 统一测量事实契约（v4.3.0 B0）。

设计要点（与 `PLAN_v4.3.0.md` 第 3.2 节一致）:
- **批量粒度**：一次设备 poll / 一列导入 / 一次手工录入 = 一条事件，
  避免百万行数据产生百万条账本记录；
- 双时间：`ts_start` / `ts_end` 是测量发生时间，`recorded_at` 是记录时间，
  两者都必须带时区偏移；记录时间早于事件时间超过容差时拒绝；
- 大批量只保留 summary + raw_ref，小批量可内联 values（默认上限 1000）；
- `fingerprint` 复用 `core.evidence.pd-hash-v1`，与判定凭证同源可比。

本模块无 Qt、无 ui 依赖（core 分层守卫）。
"""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass, field, fields
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from core.evidence import fingerprint_dataframe
from core.time_utils import epoch_to_iso, now_iso, parse_iso

MEASUREMENT_SCHEMA_VERSION = "1"
SOURCE_KINDS = ("connector", "plugin", "manual", "file", "analysis")
CONFIDENCE_LEVELS = ("high", "medium", "low")
VALIDITY_STATES = ("valid", "suspect", "invalid")
SUMMARY_KEYS = ("n", "mean", "std", "min", "max", "dropped_invalid")

#: 单事件内联原始值的上限；超过则只保留 summary + raw_ref
INLINE_VALUE_LIMIT = 1000
#: recorded_at 允许早于 ts_end 的容差（设备/主机时钟偏差）
CLOCK_SKEW_TOLERANCE_S = 300.0


def new_event_id() -> str:
    """生成批量测量事件 ID：MEV-<本地时间>-<4 位随机>。"""
    stamp = datetime.now().astimezone().strftime("%Y%m%d%H%M%S")
    return f"MEV-{stamp}-{uuid.uuid4().hex[:4]}"


def summarize_values(values: list[float] | tuple[float, ...]) -> dict[str, Any]:
    """计算批量摘要（n/mean/std/min/max）；空序列报错，std 为样本标准差。"""
    series = pd.Series(list(values), dtype="float64")
    if series.empty:
        raise ValueError("无法为空序列生成测量摘要")
    array = series.to_numpy(dtype=float)
    if not np.isfinite(array).all():
        raise ValueError("测量值包含 NaN/Inf，请先净化或标记 validity=invalid")
    count = int(series.count())
    return {
        "n": count,
        "mean": float(series.mean()),
        "std": float(series.std(ddof=1)) if count > 1 else 0.0,
        "min": float(series.min()),
        "max": float(series.max()),
    }


def _coerce_values(values: list[float] | tuple[float, ...]) -> list[float]:
    array = np.asarray(list(values), dtype=float)
    if array.size == 0:
        raise ValueError("values 不能为空列表")
    if not np.isfinite(array).all():
        raise ValueError("测量值包含 NaN/Inf，请先净化或标记 validity=invalid")
    return [float(v) for v in array]


def _normalize_summary(summary: dict[str, Any] | None) -> dict[str, Any]:
    if summary is None:
        return {}
    if not isinstance(summary, dict):
        raise ValueError("summary 必须为 dict")
    unknown = sorted(set(summary) - set(SUMMARY_KEYS))
    if unknown:
        raise ValueError(f"summary 含未知字段: {unknown}（可选 {list(SUMMARY_KEYS)}）")
    normalized: dict[str, Any] = {}
    for key, value in summary.items():
        if value is None:
            continue
        if key in ("n", "dropped_invalid"):
            normalized[key] = int(value)
        else:
            normalized[key] = float(value)
    if normalized.get("n") is not None and normalized["n"] <= 0:
        raise ValueError("summary.n 必须为正整数")
    if normalized.get("dropped_invalid") is not None and normalized["dropped_invalid"] < 0:
        raise ValueError("summary.dropped_invalid 不能为负")
    return normalized


def fingerprint_values(values: list[float] | tuple[float, ...]) -> str:
    """内联测量值的稳定指纹（与判定凭证同为 pd-hash-v1）。"""
    frame = pd.DataFrame({"value": list(values)})
    return fingerprint_dataframe(frame)


def timeseries_ref(device: str, channel: str, since_ts: float | None = None,
                   until_ts: float | None = None) -> str:
    """构造时序库原始引用（B2 连接器适配的 raw_ref 格式）。"""
    query = []
    if since_ts is not None:
        query.append(f"since={float(since_ts):.3f}")
    if until_ts is not None:
        query.append(f"until={float(until_ts):.3f}")
    suffix = f"?{'&'.join(query)}" if query else ""
    return f"timeseries://{device or '-'}/{channel or '-'}{suffix}"


_TS_REF_RE = re.compile(r"^timeseries://([^/]+)/([^?]+)(?:\?(.*))?$")


def parse_timeseries_ref(ref: str) -> dict[str, Any]:
    """解析 ``timeseries://device/channel?since=&until=`` 引用。

    返回 ``{"device", "channel", "since_ts", "until_ts"}``；``-`` 表示空值。
    """
    text = str(ref or "").strip()
    match = _TS_REF_RE.fullmatch(text)
    if not match:
        raise ValueError(f"非法时序引用: {text or '(空)'}")
    device = "" if match.group(1) == "-" else match.group(1)
    channel = "" if match.group(2) == "-" else match.group(2)
    since_ts: float | None = None
    until_ts: float | None = None
    query = match.group(3) or ""
    for part in query.split("&") if query else []:
        key, _, value = part.partition("=")
        if key not in ("since", "until"):
            raise ValueError(f"非法时序引用参数: {key or '(空)'}")
        try:
            number = float(value)
        except ValueError as exc:
            raise ValueError(f"非法时序引用参数值: {key}={value}") from exc
        if key == "since":
            since_ts = number
        else:
            until_ts = number
    return {"device": device, "channel": channel,
            "since_ts": since_ts, "until_ts": until_ts}


def _stamp_to_iso(value: Any) -> str:
    """pandas Timestamp / datetime → 带偏移 ISO-8601；naive 按本机时区解释。"""
    if isinstance(value, pd.Timestamp):
        value = value.to_pydatetime()
    if not isinstance(value, datetime):
        raise ValueError(f"时间列值不是日期时间: {value!r}")
    if value.tzinfo is None:
        value = value.astimezone()
    return value.isoformat(timespec="seconds")


@dataclass
class MeasurementEvent:
    """一批测量事实 — source/subject/时间/可信度/原始引用。"""

    event_id: str = field(default_factory=new_event_id)
    source_kind: str = ""
    source_id: str = ""
    source_name: str = ""
    device: str = ""
    channel: str = ""
    characteristic_id: str = ""
    method: str = ""
    ts_start: str = ""
    ts_end: str = ""
    recorded_at: str = ""
    confidence: str = "high"
    validity: str = "valid"
    validity_reason: str = ""
    summary: dict[str, Any] = field(default_factory=dict)
    values: list[float] = field(default_factory=list)
    raw_ref: str = ""
    fingerprint: str = ""
    parent_event_ids: list[str] = field(default_factory=list)
    clock_skew_s: float = 0.0
    schema_version: str = MEASUREMENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        self.event_id = str(self.event_id or "").strip() or new_event_id()
        self.source_kind = str(self.source_kind or "").strip().lower()
        self.source_id = str(self.source_id or "").strip()
        self.source_name = str(self.source_name or "").strip()
        self.device = str(self.device or "").strip()
        self.channel = str(self.channel or "").strip()
        self.characteristic_id = str(self.characteristic_id or "").strip()
        self.method = str(self.method or "").strip()
        self.validity_reason = str(self.validity_reason or "").strip()
        self.raw_ref = str(self.raw_ref or "").strip()
        self.fingerprint = str(self.fingerprint or "").strip()

        if self.schema_version != MEASUREMENT_SCHEMA_VERSION:
            raise ValueError(f"不支持的测量事件 schema 版本: {self.schema_version}")
        if self.source_kind not in SOURCE_KINDS:
            raise ValueError(f"非法测量来源 kind: {self.source_kind!r}（可选 {list(SOURCE_KINDS)}）")
        if self.confidence not in CONFIDENCE_LEVELS:
            raise ValueError(
                f"非法 confidence: {self.confidence!r}（可选 {list(CONFIDENCE_LEVELS)}）")
        if self.validity not in VALIDITY_STATES:
            raise ValueError(f"非法 validity: {self.validity!r}（可选 {list(VALIDITY_STATES)}）")
        if self.validity in ("suspect", "invalid") and not self.validity_reason:
            raise ValueError("suspect/invalid 事件必须填写 validity_reason")

        self.recorded_at = str(self.recorded_at or now_iso())
        self.ts_end = str(self.ts_end or self.recorded_at)
        self.ts_start = str(self.ts_start or self.ts_end)
        start = parse_iso(self.ts_start, "ts_start")
        end = parse_iso(self.ts_end, "ts_end")
        recorded = parse_iso(self.recorded_at, "recorded_at")
        if end < start:
            raise ValueError(f"ts_end ({self.ts_end}) 不能早于 ts_start ({self.ts_start})")
        if recorded < end:
            skew = (end - recorded).total_seconds()
            if skew > CLOCK_SKEW_TOLERANCE_S:
                raise ValueError(
                    f"recorded_at ({self.recorded_at}) 早于 ts_end ({self.ts_end}) "
                    f"{skew:.0f}s，超过时钟偏差容差 {CLOCK_SKEW_TOLERANCE_S:.0f}s")
            self.clock_skew_s = float(skew)
        else:
            self.clock_skew_s = 0.0

        if self.values:
            self.values = _coerce_values(self.values)
            if not self.summary:
                self.summary = summarize_values(self.values)
        self.summary = _normalize_summary(self.summary)
        if not self.values and not self.summary and self.validity != "invalid":
            raise ValueError("测量事件必须携带 values 或 summary（invalid 事件除外）")

        if not self.fingerprint and self.values:
            self.fingerprint = fingerprint_values(self.values)
        if not self.raw_ref:
            self.raw_ref = (f"dataframe://{self.fingerprint}" if self.fingerprint
                            else f"inline://{self.event_id}")

        if not isinstance(self.parent_event_ids, (list, tuple)):
            raise ValueError("parent_event_ids 必须为字符串列表")
        self.parent_event_ids = [str(item) for item in self.parent_event_ids if str(item)]

    # ------------------------------------------------------------ 适配器
    @classmethod
    def from_samples(cls, samples, *, source_kind: str = "connector",
                     source_id: str = "", source_name: str = "", method: str = "",
                     confidence: str = "high", validity: str = "valid",
                     validity_reason: str = "", characteristic_id: str = "",
                     raw_ref: str = "", recorded_at: str = "",
                     event_id: str = "") -> MeasurementEvent:
        """单设备/单通道样本批 → 一条事件（多通道请用 ``events_from_samples``）。"""
        items = list(samples or [])
        if not items:
            raise ValueError("样本列表不能为空")
        subjects = {(str(getattr(s, "device", "") or ""),
                     str(getattr(s, "channel", "") or "")) for s in items}
        if len(subjects) != 1:
            raise ValueError("from_samples 要求同一设备/通道；多通道批次请用 events_from_samples")
        device, channel = subjects.pop()
        values = [float(s.value) for s in items]
        stamps = [float(s.ts) for s in items]
        summary = summarize_values(values)
        inline = values if len(values) <= INLINE_VALUE_LIMIT else []
        return cls(
            event_id=event_id or new_event_id(),
            source_kind=source_kind,
            source_id=source_id,
            source_name=source_name,
            device=device,
            channel=channel,
            characteristic_id=characteristic_id,
            method=method,
            ts_start=epoch_to_iso(min(stamps)),
            ts_end=epoch_to_iso(max(stamps)),
            recorded_at=recorded_at or now_iso(),
            confidence=confidence,
            validity=validity,
            validity_reason=validity_reason,
            summary=summary,
            values=inline,
            raw_ref=raw_ref or timeseries_ref(device, channel, min(stamps), max(stamps)),
        )

    @classmethod
    def events_from_samples(cls, samples, **kwargs) -> list[MeasurementEvent]:
        """按 (device, channel) 分组，每个分组产出一条事件。"""
        groups: dict[tuple[str, str], list] = {}
        for sample in samples or []:
            key = (str(getattr(sample, "device", "") or ""),
                   str(getattr(sample, "channel", "") or ""))
            groups.setdefault(key, []).append(sample)
        return [cls.from_samples(items, **kwargs) for items in groups.values()]

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame, *, source_kind: str = "file",
                       source_id: str = "", source_name: str = "",
                       column: str = "", ts_column: str = "", method: str = "",
                       confidence: str = "high", validity: str = "valid",
                       validity_reason: str = "", characteristic_id: str = "",
                       device: str = "", channel: str = "", raw_ref: str = "",
                       recorded_at: str = "", event_id: str = "") -> MeasurementEvent:
        """导入表/工作表 → 一条事件；指纹取整张传入表（与判定凭证同源）。"""
        if not isinstance(df, pd.DataFrame):
            raise TypeError("from_dataframe 仅支持 pandas.DataFrame")
        if df.empty:
            raise ValueError("数据表为空，无法生成测量事件")
        target = str(column or "").strip()
        if target:
            if target not in df.columns:
                raise ValueError(f"列不存在: {target}")
        else:
            numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
            if not numeric:
                raise ValueError("数据表没有可用数值列")
            target = str(numeric[0])
        series = pd.to_numeric(df[target], errors="coerce")
        valid = series.dropna()
        dropped = int(series.isna().sum())
        if valid.empty:
            raise ValueError(f"列「{target}」没有有效数值")
        values = [float(v) for v in valid.tolist()]
        summary = summarize_values(values)
        if dropped:
            summary["dropped_invalid"] = dropped

        ts_start = ts_end = ""
        ts_name = str(ts_column or "").strip()
        if ts_name:
            if ts_name not in df.columns:
                raise ValueError(f"时间列不存在: {ts_name}")
            stamps = pd.to_datetime(df[ts_name], errors="coerce").dropna()
            if not stamps.empty:
                # 批量事件取全窗口最早/最晚时间：行序不等于时间序的乱序文件
                # 不应因 ts_end < ts_start 被拒绝
                ts_start = _stamp_to_iso(stamps.min())
                ts_end = _stamp_to_iso(stamps.max())

        fingerprint = fingerprint_dataframe(df)
        return cls(
            event_id=event_id or new_event_id(),
            source_kind=source_kind,
            source_id=source_id,
            source_name=source_name,
            device=device,
            channel=channel or target,
            characteristic_id=characteristic_id,
            method=method,
            ts_start=ts_start,
            ts_end=ts_end,
            recorded_at=recorded_at or now_iso(),
            confidence=confidence,
            validity=validity,
            validity_reason=validity_reason,
            summary=summary,
            values=values if len(values) <= INLINE_VALUE_LIMIT else [],
            raw_ref=raw_ref or f"dataframe://{fingerprint}",
            fingerprint=fingerprint,
        )

    @classmethod
    def from_manual(cls, value: float, *, characteristic_id: str = "",
                    method: str = "", device: str = "", channel: str = "",
                    confidence: str = "medium", recorded_at: str = "",
                    validity: str = "valid", validity_reason: str = "",
                    note: str = "", event_id: str = "") -> MeasurementEvent:
        """手工录入单个测量值 → 一条事件。"""
        number = float(value)
        recorded = recorded_at or now_iso()
        event = cls(
            event_id=event_id or new_event_id(),
            source_kind="manual",
            source_id="manual",
            source_name="手工录入",
            device=device,
            channel=channel,
            characteristic_id=characteristic_id,
            method=method or note,
            ts_start=recorded,
            ts_end=recorded,
            recorded_at=recorded,
            confidence=confidence,
            validity=validity,
            validity_reason=validity_reason,
            summary=summarize_values([number]),
            values=[number],
        )
        event.raw_ref = f"manual://{event.event_id}"
        return event

    @classmethod
    def from_timeseries(cls, samples, *, device: str, channel: str,
                        since_ts: float | None = None, until_ts: float | None = None,
                        **kwargs) -> MeasurementEvent:
        """时序库查询结果 → 一条事件；raw_ref 指向查询窗口。"""
        kwargs.setdefault("raw_ref", timeseries_ref(device, channel, since_ts, until_ts))
        return cls.from_samples(samples, **kwargs)

    @classmethod
    def events_from_raw_data(cls, raw_data: dict[str, pd.DataFrame], *,
                             source_kind: str = "file", source_id: str = "",
                             source_name: str = "", method: str = "",
                             confidence: str = "high", recorded_at: str = ""
                             ) -> list[MeasurementEvent]:
        """工作表字典 → 每张含数值列的表一条事件；无数值列的表跳过。"""
        events: list[MeasurementEvent] = []
        for sheet, frame in (raw_data or {}).items():
            if not isinstance(frame, pd.DataFrame) or frame.empty:
                continue
            try:
                events.append(cls.from_dataframe(
                    frame, source_kind=source_kind, source_id=source_id,
                    source_name=source_name, channel=str(sheet), method=method,
                    confidence=confidence, recorded_at=recorded_at,
                    raw_ref=f"sheet://{sheet}"))
            except ValueError:
                continue
        return events

    # ------------------------------------------------------------ 序列化
    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "source_kind": self.source_kind,
            "source_id": self.source_id,
            "source_name": self.source_name,
            "device": self.device,
            "channel": self.channel,
            "characteristic_id": self.characteristic_id,
            "method": self.method,
            "ts_start": self.ts_start,
            "ts_end": self.ts_end,
            "recorded_at": self.recorded_at,
            "confidence": self.confidence,
            "validity": self.validity,
            "validity_reason": self.validity_reason,
            "summary": dict(self.summary),
            "values": list(self.values),
            "raw_ref": self.raw_ref,
            "fingerprint": self.fingerprint,
            "parent_event_ids": list(self.parent_event_ids),
            "clock_skew_s": float(self.clock_skew_s),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MeasurementEvent:
        if not isinstance(data, dict):
            raise ValueError("测量事件必须为 dict")
        schema = str(data.get("schema_version") or MEASUREMENT_SCHEMA_VERSION)
        if schema != MEASUREMENT_SCHEMA_VERSION:
            raise ValueError(f"不支持的测量事件 schema 版本: {schema}")
        allowed = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in allowed})

    # ------------------------------------------------------------ 消费
    def to_dataframe(self) -> pd.DataFrame:
        """内联 values → DataFrame；仅 summary 的事件拒绝还原（请按 raw_ref 取数）。"""
        if not self.values:
            raise ValueError("该事件未内联原始值，请按 raw_ref 从原始数据源取数")
        return pd.DataFrame({
            "device": [self.device] * len(self.values),
            "channel": [self.channel] * len(self.values),
            "ts": [self.ts_start] * len(self.values),
            "value": list(self.values),
        })

    def content_hash(self) -> str:
        """事件内容指纹（用于外部核对；账本链另有 prev_hash 机制）。"""
        payload = self.to_dict()
        payload.pop("values", None)
        payload.pop("clock_skew_s", None)
        text = repr(sorted(payload.items()))
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
