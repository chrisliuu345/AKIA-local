"""
生产线平衡分析页 — 山积图 + 自动平衡建议
"""

from typing import Dict, Any, List

from PySide6.QtWidgets import (
    QFrame,
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDoubleSpinBox, QGroupBox, QFormLayout,
    QTableWidget, QTableWidgetItem, QSplitter, QHeaderView,
    QStackedWidget, QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from core.i18n import i18n
from ui.tabs.base_tab import BaseAnalysisTab
from ui.theme import BUTTON_PRIMARY_STRETCH, BUTTON_SECONDARY, BUTTON_TOGGLE
from ui.theme import colors as theme_colors
from ui.font_config import get_ui_font
from core.data_objects import Process
from analysis.ie.line_balance import LineBalanceEngine


class LineBalanceTab(BaseAnalysisTab):

    def __init__(self, parent=None):
        self.ie_processes: List[Process] = []
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self.title_label = QLabel(i18n.tr("ie.line_balance.title"))
        self.title_label.setFont(QFont(get_ui_font(), 18, QFont.Bold))
        layout.addWidget(self.title_label)
        layout.addSpacing(4)

        splitter = QSplitter(Qt.Vertical)

        top = QWidget()
        top_layout = QHBoxLayout(top)
        top_layout.setSpacing(10)
        top_layout.setContentsMargins(0, 0, 0, 0)

        config_group = QGroupBox("分析参数")
        config_layout = QFormLayout(config_group)
        config_layout.setContentsMargins(10, 10, 10, 10)

        self.takt_spin = QDoubleSpinBox()
        self.takt_spin.setRange(0, 1e7)
        self.takt_spin.setValue(0)
        self.takt_spin.setDecimals(1)
        self.takt_spin.setSuffix(" s")
        self.takt_spin.setSpecialValueText(" 自动 (瓶颈CT)")
        config_layout.addRow("目标节拍:", self.takt_spin)

        self.btn_analyze = QPushButton(i18n.tr("ie.run_btn"))
        self.btn_analyze.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.btn_analyze.setCursor(Qt.PointingHandCursor)
        self.btn_analyze.setMinimumHeight(44)
        self.btn_analyze.setFont(QFont(get_ui_font(), 12, QFont.Bold))
        self.btn_analyze.clicked.connect(self._on_one_click_analyze)
        config_layout.addRow(self.btn_analyze)

        top_layout.addWidget(config_group)


        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setStyleSheet("")
        separator.setMaximumWidth(1)
        top_layout.addWidget(separator)

        preview_group = QGroupBox("工序数据预览")
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
        self.btn_save_png = QPushButton(i18n.tr("chart_tab.save_png"))
        self.btn_save_png.setFont(QFont(get_ui_font(), 11))
        self.btn_save_png.setFixedHeight(30)
        self.btn_save_png.setStyleSheet(BUTTON_SECONDARY)
        self.btn_save_png.clicked.connect(self._on_save_png)
        toggle_row.addWidget(self.btn_save_png)

        bottom_layout.addLayout(toggle_row)
        bottom_layout.addWidget(self.result_stack, 1)

        splitter.addWidget(bottom)
        splitter.setSizes([280, 520])
        layout.addWidget(splitter, 1)

    def set_raw_data(self, *args, **kwargs):
        pass

    def set_ie_data(self, processes: List[Process]):
        self.ie_processes = processes
        self._populate_preview(processes)

    def _populate_preview(self, processes: List[Process]):
        cols = ["工序编号", "工序名称", "设备", "CT(s)", "人数", "前置工序"]
        self.preview_table.setColumnCount(len(cols))
        self.preview_table.setHorizontalHeaderLabels(cols)
        rows = min(50, len(processes))
        self.preview_table.setRowCount(rows)
        for i in range(rows):
            p = processes[i]
            vals = [p.process_id, p.process_name, p.equipment,
                    f"{p.cycle_time:.1f}", str(p.labor_count),
                    ",".join(p.predecessors)]
            for j, val in enumerate(vals):
                self.preview_table.setItem(i, j, QTableWidgetItem(val))
        with_ct = sum(1 for p in processes if p.cycle_time > 0)
        self.preview_label.setText(
            f"工序: {len(processes)} 个 | 含CT: {with_ct} 个 | "
            f"ΣCT: {sum(p.cycle_time for p in processes):.1f}s"
        )

    def _on_one_click_analyze(self):
        if not self.ie_processes:
            QMessageBox.warning(self, "无数据", "请先导入包含工序表的 Excel 文件")
            return

        takt = self.takt_spin.value() if self.takt_spin.value() > 0 else None
        engine = LineBalanceEngine()
        result = engine.analyze(self.ie_processes, takt)

        if result.get("error"):
            QMessageBox.warning(self, "分析失败", result["error"])
            return

        self.current_result = {
            "analysis_type": "生产线平衡",
            "params": {"takt": result["takt"]},
            "result": result,
        }
        self._display_result(result)
        self.analysis_completed.emit()

    def _display_result(self, result: Dict[str, Any]):
        self._fill_table(result)
        self._draw_yamazumi(result)

    def _fill_table(self, result: Dict[str, Any]):
        cur = result["current"]
        bal = result["balanced"]
        stations = result["stations"]

        headers = ["类别", "项目", "值"]
        rows = [
            ["现状评估", "工位数（=工序数）", str(cur["station_count"])],
            ["现状评估", "ΣCT / 瓶颈CT", f"{cur['total_ct']}s / {cur['max_ct']}s"],
            ["现状评估", "瓶颈工序", f"{cur['bottleneck_name']} ({cur['bottleneck_id']})"],
            ["现状评估", "平衡率", f"{cur['balance_rate']:.1%}"],
            ["现状评估", "平衡损失率", f"{cur['balance_loss']:.1%}"],
            ["平衡建议", "目标节拍", f"{result['takt']}s"],
            ["平衡建议", "建议工位数", str(bal["station_count"])],
            ["平衡建议", "减少工位", str(bal["stations_reduced"])],
            ["平衡建议", "平衡后平衡率", f"{bal['balance_rate']:.1%}"],
            ["平衡建议", "平衡率提升", f"+{bal['rate_improvement']:.1%}"],
        ]
        for s in stations:
            rows.append([
                "工位分配", f"工位{s['station_id']}",
                f"{' + '.join(s['process_names'])}  "
                f"[{s['total_time']}s, 利用率 {s['utilization']:.0%}"
                f"{', 超节拍!' if s['over_takt'] else ''}]",
            ])
        for w in result.get("warnings", []):
            rows.append(["警告", "-", w])

        self.result_table.setColumnCount(3)
        self.result_table.setHorizontalHeaderLabels(headers)
        self.result_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, val in enumerate(row):
                self.result_table.setItem(i, j, QTableWidgetItem(str(val)))
        self.result_table.resizeColumnsToContents()

    def _draw_yamazumi(self, result: Dict[str, Any]):
        self._clear_canvas()
        tc = theme_colors()
        plt.rcParams["axes.unicode_minus"] = False

        takt = result["takt"]
        stations = result["stations"]
        procs = [p for p in self.ie_processes if p.cycle_time > 0]

        fig = Figure(figsize=(11, 4.6), dpi=100)
        fig.set_facecolor(tc["bg_card"])
        fig.subplots_adjust(left=0.07, right=0.98, top=0.88, bottom=0.14, wspace=0.25)

        ax1 = fig.add_subplot(1, 2, 1)
        names = [p.process_name or p.process_id for p in procs]
        cts = [p.cycle_time for p in procs]
        cur = result["current"]
        colors = [tc["accent_bright"] if p.process_id == cur["bottleneck_id"]
                  else tc["accent"] for p in procs]
        ax1.bar(names, cts, color=colors, width=0.62)
        ax1.axhline(takt, color="#e74c3c", linestyle="--", linewidth=1.6,
                    label=f"节拍 {takt}s")
        ax1.set_title(f"现状：平衡率 {cur['balance_rate']:.1%}（{cur['station_count']} 工位）",
                      color=tc["text_primary"], fontsize=11)
        ax1.set_ylabel("CT (s)", color=tc["text_secondary"], fontsize=9)
        ax1.legend(fontsize=8, facecolor=tc["bg_card"], edgecolor=tc["border"],
                   labelcolor=tc["text_primary"])
        self._style_axis(ax1, tc, rotate=25)

        ax2 = fig.add_subplot(1, 2, 2)
        palette = ["#1b5faa", "#217ca3", "#27ae60", "#9467bd", "#b85c38",
                   "#17becf", "#6b4c9a", "#4da6ff"]
        xlabels = []
        for s in stations:
            bottom = 0.0
            for k, (pname, ct) in enumerate(zip(s["process_names"], s["cts"], strict=True)):
                ax2.bar(f"工位{s['station_id']}", ct, bottom=bottom,
                        color=palette[k % len(palette)], width=0.55,
                        edgecolor=tc["bg_card"], linewidth=0.6)
                if ct >= takt * 0.12:
                    ax2.text(f"工位{s['station_id']}", bottom + ct / 2, pname,
                             ha="center", va="center", fontsize=8, color="#ffffff")
                bottom += ct
            ax2.text(f"工位{s['station_id']}", bottom + takt * 0.02,
                     f"{s['total_time']}s ({s['utilization']:.0%})",
                     ha="center", va="bottom", fontsize=8,
                     color=tc["text_primary"])
            xlabels.append(f"工位{s['station_id']}")
        ax2.axhline(takt, color="#e74c3c", linestyle="--", linewidth=1.6)
        bal = result["balanced"]
        ax2.set_title(f"平衡后：平衡率 {bal['balance_rate']:.1%}"
                      f"（{bal['station_count']} 工位, +{bal['rate_improvement']:.0%}）",
                      color=tc["text_primary"], fontsize=11)
        ax2.set_ylim(0, takt * 1.25)
        self._style_axis(ax2, tc, rotate=0)

        self.current_figure = fig
        self.canvas = FigureCanvasQTAgg(fig)
        self.chart_layout.addWidget(self.canvas)
        self._switch_result_view(0)

    @staticmethod
    def _style_axis(ax, tc, rotate=0):
        ax.set_facecolor(tc["bg_card"])
        ax.tick_params(colors=tc["text_primary"], labelsize=9)
        if rotate:
            ax.tick_params(axis="x", rotation=rotate)
        for spine in ax.spines.values():
            spine.set_color(tc["border"])

    def refresh_texts(self):
        self.title_label.setText(i18n.tr("ie.line_balance.title"))
