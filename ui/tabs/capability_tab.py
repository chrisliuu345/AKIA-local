"""
过程能力分析页 — 含图表嵌入
"""

from typing import Any
import pandas as pd
import numpy as np

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QDoubleSpinBox, QSpinBox, QGroupBox, QFormLayout,
    QTableWidget, QTableWidgetItem, QTextEdit, QSplitter, QHeaderView,
    QFrame, QStackedWidget, QInputDialog, QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from core.i18n import i18n
from ui.tabs.base_tab import BaseAnalysisTab
from ui.theme import BUTTON_SECONDARY, BUTTON_TOGGLE, BUTTON_PRIMARY_STRETCH
from ui.font_config import get_ui_font
from core.formatting import format_pvalue
from output.chart_engine import create_capability_chart


class CapabilityTab(BaseAnalysisTab):

    def __init__(self, parent=None):
        self._project_context = None
        self.standard_object_ref = ""
        super().__init__(parent)
        self._setup_ui()

    def set_project_context(self, ctx):
        self._project_context = ctx
        self._apply_context_standard()

    def _apply_context_standard(self):
        """当前测量列存在标准版本时，回填其规格限。"""
        ctx = self._project_context
        col = self.col_combo.currentText().strip() if hasattr(self, "col_combo") else ""
        if ctx is None or not col:
            return
        record = ctx.standards.current(col)
        if record is None:
            return
        payload = record.payload
        for widget, key in ((self.usl_spin, "usl"), (self.lsl_spin, "lsl"),
                            (self.target_spin, "target")):
            value = payload.get(key)
            if value is not None:
                widget.setValue(float(value))
        self.standard_object_ref = col

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self.title_label = QLabel(i18n.tr("cap.title"))
        self.title_label.setFont(QFont(get_ui_font(), 18, QFont.Bold))
        layout.addWidget(self.title_label)
        layout.addSpacing(4)

        splitter = QSplitter(Qt.Vertical)

        top = QWidget()
        top_layout = QHBoxLayout(top)
        top_layout.setSpacing(10)
        top_layout.setContentsMargins(0, 0, 0, 0)

        config_group = QGroupBox("分析配置")
        config_layout = QFormLayout(config_group)
        config_layout.setContentsMargins(10, 10, 10, 10)

        self.method_combo = QComboBox()
        self.method_combo.addItems(["正态过程能力", "非正态 (Box-Cox)", "非正态 (Johnson)", "非正态 (百分位法)", "组间/组内能力", "公差区间 (正态)", "公差区间 (非参数)", "分布拟合"])
        config_layout.addRow("分析方法:", self.method_combo)

        self.col_combo = QComboBox()
        self.col_combo.currentTextChanged.connect(lambda *_: self._apply_context_standard())
        config_layout.addRow("测量列:", self.col_combo)

        self.sheet_combo = QComboBox()
        self.sheet_combo.setMinimumWidth(140)
        self.sheet_combo.currentTextChanged.connect(self._on_sheet_changed)
        config_layout.addRow("Sheet:", self.sheet_combo)

        self.usl_spin = QDoubleSpinBox()
        self.usl_spin.setRange(-1e9, 1e9)
        self.usl_spin.setDecimals(4)
        self.usl_spin.setValue(10.0)
        config_layout.addRow("USL:", self.usl_spin)

        self.lsl_spin = QDoubleSpinBox()
        self.lsl_spin.setRange(-1e9, 1e9)
        self.lsl_spin.setDecimals(4)
        self.lsl_spin.setValue(0.0)
        config_layout.addRow("LSL:", self.lsl_spin)

        self.target_spin = QDoubleSpinBox()
        self.target_spin.setRange(-1e9, 1e9)
        self.target_spin.setDecimals(4)
        config_layout.addRow("目标值:", self.target_spin)

        self.subgroup_spin = QSpinBox()
        self.subgroup_spin.setRange(1, 25)
        self.subgroup_spin.setValue(5)
        config_layout.addRow("子组大小:", self.subgroup_spin)

        self.ti_confidence_spin = QDoubleSpinBox()
        self.ti_confidence_spin.setRange(0.5, 0.999)
        self.ti_confidence_spin.setValue(0.95)
        self.ti_confidence_spin.setSingleStep(0.01)
        self.ti_confidence_spin.setDecimals(3)
        self.row_ti_confidence = QWidget()
        self.row_ti_confidence.setVisible(False)
        ti_conf_layout = QHBoxLayout(self.row_ti_confidence)
        ti_conf_layout.setContentsMargins(0, 0, 0, 0)
        ti_conf_layout.addWidget(QLabel("置信水平:"))
        ti_conf_layout.addWidget(self.ti_confidence_spin)
        config_layout.addRow(self.row_ti_confidence)

        self.ti_proportion_spin = QDoubleSpinBox()
        self.ti_proportion_spin.setRange(0.5, 0.999)
        self.ti_proportion_spin.setValue(0.99)
        self.ti_proportion_spin.setSingleStep(0.01)
        self.ti_proportion_spin.setDecimals(3)
        self.row_ti_proportion = QWidget()
        self.row_ti_proportion.setVisible(False)
        ti_prop_layout = QHBoxLayout(self.row_ti_proportion)
        ti_prop_layout.setContentsMargins(0, 0, 0, 0)
        ti_prop_layout.addWidget(QLabel("总体比例:"))
        ti_prop_layout.addWidget(self.ti_proportion_spin)
        config_layout.addRow(self.row_ti_proportion)

        self.ti_method_combo = QComboBox()
        self.ti_method_combo.addItems(["双侧", "单侧上", "单侧下"])
        self.row_ti_method = QWidget()
        self.row_ti_method.setVisible(False)
        ti_method_layout = QHBoxLayout(self.row_ti_method)
        ti_method_layout.setContentsMargins(0, 0, 0, 0)
        ti_method_layout.addWidget(QLabel("区间类型:"))
        ti_method_layout.addWidget(self.ti_method_combo)
        config_layout.addRow(self.row_ti_method)

        self.dist_combo = QComboBox()
        self.dist_combo.addItems(["正态", "对数正态", "指数", "Gamma", "Weibull"])
        self.row_dist = QWidget()
        self.row_dist.setVisible(False)
        dist_layout = QHBoxLayout(self.row_dist)
        dist_layout.setContentsMargins(0, 0, 0, 0)
        dist_layout.addWidget(QLabel("分布类型:"))
        dist_layout.addWidget(self.dist_combo)
        config_layout.addRow(self.row_dist)

        self.method_combo.currentTextChanged.connect(self._on_method_changed)

        self.run_btn = QPushButton(i18n.tr("cap.run_btn"))
        self.run_btn.setFont(QFont(get_ui_font(), 12, QFont.Bold))
        self.run_btn.setMinimumHeight(44)
        self.run_btn.setCursor(Qt.PointingHandCursor)
        self.run_btn.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.run_btn.clicked.connect(self.run_and_display)
        config_layout.addRow(self.run_btn)

        self.save_png_btn = QPushButton(i18n.tr("cap.save_png"))
        self.save_png_btn.setFont(QFont(get_ui_font(), 12, QFont.Bold))
        self.save_png_btn.setMinimumHeight(40)
        self.save_png_btn.setCursor(Qt.PointingHandCursor)
        self.save_png_btn.setStyleSheet(BUTTON_SECONDARY)
        self.save_png_btn.clicked.connect(self._on_save_png)
        config_layout.addRow(self.save_png_btn)

        self.standard_btn = QPushButton("保存规格限为标准")
        self.standard_btn.setFont(QFont(get_ui_font(), 12, QFont.Bold))
        self.standard_btn.setMinimumHeight(40)
        self.standard_btn.setCursor(Qt.PointingHandCursor)
        self.standard_btn.setStyleSheet(BUTTON_SECONDARY)
        self.standard_btn.clicked.connect(self.save_specification_standard)
        config_layout.addRow(self.standard_btn)

        self.export_btn = QPushButton(i18n.tr("cap.export_btn"))
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

        self.result_label = QLabel(i18n.tr("cap.result"))
        self.result_label.setFont(QFont(get_ui_font(), 13, QFont.Bold))
        bottom_layout.addWidget(self.result_label)

        toggle_row = QHBoxLayout()
        toggle_row.setSpacing(8)
        self.btn_view_chart = QPushButton(i18n.tr("tab.view_chart"))
        self.btn_view_chart.setFont(QFont(get_ui_font(), 11))
        self.btn_view_chart.setFixedHeight(30)
        self.btn_view_chart.setCheckable(True)
        self.btn_view_chart.setChecked(True)
        self.btn_view_chart.setStyleSheet(
            BUTTON_TOGGLE
        )
        self.btn_view_chart.clicked.connect(lambda: self._switch_result_view(0))
        toggle_row.addWidget(self.btn_view_chart)
        self.btn_view_data = QPushButton(i18n.tr("tab.view_data"))
        self.btn_view_data.setFont(QFont(get_ui_font(), 11))
        self.btn_view_data.setFixedHeight(30)
        self.btn_view_data.setCheckable(True)
        self.btn_view_data.setStyleSheet(
            BUTTON_TOGGLE
        )
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

    def _on_method_changed(self, method: str):
        """方法切换时控制参数可见性"""
        is_tolerance = method.startswith("公差区间")
        is_normal_like = method in ("正态过程能力", "组间/组内能力")
        is_dist_fit = method == "分布拟合"
        
        self.row_ti_confidence.setVisible(is_tolerance)
        self.row_ti_proportion.setVisible(is_tolerance)
        self.row_ti_method.setVisible(is_tolerance)
        self.subgroup_spin.setVisible(is_normal_like)
        self.target_spin.setVisible(not is_tolerance and not is_dist_fit)
        self.usl_spin.setVisible(not is_dist_fit)
        self.lsl_spin.setVisible(not is_dist_fit)
        self.row_dist.setVisible(is_dist_fit)

    def set_data(self, df: pd.DataFrame, parsed_info: dict[str, Any]):
        self.df = df
        self.parsed_info = parsed_info
        self.col_combo.clear()
        self.col_combo.addItems(list(df.columns))

        self._populate_preview_table(df)

    def validate_params(self) -> tuple:
        if self.df is None:
            return False, "请先导入数据文件"
        col = self.col_combo.currentText()
        if not col:
            return False, "请选择测量列（可点击右侧表格列标题快速选择）"
        try:
            data = pd.to_numeric(self.df[col], errors="coerce").dropna()
        except KeyError:
            return False, f"列 '{col}' 在当前数据表中不存在，请点击右侧表格列标题重新选择"
        if len(data) < 5:
            return False, f"测量列 '{col}' 有效数据不足（仅{len(data)}行），至少需要5行"
        usl = self.usl_spin.value()
        lsl = self.lsl_spin.value()
        if usl <= lsl:
            return False, f"规格限无效：USL ({usl}) 必须大于 LSL ({lsl})"
        return True, ""

    def run_and_display(self) -> dict[str, Any]:
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
            self.result_text.setText(f"▎分析失败\n{e!s}")
            return None

    def run_analysis(self) -> dict[str, Any]:
        from analysis.capability import normal_cap, non_normal_cap, between_within_cap, tolerance_interval
        from analysis.distribution import fitting

        col = self.col_combo.currentText()
        method = self.method_combo.currentText()
        usl = self.usl_spin.value()
        lsl = self.lsl_spin.value()
        target = self.target_spin.value()
        sub_size = self.subgroup_spin.value()
        data = pd.to_numeric(self.df[col], errors="coerce").dropna()

        result = {}
        if method == "正态过程能力":
            result = normal_cap.analyze(data, usl, lsl, target, sub_size)
        elif method.startswith("非正态"):
            if "百分位法" in method:
                m = "percentile"
            else:
                m = "box_cox" if "Box-Cox" in method else "johnson"
            result = non_normal_cap.analyze(data, usl, lsl, m)
        elif method == "组间/组内能力":
            result = between_within_cap.analyze(self.df, col, self.parsed_info.get("subgroup_column", ""), usl, lsl)
        elif method == "公差区间 (正态)":
            ti_method = "two-sided" if "双侧" in self.ti_method_combo.currentText() else "one-sided"
            result = tolerance_interval.tolerance_interval_normal(
                data.values, 
                confidence=self.ti_confidence_spin.value(),
                proportion=self.ti_proportion_spin.value(),
                method=ti_method
            )
        elif method == "公差区间 (非参数)":
            ti_method = "two-sided" if "双侧" in self.ti_method_combo.currentText() else "one-sided"
            result = tolerance_interval.tolerance_interval_nonparam(
                data.values,
                confidence=self.ti_confidence_spin.value(),
                proportion=self.ti_proportion_spin.value(),
                method=ti_method
            )
        elif method == "分布拟合":
            dist_map = {"正态": "normal", "对数正态": "lognormal", "指数": "exponential", "Gamma": "gamma", "Weibull": "weibull"}
            dist_name = dist_map.get(self.dist_combo.currentText(), "normal")
            fit_result = fitting.fit_distribution(data, dist_name)
            gof_result = fitting.goodness_of_fit(data, dist_name)
            result = {**fit_result, **gof_result}

        self.current_result = {
            "analysis_type": method,
            "params": {"column": col, "usl": usl, "lsl": lsl, "target": target, "method": method},
            "result": result,
            "chart_data": result,
        }
        return self.current_result

    def save_specification_standard(self, reason: str = ""):
        """把当前 USL/LSL/目标值记录为规格限标准版本（B3-2）。"""
        ctx = self._project_context
        if ctx is None:
            QMessageBox.warning(self, "无项目上下文", "请先保存/加载一个 .qap 项目")
            return None
        col = self.col_combo.currentText().strip()
        usl, lsl = self.usl_spin.value(), self.lsl_spin.value()
        if not col:
            QMessageBox.warning(self, "缺少对象", "请先选择测量列")
            return None
        if usl <= lsl:
            QMessageBox.warning(self, "规格限无效", f"USL ({usl}) 必须大于 LSL ({lsl})")
            return None
        text = str(reason or "").strip()
        if not text:
            text, ok = QInputDialog.getText(self, "保存规格限标准", "变更原因:")
            if not ok:
                return None
            text = str(text or "").strip()
        if not text:
            QMessageBox.warning(self, "缺少原因", "标准变更必须填写原因")
            return None
        before = len(ctx.standards)
        record = ctx.record_specification(
            col, usl=usl, lsl=lsl, target=self.target_spin.value(),
            change_reason=text, changed_by="user")
        self.standard_object_ref = col
        if len(ctx.standards) == before:
            QMessageBox.information(self, "标准未变化", "与现行版本一致，未产生新版本")
        else:
            QMessageBox.information(
                self, "标准已记录",
                f"{col}: USL={usl} / LSL={lsl} · 版本 {record.record_id}")
        return record

    def display_result(self, analysis: dict[str, Any] | None = None):
        if analysis is None:
            analysis = self.current_result
        result = analysis.get("result", {})
        cap = result.get("capability", {})
        summary = result.get("summary", {})
        normality = result.get("normality", {})

        col = analysis.get("params", {}).get("column", "")
        if self.df is not None and col:
            try:
                raw = pd.to_numeric(self.df[col], errors="coerce").dropna().values
                self._render_chart(result, raw)
            except Exception:
                self._clear_canvas()

        lines = [f"=== {analysis.get('analysis_type', '')} ===\n"]

        if "distribution" in result and "params" in result:
            lines.append(f"分布: {result.get('distribution', '')}")
            lines.append(f"样本量: {result.get('sample_size', '')}")
            params = result.get("params", {})
            if params:
                lines.append("\n【参数估计】")
                for k, v in params.items():
                    lines.append(f"  {k}: {v}")
            data_stats = result.get("data_stats", {})
            if data_stats:
                lines.append("\n【数据统计】")
                for k, v in data_stats.items():
                    lines.append(f"  {k}: {v}")
            tests = result.get("tests", {})
            if tests:
                lines.append("\n【拟合优度检验】")
                for test_name, test_result in tests.items():
                    if isinstance(test_result, dict):
                        stat = test_result.get("statistic", "")
                        pv = test_result.get("p_value", "")
                        interp = test_result.get("interpretation", "")
                        lines.append(f"  {test_name}: 统计量={stat}, p={pv}")
                        if interp:
                            lines.append(f"    {interp}")
        else:
            lines.append("【数据摘要】")
            for k, v in summary.items():
                lines.append(f"  {k}: {v}")

            if normality:
                lines.append("\n【正态性检验】")
                pv = normality.get('p_value', '')
                pv_str = format_pvalue(pv) if isinstance(pv, (int, float)) else str(pv)
                lines.append(f"  p值: {pv_str}, 正态: {normality.get('is_normal', '')}")

            if cap:
                lines.append("\n【过程能力指标】")
                for k, v in cap.items():
                    lines.append(f"  {k}: {v}")
                grade = cap.get("grade", "")
                if grade:
                    lines.append(f"\n  能力等级: {grade}")
                    if "D" in str(grade):
                        lines.append("  过程能力不足，建议改进！")
                    elif "C" in str(grade):
                        lines.append("  过程能力一般，考虑改进。")
                    elif "B" in str(grade):
                        lines.append("  过程能力良好。")
                    else:
                        lines.append("  过程能力优秀！")

        self.result_text.setPlainText("\n".join(lines))
        self.result_text.update()

        table_data = []
        for k, v in summary.items():
            table_data.append([k, str(v)])
        if normality:
            pv = normality.get('p_value', '')
            table_data.append(["正态p值", format_pvalue(pv) if isinstance(pv, (int, float)) else str(pv)])
            table_data.append(["是否正态", str(normality.get('is_normal', ''))])
        if cap:
            for k, v in cap.items():
                table_data.append([k, str(v)])

        self.result_table.setRowCount(len(table_data))
        self.result_table.setColumnCount(2)
        self.result_table.setHorizontalHeaderLabels(["项目", "值"])
        for i, (k, v) in enumerate(table_data):
            self.result_table.setItem(i, 0, QTableWidgetItem(k))
            self.result_table.setItem(i, 1, QTableWidgetItem(v))
        self.result_table.horizontalHeader().setStretchLastSection(True)
        self._switch_result_view(0)

    def _render_chart(self, result: dict, raw_data: np.ndarray):
        try:
            fig = create_capability_chart(result, raw_data, title="过程能力分析", options=self._chart_options)
            self._render_figure(fig)
            self._add_chart_toolbar()
            self.set_chart_type("能力图")
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
        combo_items = [self.col_combo.itemText(i) for i in range(self.col_combo.count())]
        if col_name in combo_items:
            self.col_combo.setCurrentText(col_name)
            self.data_table.selectColumn(index)

    def refresh_texts(self):
        self.title_label.setText(i18n.tr("cap.title"))
        self.run_btn.setText(i18n.tr("cap.run_btn"))
        self.result_label.setText(i18n.tr("cap.result"))
