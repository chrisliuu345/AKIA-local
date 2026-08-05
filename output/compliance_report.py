"""合规模板引擎 — 加载 JSON 模板并生成合规报告"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, List

from output.base_report_engine import BaseReportEngine
from output.word_report import WordReport
from output.pdf_report import generate_pdf_report

_logger = logging.getLogger("QA-Tool.Compliance")

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "config", "templates")


class ComplianceReportGenerator:
    """合规模板 → 报告生成"""

    @staticmethod
    def list_templates() -> List[Dict[str, str]]:
        if not os.path.isdir(TEMPLATES_DIR):
            return []
        result = []
        for fname in os.listdir(TEMPLATES_DIR):
            if fname.endswith(".json"):
                try:
                    with open(os.path.join(TEMPLATES_DIR, fname), "r", encoding="utf-8") as f:
                        t = json.load(f)
                    result.append({
                        "id": fname.replace(".json", ""),
                        "name": t.get("name", fname),
                        "standard": t.get("standard", ""),
                        "format": t.get("format", "docx"),
                    })
                except Exception as e:
                    _logger.warning(f"加载合规模板 '{fname}' 失败: {e}")
                    continue
        return result

    @staticmethod
    def load_template(template_id: str) -> Dict[str, Any]:
        path = os.path.join(TEMPLATES_DIR, f"{template_id}.json")
        if not os.path.exists(path):
            raise FileNotFoundError(f"模板不存在: {template_id}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def generate(template_id: str, analyses: List[Dict],
                 output_path: str, charts: Dict[str, bytes] = None,
                 file_name: str = "") -> str:
        template = ComplianceReportGenerator.load_template(template_id)
        fmt = template.get("format", "docx")
        sections = template.get("sections", [])

        engine = BaseReportEngine()
        selected = []
        for section in sections:
            if section.get("type") == "analysis":
                cat = section.get("category", "")
                for a in analyses:
                    if engine.classify_analysis_type(a) == cat:
                        selected.append(a)

        if fmt == "pdf":
            return generate_pdf_report(selected, output_path,
                                       title=template.get("name", ""), charts=charts or {})
        else:
            return WordReport().generate(selected, output_path,
                                         title=template.get("name", ""), charts=charts or {})
