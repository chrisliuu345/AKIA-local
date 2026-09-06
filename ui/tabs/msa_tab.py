"""
MSA 测量系统分析页 — 含图表嵌入
"""

from typing import Dict, Any
import pandas as pd
import numpy as np

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QDoubleSpinBox, QGroupBox, QFormLayout,
    QTableWidget, QTextEdit, QSplitter, QHeaderView,
    QFrame, QMenu, QStackedWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from core.i18n import i18n
from ui.tabs.base_tab import BaseAnalysisTab
from ui.theme import BUTTON_SECONDARY, BUTTON_TOGGLE, BUTTON_PRIMARY_STRETCH
from ui.font_config import get_ui_font
from core.formatting import format_pvalue
from output.chart_engine import create_histogram


class MSATab(BaseAnalysisTab):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self.title_label = QLabel(i18n.tr("msa.title"))
        self.title_label.setFont(QFont(get_ui_font(), 18, QFont.Bold))
        layout.addWidget(self.title_label)
        layout.addSpacing(4)

        splitter = QSplitter(Qt.Vertical)

        top = QWidget()
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(0, 0, 0, 0)

        config_group = QGroupBox("分析配置")
        config_layout = QFormLayout(config_group)

        self.method_combo = QComboBox()
        self.method_combo.addItems(["量具R&R (交叉)", "量具R&R (嵌套)", "EMP 方法", "偏倚分析", "线性分析", "属性一致性分析", "Type 1 量具研究"])
        config_layout.addRow("分析方法:", self.method_combo)

        self.measure_col = QComboBox()
        config_layout.addRow("测量列:", self.measure_col)

        self.sheet_combo = QComboBox()
        self.sheet_combo.setMinimumWidth(140)
        self.sheet_combo.currentTextChanged.connect(self._on_sheet_changed)
        config_layout.addRow("Sheet:", self.sheet_combo)

        self.part_col = QComboBox()
        config_layout.addRow("零件列:", self.part_col)

        self.operator_col = QComboBox()
        config_layout.addRow("操作员列:", self.operator_col)

        self.tolerance_spin = QDoubleSpinBox()
        self.tolerance_spin.setRange(0, 1e9)
        self.tolerance_spin.setDecimals(4)
        self.tolerance_spin.setValue(1.0)
        config_layout.addRow("公差:", self.tolerance_spin)

        self.ref_spin = QDoubleSpinBox()
        self.ref_spin.setRange(0, 1e9)
        self.ref_spin.setDecimals(4)
        config_layout.addRow("参考值:", self.ref_spin)

        self.run_btn = QPushButton(i18n.tr("msa.run_btn"))
        self.run_btn.setFont(QFont(get_ui_font(), 12, QFont.Bold))
        self.run_btn.setMinimumHeight(44)
        self.run_btn.setCursor(Qt.PointingHandCursor)
        self.run_btn.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.run_btn.clicked.connect(self.run_and_display)
        config_layout.addRow(self.run_btn)

        self.save_png_btn = QPushButton(i18n.tr("msa.save_png"))
        self.save_png_btn.setFont(QFont(get_ui_font(), 12, QFont.Bold))
        self.save_png_btn.setMinimumHeight(40)
        self.save_png_btn.setCursor(Qt.PointingHandCursor)
        self.save_png_btn.setStyleSheet(BUTTON_SECONDARY)
        self.save_png_btn.clicked.connect(self._on_save_png)
        config_layout.addRow(self.save_png_btn)

        self.export_btn = QPushButton(i18n.tr("msa.export_btn"))
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
        self.data_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.data_table.customContextMenuRequested.connect(self._on_context_menu)
        top_layout.addWidget(self.data_table, 1)

        splitter.addWidget(top)

        bottom = QWidget()
        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(6)

        self.result_label = QLabel(i18n.tr("msa.result"))
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
        self.measure_col.clear()
        self.measure_col.addItems(list(df.columns))

        all_cols = list(df.columns)
        self.part_col.clear()
        self.part_col.addItems(all_cols)
        self.operator_col.clear()
        self.operator_col.addItems(all_cols)

        self._populate_preview_table(df)

    def validate_params(self) -> tuple:
        if self.df is None:
            return False, "请先导入数据文件"
        measure = self.measure_col.currentText()
        if not measure:
            return False, "请选择测量列（可点击右侧表格列标题快速选择）"
        method = self.method_combo.currentText()
        try:
            if "R&R" in method or "属性一致性" in method or "线性" in method:
                part = self.part_col.currentText()
                if part:
                    parts = self.df[part].dropna().unique()
                    if len(parts) < 2:
                        return False, f"零件列 '{part}' 至少需要2个不同零件，当前：{len(parts)}"
                elif "线性" in method:
                    return False, "线性分析需要选择零件列"
                elif "R&R" in method:
                    return False, "请选择零件列（可右键点击表格列标题设为零件列）"
            if "R&R" in method or "属性一致性" in method:
                operator = self.operator_col.currentText()
                if operator:
                    ops = self.df[operator].dropna().unique()
                    if len(ops) < 2:
                        return False, f"操作员列 '{operator}' 至少需要2个不同操作员，当前：{len(ops)}"
                elif "R&R" in method:
                    return False, "请选择操作员列（可右键点击表格列标题设为操作员列）"
        except KeyError as e:
            return False, f"列选择错误：{e} 在当前数据表中不存在，请点击表格列标题重新选择"
        if "Type 1" in method:
            reference = self.ref_spin.value()
            if reference == 0.0:
                return False, "Type 1 量具研究需要设置参考值（真值）"
            data = pd.to_numeric(self.df[measure], errors="coerce").dropna()
            if len(data) < 5:
                return False, f"Type 1 量具研究至少需要 5 个观测值，当前 {len(data)}"
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
        from analysis.msa import gage_rr, linearity_bias, attribute_agree, type1_study, emp

        method = self.method_combo.currentText()
        measure = self.measure_col.currentText()
        part = self.part_col.currentText()
        operator = self.operator_col.currentText()
        tolerance = self.tolerance_spin.value()
        reference = self.ref_spin.value()

        result = {}
        if "R&R" in method and "交叉" in method:
            result = gage_rr.analyze_crossed(self.df, measure, part, operator, tolerance)
        elif "R&R" in method and "嵌套" in method:
            result = gage_rr.analyze_nested(self.df, measure, part, operator, tolerance)
        elif "EMP" in method:
            result = emp.analyze_crossed(self.df, measure, part, operator, tolerance)
        elif "偏倚" in method:
            data = pd.to_numeric(self.df[measure], errors="coerce").dropna()
            result = linearity_bias.analyze_bias(data, reference)
        elif "线性" in method:
            result = linearity_bias.analyze_linearity(self.df, measure, part)
        elif "属性一致性" in method:
            result = attribute_agree.analyze(self.df, measure, part, operator)
        elif "Type 1" in method:
            data = pd.to_numeric(self.df[measure], errors="coerce").dropna()
            result = type1_study.analyze(data, reference, tolerance=tolerance)

        self.current_result = {
            "analysis_type": method,
            "params": {"measurement": measure, "part": part, "operator": operator, "tolerance": tolerance, "method": method},
            "result": result,
            "chart_data": result,
        }
        return self.current_result

    def display_result(self, analysis: Dict[str, Any] = None):
        if analysis is None:
            analysis = self.current_result
        result = analysis.get("result", {})
        lines = [f"=== {analysis.get('analysis_type', 'MSA')} ===\n"]

        measure = analysis.get("params", {}).get("measurement", "")
        if self.df is not None and measure:
            try:
                raw = pd.to_numeric(self.df[measure], errors="coerce").dropna().values
                self._render_chart(raw)
            except Exception:
                self._clear_canvas()

        vc = result.get("variance_components", {})
        if vc:
            lines.append("【方差分量】")
            for k, v in vc.items():
                lines.append(f"  {k}: {v}")
        pct = result.get("percentages", {})
        if pct:
            lines.append("\n【变异百分比】")
            for k, v in pct.items():
                lines.append(f"  {k}: {v}%")
        ndc = result.get("ndc", "")
        if ndc:
            lines.append(f"\n  NDC: {ndc}")
        acceptance = result.get("acceptance", {})
        if acceptance:
            lines.append("\n【判定】")
            lines.append(f"  {acceptance.get('message', '')} ({acceptance.get('level', '')})")
        if "kappa" in result:
            lines.append(f"\n  Kappa: {result.get('kappa', '')}")
            lines.append(f"  {result.get('kappa_interpretation', '')}")
            lines.append(f"  一致率: {result.get('agreement_rate', '')}%")
            if "effective_kappa" in result:
                lines.append(f"  有效 Kappa: {result.get('effective_kappa', '')}")
        if "discrimination_grade" in result:
            dg = result.get("discrimination_grade", {})
            lines.append("\n【分辨力分级】")
            lines.append(f"  等级: {dg.get('grade', '')} 级 ({dg.get('level', '')})")
            lines.append(f"  {dg.get('description', '')}")
        if "wheeler_criteria" in result:
            lines.append("\n【Wheeler 判异准则】")
            for c in result.get("wheeler_criteria", []):
                status = "✓" if c.get("status") == "pass" else "✗"
                lines.append(f"  {status} {c.get('name', '')}: {c.get('detail', '')}")
        if "uncertainty" in result:
            unc = result.get("uncertainty", {})
            lines.append("\n【不确定度预算 (GUM)】")
            lines.append(f"  合成不确定度: {unc.get('combined_uncertainty', '')}")
            lines.append(f"  扩展不确定度 (k={unc.get('coverage_factor', '')}): {unc.get('expanded_uncertainty', '')}")
            if unc.get("tolerance_ratio") is not None:
                lines.append(f"  公差比: {unc.get('tolerance_ratio', '')}")
            lines.append(f"  {unc.get('interpretation', '')}")
        if "mean_bias" in result:
            lines.append(f"\n  平均偏倚: {result.get('mean_bias', '')}")
            pv = result.get('p_value', '')
            pv_str = format_pvalue(pv) if isinstance(pv, (int, float)) else str(pv)
            lines.append(f"  p值: {pv_str}")
        cap = result.get("capability", {})
        if cap:
            lines.append("\n【Type 1 能力指标】")
            lines.append(f"  Cg: {cap.get('cg', '')}")
            lines.append(f"  Cgk: {cap.get('cgk', '')}")
            lines.append(f"  偏倚: {cap.get('bias', '')} ({cap.get('bias_pct', '')}%)")
            lines.append(f"  可接受: {'是' if cap.get('is_capable') else '否'}")
        bias_test = result.get("bias_test", {})
        if bias_test:
            lines.append("\n【偏倚 t 检验】")
            lines.append(f"  平均偏倚: {bias_test.get('mean_bias', '')}")
            pv = bias_test.get('p_value', '')
            pv_str = format_pvalue(pv) if isinstance(pv, (int, float)) else str(pv)
            lines.append(f"  p值: {pv_str}")
            lines.append(f"  结论: {bias_test.get('interpretation', '')}")

        self.result_text.setPlainText("\n".join(lines))
        self.result_text.update()
        self._switch_result_view(0)
        self.result_text.update()

    def _render_chart(self, raw_data: np.ndarray):
        try:
            fig = create_histogram(raw_data, title="测量数据分布", options=self._chart_options)
            self._render_figure(fig)
            self._add_chart_toolbar()
            self.set_chart_type("直方图")
        except Exception as e:
            self._clear_canvas()
            err_label = QLabel(f"图表渲染失败: {e}")
            err_label.setStyleSheet("color: #e74c3c; padding: 12px;")
            err_label.setWordWrap(True)
            self.chart_layout.addWidget(err_label)


    def _on_header_clicked(self, index: int):
        item = self.data_table.horizontalHeaderItem(index)
        if item is None:
            return
        col_name = item.text()
        combo_items = [self.measure_col.itemText(i) for i in range(self.measure_col.count())]
        if col_name in combo_items:
            self.measure_col.setCurrentText(col_name)
            self.data_table.selectColumn(index)

    def _on_context_menu(self, pos):
        vp = self.data_table.viewport()
        vp_pos = vp.mapFrom(self, pos)
        col = self.data_table.columnAt(vp_pos.x())
        if col < 0:
            return
        item = self.data_table.horizontalHeaderItem(col)
        if item is None:
            return
        col_name = item.text()
        is_numeric = col_name in [self.measure_col.itemText(i) for i in range(self.measure_col.count())]
        menu = QMenu(self)
        act_part = menu.addAction(f"{i18n.tr('msa.set_part')}: {col_name}")
        act_op = menu.addAction(f"{i18n.tr('msa.set_operator')}: {col_name}")
        if is_numeric:
            act_measure = menu.addAction(f"{i18n.tr('msa.set_measure')}: {col_name}")
        else:
            act_measure = None
        action = menu.exec(vp.mapToGlobal(vp_pos))
        if action == act_part:
            self.part_col.setCurrentText(col_name)
        elif action == act_op:
            self.operator_col.setCurrentText(col_name)
        elif act_measure and action == act_measure:
            self.measure_col.setCurrentText(col_name)

    def refresh_texts(self):
        self.title_label.setText(i18n.tr("msa.title"))
        self.run_btn.setText(i18n.tr("msa.run_btn"))
        self.result_label.setText(i18n.tr("msa.result"))
