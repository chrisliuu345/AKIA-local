"""
回归分析页
"""

from typing import Dict, Any
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QGroupBox, QFormLayout, QTextEdit,
    QTableWidget, QHeaderView,
    QStackedWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from analysis.regression.linear_regression import analyze as reg_analyze
from core.i18n import i18n
from ui.tabs.base_tab import BaseAnalysisTab
from ui.theme import BUTTON_SECONDARY, BUTTON_TOGGLE, BUTTON_PRIMARY_STRETCH
from ui.font_config import get_ui_font
from core.formatting import format_pvalue


class RegressionTab(BaseAnalysisTab):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.df: pd.DataFrame = None
        self.parsed_info: Dict[str, Any] = {}
        self.current_result: Dict[str, Any] = {}
        self.current_figure = None
        self.canvas = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self.title_label = QLabel(i18n.tr("reg.title"))
        self.title_label.setFont(QFont(get_ui_font(), 18, QFont.Bold))
        layout.addWidget(self.title_label)

        top_layout = QHBoxLayout()

        config_group = QGroupBox(i18n.tr("reg.config"))
        config_layout = QFormLayout(config_group)

        self.response_combo = QComboBox()
        config_layout.addRow(i18n.tr("reg.response"), self.response_combo)

        self.sheet_combo = QComboBox()
        self.sheet_combo.setMinimumWidth(140)
        self.sheet_combo.currentTextChanged.connect(self._on_sheet_changed)
        config_layout.addRow("Sheet:", self.sheet_combo)

        self.factor1_combo = QComboBox()
        config_layout.addRow(i18n.tr("reg.factor1"), self.factor1_combo)
        self.factor2_combo = QComboBox()
        config_layout.addRow(i18n.tr("reg.factor2"), self.factor2_combo)
        self.factor3_combo = QComboBox()
        config_layout.addRow(i18n.tr("reg.factor3"), self.factor3_combo)

        self.run_btn = QPushButton(i18n.tr("reg.run_btn"))
        self.run_btn.setFont(QFont(get_ui_font(), 12, QFont.Bold))
        self.run_btn.setMinimumHeight(44)
        self.run_btn.setCursor(Qt.PointingHandCursor)
        self.run_btn.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.run_btn.clicked.connect(self.run_and_display)
        config_layout.addRow(self.run_btn)

        self.save_png_btn = QPushButton(i18n.tr("reg.save_png"))
        self.save_png_btn.setFont(QFont(get_ui_font(), 12, QFont.Bold))
        self.save_png_btn.setMinimumHeight(40)
        self.save_png_btn.setCursor(Qt.PointingHandCursor)
        self.save_png_btn.setStyleSheet(BUTTON_SECONDARY)
        self.save_png_btn.clicked.connect(self._on_save_png)
        config_layout.addRow(self.save_png_btn)

        self.corr_btn = QPushButton(i18n.tr("reg.correlation"))
        self.corr_btn.setFont(QFont(get_ui_font(), 12, QFont.Bold))
        self.corr_btn.setMinimumHeight(40)
        self.corr_btn.setCursor(Qt.PointingHandCursor)
        self.corr_btn.setStyleSheet(BUTTON_SECONDARY)
        self.corr_btn.clicked.connect(self._on_show_correlation)
        config_layout.addRow(self.corr_btn)

        self.export_btn = QPushButton(i18n.tr("reg.export_btn"))
        self.export_btn.setFont(QFont(get_ui_font(), 12, QFont.Bold))
        self.export_btn.setMinimumHeight(44)
        self.export_btn.setCursor(Qt.PointingHandCursor)
        self.export_btn.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.export_btn.clicked.connect(self.export_clicked.emit)
        config_layout.addRow(self.export_btn)

        top_layout.addWidget(config_group)

        
        self.data_table = QTableWidget()
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.data_table.horizontalHeader().setStretchLastSection(True)
        self.data_table.horizontalHeader().setMinimumSectionSize(70)
        self.data_table.setAlternatingRowColors(True)
        self.data_table.horizontalHeader().sectionClicked.connect(self._on_header_clicked)
        self.data_table.setSelectionBehavior(QTableWidget.SelectColumns)
        top_layout.addWidget(self.data_table, 1)

        layout.addLayout(top_layout)

        bottom_layout = QVBoxLayout()
        self.result_label = QLabel(i18n.tr("reg.result"))
        self.result_label.setFont(QFont(get_ui_font(), 14, QFont.Bold))
        bottom_layout.addWidget(self.result_label)

        toggle_row = QHBoxLayout()
        toggle_row.setSpacing(8)
        self.btn_view_chart = QPushButton(i18n.tr("tab.view_chart"))
        self.btn_view_chart.setFont(QFont(get_ui_font(), 11))
        self.btn_view_chart.setFixedHeight(30)
        self.btn_view_chart.setCheckable(True)
        self.btn_view_chart.setChecked(True)
        self.btn_view_chart.setStyleSheet(BUTTON_TOGGLE)
        self.btn_view_chart.clicked.connect(lambda: self._switch_result_view(0))
        toggle_row.addWidget(self.btn_view_chart)
        self.btn_view_data = QPushButton(i18n.tr("tab.view_data"))
        self.btn_view_data.setFont(QFont(get_ui_font(), 11))
        self.btn_view_data.setFixedHeight(30)
        self.btn_view_data.setCheckable(True)
        self.btn_view_data.setStyleSheet(BUTTON_TOGGLE)
        self.btn_view_data.clicked.connect(lambda: self._switch_result_view(1))
        toggle_row.addWidget(self.btn_view_data)
        toggle_row.addStretch()
        bottom_layout.addLayout(toggle_row)

        self.result_stack = QStackedWidget()

        self.chart_container = QWidget()
        self.chart_layout = QVBoxLayout(self.chart_container)
        self.chart_layout.setContentsMargins(0, 0, 0, 0)
        self.chart_container.setMinimumHeight(300)
        self.result_stack.addWidget(self.chart_container)

        self.data_container = QWidget()
        data_layout = QVBoxLayout(self.data_container)
        data_layout.setContentsMargins(0, 0, 0, 0)
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setFont(QFont(get_ui_font(), 12))
        self.result_text.setMinimumHeight(80)
        data_layout.addWidget(self.result_text)
        self.result_table = QTableWidget()
        self.result_table.horizontalHeader().setStretchLastSection(True)
        self.result_table.setAlternatingRowColors(True)
        self.result_table.setShowGrid(True)
        self.result_table.setStyleSheet(
            "QTableWidget { font-size: 12px; }"
            "QHeaderView::section { font-weight: bold; padding: 4px; }"
        )
        data_layout.addWidget(self.result_table)
        self.result_stack.addWidget(self.data_container)

        bottom_layout.addWidget(self.result_stack)
        layout.addLayout(bottom_layout)

    def set_data(self, df: pd.DataFrame, parsed_info: Dict[str, Any] = None):
        self.df = df
        self.parsed_info = parsed_info or {}
        cols = list(df.columns)
        for combo in [self.response_combo, self.factor1_combo, self.factor2_combo, self.factor3_combo]:
            combo.clear()
            combo.addItems(cols)
        if cols:
            self.factor1_combo.setCurrentIndex(min(1, len(cols) - 1))
            if len(cols) > 2:
                self.factor2_combo.setCurrentIndex(2)
        self._update_preview()

    def _update_preview(self):
        if self.df is None:
            return
        self._populate_preview_table(self.df)

    def _on_header_clicked(self, index: int):
        item = self.data_table.horizontalHeaderItem(index)
        if item is None:
            return
        col_name = item.text()
        for combo in [self.response_combo, self.factor1_combo, self.factor2_combo, self.factor3_combo]:
            if combo.currentText() == col_name:
                combo.setCurrentIndex(-1)
                return
        for combo in [self.response_combo, self.factor1_combo, self.factor2_combo, self.factor3_combo]:
            if combo.currentText() == "":
                combo.setCurrentText(col_name)
                return
        self.response_combo.setCurrentText(col_name)
        self.data_table.selectColumn(index)

    def run_and_display(self) -> Dict[str, Any]:
        ok, msg = self.validate_params()
        if not ok:
            self._clear_canvas()
            self.result_text.setStyleSheet("color: #e74c3c; font-weight: bold;")
            self.result_text.setText(f"{i18n.tr('reg.val_param_failed')}\n{msg}")
            return None
        try:
            result = self.run_analysis()
            self.display_result(result)
            self.analysis_completed.emit()
            return result
        except Exception as e:
            self._clear_canvas()
            self.result_text.setStyleSheet("color: #e74c3c; font-weight: bold;")
            self.result_text.setText(f"{i18n.tr('reg.val_analysis_failed')}\n{str(e)}")

    def validate_params(self) -> tuple:
        if self.df is None:
            return False, i18n.tr("val.no_data")
        if not self.response_combo.currentText():
            return False, i18n.tr("reg.val_no_response")
        return True, ""

    def run_analysis(self) -> Dict[str, Any]:
        response = self.response_combo.currentText()
        factors = []
        for combo in [self.factor1_combo, self.factor2_combo, self.factor3_combo]:
            txt = combo.currentText()
            if txt and txt != response:
                factors.append(txt)
        result = reg_analyze(self.df, response, factors)
        self.current_result = {
            "analysis_type": f"Regression: {response}",
            "params": {"response": response, "factors": factors},
            "result": result,
            "chart_data": result,
        }
        return self.current_result

    def display_result(self, analysis: Dict[str, Any] = None):
        if analysis is None:
            analysis = self.current_result
        result = analysis.get("result", {})
        self._render_chart(result)
        text_lines = []
        text_lines.append(f"{i18n.tr('reg.title')} {i18n.tr('reg.result')}")
        text_lines.append(f"{i18n.tr('reg.response')} {result.get('response', '')}")
        text_lines.append(f"因子: {', '.join(result.get('factors', []))}")
        text_lines.append(f"{i18n.tr('report.sample_size')}: {result.get('n', 0)}")
        text_lines.append(f"R² = {result.get('r_squared', '')}")
        text_lines.append(f"R²(adj) = {result.get('r_squared_adjusted', '')}")
        text_lines.append(f"残差标准差: {result.get('residual_std', '')}")
        text_lines.append("")
        text_lines.append(f"{i18n.tr('report.regression_coeffs')}:")
        text_lines.append(f"{'项':20s} {'估计值':>12s} {'标准误':>10s} {'t值':>10s} {'p值':>10s}")
        text_lines.append("-" * 64)
        for coef in result.get("coefficients", []):
            pv = coef.get('p_value', '')
            pv_str = format_pvalue(pv) if isinstance(pv, (int, float)) else str(pv)
            text_lines.append(
                f"{coef['term']:20s} {coef['estimate']:>12.4f} {coef['std_error']:>10.4f} "
                f"{str(coef.get('t_value', '')):>10s} {pv_str:>10s}"
            )
        text_lines.append("")
        anova = result.get("anova", {})
        fpv = anova.get('f_p_value', '')
        fpv_str = format_pvalue(fpv) if isinstance(fpv, (int, float)) else str(fpv)
        text_lines.append(f"ANOVA: F={anova.get('f_statistic', '')}, p={fpv_str}")
        self.result_text.setStyleSheet("")
        self.result_text.setText("\n".join(text_lines))
        self.result_text.update()
        self._switch_result_view(0)

    def _render_chart(self, result: Dict):
        self._clear_canvas()
        try:
            import matplotlib.pyplot as plt
            from config.settings import CHART_DPI
            fitted = result.get("fitted_values", [])
            residuals = result.get("residuals", [])
            actual = result.get("actual_values", [])
            fig, axes = plt.subplots(2, 1, figsize=(10, 8), dpi=CHART_DPI)
            axes[0].scatter(fitted, residuals, alpha=0.6, edgecolors="k", linewidth=0.3, color="#1b5faa")
            axes[0].axhline(y=0, color="red", linestyle="--", linewidth=1)
            axes[0].set_xlabel("拟合值", fontsize=10)
            axes[0].set_ylabel("残差", fontsize=10)
            axes[0].set_title("残差 vs 拟合值", fontsize=12, fontweight="bold")
            axes[0].grid(True, alpha=0.3)
            if len(residuals) > 3:
                from scipy import stats as scs
                scs.probplot(residuals, dist="norm", plot=axes[1])
                axes[1].set_title("残差 Q-Q 图", fontsize=12, fontweight="bold")
                axes[1].grid(True, alpha=0.3)
            self.current_figure = fig
            self.canvas = FigureCanvasQTAgg(fig)
            self.chart_layout.addWidget(self.canvas)
            self.canvas.draw()
            self._add_chart_toolbar()
        except Exception as e:
            err_label = QLabel(f"{i18n.tr('reg.chart_failed')}{e}")
            err_label.setStyleSheet("color: #e74c3c; padding: 12px;")
            err_label.setWordWrap(True)
            self.chart_layout.addWidget(err_label)

    def refresh_texts(self):
        self.title_label.setText(i18n.tr("reg.title"))
        self.run_btn.setText(i18n.tr("reg.run_btn"))
        self.result_label.setText(i18n.tr("reg.result"))





    def _on_show_correlation(self):
        if self.df is None:
            return
        self._clear_canvas()
        try:
            from output.chart_engine import create_correlation_heatmap
            fig = create_correlation_heatmap(self.df)
            self.current_figure = fig
            self.canvas = FigureCanvasQTAgg(fig)
            self.chart_layout.addWidget(self.canvas)
            self.canvas.draw()
            self._add_chart_toolbar()
        except Exception as e:
            err_label = QLabel(f"{i18n.tr('reg.chart_failed')}{e}")
            err_label.setStyleSheet("color: #e74c3c; padding: 12px;")
            err_label.setWordWrap(True)
            self.chart_layout.addWidget(err_label)
