"""统计摘要面板 — mini直方图+sparkline+五数汇总 Grid"""

import numpy as np
import pandas as pd
from typing import Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QFormLayout, QComboBox,
    QTableWidget, QTableWidgetItem, QSplitter, QHeaderView,
    QScrollArea, QFrame, QListWidget, QAbstractItemView, QGridLayout,
    QFileDialog, QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from core.i18n import i18n
from ui.tabs.base_tab import BaseAnalysisTab
from ui.theme import BUTTON_PRIMARY_STRETCH, BUTTON_SECONDARY
from ui.theme import colors as theme_colors


class SummaryPanelTab(BaseAnalysisTab):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def set_data(self, df: pd.DataFrame, parsed_info: Dict[str, Any] = None):
        BaseAnalysisTab.set_data(self, df, parsed_info)
        if df is not None:
            self._populate_list()

    def _setup_ui(self):
        tc = theme_colors()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self.title_label = QLabel("统计摘要面板")
        self.title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        layout.addWidget(self.title_label)
        layout.addSpacing(4)

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("选择数值列:"))
        self.val_list = QListWidget()
        self.val_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.val_list.setMaximumHeight(80)
        self.val_list.setMinimumWidth(200)
        toolbar.addWidget(self.val_list, 1)

        self.btn_run = QPushButton("生成摘要")
        self.btn_run.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.btn_run.setCursor(Qt.PointingHandCursor)
        self.btn_run.setMinimumHeight(40)
        self.btn_run.clicked.connect(self._run)
        toolbar.addWidget(self.btn_run)
        layout.addLayout(toolbar)

        chart_wrapper = QScrollArea(); chart_wrapper.setWidgetResizable(True)
        chart_wrapper.setFrameShape(QFrame.NoFrame)
        self.chart_container = QWidget()
        self.chart_layout = QVBoxLayout(self.chart_container)
        self.chart_layout.setContentsMargins(0, 0, 0, 0)
        chart_wrapper.setWidget(self.chart_container)
        layout.addWidget(chart_wrapper, 1)

    def _populate_list(self):
        if self.df is None: return
        self.val_list.clear()
        for c in self.df.columns:
            try:
                s = pd.to_numeric(self.df[c], errors="coerce").dropna()
                if len(s) > 0:
                    self.val_list.addItem(str(c))
            except Exception:
                pass

    def _run(self):
        if self.df is None or self.df.empty:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, "提示", "请先导入数据文件")
            return
        val_cols = [i.text() for i in self.val_list.selectedItems()]
        if not val_cols:
            val_cols = [self.val_list.item(i).text() for i in range(min(6, self.val_list.count()))]
        if not val_cols: return

        self._clear_canvas()
        tc = theme_colors()
        plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
        plt.rcParams["axes.unicode_minus"] = False

        n = len(val_cols)
        cols_per_row = min(3, n)
        rows = (n + cols_per_row - 1) // cols_per_row
        fig = Figure(figsize=(cols_per_row * 4.5, rows * 3.2), dpi=100)
        fig.set_facecolor(tc["bg_card"])

        for i, col in enumerate(val_cols):
            vals = pd.to_numeric(self.df[col], errors="coerce").dropna().values
            if len(vals) < 3: continue

            # 每列: 左hist + 右stats
            ax_hist = fig.add_subplot(rows, cols_per_row * 2,
                                      i // cols_per_row * cols_per_row * 2 + (i % cols_per_row) * 2 + 1)
            ax_stats = fig.add_subplot(rows, cols_per_row * 2,
                                       i // cols_per_row * cols_per_row * 2 + (i % cols_per_row) * 2 + 2)

            ax_hist.set_facecolor(tc["bg_body"])
            ax_stats.set_facecolor(tc["bg_body"])

            # Mini 直方图
            bins = min(25, max(5, int(np.sqrt(len(vals)))))
            ax_hist.hist(vals, bins=bins, color=tc["accent_bright"], alpha=0.75, edgecolor="white", linewidth=0.3)
            ax_hist.axvline(np.mean(vals), color="#ff6b6b", linestyle="--", linewidth=1)
            ax_hist.set_title(col, fontsize=9, fontweight="bold", color=tc["text_primary"])
            ax_hist.tick_params(colors=tc["text_muted"], labelsize=7)

            # Sparkline (mini 折线图)
            ax_spark = ax_hist.inset_axes([0.78, 0.85, 0.20, 0.12])
            ax_spark.plot(np.arange(len(vals)), vals, linewidth=0.5, color=tc["accent_bright"])
            ax_spark.fill_between(np.arange(len(vals)), vals, alpha=0.15, color=tc["accent_bright"])
            ax_spark.axis("off")

            # 右侧统计
            ax_stats.axis("off")
            stats = [
                f"N = {len(vals)}",
                f"μ = {np.mean(vals):.3f}",
                f"σ = {np.std(vals, ddof=1):.3f}",
                f"Min = {np.min(vals):.3f}",
                f"Q1 = {np.percentile(vals, 25):.3f}",
                f"Med = {np.median(vals):.3f}",
                f"Q3 = {np.percentile(vals, 75):.3f}",
                f"Max = {np.max(vals):.3f}",
            ]
            for j, s in enumerate(stats):
                ax_stats.text(0.05, 0.92 - j * 0.11, s, transform=ax_stats.transAxes,
                              fontsize=7.5, fontfamily="Consolas", color=tc["text_secondary"])

        fig.suptitle("统计摘要面板", fontsize=14, fontweight="bold", color=tc["text_primary"], y=0.98)
        fig.subplots_adjust(left=0.04, right=0.97, top=0.93, bottom=0.04, wspace=0.25, hspace=0.4)

        canvas = FigureCanvasQTAgg(fig)
        self.chart_layout.addWidget(canvas)
        self.canvas = canvas; self.current_figure = fig
        self._add_chart_toolbar()
        self.analysis_completed.emit()
