"""
时间序列分析页 — ACF/PACF / 季节分解 / 指数平滑 / ARIMA / 模型对比
"""

from typing import Dict, Any
import pandas as pd

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QGroupBox, QFormLayout, QTextEdit,
    QTableWidget, QHeaderView, QSpinBox,
    QStackedWidget, QRadioButton, QButtonGroup,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ui.tabs.base_tab import BaseAnalysisTab
from ui.theme import BUTTON_SECONDARY, BUTTON_TOGGLE, BUTTON_PRIMARY_STRETCH
from ui.font_config import get_ui_font


class TimeSeriesTab(BaseAnalysisTab):

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

        self.title_label = QLabel("时间序列分析")
        self.title_label.setFont(QFont(get_ui_font(), 18, QFont.Bold))
        layout.addWidget(self.title_label)

        top_layout = QHBoxLayout()

        config_group = QGroupBox("分析配置")
        config_layout = QFormLayout(config_group)

        self.sheet_combo = QComboBox()
        self.sheet_combo.setMinimumWidth(140)
        self.sheet_combo.currentTextChanged.connect(self._on_sheet_changed)
        config_layout.addRow("Sheet:", self.sheet_combo)

        self.time_col_combo = QComboBox()
        config_layout.addRow("时间列:", self.time_col_combo)

        self.value_col_combo = QComboBox()
        config_layout.addRow("数值列:", self.value_col_combo)

        method_group = QGroupBox("分析方法")
        method_layout = QVBoxLayout(method_group)
        self.method_btn_group = QButtonGroup()
        self.method_btns = {}
        methods = [
            ("acf_pacf", "ACF/PACF 分析"),
            ("decomposition", "季节性分解"),
            ("exp_smoothing", "指数平滑"),
            ("arima", "ARIMA 建模"),
            ("compare", "模型对比"),
        ]
        for key, label in methods:
            btn = QRadioButton(label)
            btn.setFont(QFont(get_ui_font(), 11))
            self.method_btn_group.addButton(btn)
            self.method_btns[key] = btn
            method_layout.addWidget(btn)
        self.method_btns["acf_pacf"].setChecked(True)
        config_layout.addRow(method_group)

        params_group = QGroupBox("参数")
        params_layout = QFormLayout(params_group)

        self.forecast_steps_spin = QSpinBox()
        self.forecast_steps_spin.setRange(1, 365)
        self.forecast_steps_spin.setValue(12)
        params_layout.addRow("预测步数:", self.forecast_steps_spin)

        self.seasonal_period_spin = QSpinBox()
        self.seasonal_period_spin.setRange(2, 365)
        self.seasonal_period_spin.setValue(12)
        self.seasonal_period_spin.setSpecialValueText("自动")
        params_layout.addRow("季节周期:", self.seasonal_period_spin)

        self.seasonal_type_combo = QComboBox()
        self.seasonal_type_combo.addItems(["加法 (additive)", "乘法 (multiplicative)"])
        params_layout.addRow("季节类型:", self.seasonal_type_combo)

        self.arima_p_spin = QSpinBox()
        self.arima_p_spin.setRange(0, 5)
        self.arima_p_spin.setValue(1)
        params_layout.addRow("ARIMA p:", self.arima_p_spin)

        self.arima_d_spin = QSpinBox()
        self.arima_d_spin.setRange(0, 2)
        self.arima_d_spin.setValue(1)
        params_layout.addRow("ARIMA d:", self.arima_d_spin)

        self.arima_q_spin = QSpinBox()
        self.arima_q_spin.setRange(0, 5)
        self.arima_q_spin.setValue(1)
        params_layout.addRow("ARIMA q:", self.arima_q_spin)

        config_layout.addRow(params_group)

        self.run_btn = QPushButton("▶ 运行分析")
        self.run_btn.setFont(QFont(get_ui_font(), 12, QFont.Bold))
        self.run_btn.setMinimumHeight(44)
        self.run_btn.setCursor(Qt.PointingHandCursor)
        self.run_btn.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.run_btn.clicked.connect(self.run_and_display)
        config_layout.addRow(self.run_btn)

        self.save_png_btn = QPushButton("保存 PNG")
        self.save_png_btn.setFont(QFont(get_ui_font(), 12, QFont.Bold))
        self.save_png_btn.setMinimumHeight(40)
        self.save_png_btn.setCursor(Qt.PointingHandCursor)
        self.save_png_btn.setStyleSheet(BUTTON_SECONDARY)
        self.save_png_btn.clicked.connect(self._on_save_png)
        config_layout.addRow(self.save_png_btn)

        self.export_btn = QPushButton("导出报告")
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
        top_layout.addWidget(self.data_table, 1)

        layout.addLayout(top_layout)

        bottom_layout = QVBoxLayout()
        self.result_label = QLabel("分析结果")
        self.result_label.setFont(QFont(get_ui_font(), 14, QFont.Bold))
        bottom_layout.addWidget(self.result_label)

        toggle_row = QHBoxLayout()
        toggle_row.setSpacing(8)
        self.btn_view_chart = QPushButton("图表")
        self.btn_view_chart.setFont(QFont(get_ui_font(), 11))
        self.btn_view_chart.setFixedHeight(30)
        self.btn_view_chart.setCheckable(True)
        self.btn_view_chart.setChecked(True)
        self.btn_view_chart.setStyleSheet(BUTTON_TOGGLE)
        self.btn_view_chart.clicked.connect(lambda: self._switch_result_view(0))
        toggle_row.addWidget(self.btn_view_chart)
        self.btn_view_data = QPushButton("数据")
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
        self.time_col_combo.clear()
        self.value_col_combo.clear()
        self.time_col_combo.addItems(cols)
        self.value_col_combo.addItems(cols)
        for i, c in enumerate(cols):
            if pd.api.types.is_datetime64_any_dtype(df[c]):
                self.time_col_combo.setCurrentIndex(i)
                break
        numeric_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
        if numeric_cols:
            self.value_col_combo.setCurrentText(numeric_cols[0])
        self._update_preview()

    def _update_preview(self):
        if self.df is None:
            return
        self._populate_preview_table(self.df)

    def validate_params(self) -> tuple:
        if self.df is None:
            return False, "未加载数据"
        if self.value_col_combo.currentText() == "":
            return False, "请选择数值列"
        return True, ""

    def run_and_display(self) -> Dict[str, Any]:
        ok, msg = self.validate_params()
        if not ok:
            self._clear_canvas()
            self.result_text.setStyleSheet("color: #e74c3c; font-weight: bold;")
            self.result_text.setText(msg)
            return None
        try:
            result = self.run_analysis()
            if result and "error" in result:
                self._clear_canvas()
                self.result_text.setStyleSheet("color: #e74c3c; font-weight: bold;")
                self.result_text.setText(result["error"])
                return None
            self.display_result(result)
            self.analysis_completed.emit()
            return result
        except Exception as e:
            self._clear_canvas()
            self.result_text.setStyleSheet("color: #e74c3c; font-weight: bold;")
            self.result_text.setText(f"分析失败: {str(e)}")

    def run_analysis(self) -> Dict[str, Any]:
        from analysis.time_series import acf_pacf, seasonal_decomposition, exponential_smoothing, arima, forecasting

        value_col = self.value_col_combo.currentText()
        data = self.df[value_col].dropna()

        for key, btn in self.method_btns.items():
            if btn.isChecked():
                method = key
                break
        else:
            method = "acf_pacf"

        if method == "acf_pacf":
            result = acf_pacf.analyze(data)
        elif method == "decomposition":
            period = self.seasonal_period_spin.value()
            if period == 2:
                period = None
            result = seasonal_decomposition.analyze(data, period=period)
        elif method == "exp_smoothing":
            period = self.seasonal_period_spin.value()
            if period == 2:
                period = None
            seasonal = "additive" if self.seasonal_type_combo.currentIndex() == 0 else "multiplicative"
            result = exponential_smoothing.analyze(
                data, method="holt_winters", seasonal=seasonal,
                seasonal_periods=period, forecast_steps=self.forecast_steps_spin.value(),
            )
        elif method == "arima":
            p = self.arima_p_spin.value()
            d = self.arima_d_spin.value()
            q = self.arima_q_spin.value()
            use_auto = (p == 0 and q == 0)
            result = arima.analyze(
                data, order=None if use_auto else (p, d, q),
                auto_select=use_auto, forecast_steps=self.forecast_steps_spin.value(),
            )
        elif method == "compare":
            period = self.seasonal_period_spin.value()
            if period == 2:
                period = None
            seasonal = "additive" if self.seasonal_type_combo.currentIndex() == 0 else "multiplicative"
            result = forecasting.compare_models(
                data, forecast_steps=self.forecast_steps_spin.value(),
                seasonal_periods=period, seasonal=seasonal,
            )
        else:
            result = {"error": f"未知方法: {method}"}

        self.current_result = {
            "analysis_type": f"TimeSeries: {method}",
            "params": {"method": method, "value_col": value_col},
            "result": result,
        }
        return result

    def display_result(self, result: Dict[str, Any]):
        self._clear_canvas()
        self.result_text.clear()
        self.result_table.setRowCount(0)

        if not result or "error" in result:
            self.result_text.setText(result.get("error", "无结果"))
            return

        summary = result.get("summary", {})
        lines = []
        lines.append(f"分析类型: {result.get('analysis_type', 'N/A')}")
        for k, v in summary.items():
            lines.append(f"  {k}: {v}")
        self.result_text.setText("\n".join(lines))

        self._render_chart(result)

    def _render_chart(self, result: Dict[str, Any]):
        chart_type = result.get("chart_type", "")
        from analysis.charts.chart_generator import generate_chart

        data_for_chart = {}
        if chart_type == "ACF/PACF":
            data_for_chart = {"acf": result.get("acf", {}), "pacf": result.get("pacf", {})}
            chart_type_name = "ACF/PACF图"
        elif chart_type == "Seasonal Decomposition":
            data_for_chart = result
            chart_type_name = "分解图"
        elif chart_type == "ARIMA":
            historical = result.get("fitted_values", [])
            data_for_chart = {
                "historical": historical,
                "forecast": result.get("forecast", []),
                "confidence_lower": result.get("confidence_lower", []),
                "confidence_upper": result.get("confidence_upper", []),
            }
            chart_type_name = "预测图"
            self._render_single_chart(chart_type_name, data_for_chart)
            resid = result.get("residual_diagnostics", {})
            if resid:
                self._render_single_chart("残差ACF/PACF图", {
                    "resid_acf": resid.get("acf_values", []),
                    "resid_pacf": resid.get("pacf_values", []),
                })
                self._render_single_chart("Q-Q图", {
                    "qq_theoretical": resid.get("qq_theoretical", []),
                    "qq_sample": resid.get("qq_sample", []),
                })
            return
        elif chart_type in ("Exponential Smoothing", "Forecast"):
            historical = result.get("fitted_values", [])
            data_for_chart = {
                "historical": historical,
                "forecast": result.get("forecast", []),
                "confidence_lower": result.get("confidence_lower", []),
                "confidence_upper": result.get("confidence_upper", []),
            }
            chart_type_name = "预测图"
        elif chart_type == "Model Comparison":
            historical = result.get("comparisons", [{}])[0].get("fitted_values", [])
            data_for_chart = {
                "historical": historical,
                "forecast": result.get("best_forecast", []),
                "confidence_lower": result.get("best_confidence_lower", []),
                "confidence_upper": result.get("best_confidence_upper", []),
            }
            chart_type_name = "预测图"
        else:
            return

        self._render_single_chart(chart_type_name, data_for_chart)

    def _render_single_chart(self, chart_type_name: str, data_for_chart: dict):
        from analysis.charts.chart_generator import generate_chart
        try:
            fig = generate_chart(chart_type_name, data_for_chart)
            self.current_figure = fig
            self._clear_canvas()
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
            self.canvas = FigureCanvasQTAgg(fig)
            self.chart_layout.addWidget(self.canvas)
            self.canvas.draw()
            self._switch_result_view(0)
            self._animate_chart_container()
        except Exception as e:
            self.result_text.append(f"\n图表渲染失败: {str(e)}")
