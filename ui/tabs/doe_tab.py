"""
DOE 实验设计分析页 — 含图表嵌入
"""

from typing import Any
import pandas as pd

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QGroupBox, QFormLayout, QTableWidget, QTableWidgetItem, QSplitter, QHeaderView,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from core.i18n import i18n
from ui.tabs.base_tab import BaseAnalysisTab
from ui.theme import BUTTON_SECONDARY, BUTTON_PRIMARY_STRETCH
from ui.font_config import get_ui_font
from output.chart_engine import create_pareto_chart


class DOETab(BaseAnalysisTab):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._original_df = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self.title_label = QLabel(i18n.tr("doe.title"))
        self.title_label.setFont(QFont(get_ui_font(), 18, QFont.DemiBold))
        layout.addWidget(self.title_label)
        layout.addSpacing(4)

        splitter = QSplitter(Qt.Vertical)

        top = QWidget()
        top_layout = QHBoxLayout(top)
        top_layout.setSpacing(10)
        top_layout.setContentsMargins(0, 0, 0, 0)

        config_group = QGroupBox("DOE 配置")
        config_layout = QFormLayout(config_group)
        config_layout.setContentsMargins(10, 10, 10, 10)

        self.method_combo = QComboBox()
        self.method_combo.addItems([
            "Plackett-Burman 筛选设计",
            "Definitive Screening 设计",
            "全因子 2^k 设计分析",
            "生成全因子 2^k 设计",
            "部分因子 2^(k-p) 设计",
            "响应曲面分析 (CCD)",
            "Box-Behnken 设计",
            "田口正交阵列分析",
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
        self.run_btn.setFont(QFont(get_ui_font(), 12))
        self.run_btn.setMinimumHeight(44)
        self.run_btn.setCursor(Qt.PointingHandCursor)
        self.run_btn.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.run_btn.clicked.connect(self.run_and_display)
        config_layout.addRow(self.run_btn)

        self.power_btn = QPushButton("📊 Power & Sample Size")
        self.power_btn.setFont(QFont(get_ui_font(), 12))
        self.power_btn.setMinimumHeight(40)
        self.power_btn.setCursor(Qt.PointingHandCursor)
        self.power_btn.setStyleSheet(BUTTON_SECONDARY)
        self.power_btn.clicked.connect(self._open_power_dialog)
        config_layout.addRow(self.power_btn)

        self.save_png_btn = QPushButton(i18n.tr("doe.save_png"))
        self.save_png_btn.setFont(QFont(get_ui_font(), 12))
        self.save_png_btn.setMinimumHeight(40)
        self.save_png_btn.setCursor(Qt.PointingHandCursor)
        self.save_png_btn.setStyleSheet(BUTTON_SECONDARY)
        self.save_png_btn.clicked.connect(self._on_save_png)
        config_layout.addRow(self.save_png_btn)

        self.export_btn = QPushButton(i18n.tr("doe.export_btn"))
        self.export_btn.setFont(QFont(get_ui_font(), 12))
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

        splitter.addWidget(top)

        bottom = QWidget()
        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(6)

        self.result_label = QLabel(i18n.tr("doe.result"))
        self.result_label.setFont(QFont(get_ui_font(), 13))
        bottom_layout.addWidget(self.result_label)

        self.mount_results(bottom_layout)

        splitter.addWidget(bottom)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        layout.addWidget(splitter)

    def set_data(self, df: pd.DataFrame, parsed_info: dict[str, Any]):
        self.df = df
        self.parsed_info = parsed_info
        all_cols = list(df.columns)
        self.response_combo.clear()
        self.response_combo.addItems(all_cols)

        self.data_table.setRowCount(min(50, len(df)))
        self.data_table.setColumnCount(len(df.columns))
        self.data_table.setHorizontalHeaderLabels(all_cols)
        for i in range(min(50, len(df))):
            for j, _col in enumerate(df.columns):
                val = str(df.iloc[i, j])
                item = QTableWidgetItem(val)
                item.setToolTip(val)
                self.data_table.setItem(i, j, item)

    def validate_params(self) -> tuple:
        method = self.method_combo.currentText()
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

    def run_and_display(self) -> dict[str, Any]:
        from ui.present import present_analysis

        def finish(produced):
            result, design = produced
            return self._apply_doe(result, design)

        return present_analysis(self, self._doe_job, finish=finish)

    def run_analysis(self) -> dict[str, Any]:
        result, design = self._doe_job()()
        return self._apply_doe(result, design)

    def _apply_doe(self, result, design):
        if design is not None:
            if self._original_df is None:
                self._original_df = self.df
            self.df = design
            self.set_data(design, self.parsed_info)
        if result is None:
            return None
        method = result.pop("_method")
        response = result.pop("_response")
        self.current_result = {
            "analysis_type": method,
            "params": {"method": method, "response": response},
            "result": result,
            "chart_data": result,
        }
        return self.current_result

    def _doe_job(self):
        from analysis.doe import factorial, response_surface, box_behnken
        from analysis.doe import plackett_burman, definitive_screening, fractional, taguchi, mixture

        method = self.method_combo.currentText()
        response = self.response_combo.currentText()
        numeric_cols = list(self.parsed_info.get("numeric_columns", []) or [])
        frame = self.df
        reps = self.replicates_spin.value()
        if not numeric_cols and frame is not None:
            numeric_cols = list(frame.select_dtypes(include="number").columns)

        def compute():
            return _compute_doe(
                frame, method, response, numeric_cols, reps,
                factorial, response_surface, box_behnken, plackett_burman,
                definitive_screening, fractional, taguchi, mixture)
        return compute

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

    def display_result(self, analysis: dict[str, Any] | None = None):
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
                lines.append("\n【因子效应】")
                for k, v in effects.items():
                    lines.append(f"  {k}: {v}")
            interaction = result.get("interaction_effects", {})
            if interaction:
                lines.append("\n【交互效应】")
                for k, v in interaction.items():
                    lines.append(f"  {k}: {v}")

            pareto = result.get("pareto", result.get("pareto_data", []))
            if pareto:
                self._render_pareto(pareto)
                lines.append("\n【Pareto排序】")
                for item in pareto[:10]:
                    lines.append(f"  {item.get('term', '')}: {item.get('effect', '')}")
            else:
                self._clear_canvas()

            anova_table = result.get("anova", {})
            if anova_table:
                lines.append("\n【ANOVA】")
                sources = anova_table.get("source", [])
                p_vals = anova_table.get("p_value", [])
                for s, p in zip(sources, p_vals, strict=True):
                    sig = "***" if p is not None and p < 0.001 else "**" if p is not None and p < 0.01 else "*" if p is not None and p < 0.05 else ""
                    lines.append(f"  {s}: p={p} {sig}")

            coeffs = result.get("coefficients", {})
            if coeffs:
                lines.append("\n【回归系数】")
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
                from ui.widgets.chart_canvas import ChartCanvas
                self.canvas = ChartCanvas(fig)
                self.chart_layout.addWidget(self.canvas)
                self.canvas.draw()
            self._add_chart_toolbar()
        except Exception as e:
            err_label = QLabel(f"图表渲染失败: {e}")
            err_label.setStyleSheet("color: #E00000; padding: 12px;")
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


def _compute_doe(frame, method, response, numeric_cols, reps,
                 factorial, response_surface, box_behnken, plackett_burman,
                 definitive_screening, fractional, taguchi, mixture):
    factor_cols = [col for col in numeric_cols if col != response]
    if not factor_cols and method != "生成全因子 2^k 设计":
        raise ValueError(
            "没有可用的因子列。\n"
            "DOE 分析需要至少 2 列数值数据（1 列响应 + 1 列因子）。\n"
            "请检查：数据列是否为数值、列名是否被误判为规格/序号列。")
    result: dict[str, Any] = {}
    design = None
    if method == "Plackett-Burman 筛选设计":
        result = plackett_burman.analyze(frame, response, factor_cols)
    elif method == "Definitive Screening 设计":
        result = definitive_screening.analyze(frame, response, factor_cols)
    elif method == "全因子 2^k 设计分析":
        result = factorial.analyze_factorial(frame, response, factor_cols)
    elif method == "生成全因子 2^k 设计":
        factors = factor_cols[:3] if len(factor_cols) >= 3 else factor_cols
        if not factors:
            factors = ["A", "B", "C"]
        design = factorial.generate_design(factors, reps)
        result = {"chart_type": "2^k Factorial Design", "design": design.to_dict("records"),
                  "factors": factors, "runs": len(design), "replicates": reps}
    elif method == "部分因子 2^(k-p) 设计":
        result = fractional.analyze(frame, response, factor_cols)
    elif method == "响应曲面分析 (CCD)":
        result = response_surface.analyze_response_surface(frame, response, factor_cols[:3])
    elif method == "Box-Behnken 设计":
        result = box_behnken.analyze_box_behnken(frame, response, factor_cols[:3])
    elif method == "田口正交阵列分析":
        result = taguchi.analyze(frame, response, factor_cols)
    elif method == "混合设计分析":
        result = mixture.analyze(frame, response, factor_cols)
    if result is None:
        return None, design
    result = dict(result)
    result["_method"] = method
    result["_response"] = response
    return result, design
