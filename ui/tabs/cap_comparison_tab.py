"""工序能力对比图 — 多工序/多特性 Cp/Cpk 并排柱状图 + 规格限"""

import numpy as np
import pandas as pd
from typing import Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QFormLayout, QDoubleSpinBox,
    QTableWidget, QTableWidgetItem, QSplitter, QScrollArea, QFrame, QListWidget, QAbstractItemView,
    QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from config.settings import CAPABILITY_GRADES
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from ui.tabs.base_tab import BaseAnalysisTab
from ui.theme import BUTTON_PRIMARY_STRETCH, BUTTON_SECONDARY
from ui.theme import colors as theme_colors
from analysis.capability import normal_cap
from core.formatting import format_cp


class CapComparisonTab(BaseAnalysisTab):

    def __init__(self, parent=None):
        self._specs: Dict[str, dict] = {}  # {col: {usl, lsl, target}}
        super().__init__(parent)
        self._setup_ui()

    def set_data(self, df: pd.DataFrame, parsed_info: Dict[str, Any] = None):
        BaseAnalysisTab.set_data(self, df, parsed_info)
        if df is not None:
            self._populate_col_list()

    def _setup_ui(self):
        tc = theme_colors()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self.title_label = QLabel("工序能力对比图")
        self.title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        layout.addWidget(self.title_label)
        layout.addSpacing(4)

        splitter = QSplitter(Qt.Horizontal)

        # ── 左侧配置 ──
        left = QWidget()
        left.setMaximumWidth(340)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 4, 0)

        # 列选择 (多选)
        col_group = QGroupBox("选择工序/特性列")
        col_layout = QVBoxLayout(col_group)
        self.col_list = QListWidget()
        self.col_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.col_list.setAlternatingRowColors(True)
        self.col_list.setMinimumHeight(100)
        col_layout.addWidget(self.col_list)
        left_layout.addWidget(col_group)

        # 规格限
        spec_group = QGroupBox("规格限设置")
        spec_layout = QFormLayout(spec_group)
        self.usl_spin = QDoubleSpinBox()
        self.usl_spin.setRange(-9999, 9999)
        self.usl_spin.setValue(0)
        self.usl_spin.setPrefix("USL: ")
        spec_layout.addRow("上限:", self.usl_spin)

        self.lsl_spin = QDoubleSpinBox()
        self.lsl_spin.setRange(-9999, 9999)
        self.lsl_spin.setValue(0)
        self.lsl_spin.setPrefix("LSL: ")
        spec_layout.addRow("下限:", self.lsl_spin)

        spec_btns = QHBoxLayout()
        self.btn_apply_spec = QPushButton("应用至选中列")
        self.btn_apply_spec.setStyleSheet(BUTTON_SECONDARY)
        self.btn_apply_spec.setCursor(Qt.PointingHandCursor)
        self.btn_apply_spec.clicked.connect(self._apply_spec)
        spec_btns.addWidget(self.btn_apply_spec)

        self.btn_clear_specs = QPushButton("清除规格限")
        self.btn_clear_specs.setStyleSheet(BUTTON_SECONDARY)
        self.btn_clear_specs.setCursor(Qt.PointingHandCursor)
        self.btn_clear_specs.clicked.connect(self._clear_specs)
        spec_btns.addWidget(self.btn_clear_specs)
        spec_layout.addRow(spec_btns)
        left_layout.addWidget(spec_group)

        # 运行按钮
        self.btn_run = QPushButton("对比分析")
        self.btn_run.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.btn_run.setCursor(Qt.PointingHandCursor)
        self.btn_run.setMinimumHeight(44)
        self.btn_run.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        self.btn_run.clicked.connect(self._run)
        left_layout.addWidget(self.btn_run)

        # 结果表
        self.result_table = QTableWidget()
        self.result_table.setAlternatingRowColors(True)
        self.result_table.horizontalHeader().setStretchLastSection(True)
        left_layout.addWidget(self.result_table)

        splitter.addWidget(left)

        # ── 右侧图表 ──
        chart_wrapper = QScrollArea()
        chart_wrapper.setWidgetResizable(True)
        chart_wrapper.setFrameShape(QFrame.NoFrame)
        self.chart_container = QWidget()
        self.chart_layout = QVBoxLayout(self.chart_container)
        self.chart_layout.setContentsMargins(0, 0, 0, 0)
        chart_wrapper.setWidget(self.chart_container)
        splitter.addWidget(chart_wrapper)

        splitter.setSizes([340, 700])
        layout.addWidget(splitter, 1)

    def _populate_col_list(self):
        if self.df is None:
            return
        self.col_list.clear()
        for c in self.df.columns:
            try:
                s = pd.to_numeric(self.df[c], errors="coerce").dropna()
                if len(s) > 0:
                    self.col_list.addItem(str(c))
            except Exception:
                pass

    def _apply_spec(self):
        usl = self.usl_spin.value()
        lsl = self.lsl_spin.value()
        if usl == 0 and lsl == 0:
            return
        for item in self.col_list.selectedItems():
            col = item.text()
            self._specs[col] = {"usl": usl if usl != 0 else None,
                                "lsl": lsl if lsl != 0 else None}

    def _clear_specs(self):
        self._specs.clear()
        self.usl_spin.setValue(0)
        self.lsl_spin.setValue(0)

    def _run(self):
        if self.df is None or self.df.empty:
            QMessageBox.information(self, "提示", "请先导入数据文件")
            return
        selected = [i.text() for i in self.col_list.selectedItems()]
        if not selected:
            selected = [self.col_list.item(i).text()
                        for i in range(min(8, self.col_list.count()))]

        results = []
        for col in selected:
            series = pd.to_numeric(self.df[col], errors="coerce").dropna()
            if len(series) < 5:
                continue
            spec = self._specs.get(col, {})
            usl = spec.get("usl")
            lsl = spec.get("lsl")
            r = normal_cap.analyze(series, usl=usl, lsl=lsl)
            cap = r.get("capability", {})
            results.append({
                "column": col,
                "n": len(series),
                "mean": r.get("summary", {}).get("mean", series.mean()),
                "std": r.get("summary", {}).get("std_overall", series.std()),
                "cp": cap.get("cp"),
                "cpk": cap.get("cpk"),
                "pp": cap.get("pp"),
                "ppk": cap.get("ppk"),
                "ppm": cap.get("ppm_total"),
                "grade": cap.get("grade", ""),
                "usl": usl,
                "lsl": lsl,
            })

        if not results:
            return

        self._fill_table(results)
        self._draw_chart(results)
        self.analysis_completed.emit()

    def _fill_table(self, results: list):
        headers = ["工序", "N", "均值", "Std", "Cp", "Cpk", "Pp", "Ppk", "PPM", "等级"]
        self.result_table.setColumnCount(len(headers))
        self.result_table.setHorizontalHeaderLabels(headers)
        self.result_table.setRowCount(len(results))
        for i, r in enumerate(results):
            vals = [
                r["column"], str(r["n"]), f"{r['mean']:.3f}", f"{r['std']:.4f}",
                format_cp(r["cp"]) if r["cp"] is not None else "-",
                format_cp(r["cpk"]) if r["cpk"] is not None else "-",
                format_cp(r["pp"]) if r["pp"] is not None else "-",
                format_cp(r["ppk"]) if r["ppk"] is not None else "-",
                f"{r['ppm']:.0f}" if r["ppm"] is not None else "-",
                r["grade"],
            ]
            for j, v in enumerate(vals):
                self.result_table.setItem(i, j, QTableWidgetItem(v))
        self.result_table.resizeColumnsToContents()

    def _draw_chart(self, results: list):
        self._clear_canvas()
        tc = theme_colors()
        plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
        plt.rcParams["axes.unicode_minus"] = False

        n = len(results)
        fig = Figure(figsize=(max(9, n * 1.2), 5.5), dpi=100)
        fig.set_facecolor(tc["bg_card"])
        ax = fig.add_subplot(111)
        ax.set_facecolor(tc["bg_body"])

        labels = [r["column"][:12] for r in results]
        x = np.arange(n)
        w = 0.35

        cp_vals = [r["cp"] if r["cp"] is not None else 0 for r in results]
        cpk_vals = [r["cpk"] if r["cpk"] is not None else 0 for r in results]
        pp_vals = [r["pp"] if r["pp"] is not None else 0 for r in results]
        ppk_vals = [r["ppk"] if r["ppk"] is not None else 0 for r in results]

        bars1 = ax.bar(x - w/2, cp_vals, w * 0.45, label="Cp",
                       color=tc["accent_bright"], alpha=0.85)
        bars2 = ax.bar(x - w/2 + w * 0.45, cpk_vals, w * 0.45, label="Cpk",
                       color="#ff6b6b", alpha=0.85)
        bars3 = ax.bar(x + w/2, pp_vals, w * 0.45, label="Pp",
                       color=tc["accent"], alpha=0.6, hatch="//")
        bars4 = ax.bar(x + w/2 + w * 0.45, ppk_vals, w * 0.45, label="Ppk",
                       color="#ffa726", alpha=0.6, hatch="//")

        # 阈值线
        cpk_b = CAPABILITY_GRADES["B"][0]  # 1.00
        cpk_a = CAPABILITY_GRADES["A"][0]  # 1.33
        ax.axhline(y=cpk_b, color="#6e7080", linestyle="--", linewidth=1, alpha=0.6)
        ax.axhline(y=cpk_a, color="#a0a3ae", linestyle=":", linewidth=1, alpha=0.5)
        ax.text(n - 0.5, cpk_b, f"Cp={cpk_b}", fontsize=7, color="#6e7080", va="bottom")
        ax.text(n - 0.5, cpk_a, f"Cp={cpk_a}", fontsize=7, color="#a0a3ae", va="bottom")

        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=9, rotation=25, ha="right")
        ax.set_ylabel("能力指数", fontsize=10)
        ax.set_title("工序能力对比 (Cp/Cpk/Pp/Ppk)", fontsize=12, fontweight="bold")
        ax.legend(fontsize=8, ncol=4, loc="upper right")
        ax.grid(True, alpha=0.3, axis="y")

        fig.subplots_adjust(left=0.08, right=0.95, top=0.90, bottom=0.18)
        canvas = FigureCanvasQTAgg(fig)
        self.chart_layout.addWidget(canvas)
        self.canvas = canvas
        self.current_figure = fig
        self._add_chart_toolbar()
