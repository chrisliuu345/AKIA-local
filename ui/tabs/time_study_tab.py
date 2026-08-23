"""
工时研究分析页面 — 秒表时间研究，一键自动分析
"""

from typing import Dict, Any, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QDoubleSpinBox, QGroupBox, QFormLayout,
    QTableWidget, QTableWidgetItem, QSplitter, QHeaderView,
    QStackedWidget, QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from core.i18n import i18n
from ui.tabs.base_tab import BaseAnalysisTab
from ui.theme import BUTTON_PRIMARY_STRETCH, BUTTON_SECONDARY, BUTTON_TOGGLE
from core.data_objects import TimeObservation
from analysis.ie.time_study import TimeStudyEngine


class TimeStudyTab(BaseAnalysisTab):

    def __init__(self, parent=None):
        self.ie_observations: List[TimeObservation] = []
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self.title_label = QLabel(i18n.tr("ie.time_study.title"))
        self.title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        layout.addWidget(self.title_label)
        layout.addSpacing(4)

        splitter = QSplitter(Qt.Vertical)

        top = QWidget()
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(0, 0, 0, 0)

        config_group = QGroupBox("分析参数")
        config_layout = QFormLayout(config_group)

        self.rating_spin = QDoubleSpinBox()
        self.rating_spin.setRange(0.5, 1.5)
        self.rating_spin.setValue(1.0)
        self.rating_spin.setDecimals(2)
        self.rating_spin.setSingleStep(0.05)
        self.rating_spin.setSuffix(" (0.7-1.3)")
        config_layout.addRow("评定系数:", self.rating_spin)

        self.allowance_spin = QDoubleSpinBox()
        self.allowance_spin.setRange(0, 30)
        self.allowance_spin.setValue(12.0)
        self.allowance_spin.setDecimals(1)
        self.allowance_spin.setSingleStep(0.5)
        self.allowance_spin.setSuffix(" %")
        config_layout.addRow("宽放率:", self.allowance_spin)

        self.takt_spin = QDoubleSpinBox()
        self.takt_spin.setRange(0.001, 1e7)
        self.takt_spin.setValue(0)
        self.takt_spin.setDecimals(1)
        self.takt_spin.setSuffix(" s")
        self.takt_spin.setSpecialValueText(" 不启用")
        config_layout.addRow("节拍时间:", self.takt_spin)

        self.confidence_combo = QComboBox()
        self.confidence_combo.addItems(["90%", "95%", "99%"])
        self.confidence_combo.setCurrentText("95%")
        config_layout.addRow("置信水平:", self.confidence_combo)

        self.process_filter = QComboBox()
        self.process_filter.addItem("全部工序")
        config_layout.addRow("工序筛选:", self.process_filter)

        self.btn_analyze = QPushButton(i18n.tr("ie.run_btn"))
        self.btn_analyze.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.btn_analyze.setCursor(Qt.PointingHandCursor)
        self.btn_analyze.setMinimumHeight(44)
        self.btn_analyze.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        self.btn_analyze.clicked.connect(self._on_one_click_analyze)
        config_layout.addRow(self.btn_analyze)

        top_layout.addWidget(config_group)

        preview_group = QGroupBox("数据预览")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_table = QTableWidget()
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        preview_layout.addWidget(self.preview_table)
        self.preview_label = QLabel("")
        self.preview_label.setStyleSheet("color: #888; font-size: 11px;")
        preview_layout.addWidget(self.preview_label)
        top_layout.addWidget(preview_group, 1)

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

        splitter.setSizes([300, 500])
        layout.addWidget(splitter, 1)

    def set_raw_data(self, *args, **kwargs):
        pass

    def set_ie_data(self, observations: List[TimeObservation]):
        self.ie_observations = observations
        self._populate_preview(observations)
        pids = sorted(set(o.process_id for o in observations if o.process_id))
        self.process_filter.blockSignals(True)
        self.process_filter.clear()
        self.process_filter.addItem("全部工序")
        self.process_filter.addItems(pids)
        self.process_filter.blockSignals(False)

    def _populate_preview(self, observations: List[TimeObservation]):
        cols = ["工序编号", "作业员", "循环", "观测时间(s)"]
        self.preview_table.setColumnCount(len(cols))
        self.preview_table.setHorizontalHeaderLabels(cols)
        rows = min(50, len(observations))
        self.preview_table.setRowCount(rows)
        for i in range(rows):
            o = observations[i]
            for j, val in enumerate([o.process_id, o.operator, str(o.cycle), f"{o.observation_time:.2f}"]):
                self.preview_table.setItem(i, j, QTableWidgetItem(val))
        total = len(observations)
        unique_ops = len(set(o.operator for o in observations if o.operator))
        self.preview_label.setText(f"观测: {total} 条 | 作业员: {unique_ops} 人")

    def _on_one_click_analyze(self):
        if not self.ie_observations:
            QMessageBox.warning(self, "无数据", "请先导入包含时间观测数据的 Excel 文件")
            return

        obs = self.ie_observations
        filt = self.process_filter.currentText()
        if filt != "全部工序":
            obs = [o for o in obs if o.process_id == filt]
        if not obs:
            QMessageBox.warning(self, "无数据", f"工序 '{filt}' 没有观测数据")
            return

        rating = self.rating_spin.value()
        allowance = self.allowance_spin.value()
        takt = self.takt_spin.value() if self.takt_spin.value() > 0 else None
        conf_text = self.confidence_combo.currentText()
        confidence = {"90%": 0.90, "95%": 0.95, "99%": 0.99}.get(conf_text, 0.95)

        result = TimeStudyEngine.analyze(obs, rating, allowance, takt, confidence)
        # W59-W62: 标准化 current_result 三件套
        self.current_result = {
            "analysis_type": "时间研究",
            "params": {"rating": rating, "allowance": allowance, "confidence": confidence},
            "result": result.get("result", result) if isinstance(result, dict) else result,
        }
        self._display_result(result)
        self.analysis_completed.emit()

    def _display_result(self, result: Dict[str, Any]):
        if not result.get("valid"):
            return

        results = result.get("results", [])
        summary = result.get("summary", {})

        rows = ["工序编号 作业员 循环数 异常值 平均时间(s) 正常时间(s) 标准工时(s) 标准差 CV".split()]
        for r in results:
            st = r["stats"]
            rows.append([
                r["process_id"], r["operator"], str(r["cycles"]),
                str(r["outliers_removed"]), f"{r['avg_time']:.2f}",
                f"{r['normal_time']:.2f}", f"{r['standard_time']:.2f}",
                f"{st['std']:.3f}", f"{st['cv']:.3f}",
            ])

        self.result_table.setColumnCount(len(rows[0]))
        self.result_table.setHorizontalHeaderLabels(rows[0])
        self.result_table.setRowCount(len(rows) - 1)
        for i, row in enumerate(rows[1:]):
            for j, val in enumerate(row):
                self.result_table.setItem(i, j, QTableWidgetItem(val))
        self.result_table.resizeColumnsToContents()

        self._draw_chart(results, summary)

    def _draw_chart(self, results: list, summary: Dict[str, Any]):
        self._clear_canvas()
        n = len(results)
        if n == 0:
            return

        fig = Figure(figsize=(10, max(3, n * 1.4)), dpi=100)
        fig.subplots_adjust(left=0.12, right=0.95, top=0.93, bottom=0.08, hspace=0.5)

        for i, r in enumerate(results):
            ax = fig.add_subplot(n, 2, i * 2 + 1)
            dist = r.get("distribution", {})
            bins = dist.get("bins", [])
            counts = dist.get("counts", [])
            if bins and counts and len(bins) > 1:
                mid = [(bins[j] + bins[j+1]) / 2 for j in range(len(bins) - 1)]
                ax.bar(mid, counts, width=(bins[1]-bins[0])*0.9, color="#2196F3", alpha=0.7)
                ax.axvline(r["avg_time"], color="#F44336", linestyle="--", linewidth=2, label=f"均值 {r['avg_time']:.1f}s")
                ax.axvline(r["standard_time"], color="#FF9800", linestyle="-", linewidth=2, label=f"标准 {r['standard_time']:.1f}s")
                ax.legend(fontsize=8, loc="upper right")
            ax.set_title(f"{r['process_id']} | {r['operator']}", fontsize=9)
            ax.set_xlabel("时间 (s)", fontsize=7)
            ax.set_ylabel("频次", fontsize=7)

            ax2 = fig.add_subplot(n, 2, i * 2 + 2)
            st = r["stats"]
            labels = ["均值", "中位数", "标准差", "范围"]
            values = [st["mean"], st["median"], st["std"], st["range"]]
            colors = ["#2196F3", "#4CAF50", "#FF9800", "#F44336"]
            bars = ax2.barh(labels, values, color=colors, alpha=0.75)
            for bar, val in zip(bars, values):
                ax2.text(bar.get_width() + max(values)*0.01, bar.get_y() + bar.get_height()/2,
                         f"{val:.2f}", va="center", fontsize=8)
            cap = r.get("capability", {})
            if cap.get("available"):
                ax2.set_title(f"CPK={cap['cpk']:.2f}  Sigma={cap['sigma_level']:.1f}σ  "
                              f"{'✓ 满足节拍' if cap.get('can_meet_takt') else '✗ 超节拍'}", fontsize=8)
            else:
                ax2.set_title(f"n={st['n']}  CV={st['cv']:.3f}", fontsize=8)

        self.current_figure = fig
        self.canvas = FigureCanvasQTAgg(fig)
        self.chart_layout.addWidget(self.canvas)
        self._switch_result_view(0)
