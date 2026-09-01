"""合规模板引擎 — 加载 JSON 模板并生成合规报告"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, List

from config.settings import APP_VERSION
from output.base_report_engine import BaseReportEngine
from output.word_report import WordReport
from output.pdf_report import generate_pdf_report

_logger = logging.getLogger("QA-Tool.Compliance")

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "config", "templates")


def _fill_placeholders(text: str, file_name: str = "") -> str:
    """替换模板正文中的 {{file_name}} / {{timestamp}} / {{version}} 占位符"""
    if not text:
        return text
    return (
        text.replace("{{file_name}}", file_name)
        .replace("{{timestamp}}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        .replace("{{version}}", APP_VERSION)
    )


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
        if not template_id or "/" in template_id or "\\" in template_id or ".." in template_id:
            raise ValueError(f"非法的模板 ID: {template_id}")
        path = os.path.join(TEMPLATES_DIR, f"{template_id}.json")
        real_path = os.path.abspath(path)
        real_templates_dir = os.path.abspath(TEMPLATES_DIR)
        if not real_path.startswith(real_templates_dir + os.sep) and real_path != real_templates_dir:
            raise ValueError(f"模板路径越界: {template_id}")
        if not os.path.exists(path):
            raise FileNotFoundError(f"模板不存在: {template_id}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def generate(template_id: str, analyses: List[Dict],
                 output_path: str, charts: Dict[str, bytes] = None,
                 file_name: str = "") -> str:
        # W43: load_template 异常时 fallback 到内置默认模板
        try:
            template = ComplianceReportGenerator.load_template(template_id)
        except (FileNotFoundError, ValueError) as e:
            _logger.warning(f"加载合规模板 '{template_id}' 失败: {e}，使用默认模板")
            template = {"name": "默认合规模板", "format": "docx", "sections": []}
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
                                       title=_fill_placeholders(template.get("name", ""), file_name),
                                       charts=charts or {})
        else:
            return WordReport().generate(selected, output_path,
                                         title=_fill_placeholders(template.get("name", ""), file_name),
                                         charts=charts or {})
