"""
工作抽样分析页面 — 工时利用率/状态占比/置信区间
"""

from collections import OrderedDict
from typing import Dict, Any, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QGroupBox, QFormLayout,
    QTableWidget, QTableWidgetItem, QSplitter, QHeaderView,
    QStackedWidget, QMessageBox, QInputDialog,
    QColorDialog,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from core.i18n import i18n
from ui.tabs.base_tab import BaseAnalysisTab
from ui.theme import BUTTON_PRIMARY, BUTTON_PRIMARY_STRETCH, BUTTON_SECONDARY, BUTTON_TOGGLE
from analysis.ie.work_sampling import WorkSamplingEngine, BUILTIN_STATUSES


_DEFAULT_STATUSES = OrderedDict(BUILTIN_STATUSES)


class WorkSamplingTab(BaseAnalysisTab):

    statuses_changed = Signal()

    def __init__(self, parent=None):
        self.observations: List[str] = []
        self.statuses = OrderedDict(_DEFAULT_STATUSES)
        self._obs_entries: List[QComboBox] = []
        self._status_checks: List[QPushButton] = []
        super().__init__(parent)
        self._setup_ui()

    def set_raw_data(self, *args, **kwargs):
        pass

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self.title_label = QLabel(i18n.tr("ie.work_sampling.title"))
        self.title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        layout.addWidget(self.title_label)
        layout.addSpacing(4)

        splitter = QSplitter(Qt.Vertical)

        top = QWidget()
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(0, 0, 0, 0)

        config_group = QGroupBox("分析参数")
        config_layout = QFormLayout(config_group)

        self.confidence_combo = QComboBox()
        self.confidence_combo.addItems(["90%", "95%", "99%"])
        self.confidence_combo.setCurrentText("95%")
        config_layout.addRow("置信水平:", self.confidence_combo)

        self.obs_count_label = QLabel("0 条观测")
        config_layout.addRow("观测总数:", self.obs_count_label)

        status_group = QGroupBox("状态定义")
        status_layout = QVBoxLayout(status_group)
        self.status_check_widget = QWidget()
        self.status_check_layout = QVBoxLayout(self.status_check_widget)
        self.status_check_layout.setContentsMargins(0, 0, 0, 0)
        self._build_status_checks()
        status_layout.addWidget(self.status_check_widget)

        btn_add_status = QPushButton("+ 添加自定义状态")
        btn_add_status.setStyleSheet(BUTTON_SECONDARY)
        btn_add_status.clicked.connect(self._add_custom_status)
        status_layout.addWidget(btn_add_status)

        config_layout.addRow(status_group)

        self.btn_analyze = QPushButton(i18n.tr("ie.run_btn"))
        self.btn_analyze.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.btn_analyze.setCursor(Qt.PointingHandCursor)
        self.btn_analyze.setMinimumHeight(44)
        self.btn_analyze.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        self.btn_analyze.clicked.connect(self._on_one_click_analyze)
        config_layout.addRow(self.btn_analyze)

        top_layout.addWidget(config_group)

        obs_group = QGroupBox("观测记录")
        obs_layout = QVBoxLayout(obs_group)
        self.obs_table = QTableWidget()
        self.obs_table.setColumnCount(3)
        self.obs_table.setHorizontalHeaderLabels(["序号", "状态", "备注"])
        self.obs_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.obs_table.setColumnWidth(0, 50)
        self.obs_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.obs_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        obs_layout.addWidget(self.obs_table)

        obs_btn_layout = QHBoxLayout()
        btn_add = QPushButton("+ 添加观测")
        btn_add.setStyleSheet(BUTTON_PRIMARY)
        btn_add.clicked.connect(self._add_observation)
        obs_btn_layout.addWidget(btn_add)
        self.btn_import_obs = QPushButton("导入 Excel 列")
        self.btn_import_obs.setStyleSheet(BUTTON_SECONDARY)
        self.btn_import_obs.clicked.connect(self._import_observations)
        obs_btn_layout.addWidget(self.btn_import_obs)
        btn_del = QPushButton("删除最后一行")
        btn_del.setStyleSheet(BUTTON_TOGGLE)
        btn_del.clicked.connect(self._remove_observation)
        obs_btn_layout.addWidget(btn_del)
        obs_btn_layout.addStretch()
        obs_layout.addLayout(obs_btn_layout)

        top_layout.addWidget(obs_group, 1)

        splitter.addWidget(top)

        bottom = QWidget()
        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.setContentsMargins(0, 0, 0, 0)

        self.result_stack = QStackedWidget()

        self.chart_widget = QWidget()
        self.chart_layout = QVBoxLayout(self.chart_widget)
        self.chart_layout.setContentsMargins(0, 0, 0, 0)
        self.result_stack.addWidget(self.chart_widget)

        self.data_widget = QWidget()
        data_layout = QVBoxLayout(self.data_widget)
        data_layout.setContentsMargins(0, 0, 0, 0)
        self.result_table = QTableWidget()
        self.result_table.setAlternatingRowColors(True)
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        data_layout.addWidget(self.result_table)
        self.result_stack.addWidget(self.data_widget)

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
        self.btn_save_png = QPushButton(i18n.tr("chart_tab.save_png"))
        self.btn_save_png.setFont(QFont("Microsoft YaHei", 11))
        self.btn_save_png.setFixedHeight(30)
        self.btn_save_png.setStyleSheet(BUTTON_SECONDARY)
        self.btn_save_png.clicked.connect(self._on_save_png)
        toggle_row.addWidget(self.btn_save_png)

        bottom_layout.addLayout(toggle_row)
        bottom_layout.addWidget(self.result_stack, 1)

        splitter.addWidget(bottom)
        splitter.setSizes([400, 350])
        layout.addWidget(splitter, 1)
        self._rebuild_obs_rows()

    def _build_status_checks(self):
        # 清除旧按钮
        for btn in self._status_checks:
            self.status_check_layout.removeWidget(btn)
            btn.deleteLater()
        self._status_checks.clear()

        for key, info in self.statuses.items():
            btn = QPushButton()
            btn.setCheckable(True)
            btn.setChecked(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setProperty("status_key", key)
            col = QColor(info["color"])
            # 选中时纯色填充，未选中时暗底+细色框
            btn.setStyleSheet(
                f"QPushButton {{"
                f"background-color: {col.name()}; color: #fff;"
                f"font-weight: bold; font-size: 12px;"
                f"border: none; border-radius: 6px; padding: 6px 12px;"
                f"text-align: left;"
                f"}}"
                f"QPushButton:checked {{"
                f"background-color: {col.name()}; color: #fff;"
                f"}}"
                f"QPushButton:!checked {{"
                f"background-color: #2a2a36; color: #fff;"
                f"border: 2px solid {col.name()};"
                f"}}"
                f"QPushButton:hover {{"
                f"background-color: {col.darker(120).name()}; color: #fff;"
                f"}}"
            )
            btn.setText(info['label'])
            btn.clicked.connect(lambda checked, b=btn: self._on_status_toggle(b))
            self._status_checks.append(btn)
            self.status_check_layout.addWidget(btn)

    def _on_status_toggle(self, btn: QPushButton):
        """状态切换时刷新观测下拉选项"""
        self._rebuild_obs_rows()

    def _get_active_statuses(self) -> OrderedDict:
        active = OrderedDict()
        for btn in self._status_checks:
            if btn.isChecked():
                key = btn.property("status_key")
                if key in self.statuses:
                    active[key] = self.statuses[key]
        return active if active else self.statuses

    def _add_custom_status(self):
        label, ok = QInputDialog.getText(self, "添加自定义状态", "状态名称:")
        if not ok or not label.strip():
            return
        label = label.strip()
        key = label.lower().replace(" ", "_")
        if key in self.statuses:
            QMessageBox.warning(self, "已存在", f"状态 '{label}' 已存在")
            return
        color = QColorDialog.getColor(parent=self, title=f"选择 '{label}' 的颜色")
        self.statuses[key] = {
            "label": label,
            "color": color.name() if color.isValid() else "#9E9E9E",
            "productive": False,
        }
        self._build_status_checks()
        self._rebuild_obs_rows()

    def _add_observation(self):
        self.observations.append("")
        self._rebuild_obs_rows()
        self.obs_count_label.setText(f"{len(self.observations)} 条观测")

    def _remove_observation(self):
        if self.observations:
            self.observations.pop()
            self._rebuild_obs_rows()
            self.obs_count_label.setText(f"{len(self.observations)} 条观测")

    def _import_observations(self):
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "导入观测数据", "", "Excel (*.xlsx *.xls)"
        )
        if not path:
            return
        try:
            from core.excel_utils import read_excel_auto
            df = read_excel_auto(path, dtype=str)
            if df.empty:
                QMessageBox.warning(self, "空文件", "Excel 文件中无数据")
                return
            col = df.columns[0]
            new_obs = df[col].dropna().astype(str).tolist()
            self.observations.extend(new_obs)
            self._rebuild_obs_rows()
            self.obs_count_label.setText(f"{len(self.observations)} 条观测")
        except Exception as e:
            QMessageBox.critical(self, "导入失败", str(e))

    def _rebuild_obs_rows(self):
        self.obs_table.setRowCount(len(self.observations))
        statuses = self._get_active_statuses()
        labels = [info["label"] for info in statuses.values()]
        for i, obs in enumerate(self.observations):
            self.obs_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            combo = QComboBox()
            combo.addItems(labels)
            if obs in labels:
                combo.setCurrentText(obs)
            else:
                combo.setCurrentIndex(0)
            combo.currentTextChanged.connect(lambda txt, idx=i: self._on_obs_changed(idx, txt))
            self.obs_table.setCellWidget(i, 1, combo)
            self.obs_table.setItem(i, 2, QTableWidgetItem(""))

    def _on_obs_changed(self, idx: int, text: str):
        if idx < len(self.observations):
            self.observations[idx] = text

    def _on_one_click_analyze(self):
        self._sync_observations()
        obs = [o for o in self.observations if o]
        if len(obs) < 5:
            QMessageBox.warning(self, "数据不足", "至少需要 5 条有效观测")
            return

        conf_text = self.confidence_combo.currentText()
        confidence = {"90%": 0.90, "95%": 0.95, "99%": 0.99}.get(conf_text, 0.95)
        result = WorkSamplingEngine.analyze(obs, confidence)
        self.current_result = result
        self._display_result(result)
        self.analysis_completed.emit()

    def _sync_observations(self):
        self.observations = []
        for i in range(self.obs_table.rowCount()):
            w = self.obs_table.cellWidget(i, 1)
            if w and isinstance(w, QComboBox):
                self.observations.append(w.currentText())
            else:
                item = self.obs_table.item(i, 1)
                self.observations.append(item.text() if item else "")

    def _display_result(self, result: Dict[str, Any]):
        if not result.get("valid"):
            return

        ci_data = result.get("confidence_intervals", {})
        util = result.get("utilization", {})

        headers = ["状态", "观测数", "占比(%)", "CI 下限(%)", "CI 上限(%)", "标准误"]
        self.result_table.setColumnCount(len(headers))
        self.result_table.setHorizontalHeaderLabels(headers)
        rows = list(ci_data.items())
        self.result_table.setRowCount(len(rows) + 1)
        for i, (key, info) in enumerate(rows):
            vals = [info["label"], str(info.get("count",
                     result.get("ratios", {}).get("ratios", {}).get(key, {}).get("count", 0))),
                    f"{info['pct']:.1f}", f"{info['ci_low_pct']:.1f}",
                    f"{info['ci_high_pct']:.1f}", f"{info['se']:.3f}"]
            for j, v in enumerate(vals):
                self.result_table.setItem(i, j, QTableWidgetItem(v))

        total_row = result.get("ratios", {}).get("_total", 0)
        footer = [f"合计 (n={total_row})", str(total_row), "100.0", "", "", ""]
        for j, v in enumerate(footer):
            self.result_table.setItem(len(rows), j, QTableWidgetItem(v))
        self.result_table.resizeColumnsToContents()

        self._draw_chart(result, util)

    def _draw_chart(self, result: Dict[str, Any], util: Dict[str, Any]):
        self._clear_canvas()
        fig = Figure(figsize=(10, 4.5), dpi=100)
        fig.subplots_adjust(left=0.08, right=0.95, top=0.90, bottom=0.10, wspace=0.35)

        chart = result.get("chart_data", {})
        labels = chart.get("labels", [])
        values = chart.get("values", [])
        colors = chart.get("colors", [])

        ax1 = fig.add_subplot(1, 2, 1)
        wedges, texts, autotexts = ax1.pie(
            values, labels=labels, colors=colors, autopct="%1.1f%%",
            startangle=90, pctdistance=0.75,
        )
        for t in autotexts:
            t.set_fontsize(8)
        util_pct = util.get("productive_pct", 0)
        ax1.set_title(f"利用率 {util_pct:.1f}%", fontsize=11, fontweight="bold")

        ax2 = fig.add_subplot(1, 2, 2)
        y_pos = range(len(labels))
        bars = ax2.barh(y_pos, values, color=colors, alpha=0.8, edgecolor="#333", linewidth=0.5)
        ax2.set_yticks(y_pos)
        ax2.set_yticklabels(labels, fontsize=8)
        ax2.invert_yaxis()
        ax2.set_xlabel("占比 (%)", fontsize=8)
        for bar, val in zip(bars, values):
            ax2.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                     f"{val:.1f}%", va="center", fontsize=8)

        ci = result.get("confidence_intervals", {})
        for i, (key, info) in enumerate(ci.items()):
            x_low = info["ci_low_pct"]
            x_high = info["ci_high_pct"]
            ax2.hlines(i, x_low, x_high, color="#333", linewidth=2)
            ax2.plot(x_low, i, "k|", markersize=8)
            ax2.plot(x_high, i, "k|", markersize=8)

        ax2.set_title(f"95% CI (n={result.get('ratios',{}).get('_total',0)})", fontsize=9)

        self.current_figure = fig
        self.canvas = FigureCanvasQTAgg(fig)
        self.chart_layout.addWidget(self.canvas)
        self._switch_result_view(0)
