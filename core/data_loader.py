"""
核心数据加载引擎 — 支持大规模Excel解析、智能表头识别、多Sheet处理
"""

import os
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np
from config.settings import SUPPORTED_EXCEL_EXTENSIONS, MAX_PREVIEW_ROWS, CHUNK_SIZE
from core.ie_parser import IEDataParser
from core.log_util import get_logger

_log = get_logger(__name__)


class DataLoader:
    """Excel数据加载引擎, 支持固定模板和灵活自动识别"""

    def __init__(self):
        self.file_path: str = ""
        self.raw_data: Dict[str, pd.DataFrame] = {}
        self.sheet_info: Dict[str, Dict[str, Any]] = {}
        self.metadata: Dict[str, Any] = {}
        self.ie_parser: IEDataParser = IEDataParser()
        self.ie_data: Dict[str, List[Any]] = {}
        self.ie_summary: Dict[str, Any] = {}

    def load(self, file_path: str, sheet_names: Optional[List[str]] = None) -> Dict[str, pd.DataFrame]:
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in SUPPORTED_EXCEL_EXTENSIONS:
            raise ValueError(f"不支持的文件格式: {ext}，支持: {SUPPORTED_EXCEL_EXTENSIONS}")

        self.file_path = file_path

        if ext == ".xls":
            raw = None
            for eng in ["calamine", "xlrd"]:
                try:
                    raw = pd.read_excel(file_path, sheet_name=sheet_names, dtype=str, engine=eng)
                    break
                except Exception as e:
                    _log.debug("Engine %s failed: %s", eng, e)
                    continue
            if raw is None:
                raise ValueError("无法读取 .xls 文件，请安装: pip install python-calamine")
        else:
            raw = pd.read_excel(file_path, sheet_name=sheet_names, dtype=str, engine="openpyxl")

        if isinstance(raw, pd.DataFrame):
            raw = {"Sheet1": raw}

        self.raw_data = {self._normalize_sheet_name(k): _clean_column_names(v)
                         for k, v in raw.items()}
        self._extract_metadata()
        return self.raw_data

    def load_chunked(self, file_path: str, sheet_name: str = "Sheet1",
                     chunk_size: int = CHUNK_SIZE) -> pd.DataFrame:
        """一次性加载（保持与 load() 一致的接口）。

        注意：此方法名称含 "chunked" 但实际上是受限加载（最多返回 chunk_size 行），而非真正的分块。
        对于真正的分块迭代，请使用本类的 load_chunked_iter() 方法。

        pandas 的 read_excel 不支持 chunksize 参数，对于超大文件（>100万行），
        建议先用数据库导入再通过 SqlLoader 读取。"""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".xls":
            for eng in ["calamine", "xlrd"]:
                try:
                    return pd.read_excel(file_path, sheet_name=sheet_name, dtype=str, engine=eng)
                except Exception:
                    continue
            raise ValueError("无法读取 .xls 文件，请安装: pip install python-calamine")
        if chunk_size and chunk_size > 0:
            try:
                return pd.read_excel(file_path, sheet_name=sheet_name, dtype=str,
                                     engine="openpyxl").head(chunk_size)
            except Exception:
                pass
        return pd.read_excel(file_path, sheet_name=sheet_name, dtype=str, engine="openpyxl")

    def load_chunked_iter(self, file_path: str, sheet_name: str = "Sheet1",
                          chunk_size: int = CHUNK_SIZE):
        """真正的分块迭代器 — 对 CSV 使用 chunksize，对 xlsx 逐批读取。

        Yields: pd.DataFrame — 每次返回 chunk_size 行，直到文件末尾。
        超大 Excel 文件（>100万行）建议先转 CSV 再使用此方法。
        """
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".csv":
            for chunk in pd.read_csv(file_path, chunksize=chunk_size, dtype=str):
                yield chunk
        elif ext in (".xlsx", ".xlsm"):
            # openpyxl read_only mode: 逐行迭代，累积到 chunk_size 后 yield
            from openpyxl import load_workbook
            wb = load_workbook(file_path, read_only=True, data_only=True)
            ws = wb[sheet_name] if sheet_name in wb.sheetnames else wb.active
            rows_buf, headers = [], None
            for row in ws.iter_rows(values_only=True):
                if headers is None:
                    headers = [str(c) if c is not None else f"col_{i}" for i, c in enumerate(row)]
                    continue
                rows_buf.append(dict(zip(headers, row)))
                if len(rows_buf) >= chunk_size:
                    yield pd.DataFrame(rows_buf)
                    rows_buf = []
            if rows_buf:
                yield pd.DataFrame(rows_buf)
            wb.close()
        elif ext == ".xls":
            # .xls 不支持流式，一次性加载后分块返回
            df = self.load_chunked(file_path, sheet_name)
            for start in range(0, len(df), chunk_size):
                yield df.iloc[start:start + chunk_size]
        else:
            raise ValueError(f"不支持的文件格式: {ext}")

    def get_preview(self, sheet_name: str = "Sheet1", rows: int = MAX_PREVIEW_ROWS) -> pd.DataFrame:
        sname = self._normalize_sheet_name(sheet_name)
        if sname not in self.raw_data:
            raise KeyError(f"Sheet '{sheet_name}' 不存在. 可用: {list(self.raw_data.keys())}")
        return self.raw_data[sname].head(rows)

    def get_sheet_names(self) -> List[str]:
        return list(self.raw_data.keys())

    def get_dataframe(self, sheet_name: str = "Sheet1") -> pd.DataFrame:
        sname = self._normalize_sheet_name(sheet_name)
        if sname not in self.raw_data:
            raise KeyError(f"Sheet '{sheet_name}' 不存在")
        return self.raw_data[sname]

    def _extract_metadata(self) -> None:
        total_rows = sum(len(df) for df in self.raw_data.values())
        total_cols = {name: len(df.columns) for name, df in self.raw_data.items()}
        self.metadata = {
            "file_path": self.file_path,
            "file_name": os.path.basename(self.file_path),
            "sheet_count": len(self.raw_data),
            "total_rows": total_rows,
            "columns_per_sheet": total_cols,
            "sheet_names": list(self.raw_data.keys()),
        }

    def load_ie_data(self) -> Dict[str, List[Any]]:
        """将已加载的 raw_data 解析为 IE 数据对象"""
        if not self.raw_data:
            return {}
        self.ie_data = self.ie_parser.parse_all(self.raw_data)
        self.ie_summary = self.ie_parser.get_summary(self.ie_data)
        return self.ie_data

    def get_ie_objects(self, obj_type: str) -> List[Any]:
        """获取指定类型的 IE 数据对象"""
        return self.ie_data.get(obj_type, [])

    @staticmethod
    def _normalize_sheet_name(name: str) -> str:
        return name.strip()


def _clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """清理列名: Unnamed:N→列N+1, 纯数字→列N+1"""
    import re
    new_cols = []
    for c in df.columns:
        s = str(c).strip()
        m = re.match(r"unnamed[:\s_-]*(\d+)", s, re.IGNORECASE)
        if m:
            new_cols.append(f"列 {int(m.group(1)) + 1}")
            continue
        try:
            n = int(s)
            new_cols.append(f"列 {n + 1}")
        except ValueError:
            new_cols.append(s)
    df = df.copy()
    df.columns = new_cols
    return df


def validate_data_file(file_path: str) -> bool:
    """验证数据文件是否存在且格式受支持"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in SUPPORTED_EXCEL_EXTENSIONS:
        raise ValueError(f"不支持的文件格式: {ext}")
    return True
