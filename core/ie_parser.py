"""
IE 数据解析器 — 将 Excel sheet 自动映射为统一数据对象列表
支持: sheet名称关键词检测 + 列名模糊匹配
"""

import difflib
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd

from core.data_objects import OBJECT_CLASSES, get_all_types


_SHEET_KEYWORDS = {
    "Process": ["工序", "流程", "process", "制程", "工位", "步骤表", "产线"],
    "TimeObservation": ["时间观测", "观测", "秒表", "时间研究", "time observation",
                        "工时", "timing", "observation", "测时"],
    "QualityRecord": ["质量记录", "质量", "quality", "检测", "检验记录",
                      "测量", "spc", "数据", "检查", "规格"],
    "MaterialFlow": ["物流", "flow", "搬运", "material", "距离", "运输",
                     "路径", "流动", "移动"],
    "Resource": ["资源", "resource", "设备清单", "人员", "班组", "资源表",
                 "设备表", "人员表", "machine", "worker"],
}


class IEDataParser:
    """Excel → 统一 IE 数据对象"""

    def __init__(self):
        self._column_cache: Dict[str, Dict[str, str]] = {}

    @staticmethod
    def detect_type(sheet_name: str, columns: List[str]) -> Tuple[Optional[str], float]:
        """根据 sheet 名称和列名自动检测数据类型。
        返回 (类型名, 置信度 0-1)
        """
        name_lower = sheet_name.lower().replace("_", "").replace(" ", "")
        scores: Dict[str, float] = {}

        for obj_type, keywords in _SHEET_KEYWORDS.items():
            s = 0.0
            for kw in keywords:
                if kw.lower() in name_lower:
                    s += 0.4
                    break
            all_aliases = set()
            for aliases in OBJECT_CLASSES[obj_type].FIELD_ALIASES.values():
                all_aliases.update(a.lower() for a in aliases)
            col_lower = [c.lower().strip() for c in columns]
            matched = sum(1 for c in col_lower for a in all_aliases if a in c or c in a)
            col_score = min(matched / max(len(OBJECT_CLASSES[obj_type].REQUIRED), 1) * 0.6, 0.6)
            scores[obj_type] = s + col_score

        best = max(scores, key=scores.get)
        confidence = scores[best]
        if confidence < 0.15:
            return None, confidence
        return best, confidence

    @staticmethod
    def map_columns(columns: List[str], obj_type: str) -> Dict[str, str]:
        """将 Excel 列名映射到数据对象字段名。
        返回 {excel_column: field_name}
        """
        cls = OBJECT_CLASSES.get(obj_type)
        if not cls:
            return {}
        mapping: Dict[str, str] = {}
        col_lower = [c.lower().strip() for c in columns]

        for col_orig, col_low in zip(columns, col_lower):
            best_field = None
            best_score = 0.0
            for field_name, aliases in cls.FIELD_ALIASES.items():
                for alias in aliases:
                    al = alias.lower()
                    if al == col_low:
                        score = 1.0
                    elif al in col_low or col_low in al:
                        score = 0.7
                    else:
                        ratio = difflib.SequenceMatcher(None, col_low, al).ratio()
                        score = ratio if ratio > 0.6 else 0.0
                    if score > best_score:
                        best_score = score
                        best_field = field_name
            if best_field and best_score >= 0.55:
                mapping[col_orig] = best_field

        return mapping

    def parse(self, df: pd.DataFrame, obj_type: str,
              column_map: Optional[Dict[str, str]] = None) -> List[Any]:
        """将 DataFrame 转换为数据对象列表。
        返回 List[Process|TimeObservation|...]
        """
        cls = OBJECT_CLASSES.get(obj_type)
        if not cls:
            return []

        if column_map is None:
            column_map = self.map_columns(list(df.columns), obj_type)

        objects = []
        for _, row in df.iterrows():
            row_dict: Dict[str, Any] = {}
            for excel_col, field_name in column_map.items():
                if excel_col in df.columns:
                    val = row[excel_col]
                    if pd.isna(val):
                        val = ""
                    row_dict[field_name] = val
            if row_dict:
                try:
                    obj = cls.from_dict(row_dict)
                    objects.append(obj)
                except Exception:
                    continue

        return objects

    def parse_all(self, raw_data: Dict[str, pd.DataFrame]) -> Dict[str, List[Any]]:
        """批量解析所有 sheet 为对应的数据对象。
        返回 {类型名: [对象列表]}
        """
        result: Dict[str, List[Any]] = {}
        for sheet_name, df in raw_data.items():
            columns = list(df.columns)
            obj_type, confidence = self.detect_type(sheet_name, columns)
            if obj_type and confidence >= 0.15:
                col_map = self.map_columns(columns, obj_type)
                objects = self.parse(df, obj_type, col_map)
                if objects:
                    if obj_type not in result:
                        result[obj_type] = []
                    result[obj_type].extend(objects)
        return result

    @staticmethod
    def _infer_column_semantic_type(col_name: str, sample_values: pd.Series) -> Tuple[Optional[str], float]:
        """三维推断：关键词(0.4) + 数据类型(0.3) + 值域分布(0.3)

        返回 (field_name, confidence 0-1)。
        """
        col_lower = col_name.lower().strip()
        n = len(sample_values)
        if n == 0:
            return None, 0.0

        # 维度 1: 关键词匹配 (0.4)
        best_keyword_score = 0.0
        best_keyword_field = None
        for cls_name, cls in OBJECT_CLASSES.items():
            for field_name, aliases in cls.FIELD_ALIASES.items():
                for alias in aliases:
                    al = alias.lower()
                    if al == col_lower:
                        score = 0.4
                    elif al in col_lower or col_lower in al:
                        score = 0.28
                    else:
                        ratio = difflib.SequenceMatcher(None, col_lower, al).ratio()
                        score = 0.4 * ratio if ratio > 0.6 else 0.0
                    if score > best_keyword_score:
                        best_keyword_score = score
                        best_keyword_field = field_name

        # 维度 2: 数据类型分析 (0.3)
        numeric = pd.to_numeric(sample_values, errors="coerce")
        numeric_ratio = numeric.notna().sum() / n
        # 疑似日期
        date_ratio = 0.0
        try:
            parsed = pd.to_datetime(sample_values, errors="coerce")
            date_ratio = parsed.notna().sum() / n
        except Exception:
            pass

        if numeric_ratio >= 0.9:
            dtype_score = 0.3  # 明确数值
        elif numeric_ratio >= 0.5:
            dtype_score = 0.15  # 混合
        elif date_ratio >= 0.5:
            dtype_score = 0.1  # 日期
        else:
            dtype_score = 0.05  # 文本

        # 维度 3: 值域分布 (0.3)
        if numeric_ratio >= 0.9:
            vals = numeric.dropna()
            unique_ratio = vals.nunique() / len(vals)
            has_neg = (vals < 0).any()
            # 低基数 + 无负数 → 可能是 ID/编码
            if unique_ratio < 0.1 and not has_neg:
                dist_score = 0.1
            else:
                dist_score = 0.3
        else:
            unique_ratio = sample_values.nunique() / n
            dist_score = 0.15 if unique_ratio > 0.05 else 0.05

        confidence = best_keyword_score + dtype_score + dist_score
        return best_keyword_field, min(confidence, 1.0)

    def get_summary(self, ie_data: Dict[str, List[Any]]) -> Dict[str, Any]:
        """生成 IE 数据摘要"""
        summary = {}
        for obj_type, objects in ie_data.items():
            summary[obj_type] = {
                "count": len(objects),
                "first_3": [obj.to_dict() for obj in objects[:3]],
            }
        return summary

    @staticmethod
    def format_help() -> str:
        """返回所有 5 种 IE 数据对象的格式说明文本"""
        lines = [
            "当前 Excel 未检测到 IE 数据格式。",
            "请确保 Excel 包含以下至少一种工作表（Sheet 名称建议包含对应关键词）：",
            "",
        ]
        from core.data_objects import OBJECT_CLASSES

        type_info = [
            ("Process", "工序表", "支撑线平衡、VSM、OEE",
             ["工序", "流程", "process", "制程", "工位"]),
            ("TimeObservation", "时间观测", "支撑工时研究、人机分析",
             ["时间观测", "观测", "秒表", "工时", "timing"]),
            ("QualityRecord", "质量记录", "可选，支撑 SPC/MSA/DOE/过程能力",
             ["质量记录", "质量", "quality", "检测", "spc"]),
            ("MaterialFlow", "物流", "支撑布置优化、搬运分析、VSM",
             ["物流", "flow", "搬运", "material"]),
            ("Resource", "资源", "支撑 OEE、利用率、工时分析",
             ["资源", "resource", "设备清单", "人员"]),
        ]

        for obj_type, label, usage, keywords in type_info:
            cls = OBJECT_CLASSES.get(obj_type)
            if not cls:
                continue
            example = cls.format_example()
            required = "、".join(cls.REQUIRED)
            optional = "、".join(cls.OPTIONAL) if cls.OPTIONAL else "无"
            kw_str = "、".join(keywords)
            lines.append(f"── {label} ({obj_type}) ──")
            lines.append(f"  用途: {usage}")
            lines.append(f"  示例表头: {example}")
            lines.append(f"  必填字段: {required}")
            lines.append(f"  可选字段: {optional}")
            lines.append(f"  Sheet关键词: {kw_str}")
            lines.append("")

        lines.append("Sheet 名称建议包含以上关键词以便自动识别，列名会自动模糊匹配映射。")
        return "\n".join(lines)
