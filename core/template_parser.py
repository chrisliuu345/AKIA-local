"""
分析要求模板解析器 — 解析用户上传的分析要求文件（Excel/JSON格式）
"""

import json
import logging
import os
from typing import Dict, List, Any
import pandas as pd

logger = logging.getLogger(__name__)


class TemplateParser:
    """解析质量分析要求模板文件"""

    REQUIRED_FIELDS = ["analysis_type", "data_sheet", "measurement_column"]
    OPTIONAL_FIELDS = [
        "subgroup_column", "subgroup_size",
        "usl", "lsl", "target",
        "title", "description",
        "output_format", "output_path",
        "chart_options", "confidence_level",
    ]

    VALID_ANALYSIS_TYPES = [
        "xbar_r", "xbar_s", "imr",
        "p_chart", "np_chart", "c_chart", "u_chart",
        "normal_capability", "non_normal_capability", "between_within_capability",
        "gage_rr_crossed", "gage_rr_nested", "linearity_bias", "attribute_agreement",
        "t_test_1sample", "t_test_2sample", "t_test_paired",
        "anova_oneway", "anova_twoway",
        "normality_test", "variance_test",
        "factorial_design", "response_surface", "doe_analysis", "box_behnken",
    ]

    def __init__(self):
        self.template_file: str = ""
        self.template_data: Dict[str, Any] = {}
        self.analyses: List[Dict[str, Any]] = []

    def load(self, file_path: str) -> Dict[str, Any]:
        self.template_file = file_path
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".json":
            self.template_data = self._load_json(file_path)
        elif ext in (".xlsx", ".xls", ".xlsm"):
            self.template_data = self._load_excel(file_path)
        else:
            raise ValueError(f"不支持的模板格式: {ext}")

        self.analyses = self._parse_template(self.template_data)
        return self.template_data

    def _load_json(self, file_path: str) -> Dict[str, Any]:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data

    def _load_excel(self, file_path: str) -> Dict[str, Any]:
        from core.excel_utils import open_excel_auto
        xl = open_excel_auto(file_path)
        result = {}

        for sheet_name in xl.sheet_names:
            df = pd.read_excel(xl, sheet_name=sheet_name, dtype=str)
            df = df.dropna(how="all").dropna(axis=1, how="all")

            if not df.empty and len(df.columns) >= 2:
                key_col = df.columns[0]
                value_col = df.columns[1]
                params = {}
                keys = df[key_col].fillna("").astype(str).str.strip()
                vals = df[value_col].fillna("").astype(str).str.strip()
                for k, v in zip(keys, vals, strict=False):
                    if k and k.lower() != "nan":
                        params[k] = self._parse_value(v)
                if params:
                    result[sheet_name] = params

        return result

    def _parse_template(self, raw: Dict[str, Any]) -> List[Dict[str, Any]]:
        analyses = []

        if "analyses" in raw and isinstance(raw["analyses"], list):
            analyses = raw["analyses"]
        elif "analysis" in raw and isinstance(raw["analysis"], dict):
            analyses = [raw["analysis"]]
        else:
            for _sheet_name, params in raw.items():
                if "analysis_type" in params or "analysis_type" in {k.lower() for k in params}:
                    normalized = {k.lower().replace(" ", "_"): v for k, v in params.items()}
                    analyses.append(normalized)

        validated = []
        for analysis in analyses:
            try:
                validated.append(self._validate(analysis))
            except ValueError as e:
                logger.warning(f"跳过无效分析配置: {e}")

        return validated

    def _validate(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        normalized = {}
        for k, v in analysis.items():
            normalized[k.lower().replace(" ", "_").replace("-", "_")] = v

        for field in self.REQUIRED_FIELDS:
            if field not in normalized:
                raise ValueError(f"缺少必要字段: {field}")

        atype = normalized.get("analysis_type", "").lower().strip()
        if atype not in self.VALID_ANALYSIS_TYPES:
            raise ValueError(
                f"不支持的分析类型: '{atype}'. 有效类型: {self.VALID_ANALYSIS_TYPES}"
            )

        spec_fields = ["usl", "lsl", "target", "subgroup_size", "confidence_level"]
        for field in spec_fields:
            if field in normalized:
                try:
                    normalized[field] = float(normalized[field])
                except (ValueError, TypeError):
                    pass

        return normalized

    def get_analysis_list(self) -> List[Dict[str, Any]]:
        return self.analyses

    @staticmethod
    def _parse_value(val: str) -> Any:
        val = val.strip()
        if val.lower() in ("true", "yes", "是"):
            return True
        if val.lower() in ("false", "no", "否"):
            return False
        try:
            return int(val)
        except ValueError:
            pass
        try:
            return float(val)
        except ValueError:
            pass
        if val.startswith("[") or val.startswith("{"):
            try:
                return json.loads(val)
            except json.JSONDecodeError:
                pass
        return val
