"""数值列只转换一次，结果挂在 DataFrame 上。

导入把单元格读成文本。解析、画像和页签如果各自再调 ``pd.to_numeric``，
同一列会被重复扫描。这里按列记下转换结果；列被换掉或行下标变了就重算。

使用约定：
- 整列替换（``df[col] = ...``）、换行下标会自动重算。
- **原地改单元格**（``df.loc[mask, col] = x``）发现不了：底层数组还是同一块。
  改完必须调用 ``clear_numeric_cache(df)``，否则会读到旧值。
- 返回的是副本，调用方就地修改不会写回缓存。
"""

from __future__ import annotations

import weakref

import pandas as pd

# 不放进 DataFrame.attrs。attrs 里的 Series 会在 concat 时被当成布尔值比较。
# DataFrame 不能做 WeakKeyDictionary 的键，所以按对象编号保存，并在回收时删掉。
_CACHE: dict[int, dict] = {}
_REFS: dict[int, weakref.ReferenceType] = {}
_MIN_VALUES = 2
_MIN_RATIO = 0.8
_BLANK_TOKENS = frozenset({"nan", "none", "null", "na", "<na>"})


def _bucket(df: pd.DataFrame) -> dict:
    key = id(df)
    bucket = _CACHE.get(key)
    if bucket is None:
        bucket = {}
        _CACHE[key] = bucket
    if key not in _REFS:
        def _drop(_ref, key=key):
            _CACHE.pop(key, None)
            _REFS.pop(key, None)
        _REFS[key] = weakref.ref(df, _drop)
    return bucket


def clear_numeric_cache(df: pd.DataFrame | None) -> None:
    """丢掉已缓存的数值列。单元格被改写后调用，避免沿用旧结果。"""
    if df is not None:
        _CACHE.pop(id(df), None)


def remap_numeric_cache(df: pd.DataFrame, old_names: list, new_names: list) -> None:
    """列名整列改名后，把缓存键改到新列名。长度不一致时清空。"""
    cache = _CACHE.get(id(df))
    if not isinstance(cache, dict) or not cache:
        return
    if len(old_names) != len(new_names) or len(old_names) != len(set(old_names)):
        _CACHE.pop(id(df), None)
        return
    remapped = {}
    for old, new in zip(old_names, new_names, strict=True):
        hit = cache.get(old)
        if hit is not None:
            remapped[new] = hit
    _CACHE[id(df)] = remapped


def cache_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    """抽样后把看起来是数值的列转换一次并缓存。返回同一张表。"""
    seen: set[object] = set()
    for name in df.columns:
        if name in seen:
            continue
        seen.add(name)
        series = df[name]
        if isinstance(series, pd.DataFrame):
            continue
        if _sample_numeric(series):
            cached_numeric(df, name)
    return df


def cached_numeric(df: pd.DataFrame, column: str | int) -> pd.Series:
    """返回 ``column`` 的数值序列，与 ``pd.to_numeric(..., errors='coerce')`` 相同。

    ``column`` 可以是列名，也可以是列位置。同一块数据再次调用时直接返回上次的结果。
    """
    key, series = _column_series(df, column)
    cache = _bucket(df)
    token = id(series.array)
    hit = cache.get(key)
    if (
        isinstance(hit, tuple)
        and len(hit) == 2
        and hit[0] == token
        and hit[1].index.equals(series.index)
    ):
        # 返回副本：调用方就地改值不能写回缓存。
        return hit[1].copy()
    converted = pd.to_numeric(series, errors="coerce")
    if _worth_caching(series, converted):
        cache[key] = (token, converted.copy())
    return converted


def _column_series(df: pd.DataFrame, column: str | int) -> tuple[object, pd.Series]:
    if isinstance(column, int):
        return ("#", column), df.iloc[:, column]
    series = df[column]
    if isinstance(series, pd.DataFrame):
        series = series.iloc[:, 0]
    return column, series


def _sample_numeric(series: pd.Series) -> bool:
    if pd.api.types.is_numeric_dtype(series):
        return True
    sample = series.dropna().head(64)
    if len(sample) < _MIN_VALUES:
        return False
    converted = pd.to_numeric(sample, errors="coerce")
    return float(converted.notna().mean()) >= _MIN_RATIO


def _worth_caching(series: pd.Series, converted: pd.Series) -> bool:
    if pd.api.types.is_numeric_dtype(series):
        return True
    kept = _nonblank(series)
    count = int(kept.sum())
    if count < _MIN_VALUES:
        return False
    return float(converted[kept].notna().mean()) >= _MIN_RATIO


def _nonblank(series: pd.Series) -> pd.Series:
    present = series.notna()
    if pd.api.types.is_numeric_dtype(series) or pd.api.types.is_bool_dtype(series):
        return present
    text = series.astype("string").str.strip()
    return present & text.ne("") & ~text.str.lower().isin(_BLANK_TOKENS)
