"""可靠性分析 Tab — Weibull 寿命分析 + MTBF/MTTR"""

from typing import Dict, Any

import numpy as np
import pandas as pd

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QGroupBox, QFormLayout, QFrame,
    QTableWidget, QTableWidgetItem, QSplitter, QStackedWidget, QCheckBox, QGridLayout, QScrollArea,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from core.i18n import i18n
from ui.tabs.base_tab import BaseAnalysisTab
from ui.theme import BUTTON_PRIMARY_STRETCH, BUTTON_TOGGLE
from ui.theme import colors as theme_colors
from ui.font_config import get_ui_font
from analysis.reliability.weibull import WeibullAnalyzer
from analysis.reliability.mtbf import MTBFAnalyzer


class ReliabilityTab(BaseAnalysisTab):

    def __init__(self, parent=None):
        self._weibull = WeibullAnalyzer()
        self._mtbf = MTBFAnalyzer()
        self._mode = "weibull"  # "weibull" | "mtbf"
        self._kpi_labels: Dict[str, QLabel] = {}
        super().__init__(parent)
        self._setup_ui()

    def set_data(self, df: pd.DataFrame, parsed_info: Dict[str, Any] = None):
        """重写以填充列选择器"""
        BaseAnalysisTab.set_data(self, df, parsed_info)
        if df is not None:
            cols = list(df.columns)
            self._populate_columns(self.failure_col_combo, cols)
            self._populate_columns(self.censored_combo, cols, add_none=True)
            self._populate_columns(self.tbf_combo, cols)
            self._populate_columns(self.repair_combo, cols, add_none=True)
            self._populate_columns(self.mtbf_group_combo, cols, add_none=True)

    def _setup_ui(self):
        tc = theme_colors()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        # ── 标题 ──
        self.title_label = QLabel(i18n.tr("reliability.title"))
        self.title_label.setFont(QFont(get_ui_font(), 18, QFont.Bold))
        layout.addWidget(self.title_label)
        layout.addSpacing(4)

        # ── 模式切换 ──
        mode_layout = QHBoxLayout()
        self.btn_weibull = QPushButton(i18n.tr("reliability.weibull_mode"))
        self.btn_weibull.setCheckable(True)
        self.btn_weibull.setChecked(True)
        self.btn_weibull.setCursor(Qt.PointingHandCursor)
        self.btn_weibull.setStyleSheet(BUTTON_TOGGLE)
        self.btn_weibull.clicked.connect(lambda: self._switch_mode("weibull"))

        self.btn_mtbf = QPushButton(i18n.tr("reliability.mtbf_mode"))
        self.btn_mtbf.setCheckable(True)
        self.btn_mtbf.setCursor(Qt.PointingHandCursor)
        self.btn_mtbf.setStyleSheet(BUTTON_TOGGLE)
        self.btn_mtbf.clicked.connect(lambda: self._switch_mode("mtbf"))

        mode_layout.addWidget(self.btn_weibull)
        mode_layout.addWidget(self.btn_mtbf)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)

        # ── 主体分屏 ──
        splitter = QSplitter(Qt.Vertical)

        # ── 上半: 配置 + 结果表格 ──
        top = QWidget()
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(0, 0, 0, 0)

        # 配置面板
        self.config_stack = QStackedWidget()

        # Weibull 配置页
        weibull_config = QGroupBox("分析参数")
        w_config_layout = QFormLayout(weibull_config)

        self.failure_col_combo = QComboBox()
        self.failure_col_combo.setMinimumWidth(140)
        w_config_layout.addRow(i18n.tr("reliability.failure_times") + ":", self.failure_col_combo)

        self.censored_combo = QComboBox()
        self.censored_combo.addItem("(无删失)", None)
        w_config_layout.addRow(i18n.tr("reliability.censored") + ":", self.censored_combo)

        self.fit_method_combo = QComboBox()
        self.fit_method_combo.addItem(i18n.tr("reliability.mle"), "mle")
        self.fit_method_combo.addItem(i18n.tr("reliability.rank_regression"), "rank-regression")
        w_config_layout.addRow(i18n.tr("reliability.fit_method") + ":", self.fit_method_combo)

        self.three_param_check = QCheckBox(i18n.tr("reliability.three_param"))
        self.three_param_check.setToolTip("数据 ≥ 10 点时尝试 3P Weibull (AIC 自动择优)")
        w_config_layout.addRow(self.three_param_check)

        self.btn_analyze_w = QPushButton(i18n.tr("reliability.run_btn"))
        self.btn_analyze_w.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.btn_analyze_w.setCursor(Qt.PointingHandCursor)
        self.btn_analyze_w.setMinimumHeight(44)
        self.btn_analyze_w.setFont(QFont(get_ui_font(), 12, QFont.Bold))
        self.btn_analyze_w.clicked.connect(self._run_weibull)
        w_config_layout.addRow(self.btn_analyze_w)

        self.config_stack.addWidget(weibull_config)

        # MTBF 配置页
        mtbf_config = QGroupBox("分析参数")
        m_config_layout = QFormLayout(mtbf_config)

        self.tbf_combo = QComboBox()
        self.tbf_combo.setMinimumWidth(140)
        m_config_layout.addRow(i18n.tr("reliability.tbf") + ":", self.tbf_combo)

        self.repair_combo = QComboBox()
        self.repair_combo.addItem("(无)", None)
        m_config_layout.addRow(i18n.tr("reliability.repair_time") + ":", self.repair_combo)

        self.mtbf_group_combo = QComboBox()
        self.mtbf_group_combo.addItem("(不分组)", None)
        m_config_layout.addRow(i18n.tr("reliability.group") + ":", self.mtbf_group_combo)

        self.btn_analyze_m = QPushButton(i18n.tr("reliability.run_btn"))
        self.btn_analyze_m.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.btn_analyze_m.setCursor(Qt.PointingHandCursor)
        self.btn_analyze_m.setMinimumHeight(44)
        self.btn_analyze_m.setFont(QFont(get_ui_font(), 12, QFont.Bold))
        self.btn_analyze_m.clicked.connect(self._run_mtbf)
        m_config_layout.addRow(self.btn_analyze_m)

        self.config_stack.addWidget(mtbf_config)

        top_layout.addWidget(self.config_stack)

        # KPI 卡片区
        kpi_group = QGroupBox("关键指标")
        self.kpi_grid = QGridLayout(kpi_group)
        self.kpi_grid.setSpacing(8)
        for idx, key in enumerate(("beta", "eta", "b10", "b50")):
            card = QFrame()
            card.setStyleSheet(
                "QFrame { background: #262632; border: 1px solid #2a2a36; border-radius: 8px; }")
            card.setMinimumWidth(118)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 8, 12, 8)
            title_lbl = QLabel(key.upper())
            title_lbl.setFont(QFont(get_ui_font(), 9))
            title_lbl.setStyleSheet(f"color: {tc['text_muted']};")
            title_lbl.setAlignment(Qt.AlignCenter)
            card_layout.addWidget(title_lbl)
            val_lbl = QLabel("—")
            val_lbl.setFont(QFont(get_ui_font(), 16, QFont.Bold))
            val_lbl.setStyleSheet(f"color: {tc['accent_bright']};")
            val_lbl.setAlignment(Qt.AlignCenter)
            card_layout.addWidget(val_lbl)
            self._kpi_labels[key] = val_lbl
            self.kpi_grid.addWidget(card, idx // 2, idx % 2)

        top_layout.addWidget(kpi_group)

        # 参数结果表格
        self.result_table = QTableWidget()
        self.result_table.setAlternatingRowColors(True)
        self.result_table.horizontalHeader().setStretchLastSection(True)
        self.result_table.setMaximumHeight(200)

        top_layout.addWidget(self.result_table)
        splitter.addWidget(top)

        # ── 下半: 图表 ──
        chart_wrapper = QScrollArea()
        chart_wrapper.setWidgetResizable(True)
        chart_wrapper.setFrameShape(QFrame.NoFrame)
        self.chart_container = QWidget()
        self.chart_layout = QVBoxLayout(self.chart_container)
        self.chart_layout.setContentsMargins(0, 0, 0, 0)
        chart_wrapper.setWidget(self.chart_container)
        splitter.addWidget(chart_wrapper)

        layout.addWidget(splitter, 1)

    def _switch_mode(self, mode: str):
        self._mode = mode
        self.btn_weibull.setChecked(mode == "weibull")
        self.btn_mtbf.setChecked(mode == "mtbf")
        self.config_stack.setCurrentIndex(0 if mode == "weibull" else 1)
        self._clear_canvas()
        self.result_table.clear()
        self.result_table.setRowCount(0)
        for lbl in self._kpi_labels.values():
            lbl.setText("—")

    @staticmethod
    def _populate_columns(combo: QComboBox, cols: list, add_none: bool = False):
        current = combo.currentText()
        combo.blockSignals(True)
        combo.clear()
        if add_none:
            combo.addItem("(无)", None)
        for c in cols:
            combo.addItem(str(c), c)
        idx = combo.findText(current)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        combo.blockSignals(False)

    # ──────────────────────────────────────────────
    # Weibull 分析
    # ──────────────────────────────────────────────
    def _run_weibull(self):
        if self.df is None or self.df.empty:
            return
        col = self.failure_col_combo.currentData()
        if col is None:
            return
        times = pd.to_numeric(self.df[col], errors="coerce").dropna().tolist()

        # 删失列
        cen_col = self.censored_combo.currentData()
        censored = None
        if cen_col is not None and cen_col in self.df.columns:
            censored = pd.to_numeric(self.df[cen_col], errors="coerce").clip(0, 1).fillna(1).astype(int).tolist()

        fit_method = self.fit_method_combo.currentData()
        three_p = self.three_param_check.isChecked()

        result = self._weibull.analyze(
            times, censored=censored,
            fit_method=fit_method,
            three_parameter=three_p,
        )
        if result["error"]:
            self.result_table.setColumnCount(1)
            self.result_table.setHorizontalHeaderLabels(["错误"])
            self.result_table.setRowCount(1)
            self.result_table.setItem(0, 0, QTableWidgetItem(result["error"]))
            return

        r = result["result"]
        # W66: 3P Weibull 拟合可能产生 NaN 参数，提前检测
        import math
        if any(math.isnan(v) for v in (r.beta, r.eta) if isinstance(v, float)):
            self.result_table.setColumnCount(1)
            self.result_table.setHorizontalHeaderLabels(["错误"])
            self.result_table.setRowCount(1)
            self.result_table.setItem(0, 0, QTableWidgetItem("拟合失败：参数为 NaN，请尝试其他拟合方法或检查数据"))
            return
        # 更新 KPI
        self._kpi_labels["beta"].setText(f"β = {r.beta:.4f}")
        self._kpi_labels["eta"].setText(f"η = {r.eta:.1f}")
        self._kpi_labels["b10"].setText(f"B10 = {r.b10_life:.1f}")
        self._kpi_labels["b50"].setText(f"B50 = {r.b50_life:.1f}")

        # 参数表格
        params = [
            ("形状参数 β", f"{r.beta:.4f}"),
            ("尺度参数 η", f"{r.eta:.2f}"),
            ("位置参数 γ", f"{r.gamma:.4f}"),
            ("拟合方法", r.method),
            ("B10 寿命", f"{r.b10_life:.2f}"),
            ("B50 寿命 (中位)", f"{r.b50_life:.2f}"),
            ("特征寿命", f"{r.characteristic_life:.2f}"),
            ("期望寿命", f"{r.mean_life:.2f}" if r.mean_life < float('inf') else "∞"),
            ("AD 统计量", f"{r.ad_statistic:.4f}"),
            ("概率图 R²", f"{r.r_squared:.4f}"),
            ("对数似然", f"{r.loglik:.2f}"),
            ("AIC", f"{r.aic:.2f}"),
        ]
        self.result_table.setColumnCount(2)
        self.result_table.setHorizontalHeaderLabels(["参数", "值"])
        self.result_table.setRowCount(len(params))
        for i, (k, v) in enumerate(params):
            self.result_table.setItem(i, 0, QTableWidgetItem(k))
            self.result_table.setItem(i, 1, QTableWidgetItem(v))
        self.result_table.resizeColumnsToContents()

        self._draw_weibull_charts(r)
        # v2.4: 补齐 current_result (此前只发信号, 结果进不了 MainWindow.analyses)
        self.current_result = {
            "analysis_type": "Weibull 寿命分析",
            "params": {},
            "result": {
                "beta": r.beta, "eta": r.eta, "b10_life": r.b10_life,
                "characteristic_life": r.characteristic_life,
                "mean_life": r.mean_life if r.mean_life < float("inf") else None,
            },
        }
        self.analysis_completed.emit()

    def _draw_weibull_charts(self, r):
        self._clear_canvas()
        tc = theme_colors()
        # plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]  # redundant, handled by chart_engine.setup_chinese_font()
        plt.rcParams["axes.unicode_minus"] = False

        fig = Figure(figsize=(11, 5.5), dpi=100)
        fig.set_facecolor(tc["bg_card"])
        fig.subplots_adjust(left=0.07, right=0.97, top=0.92, bottom=0.10, wspace=0.30)

        # ── 左: 概率图 ──
        ax1 = fig.add_subplot(1, 2, 1)
        pd_data = r.probability_data
        if pd_data["time"]:
            ax1.plot(pd_data["time"], pd_data["prob"], "o",
                     color=tc["accent_bright"], markersize=5, alpha=0.8,
                     label="观测数据")

            # 理论线
            t_range = np.linspace(min(pd_data["time"]) * 0.5,
                                  max(pd_data["time"]) * 1.2, 100)
            z = (t_range - r.gamma) / r.eta
            F_theory = 100 * (1 - np.exp(-(z ** r.beta)))
            ax1.plot(t_range, F_theory, "-", color="#ff6b6b", linewidth=1.5,
                     label=f"拟合 (β={r.beta:.2f}, η={r.eta:.0f})")

        ax1.set_xlabel("失效时间", fontsize=9)
        ax1.set_ylabel("累积失效概率 (%)", fontsize=9)
        ax1.set_title(i18n.tr("reliability.prob_plot"), fontsize=11, fontweight="bold")
        ax1.legend(fontsize=7)
        ax1.grid(True, alpha=0.3)
        ax1.set_facecolor(tc["bg_body"])

        # ── 右: R(t) + h(t) ──
        ax2 = fig.add_subplot(1, 2, 2)
        rc = r.reliability_curve
        ax2.plot(rc["t"], rc["R"], "-", color=tc["accent_bright"],
                 linewidth=2, label="R(t)")
        ax2.set_xlabel("时间", fontsize=9)
        ax2.set_ylabel("可靠性 R(t)", fontsize=9, color=tc["accent_bright"])
        ax2.tick_params(axis="y", labelcolor=tc["accent_bright"])

        ax2b = ax2.twinx()
        ax2b.plot(rc["t"], rc["h"], "--", color="#ff6b6b", linewidth=1.5,
                  label="h(t)")
        ax2b.set_ylabel("失效率 h(t)", fontsize=9, color="#ff6b6b")
        ax2b.tick_params(axis="y", labelcolor="#ff6b6b")

        ax2.set_title(i18n.tr("reliability.reliability_func") + " & "
                      + i18n.tr("reliability.hazard_func"),
                      fontsize=11, fontweight="bold")
        ax2.grid(True, alpha=0.3)
        ax2.set_facecolor(tc["bg_body"])

        canvas = FigureCanvasQTAgg(fig)
        self.chart_layout.addWidget(canvas)
        self.canvas = canvas
        self.current_figure = fig
        self._add_chart_toolbar()

    # ──────────────────────────────────────────────
    # MTBF 分析
    # ──────────────────────────────────────────────
    def _run_mtbf(self):
        if self.df is None or self.df.empty:
            return
        tbf_col = self.tbf_combo.currentData()
        if tbf_col is None:
            return
        tbf = pd.to_numeric(self.df[tbf_col], errors="coerce").dropna().tolist()

        # 修复时间列
        rt_col = self.repair_combo.currentData()
        rt = None
        if rt_col is not None and rt_col in self.df.columns:
            rt = pd.to_numeric(self.df[rt_col], errors="coerce").fillna(0).tolist()

        # 分组列
        grp_col = self.mtbf_group_combo.currentData()
        groups = None
        if grp_col is not None and grp_col in self.df.columns:
            groups = self.df[grp_col].astype(str).tolist()

        result = self._mtbf.analyze(tbf, repair_times=rt, group_by=groups)
        if result["error"]:
            self.result_table.setColumnCount(1)
            self.result_table.setHorizontalHeaderLabels(["错误"])
            self.result_table.setRowCount(1)
            self.result_table.setItem(0, 0, QTableWidgetItem(result["error"]))
            return

        r = result["overall"]
        self._kpi_labels["beta"].setText(f"MTBF = {r.mtbf:.0f}h")
        self._kpi_labels["eta"].setText(f"MTTR = {r.mttr:.1f}h")
        self._kpi_labels["b10"].setText(f"A = {r.availability:.3f}")
        self._kpi_labels["b50"].setText(f"λ = {r.failure_rate:.4f}")

        # 结果表格
        trend_map = {
            "improving": i18n.tr("reliability.trend_improving"),
            "degrading": i18n.tr("reliability.trend_degrading"),
            "stable": i18n.tr("reliability.trend_stable"),
        }
        all_groups = [r] + result["groups"]
        headers = ["分组", "事件数", "MTBF(h)", "MTTR(h)", "可用度",
                   "故障率 λ", "趋势", "CI-下(h)", "CI-上(h)"]
        self.result_table.setColumnCount(len(headers))
        self.result_table.setHorizontalHeaderLabels(headers)
        self.result_table.setRowCount(len(all_groups))
        for i, g in enumerate(all_groups):
            vals = [
                g.label, str(g.n_failures),
                f"{g.mtbf:.1f}", f"{g.mttr:.1f}",
                f"{g.availability:.4f}", f"{g.failure_rate:.4f}",
                trend_map.get(g.trend, g.trend),
                f"{g.mtbf_ci_low:.1f}", f"{g.mtbf_ci_high:.1f}",
            ]
            for j, v in enumerate(vals):
                self.result_table.setItem(i, j, QTableWidgetItem(v))
        self.result_table.resizeColumnsToContents()

        self._draw_mtbf_chart(result)
        # v2.4: 补齐 current_result (此前只发信号, 结果进不了 MainWindow.analyses)
        from dataclasses import asdict
        self.current_result = {
            "analysis_type": "MTBF / MTTR",
            "params": {},
            "result": asdict(result["overall"]),
        }
        self.analysis_completed.emit()

    def _draw_mtbf_chart(self, result: Dict[str, Any]):
        self._clear_canvas()
        tc = theme_colors()
        # plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]  # redundant, handled by chart_engine.setup_chinese_font()
        plt.rcParams["axes.unicode_minus"] = False

        r = result["overall"]
        groups = result["groups"]

        if groups:
            fig = Figure(figsize=(11, 4.2), dpi=100)
            fig.set_facecolor(tc["bg_card"])
            fig.subplots_adjust(left=0.08, right=0.96, top=0.88, bottom=0.18, wspace=0.30)

            # ── 左: MTBF 分组柱状图 ──
            ax1 = fig.add_subplot(1, 2, 1)
            labels = [g.label for g in groups]
            mtbf_vals = [g.mtbf for g in groups]
            ci_low = [g.mtbf - g.mtbf_ci_low for g in groups]
            ci_high = [g.mtbf_ci_high - g.mtbf for g in groups]
            x = range(len(labels))
            bars = ax1.bar(x, mtbf_vals, color=tc["accent"], alpha=0.8)
            ax1.errorbar(x, mtbf_vals, yerr=[ci_low, ci_high],
                         fmt="none", ecolor="#ff6b6b", capsize=6, linewidth=1.5)
            ax1.set_xticks(x)
            ax1.set_xticklabels(labels, fontsize=8)
            ax1.set_ylabel("MTBF (小时)", fontsize=9)
            ax1.set_title("分组 MTBF (±90%CI)", fontsize=11, fontweight="bold")
            ax1.grid(True, alpha=0.3, axis="y")
            ax1.set_facecolor(tc["bg_body"])

            # ── 右: 可用度对比 ──
            ax2 = fig.add_subplot(1, 2, 2)
            avail_vals = [g.availability * 100 for g in groups]
            colors = [tc["accent_bright"] if v >= 99 else
                      "#ffa726" if v >= 95 else "#ff6b6b" for v in avail_vals]
            ax2.bar(x, avail_vals, color=colors, alpha=0.85)
            ax2.axhline(y=99, color="#888888", linestyle="--", linewidth=1, alpha=0.5)
            ax2.set_xticks(x)
            ax2.set_xticklabels(labels, fontsize=8)
            ax2.set_ylabel("可用度 (%)", fontsize=9)
            ax2.set_title("分组可用度对比", fontsize=11, fontweight="bold")
            ax2.grid(True, alpha=0.3, axis="y")
            ax2.set_facecolor(tc["bg_body"])
        else:
            fig = Figure(figsize=(7, 3.5), dpi=100)
            fig.set_facecolor(tc["bg_card"])
            ax = fig.add_axes([0.15, 0.25, 0.78, 0.65])
            ax.axis("off")
            summary = (
                f"MTBF = {r.mtbf:.1f} h\n"
                f"MTTR = {r.mttr:.1f} h\n"
                f"可用度 A = {r.availability:.3f}\n"
                f"故障率 λ = {r.failure_rate:.4f}\n"
                f"趋势: {r.trend}\n"
                f"{r.n_failures} 次失效事件"
            )
            ax.text(0.5, 0.5, summary, transform=ax.transAxes,
                    fontsize=14, ha="center", va="center", fontfamily="monospace",
                    bbox=dict(boxstyle="round", facecolor=tc["bg_body"],
                              edgecolor=tc["border"], alpha=0.9))

        canvas = FigureCanvasQTAgg(fig)
        self.chart_layout.addWidget(canvas)
        self.canvas = canvas
        self.current_figure = fig
        self._add_chart_toolbar()
