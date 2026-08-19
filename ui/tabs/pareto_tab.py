"""帕累托图增强 Tab — 列选择 + 排序 + 累计百分比 + 二层钻取"""

from typing import Dict, Any, List

import numpy as np
import pandas as pd

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QGroupBox, QFormLayout, QFrame,
    QTableWidget, QTableWidgetItem, QSplitter, QHeaderView,
    QScrollArea, QSpinBox, QDoubleSpinBox,
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
from output.chart_engine import create_pareto_chart


class ParetoTab(BaseAnalysisTab):

    def __init__(self, parent=None):
        self._full_df: pd.DataFrame = None  # 保留完整数据用于钻取回溯
        super().__init__(parent)
        self._setup_ui()

    def set_data(self, df: pd.DataFrame, parsed_info: Dict[str, Any] = None):
        BaseAnalysisTab.set_data(self, df, parsed_info)
        self._full_df = df
        if df is not None:
            cols = list(df.columns)
            self._populate_combo(self.cat_combo, cols)
            self._populate_combo(self.val_combo, cols)

    def _setup_ui(self):
        tc = theme_colors()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self.title_label = QLabel("帕累托图 (Pareto)")
        self.title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        layout.addWidget(self.title_label)
        layout.addSpacing(4)

        splitter = QSplitter(Qt.Horizontal)

        # ── 左侧: 配置 ──
        left = QWidget()
        left.setMaximumWidth(320)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 4, 0)

        config_group = QGroupBox("图表配置")
        config_layout = QFormLayout(config_group)

        self.cat_combo = QComboBox()
        self.cat_combo.setMinimumWidth(140)
        config_layout.addRow("分类列:", self.cat_combo)

        self.val_combo = QComboBox()
        self.val_combo.setMinimumWidth(140)
        config_layout.addRow("数值列:", self.val_combo)

        self.top_n_spin = QSpinBox()
        self.top_n_spin.setRange(5, 100)
        self.top_n_spin.setValue(20)
        self.top_n_spin.setToolTip("显示前 N 项，其余归入「其他」")
        config_layout.addRow("显示前 N 项:", self.top_n_spin)

        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0, 100)
        self.threshold_spin.setValue(0)
        self.threshold_spin.setSuffix("%")
        self.threshold_spin.setToolTip("累积百分比阈值线 (0 = 不显示)")
        config_layout.addRow("阈值线:", self.threshold_spin)

        self.btn_draw = QPushButton("◈ 绘制帕累托图")
        self.btn_draw.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.btn_draw.setCursor(Qt.PointingHandCursor)
        self.btn_draw.setMinimumHeight(44)
        self.btn_draw.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        self.btn_draw.clicked.connect(self._draw)
        config_layout.addRow(self.btn_draw)

        self.btn_reset = QPushButton("↺ 还原全部数据")
        self.btn_reset.setStyleSheet(BUTTON_SECONDARY)
        self.btn_reset.setCursor(Qt.PointingHandCursor)
        self.btn_reset.clicked.connect(self._reset_data)
        config_layout.addRow(self.btn_reset)

        left_layout.addWidget(config_group)

        # 数据表
        table_group = QGroupBox("详细数据")
        table_layout = QVBoxLayout(table_group)
        self.result_table = QTableWidget()
        self.result_table.setAlternatingRowColors(True)
        self.result_table.horizontalHeader().setStretchLastSection(True)
        self.result_table.itemClicked.connect(self._on_item_clicked)
        table_layout.addWidget(self.result_table)
        left_layout.addWidget(table_group)

        splitter.addWidget(left)

        # ── 右侧: 图表 ──
        chart_wrapper = QScrollArea()
        chart_wrapper.setWidgetResizable(True)
        chart_wrapper.setFrameShape(QFrame.NoFrame)
        self.chart_container = QWidget()
        self.chart_layout = QVBoxLayout(self.chart_container)
        self.chart_layout.setContentsMargins(0, 0, 0, 0)
        chart_wrapper.setWidget(self.chart_container)
        splitter.addWidget(chart_wrapper)

        splitter.setSizes([320, 700])
        layout.addWidget(splitter, 1)

    @staticmethod
    def _populate_combo(combo: QComboBox, cols: list):
        current = combo.currentText()
        combo.blockSignals(True)
        combo.clear()
        for c in cols:
            combo.addItem(str(c), c)
        idx = combo.findText(current)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        combo.blockSignals(False)

    def _draw(self):
        if self.df is None or self.df.empty:
            return
        cat_col = self.cat_combo.currentData()
        val_col = self.val_combo.currentData()
        if cat_col is None or val_col is None:
            return

        # 聚合: 按分类列 groupby 求和
        df_work = self.df.copy()
        df_work[val_col] = pd.to_numeric(df_work[val_col], errors="coerce")
        grouped = df_work.groupby(cat_col)[val_col].sum().sort_values(ascending=False).dropna()

        if len(grouped) == 0:
            return

        # Top-N + 其他
        top_n = self.top_n_spin.value()
        if len(grouped) > top_n:
            top = grouped.head(top_n)
            other_val = grouped.iloc[top_n:].sum()
            grouped = pd.concat([top, pd.Series({f"其他 ({len(grouped)-top_n}项)": other_val})])

        labels = grouped.index.tolist()
        values = grouped.values.tolist()

        self._fill_table(labels, values, grouped)
        self._draw_chart(labels, values)

    def _fill_table(self, labels: list, values: list, grouped: pd.Series):
        total = grouped.sum()
        cum = 0
        self.result_table.setColumnCount(4)
        self.result_table.setHorizontalHeaderLabels(["分类", "数值", "占比(%)", "累计(%)"])
        self.result_table.setRowCount(len(labels))
        for i, (lbl, val) in enumerate(zip(labels, values)):
            pct = val / total * 100 if total > 0 else 0
            cum += pct
            self.result_table.setItem(i, 0, QTableWidgetItem(str(lbl)))
            self.result_table.setItem(i, 1, QTableWidgetItem(f"{val:.2f}"))
            self.result_table.setItem(i, 2, QTableWidgetItem(f"{pct:.1f}"))
            self.result_table.setItem(i, 3, QTableWidgetItem(f"{cum:.1f}"))
        self.result_table.resizeColumnsToContents()

    def _draw_chart(self, labels: list, values: list):
        self._clear_canvas()
        tc = theme_colors()
        plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
        plt.rcParams["axes.unicode_minus"] = False

        # 使用 chart_engine 的 create_pareto_chart 获得标准图表，再增强
        fig = create_pareto_chart(labels, values, title="帕累托图")

        # 增强: 阈值线
        threshold = self.threshold_spin.value()
        if threshold > 0 and threshold < 100:
            ax = fig.axes[0]
            ax.axhline(y=threshold, color="#ffa726", linestyle=":", linewidth=1.5,
                      alpha=0.7, label=f"{threshold}% 阈值")
            ax.legend(fontsize=8)

        fig.set_facecolor(tc["bg_card"])
        canvas = FigureCanvasQTAgg(fig)
        self.chart_layout.addWidget(canvas)
        self.canvas = canvas
        self.current_figure = fig
        self._add_chart_toolbar()
        self.analysis_completed.emit()

    def _on_item_clicked(self, item: QTableWidgetItem):
        """单击表格行: 钻取到该分类，仅显示该分类的数据"""
        row = item.row()
        cat_item = self.result_table.item(row, 0)
        if cat_item is None:
            return
        cat_name = cat_item.text()
        if cat_name.startswith("其他"):
            return  # 不钻取「其他」行

        if self._full_df is None:
            return
        cat_col = self.cat_combo.currentData()
        if cat_col is None:
            return

        # 过滤到该分类
        filtered = self._full_df[self._full_df[cat_col].astype(str) == cat_name]
        if len(filtered) > 0:
            self.df = filtered
            self._draw()

    def _reset_data(self):
        if self._full_df is not None:
            self.set_data(self._full_df)
            self._draw()
