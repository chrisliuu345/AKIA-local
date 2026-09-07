"""
智能数据解析器 — 自动识别表头、数据类型、规格限、分组列
"""

import re
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np


class DataParser:
    """智能数据解析：自动识别数据列类型、表头行、规格限"""

    NUMERIC_PATTERNS = re.compile(r"^(-?\d+\.?\d*|\.\d+)$")
    DATE_PATTERNS = [
        re.compile(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}$"),
        re.compile(r"^\d{1,2}[-/]\d{1,2}[-/]\d{4}$"),
        re.compile(r"^\d{4}年\d{1,2}月\d{1,2}日$"),
    ]
    INVALID_PATTERNS = re.compile(
        r"^(?:"
        r"\*+\s*$|"
        r"N/?A\s*$|"
        r"[Nn][Oo][Nn][Ee]\s*$|"
        r"[Nn][Uu][Ll][Ll]\s*$|"
        r"[-—/]+$|"
        r"[?？]+$|"
        r"[#＃]+$|"
        r"^\s*$|"
        r"[Ee][Rr][Rr][Oo][Rr]|"
        r"[Ff][Aa][Ii][Ll][Ee][Dd]|"
        r"[Ee][Rr][Rr]"
        r")$"
    )
    COLUMN_TYPE_KEYS = {
        "measurement": ["测量", "值", "数据", "measure", "value", "尺寸", "重量", "长度", "宽度", "厚度", "直径"],
        "subgroup": ["子组", "组", "批次", "样本", "subgroup", "sample", "lot", "batch"],
        "usl": ["上规格", "上限", "USL", "upper spec", "max"],
        "lsl": ["下规格", "下限", "LSL", "lower spec", "min"],
        "target": ["目标", "名义", "target", "nominal", "规格中心"],
        "timestamp": ["时间", "日期", "date", "time", "timestamp", "datetime"],
        "part_id": ["零件", "部件", "产品", "part", "product", "item", "编号", "ID"],
        "operator": ["操作员", "检验员", "operator", "inspector", "人员", "appraiser"],
        "trial": ["试验", "重复", "次数", "trial", "replicate", "repeat"],
    }

    TAG_KEYWORDS = {
        "subgroup": ["子组", "批次", "样本号", "组号", "subgroup", "sample", "lot"],
        "measurement": ["数值", "测量值", "特性值", "value", "measurement", "data"],
        "spec_limit": ["规格限", "规格", "spec", "USL", "LSL", "上限", "下限"],
        "dimension": ["长度", "宽度", "高度", "厚度", "直径", "重量", "温度", "压力"],
        "part": ["零件", "部件", "part", "编号", "批号"],
        "operator": ["操作员", "检验员", "operator", "inspector"],
    }

    def __init__(self):
        self.header_row: int = 0
        self.data_start_row: int = 1
        self.column_types: Dict[str, str] = {}
        self.spec_limits: Dict[str, Dict[str, float]] = {}
        self.subgroup_col: Optional[str] = None
        self.measurement_cols: List[str] = []
        self.identifier_cols: List[str] = []
        self.invalid_count: int = 0

    def prepare(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """清洗并解析数据：返回 (列名同步的DataFrame, 解析信息)"""
        if df.empty:
            raise ValueError("数据框为空，无法解析")
        self.header_row = self._detect_header_row(df)
        cleaned = self._apply_header(df.copy(), self.header_row)
        cleaned, self.invalid_count = self._clean_invalid_cells(cleaned)
        self.column_types = self._classify_columns(cleaned)
        self.spec_limits = self._extract_spec_limits(cleaned)
        self.subgroup_col = self._identify_subgroup_column(cleaned)
        self.measurement_cols = self._identify_measurement_columns(cleaned)
        self.identifier_cols = self._identify_identifier_columns(cleaned)
        info = {
            "header_row": self.header_row,
            "data_start_row": self.header_row + 1,
            "column_types": self.column_types,
            "spec_limits": self.spec_limits,
            "subgroup_column": self.subgroup_col,
            "measurement_columns": self.measurement_cols,
            "identifier_columns": self.identifier_cols,
            "numeric_columns": [c for c, t in self.column_types.items() if t == "numeric"],
            "row_count": len(cleaned),
            "column_count": len(cleaned.columns),
        }
        return cleaned, info

    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        if df.empty:
            raise ValueError("数据框为空，无法解析")

        self.header_row = self._detect_header_row(df)
        df = self._apply_header(df, self.header_row)
        self.column_types = self._classify_columns(df)
        self.spec_limits = self._extract_spec_limits(df)
        self.subgroup_col = self._identify_subgroup_column(df)
        self.measurement_cols = self._identify_measurement_columns(df)
        self.identifier_cols = self._identify_identifier_columns(df)

        return {
            "header_row": self.header_row,
            "data_start_row": self.header_row + 1,
            "column_types": self.column_types,
            "spec_limits": self.spec_limits,
            "subgroup_column": self.subgroup_col,
            "measurement_columns": self.measurement_cols,
            "identifier_columns": self.identifier_cols,
            "numeric_columns": [c for c, t in self.column_types.items() if t == "numeric"],
            "row_count": len(df),
            "column_count": len(df.columns),
        }

    @staticmethod
    def _is_invalid_cell(val) -> bool:
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return True
        s = str(val).strip()
        if not s:
            return True
        return bool(DataParser.INVALID_PATTERNS.match(s))

    @staticmethod
    def _clean_invalid_cells(df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
        invalid_mask = df.map(DataParser._is_invalid_cell)
        invalid_rows = invalid_mask.any(axis=1)
        cleaned = df[~invalid_rows].reset_index(drop=True)
        invalid_count = invalid_rows.sum()
        return cleaned, invalid_count

    def _detect_header_row(self, df: pd.DataFrame, n_scan: int = 20) -> int:
        """\u8868\u5934\u884c\u81ea\u52a8\u68c0\u6d4b\u2014\u2014\u57fa\u4e8e\u975e\u7a7a\u7387 + \u6570\u503c\u7387\u7a81\u53d8\u5b9a\u4f4d

        \u626b\u63cf\u524d n_scan \u884c\uff0c\u9010\u884c\u8ba1\u7b97\uff1a
          - non_empty_rate: \u975e\u7a7a\u5355\u5143\u683c\u6bd4\u4f8b\uff08\u8fc7\u6ee4 NaN/\u7a7a\u4e32/"nan"/"none"\uff09
          - numeric_rate: \u7eaf\u6570\u503c\u5355\u5143\u683c\u6bd4\u4f8b

        \u5b9a\u4f4d\u903b\u8f91\uff1a
          1. \u9996\u884c\u82e5\u975e\u7a7a\u7387\u9ad8(>70%)\u4e14\u6570\u503c\u7387\u4f4e(<30%) \u2192 \u76f4\u63a5\u8fd4\u56de 0\uff08\u6807\u51c6\u8868\u5934\u884c\uff09
          2. \u9010\u884c\u626b\u63cf\uff0c\u82e5\u4e0a\u4e00\u884c\u6570\u503c\u7387 <30% \u4e14\u5f53\u524d\u884c >60% \u2192 \u4e0a\u4e00\u884c\u4e3a\u8868\u5934
          3. \u82e5\u8fde\u7eed\u591a\u884c\u5747\u4e3a\u4f4e\u6570\u503c\u7387\uff08\u5408\u5e76\u5355\u5143\u683c\u8868\u5934\uff09\uff0c\u53d6\u6700\u540e\u4e00\u884c\u4e3a\u8868\u5934
          4. \u515c\u5e95\uff1a\u53d6\u6700\u9ad8\u6570\u503c\u7387\u7a81\u53d8\u70b9\u6240\u5728\u884c
        """
        n = min(n_scan, len(df))
        if n <= 1:
            return 0

        rates = []
        for i in range(n):
            row_vals = [str(v) if v is not None else "" for v in df.iloc[i]]
            total = len(row_vals)
            non_empty = 0
            numeric = 0
            for v in row_vals:
                stripped = v.strip()
                is_empty = not stripped or stripped.lower() in ("nan", "none", "", "null", "na")
                if not is_empty:
                    non_empty += 1
                    try:
                        float(stripped)
                        numeric += 1
                    except ValueError:
                        pass
            ne_rate = non_empty / max(total, 1)
            num_rate = numeric / max(non_empty, 1) if non_empty > 0 else 0.0
            rates.append((i, ne_rate, num_rate))

        if rates[0][1] >= 0.7 and rates[0][2] <= 0.3:
            return 0

        best_row = 0
        best_jump = 0.0
        for k in range(len(rates) - 1):
            prev_num = rates[k][2]
            curr_num = rates[k + 1][2]
            if curr_num >= 0.2 and (prev_num == 0.0 or curr_num / max(prev_num, 0.001) >= 2.0):
                jump = curr_num - prev_num
                if jump > best_jump:
                    best_jump = jump
                    best_row = k

        if best_jump > 0.1:
            return best_row

        for i in range(min(10, len(df))):
            row = df.iloc[i].apply(lambda v: str(v) if v is not None else "")
            non_empty = sum(1 for v in row if v and v.strip().lower() not in ("nan", "none", ""))
            has_chinese = sum(1 for v in row if any("\u4e00" <= c <= "\u9fff" for c in v))
            has_alpha = sum(1 for v in row if any(c.isalpha() for c in v))
            if non_empty >= 2 and (has_chinese >= 1 or has_alpha >= 2):
                return i
        return 0

    def _apply_header(self, df: pd.DataFrame, header_row: int) -> pd.DataFrame:
        if header_row > 0:
            df = df.iloc[header_row:].reset_index(drop=True)
            df.columns = [str(c).strip() for c in df.iloc[0]]
            df = df.iloc[1:].reset_index(drop=True)
            return df
        cols_are_default = all(
            str(c).isdigit() or str(c).startswith("Unnamed")
            for c in df.columns
        )
        if cols_are_default:
            df.columns = [str(c).strip() for c in df.iloc[0]]
            df = df.iloc[1:].reset_index(drop=True)
        return df

    def _classify_columns(self, df: pd.DataFrame) -> Dict[str, str]:
        types = {}
        for col in df.columns:
            col_lower = str(col).lower()
            non_null = df[col].dropna()
            if len(non_null) == 0:
                types[col] = "empty"
                continue

            matched = False
            for type_key, keywords in self.COLUMN_TYPE_KEYS.items():
                if any(kw in col_lower for kw in keywords):
                    types[col] = type_key.replace("_col", "")
                    matched = True
                    break
            if matched:
                continue

            sample = non_null.head(min(50, len(non_null)))
            numeric_count = 0
            date_count = 0
            for v in sample:
                try:
                    vs = str(v).strip() if v is not None else ""
                except Exception:
                    continue
                if not vs:
                    continue
                if self.NUMERIC_PATTERNS.match(vs):
                    numeric_count += 1
                elif any(p.match(vs) for p in self.DATE_PATTERNS):
                    date_count += 1

            n = len(sample)
            if numeric_count >= n * 0.8:
                types[col] = "numeric"
            elif date_count >= n * 0.5:
                types[col] = "datetime"
            else:
                types[col] = "text"

        return types

    def _extract_spec_limits(self, df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        specs = {}
        for col, _col_type in self.column_types.items():
            col_lower = str(col).lower()
            spec = {}
            if any(kw in col_lower for kw in ["usl", "上规格", "上限"]):
                non_null = pd.to_numeric(df[col], errors="coerce").dropna()
                if len(non_null) > 0:
                    spec["usl"] = float(non_null.iloc[0])
            if any(kw in col_lower for kw in ["lsl", "下规格", "下限"]):
                non_null = pd.to_numeric(df[col], errors="coerce").dropna()
                if len(non_null) > 0:
                    spec["lsl"] = float(non_null.iloc[0])
            if any(kw in col_lower for kw in ["target", "目标", "名义"]):
                non_null = pd.to_numeric(df[col], errors="coerce").dropna()
                if len(non_null) > 0:
                    spec["target"] = float(non_null.iloc[0])
            if spec:
                for k, v in spec.items():
                    specs.setdefault(col, {})[k] = v

        return specs

    def _identify_subgroup_column(self, df: pd.DataFrame) -> Optional[str]:
        for col in df.columns:
            col_lower = str(col).lower()
            if any(kw in col_lower for kw in self.COLUMN_TYPE_KEYS.get("subgroup", [])):
                return col
        return None

    def _identify_measurement_columns(self, df: pd.DataFrame) -> List[str]:
        return [c for c, t in self.column_types.items()
                if t in ("numeric", "measurement")]

    def _identify_identifier_columns(self, df: pd.DataFrame) -> List[str]:
        return [
            c for c, t in self.column_types.items()
            if t in ("text",) and c != self.subgroup_col
        ]

    def extract_measurement_data(self, df: pd.DataFrame, col: str) -> pd.Series:
        return pd.to_numeric(df[col], errors="coerce").dropna()

    @staticmethod
    def suggest_subgroup_size(df: pd.DataFrame, col: str) -> Optional[int]:
        data = pd.to_numeric(df[col], errors="coerce").dropna()
        total = len(data)
        common_sizes = [2, 3, 4, 5, 6, 8, 10, 12, 15, 20]
        for size in common_sizes:
            if total % size == 0 and total >= size * 2:
                return size
        if total >= 10:
            return 5
        return None
