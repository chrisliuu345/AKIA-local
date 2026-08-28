"""
DOE 实验设计分析页 — 含图表嵌入
"""

from typing import Dict, Any
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QGroupBox, QFormLayout, QTextEdit,
    QTableWidget, QTableWidgetItem, QSplitter, QHeaderView,
    QFrame, QStackedWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from analysis.doe import factorial, response_surface, box_behnken
from analysis.doe import plackett_burman, definitive_screening, fractional, taguchi, mixture
from output.chart_engine import create_pareto_chart
from core.i18n import i18n
from ui.tabs.base_tab import BaseAnalysisTab
from ui.theme import BUTTON_SECONDARY, BUTTON_TOGGLE, BUTTON_PRIMARY_STRETCH
from ui.font_config import get_ui_font


class DOETab(BaseAnalysisTab):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._original_df = None  # 备份原始数据，防止生成设计覆盖
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self.title_label = QLabel(i18n.tr("doe.title"))
        self.title_label.setFont(QFont(get_ui_font(), 18, QFont.Bold))
        layout.addWidget(self.title_label)
        layout.addSpacing(4)

        splitter = QSplitter(Qt.Vertical)

        top = QWidget()
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(0, 0, 0, 0)

        config_group = QGroupBox("DOE 配置")
        config_layout = QFormLayout(config_group)

        self.method_combo = QComboBox()
        self.method_combo.addItems([
            "── 筛选设计 ──",
            "Plackett-Burman 筛选设计",
            "Definitive Screening 设计",
            "── 因子设计 ──",
            "全因子 2^k 设计分析",
            "生成全因子 2^k 设计",
            "部分因子 2^(k-p) 设计",
            "── 响应曲面 ──",
            "响应曲面分析 (CCD)",
            "Box-Behnken 设计",
            "── 田口设计 ──",
            "田口正交阵列分析",
            "── 混合设计 ──",
            "混合设计分析",
        ])
        config_layout.addRow("方法:", self.method_combo)

        self.response_combo = QComboBox()
        config_layout.addRow("响应列:", self.response_combo)

        self.sheet_combo = QComboBox()
        self.sheet_combo.setMinimumWidth(140)
        self.sheet_combo.currentTextChanged.connect(self._on_sheet_changed)
        config_layout.addRow("Sheet:", self.sheet_combo)

        self.factors_label = QLabel("因子列自动识别 (响应列之外的前几列)")
        config_layout.addRow(self.factors_label)

        self.replicates_spin = QSpinBox()
        self.replicates_spin.setRange(1, 10)
        self.replicates_spin.setValue(1)
        config_layout.addRow("重复次数:", self.replicates_spin)

        self.run_btn = QPushButton(i18n.tr("doe.run_btn"))
        self.run_btn.setFont(QFont(get_ui_font(), 12, QFont.Bold))
        self.run_btn.setMinimumHeight(44)
        self.run_btn.setCursor(Qt.PointingHandCursor)
        self.run_btn.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.run_btn.clicked.connect(self.run_and_display)
        config_layout.addRow(self.run_btn)

        self.power_btn = QPushButton("📊 Power & Sample Size")
        self.power_btn.setFont(QFont(get_ui_font(), 12, QFont.Bold))
        self.power_btn.setMinimumHeight(40)
        self.power_btn.setCursor(Qt.PointingHandCursor)
        self.power_btn.setStyleSheet(BUTTON_SECONDARY)
        self.power_btn.clicked.connect(self._open_power_dialog)
        config_layout.addRow(self.power_btn)

        self.save_png_btn = QPushButton(i18n.tr("doe.save_png"))
        self.save_png_btn.setFont(QFont(get_ui_font(), 12, QFont.Bold))
        self.save_png_btn.setMinimumHeight(40)
        self.save_png_btn.setCursor(Qt.PointingHandCursor)
        self.save_png_btn.setStyleSheet(BUTTON_SECONDARY)
        self.save_png_btn.clicked.connect(self._on_save_png)
        config_layout.addRow(self.save_png_btn)

        self.export_btn = QPushButton(i18n.tr("doe.export_btn"))
        self.export_btn.setFont(QFont(get_ui_font(), 12, QFont.Bold))
        self.export_btn.setMinimumHeight(44)
        self.export_btn.setCursor(Qt.PointingHandCursor)
        self.export_btn.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.export_btn.clicked.connect(self.export_clicked.emit)
        config_layout.addRow(self.export_btn)

        top_layout.addWidget(config_group)

        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setStyleSheet("")
        separator.setMaximumWidth(1)
        top_layout.addWidget(separator)

        self.data_table = QTableWidget()
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.data_table.horizontalHeader().setStretchLastSection(True)
        self.data_table.horizontalHeader().setMinimumSectionSize(70)
        self.data_table.setAlternatingRowColors(True)
        self.data_table.horizontalHeader().sectionClicked.connect(self._on_header_clicked)
        self.data_table.setSelectionBehavior(QTableWidget.SelectColumns)
        top_layout.addWidget(self.data_table, 1)

        splitter.addWidget(top)

        bottom = QWidget()
        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(6)

        self.result_label = QLabel(i18n.tr("doe.result"))
        self.result_label.setFont(QFont(get_ui_font(), 13, QFont.Bold))
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

        splitter.addWidget(bottom)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        layout.addWidget(splitter)

    def set_data(self, df: pd.DataFrame, parsed_info: Dict[str, Any]):
        self.df = df
        self.parsed_info = parsed_info
        all_cols = list(df.columns)
        self.response_combo.clear()
        self.response_combo.addItems(all_cols)

        self.data_table.setRowCount(min(50, len(df)))
        self.data_table.setColumnCount(len(df.columns))
        self.data_table.setHorizontalHeaderLabels(all_cols)
        for i in range(min(50, len(df))):
            for j, col in enumerate(df.columns):
                val = str(df.iloc[i, j])
                item = QTableWidgetItem(val)
                item.setToolTip(val)
                self.data_table.setItem(i, j, item)

    def validate_params(self) -> tuple:
        method = self.method_combo.currentText()
        if method.startswith("──"):
            return False, "请从下拉菜单中选择一个有效的分析方法"
        if method == "生成全因子 2^k 设计":
            return True, ""
        if self.df is None:
            return False, "请先导入数据文件"
        response = self.response_combo.currentText()
        if not response:
            return False, "请选择响应列（可点击右侧表格列标题快速选择）"
        if len(self.df) < 4:
            return False, f"数据量不足（仅{len(self.df)}行），至少需要4行"
        try:
            data = pd.to_numeric(self.df[response], errors="coerce").dropna()
        except KeyError:
            return False, f"列 '{response}' 在当前数据表中不存在，请点击右侧表格列标题重新选择"
        if len(data) < 4:
            return False, f"响应列 '{response}' 有效数据不足（仅{len(data)}行）"
        return True, ""

    def run_and_display(self) -> Dict[str, Any]:
        valid, msg = self.validate_params()
        if not valid:
            self._clear_canvas()
            self.result_text.setStyleSheet("color: #e74c3c; font-weight: bold;")
            self.result_text.setText(f"▎参数校验失败\n{msg}")
            return None
        self.result_text.setStyleSheet("")
        try:
            result = self.run_analysis()
            self.display_result(result)
            self.analysis_completed.emit()
            return result
        except Exception as e:
            self._clear_canvas()
            self.result_text.setStyleSheet("color: #e74c3c; font-weight: bold;")
            self.result_text.setText(f"▎分析失败\n{str(e)}")
            return None

    def run_analysis(self) -> Dict[str, Any]:
        method = self.method_combo.currentText()
        result = {}

        # 跳过分隔行
        if method.startswith("──"):
            return None

        response = self.response_combo.currentText()
        numeric_cols = self.parsed_info.get("numeric_columns", [])
        if not numeric_cols:
            numeric_cols = list(self.df.select_dtypes(include="number").columns)
        factor_cols = [c for c in numeric_cols if c != response]

        if method == "Plackett-Burman 筛选设计":
            result = plackett_burman.analyze(self.df, response, factor_cols)
        elif method == "Definitive Screening 设计":
            result = definitive_screening.analyze(self.df, response, factor_cols)
        elif method == "全因子 2^k 设计分析":
            result = factorial.analyze_factorial(self.df, response, factor_cols)
        elif method == "生成全因子 2^k 设计":
            factors = factor_cols[:3] if len(factor_cols) >= 3 else factor_cols
            if not factors:
                factors = ["A", "B", "C"]
            reps = self.replicates_spin.value()
            design_df = factorial.generate_design(factors, reps)
            result = {"chart_type": "2^k Factorial Design", "design": design_df.to_dict("records"),
                       "factors": factors, "runs": len(design_df), "replicates": reps}
            if self._original_df is None:
                self._original_df = self.df
            self.df = design_df
            self.set_data(design_df, self.parsed_info)
        elif method == "部分因子 2^(k-p) 设计":
            result = fractional.analyze(self.df, response, factor_cols)
        elif method == "响应曲面分析 (CCD)":
            result = response_surface.analyze_response_surface(self.df, response, factor_cols[:3])
        elif method == "Box-Behnken 设计":
            result = box_behnken.analyze_box_behnken(self.df, response, factor_cols[:3])
        elif method == "田口正交阵列分析":
            result = taguchi.analyze(self.df, response, factor_cols)
        elif method == "混合设计分析":
            result = mixture.analyze(self.df, response, factor_cols)

        if result is None:
            return None

        self.current_result = {
            "analysis_type": method,
            "params": {"method": method, "response": self.response_combo.currentText()},
            "result": result,
            "chart_data": result,
        }
        return self.current_result

    def _open_power_dialog(self):
        """打开 Power & Sample Size 对话框"""
        from ui.dialogs.power_dialog import PowerDialog
        dlg = PowerDialog(self)
        dlg.exec()

    def _restore_original(self):
        """恢复到用户导入的原始数据（撤销生成设计覆盖）"""
        if self._original_df is not None:
            self.df = self._original_df
            self.set_data(self._original_df, self.parsed_info)
            self._original_df = None

    def display_result(self, analysis: Dict[str, Any] = None):
        if analysis is None:
            analysis = self.current_result
        result = analysis.get("result", {})
        lines = [f"=== {analysis.get('analysis_type', 'DOE')} ===\n"]

        if "runs" in result:
            lines.append(f"生成设计: {result.get('runs', '')} 次实验")
            lines.append(f"因子: {result.get('factors', [])}")
            lines.append(f"重复: {result.get('replicates', 1)}")
        else:
            lines.append(f"观测数: {result.get('observations', '')}")
            lines.append(f"R2: {result.get('r_squared', result.get('model_r_squared', ''))}")

            effects = result.get("effects", result.get("main_effects", {}))
            if effects:
                lines.append(f"\n【因子效应】")
                for k, v in effects.items():
                    lines.append(f"  {k}: {v}")
            interaction = result.get("interaction_effects", {})
            if interaction:
                lines.append(f"\n【交互效应】")
                for k, v in interaction.items():
                    lines.append(f"  {k}: {v}")

            pareto = result.get("pareto", result.get("pareto_data", []))
            if pareto:
                self._render_pareto(pareto)
                lines.append(f"\n【Pareto排序】")
                for item in pareto[:10]:
                    lines.append(f"  {item.get('term', '')}: {item.get('effect', '')}")
            else:
                self._clear_canvas()

            anova_table = result.get("anova", {})
            if anova_table:
                lines.append(f"\n【ANOVA】")
                sources = anova_table.get("source", [])
                p_vals = anova_table.get("p_value", [])
                for s, p in zip(sources, p_vals):
                    sig = "***" if p is not None and p < 0.001 else "**" if p is not None and p < 0.01 else "*" if p is not None and p < 0.05 else ""
                    lines.append(f"  {s}: p={p} {sig}")

            coeffs = result.get("coefficients", {})
            if coeffs:
                lines.append(f"\n【回归系数】")
                for k, v in list(coeffs.items())[:15]:
                    lines.append(f"  {k}: {v}")

            sig_factors = result.get("significant_factors", [])
            if sig_factors:
                lines.append(f"\n  显著因子: {sig_factors}")

        self.result_text.setPlainText("\n".join(lines))
        self.result_text.update()
        if self.canvas is not None:
            self._switch_result_view(0)
        else:
            self._switch_result_view(1)
        self.result_text.update()

    def _render_pareto(self, pareto_data: list):
        self._clear_canvas()
        try:
            labels = [item.get("term", "") for item in pareto_data[:10]]
            values = [float(item.get("effect", 0)) for item in pareto_data[:10]]
            if labels and values:
                fig = create_pareto_chart(labels, values, title="因子效应 Pareto 图")
                self.current_figure = fig
                self.canvas = FigureCanvasQTAgg(fig)
                self.chart_layout.addWidget(self.canvas)
                self.canvas.draw()
            self._add_chart_toolbar()
        except Exception as e:
            err_label = QLabel(f"图表渲染失败: {e}")
            err_label.setStyleSheet("color: #e74c3c; padding: 12px;")
            err_label.setWordWrap(True)
            self.chart_layout.addWidget(err_label)






    def _on_header_clicked(self, index: int):
        item = self.data_table.horizontalHeaderItem(index)
        if item is None:
            return
        col_name = item.text()
        combo_items = [self.response_combo.itemText(i) for i in range(self.response_combo.count())]
        if col_name in combo_items:
            self.response_combo.setCurrentText(col_name)
        self.data_table.selectColumn(index)

    def refresh_texts(self):
        self.title_label.setText(i18n.tr("doe.title"))
        self.run_btn.setText(i18n.tr("doe.run_btn"))
        self.result_label.setText(i18n.tr("doe.result"))
