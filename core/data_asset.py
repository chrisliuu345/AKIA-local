"""`.qap` 内的本地数据资产段。

资产不是第二种项目文件，只是归档成员 `data_asset.json`。
`format_version` 与 `.qap` 的 `VERSION`、程序 `APP_VERSION`、SDK `schema_version`
相互独立，这样以后可以只升这一段的格式。

本版只保证信封能写进 `.qap` 再读出来。特性、批次、标准工时仍留在原段
（`context.json`、`sampling.json`、`standards.json`）。以后迁入时填
`extension_slot()` 里的三个列表，不要再新开一种文件。
"""

from __future__ import annotations

from typing import Any

DATA_ASSET_FORMAT_VERSION = "1"
DATA_ASSET_MEMBER = "data_asset.json"

# 以后原位迁入的集合。本版保持为空，不从其它段复制。
# characteristics — 质量特性（仍在 context.json）
# batches — 批次 / 检验批（仍在 sampling.json）
# standard_times — 标准工时记录（仍在 standards.json）
DATA_ASSET_RESERVED_COLLECTIONS = (
    "characteristics",
    "batches",
    "standard_times",
)


def extension_slot() -> dict[str, list[Any]]:
    """留给后续版本原位填入的空集合。

    不读取项目上下文、抽样批或标准注册表。调用它不会把特性、批次或
    标准工时复制进资产。
    """
    return {name: [] for name in DATA_ASSET_RESERVED_COLLECTIONS}


def empty_data_asset() -> dict[str, Any]:
    """当前格式的空信封。保留列表在，但没有任何迁入的记录。"""
    asset: dict[str, Any] = {"format_version": DATA_ASSET_FORMAT_VERSION}
    asset.update(extension_slot())
    return asset


def prepare_data_asset(value: Any) -> dict[str, Any]:
    """得到可写入归档的资产字典。

    ``None`` 写成当前版本的空信封。调用方已给出的 ``format_version`` 原样保留，
    这样更新的信封可以再读出。当前版本缺少的保留列表补成空列表；已有列表
    （包括调用方显式放入的记录）不改写，也不从其它段补充。
    """
    if value is None:
        return empty_data_asset()
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    if not isinstance(value, dict):
        raise TypeError("data_asset 需为 dict 或带 to_dict() 的对象")
    payload = dict(value)
    raw_version = payload.get("format_version")
    if raw_version is None or raw_version == "":
        payload["format_version"] = DATA_ASSET_FORMAT_VERSION
    else:
        payload["format_version"] = str(raw_version)
    if payload["format_version"] != DATA_ASSET_FORMAT_VERSION:
        return payload
    for key in DATA_ASSET_RESERVED_COLLECTIONS:
        if key not in payload:
            payload[key] = []
        elif not isinstance(payload[key], list):
            raise TypeError(f"data_asset.{key} 需为 list")
    return payload
