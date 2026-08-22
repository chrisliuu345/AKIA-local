"""
假设检验分析页 — 含图表嵌入
"""

from typing import Dict, Any
import pandas as pd
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QDoubleSpinBox, QSpinBox, QGroupBox, QFormLayout,
    QTableWidget, QTableWidgetItem, QTextEdit, QSplitter, QHeaderView,
    QFrame, QFileDialog, QStackedWidget,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from analysis.hypothesis import t_tests, anova, normality, variance_tests
from output.chart_engine import create_histogram
from core.i18n import i18n
from ui.tabs.base_tab import BaseAnalysisTab
from ui.theme import BUTTON_PRIMARY, BUTTON_SECONDARY, BUTTON_TOGGLE, BUTTON_PRIMARY_STRETCH
from core.formatting import format_pvalue


class HypothesisTab(BaseAnalysisTab):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self.title_label = QLabel(i18n.tr("hyp.title"))
        self.title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        layout.addWidget(self.title_label)
        layout.addSpacing(4)

        splitter = QSplitter(Qt.Vertical)

        top = QWidget()
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(0, 0, 0, 0)

        config_group = QGroupBox("分析配置")
        config_layout = QFormLayout(config_group)

        self.test_combo = QComboBox()
        self.test_combo.addItems(["单样本 t检验", "双样本 t检验", "配对 t检验", "单因素 ANOVA", "双因素 ANOVA", "正态性检验", "方差齐性检验"])
        config_layout.addRow("检验方法:", self.test_combo)

        self.col1_combo = QComboBox()
        config_layout.addRow("数据列1:", self.col1_combo)

        self.sheet_combo = QComboBox()
        self.sheet_combo.setMinimumWidth(140)
        self.sheet_combo.currentTextChanged.connect(self._on_sheet_changed)
        config_layout.addRow("Sheet:", self.sheet_combo)

        self.col2_combo = QComboBox()
        config_layout.addRow("数据列2:", self.col2_combo)

        self.factor_combo = QComboBox()
        config_layout.addRow("因子列:", self.factor_combo)

        self.factor2_combo = QComboBox()
        config_layout.addRow("因子列2:", self.factor2_combo)

        self.target_spin = QDoubleSpinBox()
        self.target_spin.setRange(-1e9, 1e9)
        self.target_spin.setDecimals(4)
        config_layout.addRow("目标值:", self.target_spin)

        self.alternative_combo = QComboBox()
        self.alternative_combo.addItems(["two-sided", "greater", "less"])
        config_layout.addRow("备择假设:", self.alternative_combo)

        self.confidence_spin = QDoubleSpinBox()
        self.confidence_spin.setRange(0.5, 0.999)
        self.confidence_spin.setValue(0.95)
        self.confidence_spin.setSingleStep(0.01)
        config_layout.addRow("置信水平:", self.confidence_spin)

        self.run_btn = QPushButton(i18n.tr("hyp.run_btn"))
        self.run_btn.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        self.run_btn.setMinimumHeight(44)
        self.run_btn.setCursor(Qt.PointingHandCursor)
        self.run_btn.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.run_btn.clicked.connect(self.run_and_display)
        config_layout.addRow(self.run_btn)

        self.save_png_btn = QPushButton(i18n.tr("hyp.save_png"))
        self.save_png_btn.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        self.save_png_btn.setMinimumHeight(40)
        self.save_png_btn.setCursor(Qt.PointingHandCursor)
        self.save_png_btn.setStyleSheet(BUTTON_SECONDARY)
        self.save_png_btn.clicked.connect(self._on_save_png)
        config_layout.addRow(self.save_png_btn)

        self.export_btn = QPushButton(i18n.tr("hyp.export_btn"))
        self.export_btn.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
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

        self.result_label = QLabel(i18n.tr("hyp.result"))
        self.result_label.setFont(QFont("Microsoft YaHei", 13, QFont.Bold))
        bottom_layout.addWidget(self.result_label)

        toggle_row = QHBoxLayout()
        toggle_row.setSpacing(8)
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
        self.result_text.setFont(QFont("Microsoft YaHei", 12))
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
        for combo in [self.col1_combo, self.col2_combo, self.factor_combo, self.factor2_combo]:
            combo.clear()
            combo.addItems(all_cols)

        self._populate_preview_table(df)

    def validate_params(self) -> tuple:
        if self.df is None:
            return False, "请先导入数据文件"
        col1 = self.col1_combo.currentText()
        if not col1:
            return False, "请选择数据列1（可点击右侧表格列标题快速选择）"
        method = self.test_combo.currentText()
        try:
            if method in ("双样本 t检验", "配对 t检验", "方差齐性检验"):
                col2 = self.col2_combo.currentText()
                if not col2:
                    return False, "请选择数据列2（可再次点击表格列标题选择）"
                d2 = pd.to_numeric(self.df[col2], errors="coerce").dropna()
                if len(d2) < 2:
                    return False, f"数据列2 '{col2}' 有效数据不足（仅{len(d2)}行）"
            if method in ("单因素 ANOVA", "双因素 ANOVA"):
                factor = self.factor_combo.currentText()
                if not factor:
                    return False, "请选择因子列"
                groups = self.df[factor].dropna().unique()
                if len(groups) < 2:
                    return False, f"因子列 '{factor}' 至少需要2个不同水平，当前：{len(groups)}"
                if method == "双因素 ANOVA":
                    factor2 = self.factor2_combo.currentText()
                    if not factor2:
                        return False, "双因素 ANOVA 需要选择第二个因子列"
                    if factor2 == factor:
                        return False, "两个因子列不能相同"
            d1 = pd.to_numeric(self.df[col1], errors="coerce").dropna()
            if len(d1) < 2:
                return False, f"数据列1 '{col1}' 有效数据不足（仅{len(d1)}行）"
        except KeyError as e:
            return False, f"列选择错误：{e} 在当前数据表中不存在，请点击表格列标题重新选择"
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
        method = self.test_combo.currentText()
        col1 = self.col1_combo.currentText()
        col2 = self.col2_combo.currentText()
        factor = self.factor_combo.currentText()
        factor2 = self.factor2_combo.currentText()
        target = self.target_spin.value()
        alternative = self.alternative_combo.currentText()
        confidence = self.confidence_spin.value()

        result = {}
        if method == "单样本 t检验":
            data = pd.to_numeric(self.df[col1], errors="coerce").dropna()
            result = t_tests.one_sample(data, target, alternative)
        elif method == "双样本 t检验":
            g1 = pd.to_numeric(self.df[col1], errors="coerce").dropna()
            g2 = pd.to_numeric(self.df[col2], errors="coerce").dropna()
            result = t_tests.two_sample(g1, g2, alternative=alternative)
        elif method == "配对 t检验":
            g1 = pd.to_numeric(self.df[col1], errors="coerce").dropna()
            g2 = pd.to_numeric(self.df[col2], errors="coerce").dropna()
            result = t_tests.paired(g1, g2, alternative)
        elif method == "单因素 ANOVA":
            result = anova.one_way(self.df, col1, factor)
        elif method == "双因素 ANOVA":
            result = anova.two_way(self.df, col1, factor, factor2)
        elif method == "正态性检验":
            data = pd.to_numeric(self.df[col1], errors="coerce").dropna()
            result = normality.normality_test(data, confidence)
        elif method == "方差齐性检验":
            groups = [pd.to_numeric(self.df[c], errors="coerce").dropna() for c in [col1, col2]]
            result = variance_tests.variance_tests(*groups, confidence)

        self.current_result = {
            "analysis_type": method,
            "params": {"column1": col1, "column2": col2, "factor": factor, "target": target, "alternative": alternative},
            "result": result,
            "chart_data": result,
        }
        return self.current_result

    def display_result(self, analysis: Dict[str, Any] = None):
        if analysis is None:
            analysis = self.current_result
        result = analysis.get("result", {})
        lines = [f"=== {analysis.get('analysis_type', '')} ===\n"]
        lines.append(f"检验类型: {result.get('test_type', '')}")
        p_val = result.get("p_value", "")
        p_str = format_pvalue(p_val) if isinstance(p_val, (int, float)) else str(p_val)
        lines.append(f"P值: {p_str}")
        lines.append(f"显著性: {'是 (p<0.05)' if result.get('is_significant') else '否 (p>=0.05)'}")

        col1 = analysis.get("params", {}).get("column1", "")
        if self.df is not None and col1:
            try:
                raw = pd.to_numeric(self.df[col1], errors="coerce").dropna().values
                self._render_chart(raw)
            except Exception:
                self._clear_canvas()

        if "t_statistic" in result:
            lines.append(f"t统计量: {result.get('t_statistic', '')}")
        if "f_statistic" in result:
            lines.append(f"F统计量: {result.get('f_statistic', '')}")
        if "anova_table" in result:
            lines.append(f"\n【ANOVA表】")
            lines.append(str(result["anova_table"]))
        if "tests" in result:
            lines.append(f"\n【检验详情】")
            for test_name, test_result in result["tests"].items():
                pv = test_result.get('p_value', '')
                pv_str = format_pvalue(pv) if isinstance(pv, (int, float)) else str(pv)
                lines.append(f"  {test_name}: p={pv_str}")
        if "level_stats" in result:
            lines.append(f"\n【各组统计】")
            for ls in result["level_stats"]:
                lines.append(f"  {ls['level']}: n={ls['n']}, mean={ls['mean']}, std={ls['std']}")

        self.result_text.setPlainText("\n".join(lines))
        self.result_text.update()
        self._switch_result_view(0)
        self.result_text.update()

    def _render_chart(self, raw_data: np.ndarray):
        self._clear_canvas()
        try:
            fig = create_histogram(raw_data, title="数据分布")
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
        all_cols = [self.col1_combo.itemText(i) for i in range(self.col1_combo.count())]
        if col_name not in all_cols:
            self.data_table.clearSelection()
            return

        targets = [
            (self.col1_combo, "col1_combo"),
            (self.col2_combo, "col2_combo"),
            (getattr(self, 'factor_combo', None), "factor_combo"),
            (getattr(self, 'factor2_combo', None), "factor2_combo"),
        ]

        for combo, _ in targets:
            if combo is None:
                continue
            if combo.currentText() == col_name:
                combo.setCurrentIndex(-1)
                self.data_table.selectColumn(index)
                return

        for combo, _ in targets:
            if combo is None:
                continue
            if combo.currentText() == "":
                combo.setCurrentText(col_name)
                self.data_table.selectColumn(index)
                return

        self.col1_combo.setCurrentText(col_name)
        self.data_table.selectColumn(index)

    def refresh_texts(self):
        self.title_label.setText(i18n.tr("hyp.title"))
        self.run_btn.setText(i18n.tr("hyp.run_btn"))
        self.result_label.setText(i18n.tr("hyp.result"))
