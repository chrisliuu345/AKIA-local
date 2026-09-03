"""报告模板对话框 — 选择模板 + 预览 + 导出 PDF/Word"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QTextEdit, QFileDialog, QMessageBox,
)
from PySide6.QtGui import QFont

from core.report_templates import ReportTemplateEngine
from ui.theme import BUTTON_PRIMARY_STRETCH, BUTTON_SECONDARY
from ui.font_config import get_ui_font


class TemplateDialog(QDialog):
    def __init__(self, parent=None, analyses: dict = None):
        super().__init__(parent)
        self.analyses = analyses or {}
        self.engine = ReportTemplateEngine()
        self.setWindowTitle("报告模板")
        self.setMinimumSize(700, 500)
        self.resize(750, 560)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        top = QHBoxLayout()
        top.addWidget(QLabel("模板:"))
        self.template_combo = QComboBox()
        for t in self.engine.list_templates():
            self.template_combo.addItem(t["name"], t["id"])
        self.template_combo.currentIndexChanged.connect(self._refresh_preview)
        top.addWidget(self.template_combo, 1)

        preview_btn = QPushButton("刷新预览")
        preview_btn.clicked.connect(self._refresh_preview)
        top.addWidget(preview_btn)
        layout.addLayout(top)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setFont(QFont(get_ui_font(), 10))
        layout.addWidget(self.preview, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        export_html = QPushButton("导出 HTML")
        export_html.setStyleSheet(BUTTON_SECONDARY)
        export_html.clicked.connect(lambda: self._export("html"))
        btn_row.addWidget(export_html)
        export_pdf = QPushButton("导出 PDF")
        export_pdf.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        export_pdf.clicked.connect(lambda: self._export("pdf"))
        btn_row.addWidget(export_pdf)
        export_word = QPushButton("导出 Word")
        export_word.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        export_word.clicked.connect(lambda: self._export("docx"))
        btn_row.addWidget(export_word)
        layout.addLayout(btn_row)

        self._refresh_preview()

    def _refresh_preview(self):
        tid = self.template_combo.currentData()
        if not tid:
            return
        ctx = self.engine.build_context(self.analyses)
        ctx["product"] = "当前项目"
        ctx["department"] = "质量部"
        html = self.engine.render(tid, ctx)
        self.preview.setHtml(html)

    def _export(self, fmt: str):
        tid = self.template_combo.currentData()
        ctx = self.engine.build_context(self.analyses)
        ctx["product"] = "当前项目"
        ctx["department"] = "质量部"
        html = self.engine.render(tid, ctx)

        if fmt == "html":
            path, _ = QFileDialog.getSaveFileName(self, "导出 HTML", "report.html", "HTML (*.html)")
            if path:
                try:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(html)
                    QMessageBox.information(self, "导出完成", f"HTML 已导出到:\n{path}")
                except Exception as e:
                    QMessageBox.critical(self, "导出失败", str(e))
        elif fmt == "pdf":
            path, _ = QFileDialog.getSaveFileName(self, "导出 PDF", "report.pdf", "PDF (*.pdf)")
            if path:
                try:
                    from output.pdf_report import PDFReport
                    items = [{"analysis_type": k, "result": v} for k, v in ctx.items()
                             if k not in ("version", "timestamp", "date", "product", "department")]
                    PDFReport().generate(items, output_path=path, title="报告导出")
                    QMessageBox.information(self, "导出完成", "PDF 已导出")
                except Exception as e:
                    QMessageBox.critical(self, "导出失败", str(e))
        elif fmt == "docx":
            path, _ = QFileDialog.getSaveFileName(self, "导出 Word", "report.docx", "Word (*.docx)")
            if path:
                try:
                    items = [{"analysis_type": k, "result": v} for k, v in ctx.items()
                             if k not in ("version", "timestamp", "date", "product", "department")]
                    from output.word_report import WordReport
                    WordReport().generate(items, path, title="报告导出")
                    QMessageBox.information(self, "导出完成", "Word 已导出")
                except Exception as e:
                    QMessageBox.critical(self, "导出失败", str(e))
