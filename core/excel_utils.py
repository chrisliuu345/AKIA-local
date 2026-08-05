"""Excel 读取工具 — 统一引擎选择（.xls 走 calamine→xlrd 回退）

pandas 3.x 中 .xls 的默认引擎是 xlrd（本机未安装），
必须显式指定 calamine。所有读取 Excel 的入口统一走此函数。
"""

import os
from typing import Any

import pandas as pd

_XLS_ENGINES = ("calamine", "xlrd")


def read_excel_auto(file_path: str, **kwargs) -> Any:
    """按扩展名自动选择引擎读取 Excel。

    - .xls  → calamine（优先）→ xlrd（回退）
    - 其他  → openpyxl
    返回类型取决于 sheet_name 参数（DataFrame 或 dict[str, DataFrame]）。
    """
    ext = os.path.splitext(str(file_path))[1].lower()
    if ext == ".xls":
        last_err: Exception = ValueError("未知错误")
        for eng in _XLS_ENGINES:
            try:
                return pd.read_excel(file_path, engine=eng, **kwargs)
            except Exception as e:  # noqa: PERF203
                last_err = e
        raise ValueError(
            f"无法读取 .xls 文件（calamine/xlrd 均失败）: {last_err}\n"
            "建议安装: pip install python-calamine"
        )
    return pd.read_excel(file_path, engine="openpyxl", **kwargs)


def open_excel_auto(file_path: str) -> pd.ExcelFile:
    """按扩展名自动选择引擎打开 ExcelFile（用于枚举 sheet 等场景）。"""
    ext = os.path.splitext(str(file_path))[1].lower()
    if ext == ".xls":
        last_err: Exception = ValueError("未知错误")
        for eng in _XLS_ENGINES:
            try:
                return pd.ExcelFile(file_path, engine=eng)
            except Exception as e:
                last_err = e
        raise ValueError(
            f"无法读取 .xls 文件（calamine/xlrd 均失败）: {last_err}\n"
            "建议安装: pip install python-calamine"
        )
    return pd.ExcelFile(file_path, engine="openpyxl")
