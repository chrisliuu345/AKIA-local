"""判定凭证 schema v1 — 记录每个结论「当时是怎么算的」（v4.2.0 P0 契约）。

字段:
  rule_version      规则 / 算法版本
  params            判定参数（JSON 可序列化）
  data_fingerprint  数据指纹（算法前缀 + SHA-256）
  app_version       产生结论的软件版本
  computed_at       结论生成时间

本模块保持无 Qt、无 ui 依赖（分层守卫）；v4.3.0 证据账本在此基础上扩展。
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field, fields
from datetime import date, datetime
from typing import Any

import pandas as pd

from config.settings import APP_VERSION

CREDENTIAL_SCHEMA_VERSION = "1"
FINGERPRINT_ALGO = "pd-hash-v1"
FALLBACK_FINGERPRINT_ALGO = "csv-hash-v1"
NO_DATA_FINGERPRINT = "no-data"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _jsonable(value: Any) -> Any:
    """递归清理 numpy/pandas 类型，保证 params 可 JSON 序列化且跨运行稳定。"""
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, set):
        return [_jsonable(v) for v in sorted(value, key=repr)]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, float) and math.isnan(value):
        return None
    if hasattr(value, "item"):
        try:
            value = value.item()
        except (TypeError, ValueError):
            return str(value)
        if isinstance(value, float) and math.isnan(value):
            return None
    return value


def fingerprint_dataframe(df: pd.DataFrame) -> str:
    """计算 DataFrame 的稳定指纹（含列名、列顺序、dtype、索引与每一个值）。

    首选 pandas 的确定性哈希；单元格含不可哈希对象时退化为 CSV 文本哈希。
    返回形如 ``pd-hash-v1:<sha256>`` 的字符串。
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("data_fingerprint 仅支持 pandas.DataFrame")

    algo = FINGERPRINT_ALGO
    hasher = hashlib.sha256()
    hasher.update(algo.encode("utf-8"))
    hasher.update(repr(list(df.columns)).encode("utf-8"))
    hasher.update(repr([str(dtype) for dtype in df.dtypes]).encode("utf-8"))
    try:
        hashed = pd.util.hash_pandas_object(df, index=True, categorize=True)
        payload = hashed.to_numpy(dtype="uint64", copy=False).tobytes()
    except TypeError:
        algo = FALLBACK_FINGERPRINT_ALGO
        hasher = hashlib.sha256()
        hasher.update(algo.encode("utf-8"))
        hasher.update(repr(list(df.columns)).encode("utf-8"))
        hasher.update(repr([str(dtype) for dtype in df.dtypes]).encode("utf-8"))
        payload = df.to_csv(index=True).encode("utf-8")
    hasher.update(payload)
    return f"{algo}:{hasher.hexdigest()}"


@dataclass
class ConclusionCredential:
    """结论凭证 v1 — 每个分析结论的「规则版本 + 参数 + 数据指纹 + 软件版本」。"""

    rule_version: str
    data_fingerprint: str
    params: dict[str, Any] = field(default_factory=dict)
    app_version: str = APP_VERSION
    computed_at: str = field(default_factory=_now)
    algorithm: str = ""
    schema_version: str = CREDENTIAL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not str(self.rule_version or "").strip():
            raise ValueError("rule_version 不能为空")
        if not str(self.data_fingerprint or "").strip():
            raise ValueError("data_fingerprint 不能为空")
        if self.schema_version != CREDENTIAL_SCHEMA_VERSION:
            raise ValueError(f"不支持的凭证 schema 版本: {self.schema_version}")
        if not isinstance(self.params, dict):
            raise ValueError("params 必须为 dict")
        self.rule_version = str(self.rule_version)
        self.data_fingerprint = str(self.data_fingerprint)
        self.app_version = str(self.app_version or APP_VERSION)
        self.computed_at = str(self.computed_at or _now())
        self.params = _jsonable(self.params)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "rule_version": self.rule_version,
            "params": self.params,
            "data_fingerprint": self.data_fingerprint,
            "app_version": self.app_version,
            "computed_at": self.computed_at,
            "algorithm": self.algorithm,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ConclusionCredential:
        if not isinstance(d, dict):
            raise ValueError("凭证必须为 dict")
        for key in ("rule_version", "data_fingerprint"):
            if not str(d.get(key) or "").strip():
                raise ValueError(f"凭证缺少必填字段: {key}")
        schema = str(d.get("schema_version") or CREDENTIAL_SCHEMA_VERSION)
        if schema != CREDENTIAL_SCHEMA_VERSION:
            raise ValueError(f"不支持的凭证 schema 版本: {schema}")
        params = d.get("params") or {}
        if not isinstance(params, dict):
            raise ValueError("params 必须为 dict")
        allowed = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in allowed})

    def verify_dataframe(self, df: pd.DataFrame) -> bool:
        """重算数据指纹并与凭证比对（报告复核模式的数据侧）。"""
        return self.data_fingerprint == fingerprint_dataframe(df)


def make_credential(rule_version: str, params: dict[str, Any] | None = None,
                    df: pd.DataFrame | None = None,
                    algorithm: str = "") -> ConclusionCredential:
    """构造结论凭证；无数据结论（如纯参数校验）使用 ``no-data`` 指纹。"""
    return ConclusionCredential(
        rule_version=rule_version,
        data_fingerprint=fingerprint_dataframe(df) if df is not None else NO_DATA_FINGERPRINT,
        params=dict(params or {}),
        algorithm=algorithm,
    )


def diff_credentials(old: ConclusionCredential,
                     new: ConclusionCredential) -> dict[str, dict[str, Any]]:
    """逐项比较两次结论凭证，返回 ``{字段: {"old": ..., "new": ...}}``。"""
    if not isinstance(old, ConclusionCredential) or not isinstance(new, ConclusionCredential):
        raise TypeError("diff_credentials 需要两个 ConclusionCredential")
    old_dict, new_dict = old.to_dict(), new.to_dict()
    return {
        key: {"old": old_dict.get(key), "new": new_dict.get(key)}
        for key in sorted(set(old_dict) | set(new_dict))
        if old_dict.get(key) != new_dict.get(key)
    }
