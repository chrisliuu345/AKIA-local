"""
SPC 控制图分析页 — 含图表嵌入
"""

from typing import Dict, Any
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QDoubleSpinBox, QGroupBox, QFormLayout,
    QTableWidget, QTableWidgetItem, QTextEdit, QSplitter, QHeaderView,
    QFrame, QStackedWidget, QScrollArea, QCheckBox, QMessageBox, QListWidget, QListWidgetItem,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from analysis.spc import xbar_r, xbar_s, imr, p_chart, np_chart, c_chart, u_chart, cusum, ewma, laney, hotelling
from output.chart_engine import create_control_chart
from core.i18n import i18n
from ui.tabs.base_tab import BaseAnalysisTab
from ui.theme import BUTTON_SECONDARY, BUTTON_TOGGLE, BUTTON_PRIMARY_STRETCH
from ui.font_config import get_ui_font


class SPCTab(BaseAnalysisTab):

    def __init__(self, parent=None):
        self._project_context = None
        super().__init__(parent)
        self._setup_ui()

    def set_project_context(self, ctx):
        self._project_context = ctx

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self.title_label = QLabel(i18n.tr("spc.title"))
        self.title_label.setFont(QFont(get_ui_font(), 18, QFont.Bold))
        layout.addWidget(self.title_label)
        layout.addSpacing(4)

        splitter = QSplitter(Qt.Vertical)

        top = QWidget()
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(0, 0, 0, 0)

        config_group = QGroupBox(i18n.tr("spc.config"))
        config_layout = QFormLayout(config_group)

        self.chart_type_combo = QComboBox()
        self.chart_type_combo.addItems(["XBar-R", "XBar-S", "I-MR", "P Chart", "NP Chart", "C Chart", "U Chart", "CUSUM", "EWMA", "Laney P'", "Laney U'", "Hotelling T²"])
        config_layout.addRow(i18n.tr("spc.chart_type"), self.chart_type_combo)

        self.col_combo = QComboBox()
        config_layout.addRow(i18n.tr("spc.measure_col"), self.col_combo)

        self.sheet_combo = QComboBox()
        self.sheet_combo.setMinimumWidth(140)
        self.sheet_combo.currentTextChanged.connect(self._on_sheet_changed)
        config_layout.addRow("Sheet:", self.sheet_combo)

        self.subgroup_spin = QSpinBox()
        self.subgroup_spin.setRange(1, 25)
        self.subgroup_spin.setValue(5)
        self.row_subgroup = QWidget()
        sg_layout = QHBoxLayout(self.row_subgroup)
        sg_layout.setContentsMargins(0, 0, 0, 0)
        sg_layout.addWidget(QLabel(i18n.tr("spc.subgroup_size")))
        sg_layout.addWidget(self.subgroup_spin)
        config_layout.addRow(self.row_subgroup)

        self.usl_spin = QDoubleSpinBox()
        self.usl_spin.setRange(-1e9, 1e9)
        self.usl_spin.setDecimals(4)
        self.row_usl = QWidget()
        us_layout = QHBoxLayout(self.row_usl)
        us_layout.setContentsMargins(0, 0, 0, 0)
        us_layout.addWidget(QLabel(i18n.tr("spc.usl")))
        us_layout.addWidget(self.usl_spin)
        config_layout.addRow(self.row_usl)

        self.lsl_spin = QDoubleSpinBox()
        self.lsl_spin.setRange(-1e9, 1e9)
        self.lsl_spin.setDecimals(4)
        self.row_lsl = QWidget()
        ls_layout = QHBoxLayout(self.row_lsl)
        ls_layout.setContentsMargins(0, 0, 0, 0)
        ls_layout.addWidget(QLabel(i18n.tr("spc.lsl")))
        ls_layout.addWidget(self.lsl_spin)
        config_layout.addRow(self.row_lsl)

        # W42: 规格限启用开关 — 默认关闭，避免 0.0 被误当作有效规格
        self.spec_check = QCheckBox("启用规格限 (USL/LSL)")
        self.spec_check.setToolTip("勾选后在控制图上显示规格限；未勾选时 USL/LSL 值不参与分析")
        self.spec_check.stateChanged.connect(self._on_spec_toggled)
        config_layout.addRow(self.spec_check)
        self.row_usl.setVisible(False)
        self.row_lsl.setVisible(False)

        self.cusum_k_spin = QDoubleSpinBox()
        self.cusum_k_spin.setRange(0.1, 10)
        self.cusum_k_spin.setValue(0.5)
        self.cusum_k_spin.setSingleStep(0.1)
        self.cusum_h_spin = QDoubleSpinBox()
        self.cusum_h_spin.setRange(1, 20)
        self.cusum_h_spin.setValue(5.0)
        self.cusum_h_spin.setSingleStep(0.5)
        self.row_cusum = QWidget()
        self.row_cusum.setVisible(False)
        cusum_layout = QHBoxLayout(self.row_cusum)
        cusum_layout.setContentsMargins(0, 0, 0, 0)
        cusum_layout.addWidget(QLabel("CUSUM k:"))
        cusum_layout.addWidget(self.cusum_k_spin)
        cusum_layout.addWidget(QLabel("  h:"))
        cusum_layout.addWidget(self.cusum_h_spin)
        config_layout.addRow(self.row_cusum)

        self.ewma_lam_spin = QDoubleSpinBox()
        self.ewma_lam_spin.setRange(0.01, 1.0)
        self.ewma_lam_spin.setValue(0.2)
        self.ewma_lam_spin.setSingleStep(0.05)
        self.ewma_L_spin = QDoubleSpinBox()
        self.ewma_L_spin.setRange(1.0, 5.0)
        self.ewma_L_spin.setValue(3.0)
        self.ewma_L_spin.setSingleStep(0.5)
        self.row_ewma = QWidget()
        self.row_ewma.setVisible(False)
        ewma_layout = QHBoxLayout(self.row_ewma)
        ewma_layout.setContentsMargins(0, 0, 0, 0)
        ewma_layout.addWidget(QLabel("EWMA \u03bb:"))
        ewma_layout.addWidget(self.ewma_lam_spin)
        ewma_layout.addWidget(QLabel("  L:"))
        ewma_layout.addWidget(self.ewma_L_spin)
        config_layout.addRow(self.row_ewma)

        self.laney_alpha_spin = QDoubleSpinBox()
        self.laney_alpha_spin.setRange(0.0001, 0.1)
        self.laney_alpha_spin.setValue(0.0027)
        self.laney_alpha_spin.setSingleStep(0.0001)
        self.laney_alpha_spin.setDecimals(4)
        self.row_laney = QWidget()
        self.row_laney.setVisible(False)
        laney_layout = QHBoxLayout(self.row_laney)
        laney_layout.setContentsMargins(0, 0, 0, 0)
        laney_layout.addWidget(QLabel("Laney \u03b1:"))
        laney_layout.addWidget(self.laney_alpha_spin)
        config_layout.addRow(self.row_laney)

        self.hotelling_cols_list = QListWidget()
        self.hotelling_cols_list.setMaximumHeight(120)
        self.hotelling_cols_list.setSelectionMode(QListWidget.NoSelection)
        self.hotelling_select_all = QCheckBox("全选")
        self.hotelling_select_all.stateChanged.connect(self._on_hotelling_select_all)
        self.row_hotelling = QWidget()
        self.row_hotelling.setVisible(False)
        hotelling_layout = QHBoxLayout(self.row_hotelling)
        hotelling_layout.setContentsMargins(0, 0, 0, 0)
        hotelling_layout.addWidget(QLabel("分析变量:"))
        hotelling_layout.addWidget(self.hotelling_cols_list)
        hotelling_layout.addWidget(self.hotelling_select_all)
        config_layout.addRow(self.row_hotelling)

        self.chart_type_combo.currentTextChanged.connect(self._on_chart_type_changed)

        self.run_btn = QPushButton(i18n.tr("spc.run_btn"))
        self.run_btn.setFont(QFont(get_ui_font(), 12, QFont.Bold))
        self.run_btn.setMinimumHeight(44)
        self.run_btn.setCursor(Qt.PointingHandCursor)
        self.run_btn.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.run_btn.clicked.connect(self.run_and_display)
        config_layout.addRow(self.run_btn)

        self.save_png_btn = QPushButton(i18n.tr("spc.save_png"))
        self.save_png_btn.setFont(QFont(get_ui_font(), 12, QFont.Bold))
        self.save_png_btn.setMinimumHeight(40)
        self.save_png_btn.setCursor(Qt.PointingHandCursor)
        self.save_png_btn.setStyleSheet(BUTTON_SECONDARY)
        self.save_png_btn.clicked.connect(self._on_save_png)
        config_layout.addRow(self.save_png_btn)

        self.root_cause_btn = QPushButton(i18n.tr("spc.root_cause"))
        self.root_cause_btn.setFont(QFont(get_ui_font(), 12, QFont.Bold))
        self.root_cause_btn.setMinimumHeight(40)
        self.root_cause_btn.setCursor(Qt.PointingHandCursor)
        self.root_cause_btn.setStyleSheet(BUTTON_SECONDARY)
        self.root_cause_btn.setEnabled(False)
        self.root_cause_btn.setToolTip("运行分析且存在判异点后可用")
        self.root_cause_btn.clicked.connect(self._on_root_cause)
        config_layout.addRow(self.root_cause_btn)

        self.export_btn = QPushButton(i18n.tr("spc.export_btn"))
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

        self.result_label = QLabel(i18n.tr("spc.result"))
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

        # 图表滚动容器 — 大图可水平滚动
        self.chart_scroll = QScrollArea()
        self.chart_scroll.setWidgetResizable(True)
        self.chart_scroll.setFrameShape(QFrame.NoFrame)
        self.chart_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.chart_scroll.setMinimumHeight(300)

        self.chart_container = QWidget()
        self.chart_layout = QVBoxLayout(self.chart_container)
        self.chart_layout.setContentsMargins(0, 0, 0, 0)
        self.chart_scroll.setWidget(self.chart_container)
        self.result_stack.addWidget(self.chart_scroll)

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
        self.col_combo.clear()
        self.col_combo.addItems(list(df.columns))
        # Hotelling T² 多变量列选择器
        self.hotelling_cols_list.clear()
        for col in df.columns:
            item = QListWidgetItem(col)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.hotelling_cols_list.addItem(item)
        self._populate_preview_table(df)

    def import_from_cp(self, spc_items: list):
        """从控制计划导入 SPC 监控清单"""
        self._cp_monitoring_list = spc_items

    def _on_chart_type_changed(self, chart_type: str):
        is_cusum = chart_type == "CUSUM"
        is_ewma = chart_type == "EWMA"
        is_laney = chart_type in ("Laney P'", "Laney U'")
        is_hotelling = chart_type == "Hotelling T²"
        is_std = not is_cusum and not is_ewma and not is_laney and not is_hotelling
        self.row_subgroup.setVisible(is_std)
        self._update_spec_visibility()
        self.row_cusum.setVisible(is_cusum)
        self.row_ewma.setVisible(is_ewma)
        self.row_laney.setVisible(is_laney)
        self.row_hotelling.setVisible(is_hotelling)

    def _on_spec_toggled(self, state):
        """W42: 规格限复选框切换"""
        self._update_spec_visibility()

    def _update_spec_visibility(self):
        """根据图表类型和复选框状态决定规格限行可见性"""
        chart_type = self.chart_type_combo.currentText()
        is_std = chart_type not in ("CUSUM", "EWMA", "Laney P'", "Laney U'")
        show = is_std and self.spec_check.isChecked()
        self.row_usl.setVisible(show)
        self.row_lsl.setVisible(show)

    def validate_params(self) -> tuple:
        if self.df is None:
            return False, "请先导入数据文件"
        chart_type = self.chart_type_combo.currentText()
        
        # Hotelling T² 使用多变量列选择器
        if chart_type == "Hotelling T²":
            selected_cols = self._get_hotelling_columns()
            if len(selected_cols) < 2:
                return False, "Hotelling T² 需要至少选择 2 个分析变量"
            return True, ""
        
        col = self.col_combo.currentText()
        if not col:
            return False, "请选择测量列（可点击右侧表格列标题快速选择）"
        try:
            data = pd.to_numeric(self.df[col], errors="coerce").dropna()
        except KeyError:
            return False, f"列 '{col}' 在当前数据表中不存在，请点击右侧表格列标题重新选择"
        if len(data) < 2:
            return False, f"测量列 '{col}' 有效数据不足（仅{len(data)}行），至少需要2行"
        if chart_type in ("XBar-R", "XBar-S", "NP Chart"):
            subgroup_size = self.subgroup_spin.value()
            if len(data) < subgroup_size * 2:
                return False, f"子组分析需要至少 {subgroup_size * 2} 行数据，当前有效数据 {len(data)} 行"
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

    def _get_hotelling_columns(self) -> list:
        """获取 Hotelling T² 选中的列"""
        selected = []
        for i in range(self.hotelling_cols_list.count()):
            item = self.hotelling_cols_list.item(i)
            if item.checkState() == Qt.Checked:
                selected.append(item.text())
        return selected

    def _on_hotelling_select_all(self, state):
        """全选/全不选 Hotelling 列"""
        check_state = Qt.Checked if state == 2 else Qt.Unchecked
        for i in range(self.hotelling_cols_list.count()):
            item = self.hotelling_cols_list.item(i)
            item.setCheckState(check_state)

    def run_analysis(self) -> Dict[str, Any]:
        col = self.col_combo.currentText()
        chart_type = self.chart_type_combo.currentText()
        subgroup_size = self.subgroup_spin.value()

        result = {}
        if chart_type == "Hotelling T²":
            selected_cols = self._get_hotelling_columns()
            result = hotelling.analyze(self.df, selected_cols)
        else:
            data = pd.to_numeric(self.df[col], errors="coerce").dropna()
            if chart_type == "XBar-R":
                result = xbar_r.analyze(data, subgroup_size)
            elif chart_type == "XBar-S":
                result = xbar_s.analyze(data, subgroup_size)
            elif chart_type == "I-MR":
                result = imr.analyze(data)
            elif chart_type == "P Chart":
                result = p_chart.analyze(data, pd.Series([subgroup_size] * len(data)))
            elif chart_type == "NP Chart":
                result = np_chart.analyze(data, subgroup_size)
            elif chart_type == "C Chart":
                result = c_chart.analyze(data)
            elif chart_type == "U Chart":
                result = u_chart.analyze(data, pd.Series([subgroup_size] * len(data)))
            elif chart_type == "CUSUM":
                result = cusum.analyze(data, k=self.cusum_k_spin.value(), h=self.cusum_h_spin.value())
            elif chart_type == "EWMA":
                result = ewma.analyze(data, lam=self.ewma_lam_spin.value(), L=self.ewma_L_spin.value())
            elif chart_type == "Laney P'":
                sample_sizes = pd.Series([subgroup_size] * len(data))
                result = laney.laney_p_prime(data.values, sample_sizes.values, alpha=self.laney_alpha_spin.value())
            elif chart_type == "Laney U'":
                sample_sizes = pd.Series([subgroup_size] * len(data))
                result = laney.laney_u_prime(data.values, sample_sizes.values, alpha=self.laney_alpha_spin.value())

        self.current_result = {
            "analysis_type": chart_type,
            "params": {"column": col, "subgroup_size": subgroup_size, "chart_type": chart_type},
            "result": result,
            "chart_data": result,
        }
        # W42: 规格限 — 仅在启用时传入，避免默认 0.0 被误用
        if self.spec_check.isChecked():
            result["usl"] = self.usl_spin.value()
            result["lsl"] = self.lsl_spin.value()

        from config.settings import get_setting
        if not get_setting("nelson_rules_enabled", True):
            for chart_key in ("xbar_chart", "r_chart", "s_chart", "i_chart", "mr_chart",
                              "p_chart", "np_chart", "c_chart", "u_chart",
                              "cusum_chart", "ewma_chart", "laney_p_chart", "laney_u_chart"):
                chart = result.get(chart_key, {})
                if isinstance(chart, dict):
                    chart["violations"] = []
        return self.current_result

    def display_result(self, analysis: Dict[str, Any] = None):
        if analysis is None:
            analysis = self.current_result
        result = analysis.get("result", {})
        chart_type = analysis.get("analysis_type", "")

        self._render_chart(result, chart_type)

        lines = [f"=== {chart_type} 分析结果 ==="]
        summary = result.get("summary", {})
        if summary:
            lines.append("")
            lines.append("【摘要】")
            for k, v in summary.items():
                lines.append(f"  {k}: {v}")

        table_headers = ["项目", "值"]
        table_data = []

        if chart_type == "Hotelling T²":
            t2_chart = result.get("t2_chart", {})
            lines.append(f"\n【T² 控制图】")
            lines.append(f"  变量数: {result.get('num_variables', '')}")
            lines.append(f"  样本数: {result.get('num_samples', '')}")
            lines.append(f"  CL: {t2_chart.get('cl', '')}")
            lines.append(f"  UCL: {t2_chart.get('ucl', '')}")
            violations = t2_chart.get("violations", [])
            if violations:
                lines.append(f"\n判异点: {len(violations)} 个")
                for v in violations[:10]:
                    lines.append(f"  点{v.get('point', '')}: {v.get('desc', '')}")
            hotelling_test = result.get("hotelling_test", {})
            if hotelling_test:
                lines.append(f"\n【多元正态性检验】")
                lines.append(f"  偏度统计量: {hotelling_test.get('skewness_statistic', '')}")
                lines.append(f"  峰度统计量: {hotelling_test.get('kurtosis_statistic', '')}")
                lines.append(f"  结论: {hotelling_test.get('interpretation', '')}")
            table_data.append(["变量数", str(result.get('num_variables', ''))])
            table_data.append(["样本数", str(result.get('num_samples', ''))])
            table_data.append(["T² UCL", str(t2_chart.get('ucl', ''))])

        elif chart_type in ("XBar-R", "XBar-S", "I-MR"):
            xbar_key = "xbar_chart" if "xbar_chart" in result else "i_chart"
            chart = result.get(xbar_key, result)
            cl, ucl, lcl = chart.get('cl', ''), chart.get('ucl', ''), chart.get('lcl', '')
            lines.append(f"\n【主控制图】CL={cl}, UCL={ucl}, LCL={lcl}")
            table_data.append(["CL (中心线)", str(cl)])
            table_data.append(["UCL (上控制限)", str(ucl)])
            table_data.append(["LCL (下控制限)", str(lcl)])
            r_key = "r_chart" if "r_chart" in result else "mr_chart"
            r_chart = result.get(r_key, {})
            if r_chart:
                r_cl, r_ucl, r_lcl = r_chart.get('cl', ''), r_chart.get('ucl', ''), r_chart.get('lcl', '')
                lines.append(f"\n【极差控制图】CL={r_cl}, UCL={r_ucl}, LCL={r_lcl}")
                table_data.append(["R-CL (极差中心线)", str(r_cl)])
                table_data.append(["R-UCL (极差上控制限)", str(r_ucl)])
                table_data.append(["R-LCL (极差下控制限)", str(r_lcl)])
            violations = chart.get("violations", [])
            if violations:
                lines.append(f"\n判异点: {len(violations)} 个")
                for v in violations[:10]:
                    lines.append(f"  点{v.get('point', '')}: {v.get('desc', v.get('type', ''))}")

        elif "Chart" in chart_type or chart_type in ("CUSUM", "EWMA"):
            chart_key = {"CUSUM": "cusum_chart", "EWMA": "ewma_chart"}.get(chart_type, chart_type.lower() + "_chart")
            chart = result.get(chart_key, result)
            cl = chart.get("cl", "")
            ucl = chart.get("ucl", "")
            lcl = chart.get("lcl", "")
            if isinstance(ucl, list):
                ucl = ucl[-1] if ucl else ""
            if isinstance(lcl, list):
                lcl = lcl[-1] if lcl else ""
            lines.append(f"\nCL={cl}, UCL={ucl}, LCL={lcl}")
            table_data.append(["CL (中心线)", str(cl)])
            table_data.append(["UCL (上控制限)", str(ucl)])
            table_data.append(["LCL (下控制限)", str(lcl)])
            vios = result.get("violations", chart.get("violations", []))
            if vios:
                lines.append(f"\n判异点: {len(vios)} 个")
                for v in vios[:10]:
                    lines.append(f"  点{v.get('point', '')}: {v.get('desc', v.get('type', ''))}")

        self.result_text.setPlainText("\n".join(lines))
        self.result_text.update()

        self.result_table.setRowCount(len(table_data))
        self.result_table.setColumnCount(2)
        self.result_table.setHorizontalHeaderLabels(table_headers)
        for i, (k, v) in enumerate(table_data):
            self.result_table.setItem(i, 0, QTableWidgetItem(k))
            self.result_table.setItem(i, 1, QTableWidgetItem(v))
        self.result_table.horizontalHeader().setStretchLastSection(True)

        self.root_cause_btn.setEnabled(bool(self._extract_violations(result)))

        self._switch_result_view(0)

    def _extract_violations(self, result: Dict[str, Any]) -> list:
        # Hotelling T² 格式
        t2_chart = result.get("t2_chart", {})
        if t2_chart and t2_chart.get("violations"):
            return t2_chart["violations"]
        for key in ("xbar_chart", "r_chart", "s_chart", "i_chart", "mr_chart",
                    "p_chart", "np_chart", "c_chart", "u_chart",
                    "cusum_chart", "ewma_chart"):
            chart = result.get(key)
            if isinstance(chart, dict) and chart.get("violations"):
                return chart["violations"]
        # Laney P'/U' 格式: {"n_violations": N, "violation_indices": [...]}
        for key in ("laney_p_chart", "laney_u_chart"):
            chart = result.get(key)
            if isinstance(chart, dict):
                indices = chart.get("violation_indices", [])
                if indices:
                    return [{"point": i, "rule": "Laney", "desc": f"点 {i} 越界"} for i in indices]
        v = result.get("violations", [])
        return v if isinstance(v, list) else []

    def _on_root_cause(self):
        if self.df is None or self.current_result is None:
            QMessageBox.information(self, "根因分析", "请先运行 SPC 分析")
            return
        col = self.col_combo.currentText()
        result = self.current_result.get("result", {})
        violations = self._extract_violations(result)
        if not violations:
            QMessageBox.information(self, "根因分析", "当前分析结果无异常点，无法进行根因分析")
            return
        try:
            from ui.dialogs.root_cause_dialog import RootCauseDialog
            dlg = RootCauseDialog(
                self.df, col, violations,
                subgroup_size=self.subgroup_spin.value(),
                chart_type=self.chart_type_combo.currentText(),
                parent=self,
            )
            dlg.exec()
        except Exception as e:
            QMessageBox.warning(self, "根因分析", f"分析失败: {e}")

    def _render_chart(self, result: Dict, chart_type: str):
        self._clear_canvas()
        try:
            chart_data = result if result else {"chart_type": chart_type, "data": [], "cl": 0}
            chart_data.setdefault("chart_type", chart_type)
            fig = create_control_chart(chart_data, title=f"{chart_type} 控制图")
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

    def refresh_texts(self):
        self.title_label.setText(i18n.tr("spc.title"))
        self.run_btn.setText(i18n.tr("spc.run_btn"))
        self.result_label.setText(i18n.tr("spc.result"))
        self.root_cause_btn.setText(i18n.tr("spc.root_cause"))

    def _on_header_clicked(self, index: int):
        item = self.data_table.horizontalHeaderItem(index)
        if item is None:
            return
        col_name = item.text()
        combo_items = [self.col_combo.itemText(i) for i in range(self.col_combo.count())]
        if col_name in combo_items:
            self.col_combo.setCurrentText(col_name)
            self.data_table.selectColumn(index)
