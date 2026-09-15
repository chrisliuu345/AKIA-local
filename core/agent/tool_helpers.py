"""QAM Harness 工具共享助手（v4.1.0 B4 从 tools_ext.py 拆出）。

供 tools_ext / tools_ml 及后续工具模块复用：数据表解析、列名匹配、
规格限推断、结果字典取值、控制限文本化等。
"""

from __future__ import annotations

import dataclasses

import numpy as np
import pandas as pd

from core.agent.tools import AgentContext, _fmt, _to_float


def _df(ctx: AgentContext, sheet: str | None) -> tuple[str, pd.DataFrame]:
    name = ctx.sheet_of(sheet)
    frame = ctx.frame(name)
    if frame is None:
        raise ValueError("尚未导入数据表")
    return name, frame


def _as_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    return [p.strip() for p in str(value).replace("；", ",").replace(";", ",").split(",")
            if p.strip()]


def _match_columns(frame: pd.DataFrame, wanted: list[str], kind: str = "any") -> list[str]:
    """列名解析：精确 → 大小写 → 包含匹配；未匹配到的直接报错（避免静默跑错列）。"""
    columns = [str(c) for c in frame.columns]
    out: list[str] = []
    for want in wanted:
        hit = None
        for col in columns:
            if col == want:
                hit = col
                break
        if hit is None:
            lowered = want.lower()
            hit = next((c for c in columns if c.lower() == lowered), None)
        if hit is None:
            hit = next((c for c in columns if lowered_in(lowered, c)), None)
        if hit is None:
            raise ValueError(f"列「{want}」不存在（可用列: {', '.join(columns[:12])}）")
        out.append(hit)
    return out


def lowered_in(needle: str, haystack: str) -> bool:
    return needle in str(haystack).lower()


def _num_series(frame: pd.DataFrame, column: str) -> pd.Series:
    series = pd.to_numeric(frame[column], errors="coerce").dropna()
    if len(series) < 2:
        raise ValueError(f"列「{column}」有效数值不足（{len(series)} 行）")
    return series


def _first_spec(frame: pd.DataFrame, usl, lsl) -> tuple[float | None, float | None]:
    """USL/LSL：参数优先，其次从数据表的 USL/LSL 列取首值。"""
    def _column_value(names) -> float | None:
        for name in names:
            if name in frame.columns:
                series = pd.to_numeric(frame[name], errors="coerce").dropna()
                if not series.empty:
                    return float(series.iloc[0])
        return None

    usl_v = _to_float(usl)
    if usl_v is None:
        usl_v = _column_value(("USL", "usl", "规格上限"))
    lsl_v = _to_float(lsl)
    if lsl_v is None:
        lsl_v = _column_value(("LSL", "lsl", "规格下限"))
    return usl_v, lsl_v


def _pick(mapping, *keys, default=None):
    """从（可能嵌套的）结果 dict 中按 key 取第一个非空值。"""
    if not isinstance(mapping, dict):
        return default
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    for value in mapping.values():
        if isinstance(value, dict):
            found = _pick(value, *keys, default=None)
            if found is not None:
                return found
    return default


def _dataclass_dict(obj) -> dict:
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return dataclasses.asdict(obj)
    return obj if isinstance(obj, dict) else {"value": str(obj)}


def _limit_text(value) -> str:
    """控制限可能是标量或逐点列表 → 统一显示为 '标量' 或 '最小 ~ 最大'。"""
    if isinstance(value, (list, tuple, np.ndarray)):
        items = [float(v) for v in value if v is not None]
        if not items:
            return "—"
        return f"{_fmt(min(items))} ~ {_fmt(max(items))}"
    return _fmt(value)


def _call_with_supported(fn, *args, **kwargs):
    """只传目标函数签名接受的 kwargs（各设计引擎参数不完全一致）。"""
    import inspect

    try:
        params = inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return fn(*args, **kwargs)
    accepted = {k: v for k, v in kwargs.items() if k in params}
    return fn(*args, **accepted)
