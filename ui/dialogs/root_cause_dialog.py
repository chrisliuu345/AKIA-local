"""AI 根因分析对话框 — 根因排行榜 + 特征重要性图 + 相关性热力图"""

from typing import Any, Dict, List, Optional

import pandas as pd
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QSplitter, QWidget, QHeaderView,
    QApplication, QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from analysis.ai.root_cause import RootCauseAnalyzer, RootCause
from ui.theme import colors as theme_colors


class RootCauseDialog(QDialog):
    """对 SPC 违规点做三路证据融合根因排序"""

    def __init__(self, df: pd.DataFrame, target_column: str,
                 violations: Optional[List[Dict]] = None,
                 subgroup_size: int = 1, chart_type: str = "",
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"AI 根因分析 — {target_column}")
        self.setMinimumSize(960, 600)
        self.resize(1060, 660)

        self.df = df
        self.target_column = target_column
        self.violations = violations or []
        self.subgroup_size = subgroup_size
        self.chart_type = chart_type

        self._setup_ui()
        self._run_analysis()

    # ────────────────────────── UI ──────────────────────────
    def _setup_ui(self):
        tc = theme_colors()
        self.setStyleSheet(f"background-color: {tc['bg_body']}; color: {tc['text_primary']};")
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel(f"AI 根因分析 — {self.target_column}")
        title.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        title.setStyleSheet(f"color: {tc['text_primary']};")
        header.addWidget(title)
        header.addStretch()
        self.info_label = QLabel("")
        self.info_label.setFont(QFont("Microsoft YaHei", 10))
        self.info_label.setStyleSheet(f"color: {tc['text_secondary']};")
        header.addWidget(self.info_label)
        layout.addLayout(header)

        splitter = QSplitter(Qt.Horizontal)

        # 左: 根因排行榜
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        rank_label = QLabel("根因排行榜（综合得分 = 0.4×重要性 + 0.3×相关性 + 0.3×异常联动）")
        rank_label.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        rank_label.setStyleSheet(f"color: {tc['text_secondary']};")
        left_layout.addWidget(rank_label)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["#", "候选根因", "综合得分", "重要性", "相关性", "异常联动", "分析说明"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setStyleSheet(
            f"QTableWidget {{ background: {tc['bg_card']}; color: {tc['text_primary']}; "
            f"gridline-color: {tc['border_light']}; border: 1px solid {tc['border_light']}; "
            f"border-radius: 6px; }}"
            f"QHeaderView::section {{ background: {tc['bg_table_header']}; "
            f"color: {tc['text_primary']}; font-weight: bold; padding: 6px; "
            f"border: none; }}"
            f"QTableWidget::item:selected {{ background: {tc['bg_active']}; }}"
        )
        left_layout.addWidget(self.table)
        splitter.addWidget(left)

        # 右: 图表区
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self.fig = Figure(figsize=(5.6, 6.4), dpi=96)
        self.canvas = FigureCanvasQTAgg(self.fig)
        right_layout.addWidget(self.canvas)
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 4)
        layout.addWidget(splitter, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.setFont(QFont("Microsoft YaHei", 11))
        close_btn.setMinimumSize(90, 34)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(
            f"QPushButton {{ background: {tc['accent']}; color: white; border: none; "
            f"border-radius: 6px; }}"
            f"QPushButton:hover {{ background: {tc['accent_dark']}; }}"
        )
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    # ────────────────────── 分析与渲染 ──────────────────────
    def _run_analysis(self):
        tc = theme_colors()
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            analyzer = RootCauseAnalyzer(use_shap=True)
            result = analyzer.analyze(
                self.df, self.target_column,
                self.violations, self.subgroup_size, top_k=8,
            )
        finally:
            QApplication.restoreOverrideCursor()

        if result.get("error"):
            QMessageBox.information(self, "根因分析", result["error"])
            self.close()
            return

        method_label = "SHAP + RandomForest" if result.get("method") == "shap" else "RandomForest"
        self.info_label.setText(
            f"{self.chart_type} | 异常点 {len(self.violations)} 个"
            f"（联动行 {result.get('n_violation_rows', 0)}） | 算法: {method_label}"
        )

        causes: List[RootCause] = result["causes"]
        self._fill_table(causes)
        self._render_charts(causes)

    def _fill_table(self, causes: List[RootCause]):
        tc = theme_colors()
        self.table.setRowCount(len(causes))
        for i, c in enumerate(causes):
            items = [
                QTableWidgetItem(str(i + 1)),
                QTableWidgetItem(c.column),
                QTableWidgetItem(f"{c.score:.3f}"),
                QTableWidgetItem(f"{c.importance:.3f}"),
                QTableWidgetItem(f"{c.correlation:.3f}"),
                QTableWidgetItem(str(c.anomaly_linkage)),
                QTableWidgetItem(c.explanation),
            ]
            for j, item in enumerate(items):
                if j in (0, 2, 3, 4, 5):
                    item.setTextAlignment(Qt.AlignCenter)
                if i == 0 and j in (1, 2):
                    item.setForeground(QColor(tc["accent_bright"]))
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                self.table.setItem(i, j, item)

    def _render_charts(self, causes: List[RootCause]):
        tc = theme_colors()
        plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
        plt.rcParams["axes.unicode_minus"] = False

        self.fig.clear()
        self.fig.set_facecolor(tc["bg_card"])

        # ── 上图: 综合得分横向条形图 ──
        ax1 = self.fig.add_subplot(2, 1, 1)
        top = list(reversed(causes[:8]))
        names = [c.column for c in top]
        scores = [c.score for c in top]
        bar_colors = [tc["accent_bright"] if c is top[-1] else tc["accent"] for c in top]
        ax1.barh(names, scores, color=bar_colors, height=0.62)
        for i, s in enumerate(scores):
            ax1.text(s + 0.01, i, f"{s:.3f}", va="center",
                     color=tc["text_primary"], fontsize=9)
        ax1.set_xlim(0, max(scores + [1.0]) * 1.15)
        ax1.set_title("综合得分排行", color=tc["text_primary"], fontsize=11, pad=8)
        self._style_axis(ax1, tc)

        # ── 下图: 相关性热力图 (目标 + Top6) ──
        ax2 = self.fig.add_subplot(2, 1, 2)
        cols = [self.target_column] + [c.column for c in causes[:6]]
        numeric = self.df[cols].apply(pd.to_numeric, errors="coerce")
        corr = numeric.corr().fillna(0.0)

        im = ax2.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
        ax2.set_xticks(range(len(cols)))
        ax2.set_yticks(range(len(cols)))
        ax2.set_xticklabels(cols, rotation=30, ha="right", color=tc["text_primary"], fontsize=9)
        ax2.set_yticklabels(cols, color=tc["text_primary"], fontsize=9)
        for i in range(len(cols)):
            for j in range(len(cols)):
                v = corr.values[i, j]
                ax2.text(j, i, f"{v:.2f}", ha="center", va="center",
                         fontsize=8, color="#ffffff" if abs(v) > 0.5 else tc["text_secondary"])
        ax2.set_title("相关性矩阵 (Pearson)", color=tc["text_primary"], fontsize=11, pad=8)
        ax2.set_facecolor(tc["bg_card"])
        for spine in ax2.spines.values():
            spine.set_color(tc["border"])

        cbar = self.fig.colorbar(im, ax=ax2, fraction=0.04, pad=0.02)
        cbar.ax.yaxis.set_tick_params(color=tc["text_secondary"])
        cbar.outline.set_edgecolor(tc["border"])
        plt.setp(plt.getp(cbar.ax.axes, "yticklabels"), color=tc["text_secondary"])

        self.fig.tight_layout(pad=2.0)
        self.canvas.draw()

    @staticmethod
    def _style_axis(ax, tc):
        ax.set_facecolor(tc["bg_card"])
        ax.tick_params(colors=tc["text_primary"], labelsize=9)
        for spine in ax.spines.values():
            spine.set_color(tc["border"])
        ax.xaxis.label.set_color(tc["text_primary"])
