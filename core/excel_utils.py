"""Excel 读取工具 — .xlsx/.xlsm/.xls 优先用 calamine。

pandas 3.x 读 .xls 的默认引擎是 xlrd（本机通常未安装），.xlsx 的默认引擎是
openpyxl。calamine 更快，失败时 .xlsx/.xlsm 回退 openpyxl，.xls 回退 xlrd。
读出的表会把数值列转换一次并缓存，后续解析不再重扫同一列。
"""

import os
from collections.abc import Callable
from typing import Any

import pandas as pd

from core.i18n import i18n
from core.numeric_cache import cache_numeric_columns

_XLS_ENGINES = ("calamine", "xlrd")
_XLSX_ENGINES = ("calamine", "openpyxl")


def _engines(file_path: str) -> tuple[str, ...]:
    ext = os.path.splitext(str(file_path))[1].lower()
    if ext == ".xls":
        return _XLS_ENGINES
    if ext in {".xlsx", ".xlsm"}:
        return _XLSX_ENGINES
    return ("openpyxl",)


def _read_with_fallback(file_path: str, read: Callable[[str], Any]) -> Any:
    last_err: Exception = ValueError("未知错误")
    for engine in _engines(file_path):
        try:
            return read(engine)
        except OSError:
            # 文件不存在、无权限等与引擎无关，换引擎也一样。保持原异常类型。
            raise
        except Exception as exc:  # 当前引擎打不开该文件时换下一个
            last_err = exc
    ext = os.path.splitext(str(file_path))[1].lower()
    if ext == ".xls":
        raise ValueError(
            f"无法读取 .xls 文件（calamine/xlrd 均失败）: {last_err}\n"
            "建议安装: pip install python-calamine"
        ) from last_err
    raise ValueError(
        i18n.tr("excel.xlsx_failed").replace("{error}", str(last_err))
    ) from last_err


def _remember_numeric(result: Any) -> Any:
    if isinstance(result, pd.DataFrame):
        cache_numeric_columns(result)
    elif isinstance(result, dict):
        for frame in result.values():
            if isinstance(frame, pd.DataFrame):
                cache_numeric_columns(frame)
    return result


def read_excel_auto(file_path: str, **kwargs) -> Any:
    """按扩展名选择引擎读取 Excel。

    - .xlsx / .xlsm → calamine，失败后 openpyxl
    - .xls          → calamine，失败后 xlrd
    - 其他          → openpyxl

    返回类型取决于 ``sheet_name``（DataFrame 或 dict[str, DataFrame]）。
    数值列已转换并缓存在表上。
    """

    def read(engine: str) -> Any:
        return pd.read_excel(file_path, engine=engine, **kwargs)

    return _remember_numeric(_read_with_fallback(file_path, read))


def open_excel_auto(file_path: str) -> pd.ExcelFile:
    """按扩展名选择引擎打开 ExcelFile（用于枚举工作表）。"""

    def read(engine: str) -> pd.ExcelFile:
        return pd.ExcelFile(file_path, engine=engine)

    return _read_with_fallback(file_path, read)
