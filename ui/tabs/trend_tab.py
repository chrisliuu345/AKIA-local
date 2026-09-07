"""多系列趋势图 — 日期+多Y轴, 移动平均, 异常点标注, 周期标记"""

import numpy as np
import pandas as pd
from typing import Dict, Any

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QGroupBox,
    QFormLayout,
    QComboBox,
    QSpinBox,
    QCheckBox,
    QTableWidget,
    QTableWidgetItem,
    QSplitter,
    QScrollArea,
    QFrame,
    QListWidget,
    QAbstractItemView,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from ui.tabs.base_tab import BaseAnalysisTab
from ui.theme import BUTTON_PRIMARY_STRETCH
from ui.theme import colors as theme_colors
from ui.font_config import get_ui_font

TREND_COLORS = ["#4da6ff", "#ff6b6b", "#51cf66", "#ffa726", "#cc5de8", "#20c997"]


class TrendTab(BaseAnalysisTab):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def set_data(self, df: pd.DataFrame, parsed_info: Dict[str, Any] = None):
        BaseAnalysisTab.set_data(self, df, parsed_info)
        if df is not None:
            self._populate_lists()

    def _setup_ui(self):
        tc = theme_colors()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self.title_label = QLabel("多系列趋势图")
        self.title_label.setFont(QFont(get_ui_font(), 18, QFont.Bold))
        layout.addWidget(self.title_label)
        layout.addSpacing(4)

        splitter = QSplitter(Qt.Horizontal)
        left = QWidget()
        left.setMaximumWidth(320)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 4, 0)

        cfg = QGroupBox("配置")
        cfg_layout = QFormLayout(cfg)
        self.date_combo = QComboBox()
        self.date_combo.setMinimumWidth(140)
        cfg_layout.addRow("日期列:", self.date_combo)

        self.val_list = QListWidget()
        self.val_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.val_list.setMinimumHeight(80)
        self.val_list.setMaximumHeight(140)
        cfg_layout.addRow("数值列 (多选):", self.val_list)

        self.ma_spin = QSpinBox()
        self.ma_spin.setRange(0, 30)
        self.ma_spin.setValue(5)
        self.ma_spin.setToolTip("移动平均窗口 (0=不显示)")
        cfg_layout.addRow("移动平均窗口:", self.ma_spin)

        self.cb_anomaly = QCheckBox("标注异常点 (|z|>3)")
        self.cb_anomaly.setChecked(True)
        self.cb_anomaly.setStyleSheet(f"color: {tc['text_secondary']};")
        cfg_layout.addRow(self.cb_anomaly)

        self.cb_fill = QCheckBox("填充区域")
        self.cb_fill.setChecked(False)
        self.cb_fill.setStyleSheet(f"color: {tc['text_secondary']};")
        cfg_layout.addRow(self.cb_fill)

        self.btn_run = QPushButton("生成趋势图")
        self.btn_run.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.btn_run.setCursor(Qt.PointingHandCursor)
        self.btn_run.setMinimumHeight(44)
        self.btn_run.setFont(QFont(get_ui_font(), 12, QFont.Bold))
        self.btn_run.clicked.connect(self._run)
        cfg_layout.addRow(self.btn_run)
        left_layout.addWidget(cfg)

        self.result_table = QTableWidget()
        self.result_table.setAlternatingRowColors(True)
        self.result_table.horizontalHeader().setStretchLastSection(True)
        left_layout.addWidget(self.result_table)
        splitter.addWidget(left)

        chart_wrapper = QScrollArea()
        chart_wrapper.setWidgetResizable(True)
        chart_wrapper.setFrameShape(QFrame.NoFrame)
        self.chart_container = QWidget()
        self.chart_layout = QVBoxLayout(self.chart_container)
        self.chart_layout.setContentsMargins(0, 0, 0, 0)
        chart_wrapper.setWidget(self.chart_container)
        splitter.addWidget(chart_wrapper)
        splitter.setSizes([320, 750])
        layout.addWidget(splitter, 1)

    def _populate_lists(self):
        if self.df is None:
            return
        self.date_combo.clear()
        self.val_list.clear()
        for c in self.df.columns:
            self.date_combo.addItem(str(c), c)
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
        date_col = self.date_combo.currentData()
        val_cols = [i.text() for i in self.val_list.selectedItems()]
        if not date_col or not val_cols:
            return

        dates = pd.to_datetime(self.df[date_col], errors="coerce")
        n = len(dates.dropna())
        if n < 3:
            return

        self._clear_canvas()
        tc = theme_colors()
        plt.rcParams["axes.unicode_minus"] = False

        MAX_POINTS = 1000
        fig_w = min(20, max(10, n * 0.02)) if n <= MAX_POINTS else 15
        fig = Figure(figsize=(fig_w, 5.5), dpi=100)
        fig.set_facecolor(tc["bg_card"])
        ax = fig.add_subplot(111)
        ax.set_facecolor(tc["bg_body"])

        stats_rows = []
        sampled_note = ""
        for j, vcol in enumerate(val_cols):
            vals = pd.to_numeric(self.df[vcol], errors="coerce")
            mask = dates.notna() & vals.notna()
            d, v = dates[mask].values, vals[mask].values
            if len(d) < 2:
                continue
            idx = np.argsort(d)
            d, v = d[idx], v[idx]
            color = TREND_COLORS[j % len(TREND_COLORS)]

            d_plot, v_plot = d, v
            if len(d) > MAX_POINTS:
                step = max(1, len(d) // MAX_POINTS)
                sampled_idx = list(range(0, len(d), step))
                min_i = int(np.argmin(v))
                max_i = int(np.argmax(v))
                if min_i not in sampled_idx:
                    sampled_idx.append(min_i)
                if max_i not in sampled_idx:
                    sampled_idx.append(max_i)
                if 0 not in sampled_idx:
                    sampled_idx.append(0)
                if len(d) - 1 not in sampled_idx:
                    sampled_idx.append(len(d) - 1)
                sampled_idx = sorted(set(sampled_idx))
                d_plot, v_plot = d[sampled_idx], v[sampled_idx]
                if j == 0:
                    sampled_note = f" (采样 {len(d_plot)}/{len(d)})"

            ax.plot(
                d_plot,
                v_plot,
                "o-",
                color=color,
                linewidth=1.5,
                markersize=3,
                label=vcol,
                alpha=0.85,
            )

            if self.cb_fill.isChecked():
                ax.fill_between(d_plot, v_plot, alpha=0.06, color=color)

            ma_w = self.ma_spin.value()
            if ma_w > 1 and len(v) >= ma_w:
                ma = np.convolve(v, np.ones(ma_w) / ma_w, mode="valid")
                md = d[ma_w - 1 :]
                ax.plot(md, ma, "--", color=color, linewidth=1.2, alpha=0.6)

            anom = []
            if self.cb_anomaly.isChecked() and len(v) > 5:
                z = np.abs((v - np.mean(v)) / (np.std(v) + 1e-9))
                anom = np.where(z > 3)[0]
                if len(anom) > 0:
                    ax.scatter(
                        d[anom],
                        v[anom],
                        color="#ff4444",
                        s=40,
                        marker="o",
                        edgecolors="white",
                        linewidth=1,
                        zorder=5,
                        label="_",
                    )

            stats_rows.append(
                [
                    vcol,
                    f"{len(v)}",
                    f"{np.mean(v):.3f}",
                    f"{np.std(v):.3f}",
                    f"{np.min(v):.3f}",
                    f"{np.max(v):.3f}",
                    f"{len(anom) if self.cb_anomaly.isChecked() else 0}",
                ]
            )

        ax.set_xlabel("日期", fontsize=10)
        ax.set_ylabel("数值", fontsize=10)
        ax.set_title(f"多系列趋势分析{sampled_note}", fontsize=12, fontweight="bold")
        ax.legend(fontsize=8, ncol=min(3, len(val_cols)), loc="upper left")
        ax.grid(True, alpha=0.3)
        fig.autofmt_xdate()
        fig.subplots_adjust(left=0.07, right=0.96, top=0.92, bottom=0.14)

        canvas = FigureCanvasQTAgg(fig)
        self.chart_layout.addWidget(canvas)
        self.canvas = canvas
        self.current_figure = fig
        self._add_chart_toolbar()

        hdrs = ["列", "N", "均值", "Std", "Min", "Max", "异常点"]
        self.result_table.setColumnCount(len(hdrs))
        self.result_table.setHorizontalHeaderLabels(hdrs)
        self.result_table.setRowCount(len(stats_rows))
        for i, row in enumerate(stats_rows):
            for j, v in enumerate(row):
                self.result_table.setItem(i, j, QTableWidgetItem(v))
        self.result_table.resizeColumnsToContents()
        self.analysis_completed.emit()
