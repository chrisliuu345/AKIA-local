"""
通用图表生成 Tab — 动态配置面板 + 12 种图表类型
"""

from typing import Dict, Any, List, Optional
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QGroupBox, QFormLayout, QTextEdit, QCheckBox,
    QTableWidget, QTableWidgetItem, QSplitter, QHeaderView,
    QStackedWidget, QListWidget, QListWidgetItem, QLineEdit,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from core.i18n import i18n
from ui.tabs.base_tab import BaseAnalysisTab
from ui.theme import colors as theme_colors, BUTTON_PRIMARY_STRETCH, BUTTON_SECONDARY, BUTTON_TOGGLE
from analysis.charts import generate_chart, CHART_TYPES, CHART_CONFIGS
from analysis.charts.chart_generator import _build_summary, _CHART_PALETTES


_COL_TYPE_MAP = {
    "numeric": "numeric_columns",
    "multi_numeric": "numeric_columns",
    "multi_text": "identifier_columns",
    "text": "identifier_columns",
    "datetime": "column_types",
}


class ChartTab(BaseAnalysisTab):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.df: pd.DataFrame = None
        self.parsed_info: Dict[str, Any] = {}
        self.current_result: Dict[str, Any] = {}
        self.current_figure = None
        self.canvas = None
        self._col_widgets: list = []
        self._setup_ui()

    def _setup_ui(self):
        tc = theme_colors(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self.title_label = QLabel(i18n.tr("chart_tab.title"))
        self.title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        layout.addWidget(self.title_label)

        top_layout = QHBoxLayout()

        config_group = QGroupBox(i18n.tr("chart_tab.config"))
        config_form_layout = QFormLayout(config_group)

        self.sheet_combo = QComboBox()
        self.sheet_combo.setMinimumWidth(140)
        self.sheet_combo.currentTextChanged.connect(self._on_sheet_changed)
        config_form_layout.addRow(i18n.tr("chart_tab.sheet"), self.sheet_combo)

        self.chart_type_combo = QComboBox()
        self.chart_type_combo.addItems(CHART_TYPES)
        self.chart_type_combo.currentTextChanged.connect(self._on_chart_type_changed)
        config_form_layout.addRow(i18n.tr("chart_tab.chart_type"), self.chart_type_combo)

        self.config_panel = QWidget()
        self.config_form_layout = QFormLayout(self.config_panel)
        self.config_form_layout.setContentsMargins(0, 4, 0, 0)
        config_form_layout.addRow(self.config_panel)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText(i18n.tr("chart_tab.title_ph"))
        config_form_layout.addRow(i18n.tr("chart_tab.chart_title"), self.title_edit)

        self.palette_combo = QComboBox()
        self.palette_combo.addItems(list(_CHART_PALETTES.keys()))
        config_form_layout.addRow(i18n.tr("chart_tab.palette"), self.palette_combo)

        self.cb_3d = QCheckBox(i18n.tr("chart_tab.render_3d"))
        self.cb_3d.setChecked(True)
        self.cb_3d.setVisible(False)
        config_form_layout.addRow("", self.cb_3d)

        self.run_btn = QPushButton(i18n.tr("chart_tab.run_btn"))
        self.run_btn.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        self.run_btn.setMinimumHeight(44)
        self.run_btn.setCursor(Qt.PointingHandCursor)
        self.run_btn.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.run_btn.clicked.connect(self.run_and_display)
        config_form_layout.addRow(self.run_btn)

        self.save_png_btn = QPushButton(i18n.tr("chart_tab.save_png"))
        self.save_png_btn.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        self.save_png_btn.setMinimumHeight(40)
        self.save_png_btn.setCursor(Qt.PointingHandCursor)
        self.save_png_btn.setStyleSheet(BUTTON_SECONDARY)
        self.save_png_btn.clicked.connect(self._on_save_png)
        config_form_layout.addRow(self.save_png_btn)

        top_layout.addWidget(config_group)

        self.data_table = QTableWidget()
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.data_table.horizontalHeader().setStretchLastSection(True)
        self.data_table.horizontalHeader().setMinimumSectionSize(70)
        self.data_table.setAlternatingRowColors(True)
        self.data_table.setSelectionBehavior(QTableWidget.SelectColumns)
        top_layout.addWidget(self.data_table, 1)

        layout.addLayout(top_layout)

        result_group = QGroupBox(i18n.tr("chart_tab.result"))
        result_layout = QVBoxLayout(result_group)

        toggle_row = QHBoxLayout()
        self.btn_view_chart = QPushButton(i18n.tr("tab.view_chart"))
        self.btn_view_chart.setFont(QFont("Microsoft YaHei", 11))
        self.btn_view_chart.setFixedHeight(30)
        self.btn_view_chart.setCheckable(True)
        self.btn_view_chart.setChecked(True)
        self.btn_view_chart.setStyleSheet(BUTTON_TOGGLE)
        self.btn_view_chart.clicked.connect(lambda: self._switch_result_view(0))
        toggle_row.addWidget(self.btn_view_chart)

        self.btn_view_data = QPushButton(i18n.tr("tab.view_data"))
        self.btn_view_data.setFont(QFont("Microsoft YaHei", 11))
        self.btn_view_data.setFixedHeight(30)
        self.btn_view_data.setCheckable(True)
        self.btn_view_data.setStyleSheet(BUTTON_TOGGLE)
        self.btn_view_data.clicked.connect(lambda: self._switch_result_view(1))
        toggle_row.addWidget(self.btn_view_data)
        toggle_row.addStretch()
        result_layout.addLayout(toggle_row)

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
        self.result_text.setFont(QFont("Microsoft YaHei", 11))
        self.result_text.setMinimumHeight(80)
        data_layout.addWidget(self.result_text)
        self.result_table = QTableWidget()
        self.result_table.horizontalHeader().setStretchLastSection(True)
        self.result_table.setAlternatingRowColors(True)
        data_layout.addWidget(self.result_table)
        self.result_stack.addWidget(self.data_container)

        result_layout.addWidget(self.result_stack)
        layout.addWidget(result_group, 1)

        self._rebuild_config_panel(CHART_TYPES[0])

    def _on_chart_type_changed(self, chart_type: str):
        self._rebuild_config_panel(chart_type)
        self.cb_3d.setVisible(chart_type == "3D曲面图")

    def _rebuild_config_panel(self, chart_type: str):
        while self.config_form_layout.rowCount() > 0:
            self.config_form_layout.removeRow(0)
        self._col_widgets.clear()

        # 散点图回归线开关
        if hasattr(self, 'cb_show_regression'):
            self.cb_show_regression.setVisible(False)
        if chart_type == "散点图":
            if not hasattr(self, 'cb_show_regression'):
                from PySide6.QtWidgets import QCheckBox
                self.cb_show_regression = QCheckBox("显示回归线")
                self.cb_show_regression.setChecked(True)
                self.cb_show_regression.setStyleSheet("color: #a0a3ae;")
            self.cb_show_regression.setVisible(True)
            self.config_form_layout.addRow(self.cb_show_regression)

        configs = CHART_CONFIGS.get(chart_type, [])
        for label_text, col_type in configs:
            if col_type.startswith("multi_"):
                w = QListWidget()
                w.setSelectionMode(QListWidget.MultiSelection)
                w.setMinimumHeight(80)
                w.setMaximumHeight(120)
            else:
                w = QComboBox()
                w.setMinimumWidth(140)
            w.setProperty("col_type", col_type)
            self._col_widgets.append(w)
            self.config_form_layout.addRow(label_text, w)

        self._populate_column_widgets()

    def _populate_column_widgets(self):
        if self.df is None:
            return
        info = self.parsed_info or {}
        numeric = info.get("numeric_columns", [])
        text_cols = info.get("identifier_columns", [])
        datetime_cols = [c for c, t in info.get("column_types", {}).items() if t == "datetime"]
        if not datetime_cols:
            datetime_cols = []

        type_map = {
            "numeric": numeric,
            "multi_numeric": numeric,
            "text": text_cols,
            "multi_text": text_cols if text_cols else numeric,
            "datetime": datetime_cols if datetime_cols else numeric,
        }

        for w in self._col_widgets:
            col_type = w.property("col_type")
            candidates = type_map.get(col_type, [])
            if isinstance(w, QListWidget):
                w.clear()
                for c in candidates:
                    item = QListWidgetItem(c)
                    item.setCheckState(Qt.Unchecked)
                    w.addItem(item)
            else:
                w.clear()
                w.addItems(candidates)
                w.setCurrentIndex(-1)

    def set_data(self, df: pd.DataFrame, parsed_info: Dict[str, Any] = None):
        self.df = df
        self.parsed_info = parsed_info or {}
        self._populate_column_widgets()
        self._update_preview()

    def _update_preview(self):
        if self.df is not None:
            self._populate_preview_table(self.df)

    def _collect_params(self) -> dict:
        params = {"columns": [], "multi_columns": {}}
        for w in self._col_widgets:
            col_type = w.property("col_type")
            if isinstance(w, QComboBox):
                text = w.currentText()
                if text:
                    params["columns"].append(text)
            elif isinstance(w, QListWidget):
                selected = []
                for i in range(w.count()):
                    item = w.item(i)
                    if item.checkState() == Qt.Checked:
                        selected.append(item.text())
                params["multi_columns"][col_type] = selected
        return params

    def validate_params(self) -> tuple:
        if self.df is None:
            return False, i18n.tr("chart_tab.no_data")
        params = self._collect_params()
        chart_type = self.chart_type_combo.currentText()
        configs = CHART_CONFIGS.get(chart_type, [])
        for (label, col_type), w in zip(configs, self._col_widgets):
            if col_type.startswith("multi_"):
                selected = params.get("multi_columns", {}).get(col_type, [])
                if not selected:
                    return False, f"{i18n.tr('chart_tab.select_hint')}: {label}"
            else:
                if not params.get("columns", []):
                    return False, f"{i18n.tr('chart_tab.select_hint')}: {label}"
                vals = [c for c in params["columns"] if c]
                if not vals:
                    return False, f"{i18n.tr('chart_tab.select_hint')}: {label}"
            break
        return True, ""

    def run_analysis(self) -> Dict[str, Any]:
        chart_type = self.chart_type_combo.currentText()
        params = self._collect_params()

        all_cols = list(params.get("columns", []))
        for multi_list in params.get("multi_columns", {}).values():
            all_cols.extend(multi_list)
        all_cols = [c for c in all_cols if c]

        data = {
            "df": self.df,
            "columns": all_cols,
            "multi_columns": params.get("multi_columns", {}),
        }

        options = {
            "title": self.title_edit.text().strip(),
            "dark_mode": True,
            "palette": self.palette_combo.currentText(),
        }
        if hasattr(self, 'cb_show_regression') and self.cb_show_regression.isVisible():
            options["show_regression"] = self.cb_show_regression.isChecked()

        fig = generate_chart(chart_type, data, options)

        summary = _build_summary(self.df, all_cols) if all_cols else ""

        self.current_result = {
            "analysis_type": f"Chart: {chart_type}",
            "params": {"chart_type": chart_type, "columns": all_cols},
            "result": {"summary": summary, "chart_type": chart_type},
        }

        return {"figure": fig, "summary": summary, "chart_type": chart_type}

    def display_result(self, analysis: Dict[str, Any] = None):
        if analysis is None:
            return
        fig = analysis.get("figure")
        summary = analysis.get("summary", "")
        chart_type = analysis.get("chart_type", "")

        self._render_chart(fig)
        self.result_text.setPlainText(summary)
        self._switch_result_view(0)

    def _render_chart(self, fig):
        self._clear_canvas()
        self.current_figure = fig
        self.canvas = FigureCanvasQTAgg(fig)
        self.chart_layout.addWidget(self.canvas)
        self.canvas.draw()
        self._add_chart_toolbar()

    def run_and_display(self) -> Dict[str, Any]:
        ok, msg = self.validate_params()
        if not ok:
            self._clear_canvas()
            self.result_text.setStyleSheet("color: #e74c3c; font-weight: bold;")
            self.result_text.setText(msg)
            return None
        try:
            result = self.run_analysis()
            self.display_result(result)
            self.analysis_completed.emit()
            return result
        except Exception as e:
            self._clear_canvas()
            self.result_text.setStyleSheet("color: #e74c3c; font-weight: bold;")
            self.result_text.setText(f"{i18n.tr('chart_tab.analysis_failed')}\n{str(e)}")

    def refresh_texts(self):
        self.title_label.setText(i18n.tr("chart_tab.title"))
        self.run_btn.setText(i18n.tr("chart_tab.run_btn"))
