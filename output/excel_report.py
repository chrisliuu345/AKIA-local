"""Excel 报告生成器"""

import xlsxwriter

from core.i18n import i18n
from output.base_report_engine import BaseReportEngine
from core.fonts import get_ui_font


class ExcelReport(BaseReportEngine):
    """生成格式化的Excel质量分析报告"""

    def __init__(self):
        super().__init__()
        self.workbook = None
        self.formats = {}
        self.current_row = 0

    def generate(self, analyses, output_path, title=""):
        if not title:
            title = i18n.tr("report.title")
        wb = xlsxwriter.Workbook(output_path, {"nan_inf_to_errors": True})
        self.workbook = wb
        try:
            self._define_formats()

            summary_sheet = wb.add_worksheet(i18n.tr("report.summary_title"))
            self._write_summary(summary_sheet, analyses, title)

            for i, atype, params, result in self.iter_analyses(analyses):
                sheet_name = self.safe_name(f"{atype}_{i+1}")
                ws = wb.add_worksheet(sheet_name)
                self._write_analysis_sheet(ws, atype, params, result)
        finally:
            wb.close()
        return output_path

    def _define_formats(self):
        wb = self.workbook
        font_name = get_ui_font()
        self.formats = {
            "title": wb.add_format({
                "bold": True, "font_size": 16, "align": "center", "valign": "vcenter",
                "font_name": font_name,
            }),
            "heading1": wb.add_format({
                "bold": True, "font_size": 14, "font_name": font_name,
                "bg_color": "#1f77b4", "font_color": "white",
                "border": 1, "text_wrap": True,
            }),
            "heading2": wb.add_format({
                "bold": True, "font_size": 12, "font_name": font_name,
                "bg_color": "#d9e6f2", "border": 1,
            }),
            "header": wb.add_format({
                "bold": True, "font_size": 10, "font_name": font_name,
                "bg_color": "#4472C4", "font_color": "white", "border": 1,
                "text_wrap": True,
            }),
            "cell": wb.add_format({
                "font_size": 10, "font_name": font_name,
                "border": 1, "num_format": "0.0000",
            }),
            "cell_text": wb.add_format({
                "font_size": 10, "font_name": font_name, "border": 1,
            }),
            "warning": wb.add_format({
                "font_size": 10, "font_name": font_name,
                "bg_color": "#fff2cc", "border": 1,
            }),
            "error": wb.add_format({
                "font_size": 10, "font_name": font_name,
                "bg_color": "#f4cccc", "font_color": "red", "border": 1,
            }),
            "good": wb.add_format({
                "font_size": 10, "font_name": font_name,
                "bg_color": "#d9ead3", "border": 1,
            }),
            "footer": wb.add_format({
                "font_size": 9, "font_name": font_name,
                "italic": True, "align": "right",
            }),
        }

    def _safe_write(self, ws, row, col, value, fmt=None):
        """安全写入单元格 — 字符串使用 write_string 防止公式注入"""
        if isinstance(value, str):
            return ws.write_string(row, col, value, fmt)
        return ws.write(row, col, value, fmt)

    def _merge_safe(self, ws, first_row, first_col, last_row, last_col, text, fmt):
        """安全合并单元格 — 先空合并再 write_string，防止标题字符串被当公式 (W17)"""
        ws.merge_range(first_row, first_col, last_row, last_col, None, fmt)
        self._safe_write(ws, first_row, first_col, text, fmt)

    def _write_summary(self, ws, analyses, title):
        self._merge_safe(ws, 0, 0, 0, 4, title, self.formats["title"])
        ws.set_row(0, 30)
        footer_text, _ = self.footers()
        self._merge_safe(ws, 1, 0, 1, 4, footer_text, self.formats["footer"])

        headers = [
            i18n.tr("report.index"),
            i18n.tr("report.analysis_type"),
            i18n.tr("report.param"),
            i18n.tr("report.key_result"),
            i18n.tr("report.conclusion"),
        ]
        for j, h in enumerate(headers):
            self._safe_write(ws, 3, j, h, self.formats["header"])
        ws.set_row(3, 22)

        for i, analysis in enumerate(analyses):
            row = 4 + i
            atype = analysis.get("analysis_type", analysis.get("chart_type", "Unknown"))
            params = analysis.get("params", {})
            result = analysis.get("result", {})

            ws.write(row, 0, i + 1, self.formats["cell_text"])
            self._safe_write(ws, row, 1, atype, self.formats["cell_text"])

            param_str = ", ".join(f"{k}={v}" for k, v in list(params.items())[:5])
            self._safe_write(ws, row, 2, param_str[:80], self.formats["cell_text"])

            key_result = self.extract_key_result(result)
            self._safe_write(ws, row, 3, key_result[:80], self.formats["cell"])

            conclusion = self.extract_conclusion(result)
            self._safe_write(ws, row, 4, conclusion, self.formats["cell_text"])

    def _write_analysis_sheet(self, ws, atype, params, result):
        self._merge_safe(ws, 0, 0, 0, 3, f"{atype}", self.formats["heading1"])
        ws.set_row(0, 28)

        row = 2
        if params:
            self._safe_write(ws, 1, 0, i18n.tr("report.analysis_params"), self.formats["heading2"])
            for k, v in params.items():
                self._safe_write(ws, row, 0, k, self.formats["header"])
                self._safe_write(ws, row, 1, str(v), self.formats["cell_text"])
                row += 1

        row += 1
        self._flatten_dict_to_sheet(ws, row, result, 0)

    def _flatten_dict_to_sheet(self, ws, start_row, data, col, depth=0):
        if isinstance(data, dict):
            for key, val in data.items():
                if isinstance(val, (dict, list)):
                    self._safe_write(ws, start_row, col, str(key), self.formats["heading2"])
                    start_row += 1
                    start_row = self._flatten_dict_to_sheet(ws, start_row, val, col, depth + 1)
                else:
                    self._safe_write(ws, start_row, col, str(key), self.formats["cell_text"])
                    self._safe_write(ws, start_row, col + 1, val, self.formats["cell"] if isinstance(val, (int, float)) else self.formats["cell_text"])
                    start_row += 1
        elif isinstance(data, list) and data:
            if isinstance(data[0], dict):
                if not data:
                    return start_row
                keys = list(data[0].keys())
                for j, k in enumerate(keys):
                    self._safe_write(ws, start_row, col + j, k, self.formats["header"])
                start_row += 1
                for item in data:
                    for j, k in enumerate(keys):
                        val = item.get(k, "")
                        self._safe_write(ws, start_row, col + j, val, self.formats["cell"] if isinstance(val, (int, float)) else self.formats["cell_text"])
                    start_row += 1
            else:
                for i, item in enumerate(data):
                    self._safe_write(ws, start_row, col, f"[{i}]", self.formats["cell_text"])
                    self._safe_write(ws, start_row, col + 1, item, self.formats["cell"] if isinstance(item, (int, float)) else self.formats["cell_text"])
                    start_row += 1
        return start_row
