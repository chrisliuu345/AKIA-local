"""多工厂对比 Tab (34) — 跨工厂指标横向对比 (v2.4 E2)

- 添加多个工厂 Excel 文件 → 逐文件自动解析 (测量列/规格限)
- 汇总对比: 均值/标准差/Cpk(含规格列时)/SPC判异点数
- 输出分组柱状图 + 汇总表, 结果进入 analyses[34]/会话/Dashboard
"""

import os

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QMessageBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

from core.i18n import i18n
from core.plant_compare import summarize_plant, build_comparison
from ui.theme import colors as theme_colors, BUTTON_PRIMARY_STRETCH, BUTTON_SECONDARY
from ui.tabs.base_tab import BaseAnalysisTab

MULTI_PLANT_ANALYSIS_TYPE = "多工厂对比"


class MultiPlantTab(BaseAnalysisTab):
    """多工厂对比 — 同一指标跨工厂横向比较"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._plants = []
        self._setup_ui()

    # ── UI ───────────────────────────────────────────────
    def _setup_ui(self):
        tc = theme_colors()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title = QLabel(i18n.tr("multi_plant.title"))
        title.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        title.setStyleSheet(f"color: {tc['text_primary']}; background: transparent;")
        layout.addWidget(title)

        # 文件列表区
        list_row = QHBoxLayout()
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QListWidget.SingleSelection)
        list_row.addWidget(self.file_list, 1)

        btn_col = QVBoxLayout()
        btn_col.setSpacing(6)
        self.add_btn = QPushButton(i18n.tr("multi_plant.add"))
        self.add_btn.setStyleSheet(BUTTON_SECONDARY)
        self.add_btn.clicked.connect(self._on_add)
        btn_col.addWidget(self.add_btn)
        self.remove_btn = QPushButton(i18n.tr("multi_plant.remove"))
        self.remove_btn.setStyleSheet(BUTTON_SECONDARY)
        self.remove_btn.clicked.connect(self._on_remove)
        btn_col.addWidget(self.remove_btn)
        self.clear_btn = QPushButton(i18n.tr("multi_plant.clear"))
        self.clear_btn.setStyleSheet(BUTTON_SECONDARY)
        self.clear_btn.clicked.connect(self._on_clear)
        btn_col.addWidget(self.clear_btn)
        btn_col.addStretch()
        list_row.addLayout(btn_col)
        layout.addLayout(list_row, 1)

        # 运行行
        ctrl = QHBoxLayout()
        self.run_btn = QPushButton(i18n.tr("multi_plant.run"))
        self.run_btn.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        self.run_btn.setFixedHeight(44)
        self.run_btn.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.run_btn.setCursor(Qt.PointingHandCursor)
        self.run_btn.clicked.connect(self._on_run)
        ctrl.addWidget(self.run_btn)
        self.status_label = QLabel("")
        self.status_label.setFont(QFont("Microsoft YaHei", 10))
        self.status_label.setStyleSheet(f"color: {tc['text_secondary']};")
        ctrl.addWidget(self.status_label)
        ctrl.addStretch()
        layout.addLayout(ctrl)

        # 汇总表
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            i18n.tr("multi_plant.col_plant"),
            i18n.tr("multi_plant.col_samples"),
            i18n.tr("multi_plant.col_mean"),
            i18n.tr("multi_plant.col_std"),
            i18n.tr("multi_plant.col_cpk"),
            i18n.tr("multi_plant.col_violations"),
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 6):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table, 1)

        # 图表区
        self.chart_layout = QVBoxLayout()
        self.chart_layout.setSpacing(0)
        layout.addLayout(self.chart_layout, 1)
        self._show_empty_hint()

    def _show_empty_hint(self):
        while self.chart_layout.count():
            item = self.chart_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
        hint = QLabel(i18n.tr("multi_plant.empty"))
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("color: #6e7080; font-size: 14px;")
        self.chart_layout.addWidget(hint)
        self.canvas = None
        self.current_figure = None

    # ── 交互 ─────────────────────────────────────────────
    def _on_add(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, i18n.tr("multi_plant.choose_files"), "",
            "Excel (*.xlsx *.xls *.xlsm)"
        )
        for path in paths:
            if path and path not in self._plants:
                self._plants.append(path)
                self.file_list.addItem(os.path.basename(path))

    def _on_remove(self):
        row = self.file_list.currentRow()
        if row >= 0:
            self.file_list.takeItem(row)
            del self._plants[row]

    def _on_clear(self):
        self.file_list.clear()
        self._plants = []

    # ── 分析 ─────────────────────────────────────────────
    def _on_run(self):
        tc = theme_colors()
        if not self._plants:
            self.status_label.setText(i18n.tr("multi_plant.no_files"))
            self.status_label.setStyleSheet("color: #e74c3c;")
            return

        plants = [summarize_plant(path) for path in self._plants]
        comparison = build_comparison(plants)

        self._fill_table(plants)
        self._render_figure(comparison)

        self.current_result = {
            "analysis_type": MULTI_PLANT_ANALYSIS_TYPE,
            "params": {"files": list(self._plants)},
            "result": comparison,
        }
        self.analysis_completed.emit()

        errors = sum(1 for p in plants if p.get("error"))
        if errors:
            self.status_label.setText(
                i18n.tr("multi_plant.status_error").format(n=errors)
            )
            self.status_label.setStyleSheet("color: #e74c3c;")
        else:
            self.status_label.setText(
                i18n.tr("multi_plant.status_done").format(n=len(plants))
            )
            self.status_label.setStyleSheet(f"color: {tc['text_secondary']};")

    def _fill_table(self, plants):
        self.table.clearSpans()
        self.table.setRowCount(len(plants))
        for row, p in enumerate(plants):
            if p.get("error"):
                self.table.setItem(row, 0, QTableWidgetItem(p["name"]))
                self.table.setItem(row, 1, QTableWidgetItem(p["error"]))
                self.table.setSpan(row, 1, 1, 5)
                continue
            self.table.setItem(row, 0, QTableWidgetItem(p["name"]))
            self.table.setItem(row, 1, QTableWidgetItem(str(p["sample_size"])))
            self.table.setItem(row, 2, QTableWidgetItem(f"{p['mean']:.4f}"))
            self.table.setItem(row, 3, QTableWidgetItem(f"{p['std']:.4f}"))
            cpk = p.get("cpk")
            self.table.setItem(
                row, 4, QTableWidgetItem(f"{cpk:.3f}" if cpk is not None else "—")
            )
            self.table.setItem(row, 5, QTableWidgetItem(str(p.get("violations", 0))))

    def _render_figure(self, comparison: dict):
        tc = theme_colors()
        ok = [p for p in comparison["plants"] if not p.get("error")]
        if not ok:
            self._show_empty_hint()
            return

        names = [p["name"] for p in ok]
        means = [p["mean"] for p in ok]
        stds = [p["std"] for p in ok]
        viols = [p["violations"] for p in ok]
        cpk_pairs = [(p["name"], p["cpk"]) for p in ok if p["cpk"] is not None]

        panels = [
            (means, i18n.tr("multi_plant.mean"), "#4da6ff", names),
            (stds, i18n.tr("multi_plant.std"), "#27ae60", names),
            (viols, i18n.tr("multi_plant.violations"), "#e74c3c", names),
        ]
        if cpk_pairs:
            panels.append(
                ([v for _, v in cpk_pairs], i18n.tr("multi_plant.cpk"),
                 "#ffa726", [n for n, _ in cpk_pairs])
            )

        fig = Figure(figsize=(11, 4.2 * len(panels)), dpi=100)
        bg = tc.get("chart_bg", "#ffffff")
        fg = tc.get("text_primary", "#2b2b2b")

        def _bar(ax, values, ylabel, color, xnames):
            x = range(len(values))
            ax.bar(x, values, color=color, alpha=0.85)
            ax.set_xticks(list(x))
            ax.set_xticklabels(xnames, fontsize=9, rotation=15, ha="right")
            ax.set_ylabel(ylabel, fontsize=10)
            ax.set_facecolor(bg)
            ax.tick_params(colors=fg, labelsize=9)
            for spine in ax.spines.values():
                spine.set_color("#cccccc")
            ax.grid(axis="y", linestyle="--", alpha=0.3)

        for i, (values, ylabel, color, xnames) in enumerate(panels, start=1):
            ax = fig.add_subplot(len(panels), 1, i)
            _bar(ax, values, ylabel, color, xnames)
            if i == 1:
                ax.set_title(i18n.tr("multi_plant.title"), fontsize=12, color=fg)

        fig.tight_layout(rect=[0.02, 0.02, 0.98, 0.96])

        while self.chart_layout.count():
            item = self.chart_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
        canvas = FigureCanvasQTAgg(fig)
        canvas.setStyleSheet("background: transparent;")
        self.chart_layout.addWidget(canvas)
        self.canvas = canvas
        self.current_figure = fig
