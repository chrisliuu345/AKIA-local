"""时间语义工具 — 双时态契约的统一入口（v4.3.0 B0）。

规则:
- 新写入的时间戳一律为带时区偏移的 ISO-8601（本机时区，默认 Asia/Shanghai）；
- 读取历史字符串时，无时区值按本机时区解释（`allow_naive=True`）并可由调用方标记，
  不静默改写原值；
- 设备 epoch 秒转换为本机时区 ISO-8601，原始 epoch 由上层决定是否另行保留。

本模块无 Qt、无业务依赖（core 分层守卫）。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def now_iso() -> str:
    """当前时间（带本地时区偏移，秒精度）。"""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def parse_iso(value: Any, field_name: str = "时间", *,
              allow_naive: bool = False) -> datetime:
    """解析 ISO-8601 字符串为带时区的 datetime。

    Args:
        value: 待解析值（None/空串报错）。
        field_name: 报错文案中的字段名。
        allow_naive: 为 True 时，无时区输入按本机时区解释；默认拒绝。
    """
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field_name}不能为空")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{field_name}不是合法 ISO-8601 时间: {text}") from exc
    if parsed.tzinfo is None:
        if not allow_naive:
            raise ValueError(f"{field_name}必须带时区偏移（如 +08:00）: {text}")
        parsed = parsed.astimezone()
    return parsed


def normalize_iso(value: Any, field_name: str = "时间", *,
                  allow_naive: bool = False) -> str:
    """解析并统一格式化为带时区 ISO-8601（秒精度）。"""
    return parse_iso(value, field_name, allow_naive=allow_naive).isoformat(timespec="seconds")


def epoch_to_iso(ts: float) -> str:
    """epoch 秒（UTC）→ 本机时区带偏移 ISO-8601（毫秒精度）。"""
    return datetime.fromtimestamp(float(ts), tz=timezone.utc).astimezone().isoformat(
        timespec="milliseconds")


def seconds_between(later: datetime, earlier: datetime) -> float:
    """两个带时区时间点的秒差（later - earlier）。"""
    return (later - earlier).total_seconds()
