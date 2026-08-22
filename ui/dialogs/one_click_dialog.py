"""一键智能分析向导 — 4步: 确认数据 → 选择范围 → 执行 → 报告"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QProgressBar, QCheckBox, QWidget, QScrollArea,
    QFrame, QFileDialog,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont

from ui.theme import colors as theme_colors

from core.one_click_analyzer import OneClickAnalyzer
from core.llm_client import LLMClient


class AnalyzeWorker(QThread):
    progress_msg = Signal(str, int)
    finished = Signal(dict)

    def __init__(self, raw_data, selected):
        super().__init__()
        self.raw_data = raw_data
        self.selected = selected

    def run(self):
        try:
            llm = LLMClient()
            analyzer = OneClickAnalyzer(llm_client=llm if llm.available else None)
            analyzer.set_progress_callback(lambda msg, pct: self.progress_msg.emit(msg, pct))
            result = analyzer.run(self.raw_data, self.selected)
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit({"error": str(e)})


class OneClickDialog(QDialog):
    def __init__(self, raw_data: dict, parent=None):
        super().__init__(parent)
        self.raw_data = raw_data
        self.selected_analyses = []
        self.result = None

        self.setWindowTitle("一键智能分析")
        self.setMinimumSize(640, 520)
        self.resize(680, 560)

        self._setup_ui()
        # 初始化: 从数据画像提取推荐
        self._init_recommendations()

    def _setup_ui(self):
        tc = theme_colors(self)
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # ── 标题 ──
        title = QLabel("一键智能分析")
        title.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        layout.addWidget(title)

        desc = QLabel("自动画像数据 → 推荐分析组合 → 批量执行 → AI 撰写报告")
        desc.setFont(QFont("Microsoft YaHei", 9))
        desc.setStyleSheet(f"color: {tc['text_muted']};")
        layout.addWidget(desc)

        # ── 步骤1: 数据概况 ──
        info_card = QFrame()
        info_card.setStyleSheet(
            f"QFrame {{ background: {tc['bg_card']}; border: 1px solid {tc['border_light']}; "
            f"border-radius: 8px; padding: 10px; }}"
        )
        info_layout = QVBoxLayout(info_card)
        total_rows = sum(len(df) for df in self.raw_data.values())
        sheet_names = list(self.raw_data.keys())
        self.info_label = QLabel(
            f"数据概况: {len(sheet_names)} 个工作表, 约 {total_rows} 行\n"
            f"工作表: {', '.join(sheet_names[:6])}"
            + ("…" if len(sheet_names) > 6 else "")
        )
        self.info_label.setFont(QFont("Microsoft YaHei", 10))
        self.info_label.setWordWrap(True)
        info_layout.addWidget(self.info_label)
        layout.addWidget(info_card)

        # ── 步骤2: 分析范围选择 ──
        select_label = QLabel("选择分析范围（推荐项已勾选）:")
        select_label.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        layout.addWidget(select_label)

        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setMaximumHeight(200)
        self.check_widget = QWidget()
        self.check_layout = QVBoxLayout(self.check_widget)
        self.check_layout.setSpacing(4)
        self.check_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(self.check_widget)
        layout.addWidget(scroll)

        # ── 进度条 + 日志 ──
        self.progress = QProgressBar()
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        self.progress.setFixedHeight(18)
        self.progress.setStyleSheet(
            f"QProgressBar {{ background: {tc['bg_card']}; border: 1px solid {tc['border_light']}; "
            f"border-radius: 4px; text-align: center; }}"
            f"QProgressBar::chunk {{ background: {tc['accent']}; border-radius: 3px; }}"
        )
        layout.addWidget(self.progress)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("Consolas", 9))
        self.log_view.setMaximumHeight(100)
        self.log_view.setStyleSheet(
            f"QTextEdit {{ background: {tc['bg_card']}; border: 1px solid {tc['border_light']}; "
            f"border-radius: 4px; padding: 4px; }}"
        )
        layout.addWidget(self.log_view)

        # ── 报告预览 ──
        self.report_view = QTextEdit()
        self.report_view.setReadOnly(True)
        self.report_view.setFont(QFont("Microsoft YaHei", 10))
        self.report_view.setStyleSheet(
            f"QTextEdit {{ background: {tc['bg_card']}; border: 1px solid {tc['border_light']}; "
            f"border-radius: 6px; padding: 8px; }}"
        )
        self.report_view.setVisible(False)
        layout.addWidget(self.report_view, 1)

        # ── 操作按钮 ──
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()

        self.run_btn = QPushButton("开始分析")
        self.run_btn.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        self.run_btn.setMinimumHeight(36)
        self.run_btn.setMinimumWidth(120)
        self.run_btn.setCursor(Qt.PointingHandCursor)
        self.run_btn.setStyleSheet(
            f"QPushButton {{ background: {tc['accent']}; color: white; border: none; "
            f"border-radius: 6px; padding: 6px 20px; }}"
            f"QPushButton:hover {{ background: {tc['accent_dark']}; }}"
            f"QPushButton:disabled {{ background: {tc['text_muted']}; }}"
        )
        self.run_btn.clicked.connect(self._run_analysis)
        btn_row.addWidget(self.run_btn)

        self.export_pdf_btn = QPushButton("导出 PDF")
        self.export_pdf_btn.setFont(QFont("Microsoft YaHei", 10))
        self.export_pdf_btn.setMinimumHeight(36)
        self.export_pdf_btn.setCursor(Qt.PointingHandCursor)
        self.export_pdf_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {tc['accent_bright']}; "
            f"border: 1px solid {tc['accent']}; border-radius: 6px; padding: 6px 16px; }}"
            f"QPushButton:hover {{ background: {tc['bg_hover']}; }}"
        )
        self.export_pdf_btn.clicked.connect(self._export_pdf)
        self.export_pdf_btn.setVisible(False)
        btn_row.addWidget(self.export_pdf_btn)

        self.export_md_btn = QPushButton("导出 Markdown")
        self.export_md_btn.setFont(QFont("Microsoft YaHei", 10))
        self.export_md_btn.setMinimumHeight(36)
        self.export_md_btn.setCursor(Qt.PointingHandCursor)
        self.export_md_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {tc['accent_bright']}; "
            f"border: 1px solid {tc['accent']}; border-radius: 6px; padding: 6px 16px; }}"
            f"QPushButton:hover {{ background: {tc['bg_hover']}; }}"
        )
        self.export_md_btn.clicked.connect(self._export_md)
        self.export_md_btn.setVisible(False)
        btn_row.addWidget(self.export_md_btn)

        close_btn = QPushButton("关闭")
        close_btn.setFont(QFont("Microsoft YaHei", 10))
        close_btn.setMinimumHeight(36)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _init_recommendations(self):
        """用 Analyzer 生成推荐并填充复选框"""
        analyzer = OneClickAnalyzer()
        plan = analyzer.profile_and_recommend(self.raw_data)
        self._recommendations = plan.get("recommendations", [])

        self._checks = {}
        for rec in self._recommendations:
            row = QHBoxLayout()
            row.setSpacing(6)
            cb = QCheckBox(f"{rec['label']}")
            cb.setFont(QFont("Microsoft YaHei", 10))
            cb.setChecked(rec.get("priority") == "high")

            priority_color = {"high": "#ff6b6b", "medium": "#ffa726", "low": "#66bb6a"}
            badge = QLabel({
                "high": "★ 推荐", "medium": "☆ 建议", "low": "· 可选"
            }.get(rec.get("priority", ""), ""))
            badge.setFont(QFont("Microsoft YaHei", 8))
            badge.setStyleSheet(
                f"color: {priority_color.get(rec.get('priority',''), '#888')}; "
                f"background: transparent; padding: 0 4px;"
            )
            row.addWidget(cb)
            row.addWidget(badge)

            reason_lbl = QLabel(rec.get("reason", ""))
            reason_lbl.setFont(QFont("Microsoft YaHei", 8))
            reason_lbl.setStyleSheet(f"color: {theme_colors()['text_muted']}; background: transparent;")
            row.addWidget(reason_lbl, 1)

            container = QWidget()
            container.setLayout(row)
            self.check_layout.addWidget(container)
            self._checks[rec["type"]] = cb

        self.check_layout.addStretch()

    def _get_selected(self) -> list:
        return [t for t, cb in self._checks.items() if cb.isChecked()]

    def _run_analysis(self):
        selected = self._get_selected()
        if not selected:
            self.log_view.append(" 请至少选择一项分析")
            return

        self.run_btn.setEnabled(False)
        self.run_btn.setText("分析中...")
        self.progress.setValue(0)
        self.log_view.clear()
        self.report_view.setVisible(False)

        self.worker = AnalyzeWorker(self.raw_data, selected)
        self.worker.progress_msg.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, msg: str, pct: int):
        self.log_view.append(f"[{pct}%] {msg}")
        self.progress.setValue(pct)

    def _on_finished(self, result: dict):
        self.result = result
        self.run_btn.setEnabled(True)
        self.run_btn.setText("开始分析")
        self.progress.setValue(100)

        # 显示报告
        conclusion = result.get("conclusion", "无内容")
        success = result.get("success_count", 0)
        total = result.get("total_count", 0)

        header = (
            f"<h2>一键分析报告</h2>"
            f"<p><b>完成:</b> {success}/{total} 项分析成功</p>"
            f"<hr>"
        )
        body = conclusion.replace("\n", "<br>") if conclusion else ""
        self.report_view.setHtml(header + body)
        self.report_view.setVisible(True)

        self.export_pdf_btn.setVisible(True)
        self.export_md_btn.setVisible(True)
        self.log_view.append(" 分析完成 — 报告已生成")

    def _export_pdf(self):
        if not self.result:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出 PDF 报告", "analysis_report.pdf", "PDF (*.pdf)"
        )
        if not path:
            return
        try:
            from output.pdf_report import PDFReport
            conclusion = self.result.get("conclusion", "")
            results = self.result.get("results", [])
            PDFReport().generate(
                analyses=[{"analysis_type": "one_click", "results": results, "conclusion": conclusion}],
                output_path=path,
                title="一键智能分析报告",
                subtitle=f"完成 {self.result.get('success_count',0)}/{self.result.get('total_count',0)} 项",
            )
            self.log_view.append(f" PDF 报告已导出: {path}")
        except Exception as e:
            self.log_view.append(f" 导出失败: {e}")

    def _export_md(self):
        if not self.result:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出 Markdown 报告", "analysis_report.md", "Markdown (*.md)"
        )
        if not path:
            return
        conclusion = self.result.get("conclusion", "")
        lines = [
            "# 一键智能分析报告\n",
            f"完成: {self.result.get('success_count', 0)}/{self.result.get('total_count', 0)} 项\n",
            "## 分析结果\n",
        ]
        for r in self.result.get("results", []):
            ok = "✅" if r.get("success") else "❌"
            lines.append(f"- {ok} **{r.get('analysis_type', '?')}**: {r.get('summary', '')}\n")
        lines.append("\n## 分析结论\n")
        lines.append(conclusion)

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        self.log_view.append(f" Markdown 报告已导出: {path}")
