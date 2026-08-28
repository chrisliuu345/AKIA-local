"""
OEE 设备综合效率分析页 — KPI 仪表盘 + 损失瀑布
"""

from typing import Dict, Any, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QGroupBox, QFormLayout, QFrame,
    QTableWidget, QTableWidgetItem, QSplitter, QHeaderView,
    QStackedWidget, QMessageBox, QGridLayout,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from config.settings import OEE_WORLD_CLASS, OEE_GOOD, OEE_FAIR
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from core.i18n import i18n
from ui.tabs.base_tab import BaseAnalysisTab
from ui.theme import BUTTON_PRIMARY_STRETCH, BUTTON_SECONDARY, BUTTON_TOGGLE
from ui.theme import colors as theme_colors
from core.data_objects import Resource
from analysis.ie.oee import OEEEngine


class OEETab(BaseAnalysisTab):

    def __init__(self, parent=None):
        self.ie_resources: List[Resource] = []
        self._kpi_labels: Dict[str, QLabel] = {}
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self.title_label = QLabel(i18n.tr("ie.oee.title"))
        self.title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        layout.addWidget(self.title_label)
        layout.addSpacing(4)

        splitter = QSplitter(Qt.Vertical)

        top = QWidget()
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(0, 0, 0, 0)

        config_group = QGroupBox("分析参数")
        config_layout = QFormLayout(config_group)

        self.group_combo = QComboBox()
        self.group_combo.addItems(["全部", "按班组", "按班次"])
        config_layout.addRow("汇总维度:", self.group_combo)

        self.btn_analyze = QPushButton(i18n.tr("ie.run_btn"))
        self.btn_analyze.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.btn_analyze.setCursor(Qt.PointingHandCursor)
        self.btn_analyze.setMinimumHeight(44)
        self.btn_analyze.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        self.btn_analyze.clicked.connect(self._on_one_click_analyze)
        config_layout.addRow(self.btn_analyze)

        top_layout.addWidget(config_group)

        # KPI 卡片（2×2 网格独立成组，避免被表单挤压）
        kpi_group = QGroupBox("实时指标")
        kpi_grid = QGridLayout(kpi_group)
        kpi_grid.setSpacing(8)
        for idx, (key, label) in enumerate((("availability", "可用率 A"),
                                            ("performance", "性能 P"),
                                            ("quality", "良品率 Q"),
                                            ("oee", "OEE"))):
            card = QFrame()
            card.setStyleSheet(
                "QFrame { background: #262632; border: 1px solid #2a2a36; "
                "border-radius: 8px; }"
            )
            card.setMinimumWidth(118)
            cl = QVBoxLayout(card)
            cl.setContentsMargins(8, 6, 8, 6)
            name = QLabel(label)
            name.setFont(QFont("Microsoft YaHei", 9))
            name.setStyleSheet("color: #a0a3ae; border: none;")
            name.setAlignment(Qt.AlignCenter)
            val = QLabel("--")
            val.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
            val.setStyleSheet("color: #e1e2e6; border: none;")
            val.setAlignment(Qt.AlignCenter)
            cl.addWidget(name)
            cl.addWidget(val)
            kpi_grid.addWidget(card, idx // 2, idx % 2)
            self._kpi_labels[key] = val
        top_layout.addWidget(kpi_group)

        preview_group = QGroupBox("资源数据预览")
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
        splitter.setSizes([320, 480])
        layout.addWidget(splitter, 1)

    def set_raw_data(self, *args, **kwargs):
        pass

    def set_ie_data(self, resources: List[Resource]):
        self.ie_resources = resources
        self._populate_preview(resources)

    def _populate_preview(self, resources: List[Resource]):
        cols = ["资源ID", "类型", "班组", "班次", "可用(h)", "停机(h)",
                "节拍(s)", "总产量", "良品数"]
        self.preview_table.setColumnCount(len(cols))
        self.preview_table.setHorizontalHeaderLabels(cols)
        rows = min(50, len(resources))
        self.preview_table.setRowCount(rows)
        for i in range(rows):
            r = resources[i]
            vals = [r.resource_id, r.resource_type, r.group, r.shift,
                    f"{r.available_time:.1f}", f"{r.downtime:.1f}",
                    f"{r.ideal_cycle_time:.2f}" if r.ideal_cycle_time else "-",
                    f"{r.total_qty:.0f}" if r.total_qty else "-",
                    f"{r.good_qty:.0f}" if r.good_qty else "-"]
            for j, val in enumerate(vals):
                self.preview_table.setItem(i, j, QTableWidgetItem(val))
        self.preview_label.setText(f"记录: {len(resources)} 条 | "
                                   f"资源: {len(set(r.resource_id for r in resources))} 个")

    def _on_one_click_analyze(self):
        if not self.ie_resources:
            QMessageBox.warning(self, "无数据", "请先导入包含资源数据的 Excel 文件")
            return

        group_by = {"全部": "all", "按班组": "group", "按班次": "shift"}[
            self.group_combo.currentText()]
        engine = OEEEngine()
        result = engine.analyze(self.ie_resources, group_by)

        if result.get("error"):
            QMessageBox.warning(self, "分析失败", result["error"])
            return

        self.current_result = {
            "analysis_type": "OEE 分析",
            "params": {"group_by": group_by},
            "result": result,
        }
        self._display_result(result)
        self.analysis_completed.emit()

    # ── 结果展示 ──
    def _display_result(self, result: Dict[str, Any]):
        ov = result["overall"]
        self._update_kpis(ov)
        self._fill_table(result)
        self._draw_charts(result)

    def _update_kpis(self, ov: Dict[str, Any]):
        tc = theme_colors()

        def pct(key):
            v = ov.get(key)
            return f"{v:.1%}" if isinstance(v, (int, float)) else "N/A"

        self._kpi_labels["availability"].setText(pct("availability"))
        self._kpi_labels["performance"].setText(pct("performance"))
        self._kpi_labels["quality"].setText(pct("quality"))

        oee = ov.get("oee") or 0
        self._kpi_labels["oee"].setText(f"{oee:.1%}")
        if oee >= OEE_WORLD_CLASS:
            color = "#27ae60"
        elif oee >= OEE_GOOD:
            color = tc["accent_bright"]
        elif oee >= OEE_FAIR:
            color = "#e67e22"
        else:
            color = "#e74c3c"
        self._kpi_labels["oee"].setStyleSheet(f"color: {color}; border: none;")

    def _fill_table(self, result: Dict[str, Any]):
        headers = ["维度", "记录数", "可用(h)", "停机(h)", "运行(h)",
                   "A", "P", "Q", "OEE", "评级", "备注"]
        buckets = result["buckets"]
        self.result_table.setColumnCount(len(headers))
        self.result_table.setHorizontalHeaderLabels(headers)
        self.result_table.setRowCount(len(buckets))
        for i, b in enumerate(buckets):
            vals = [
                b["label"], str(b["rows"]), f"{b['available_h']:.1f}",
                f"{b['downtime_h']:.1f}", f"{b['operating_h']:.1f}",
                f"{b['availability']:.1%}",
                f"{b['performance']:.1%}" if b["performance"] is not None else "N/A",
                f"{b['quality']:.1%}" if b["quality"] is not None else "N/A",
                f"{b['oee']:.1%}", b["grade"],
                "; ".join(b["notes"]) if b["notes"] else "",
            ]
            for j, val in enumerate(vals):
                self.result_table.setItem(i, j, QTableWidgetItem(str(val)))
        self.result_table.resizeColumnsToContents()

    def _draw_charts(self, result: Dict[str, Any]):
        self._clear_canvas()
        tc = theme_colors()
        # plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]  # redundant, handled by chart_engine.setup_chinese_font()
        plt.rcParams["axes.unicode_minus"] = False

        fig = Figure(figsize=(11, 4.8), dpi=100)
        fig.set_facecolor(tc["bg_card"])
        fig.subplots_adjust(left=0.07, right=0.98, top=0.86, bottom=0.16, wspace=0.3)

        buckets = result["buckets"]
        labels = [b["label"] for b in buckets]

        # ── 左: 分组柱状图 ──
        ax1 = fig.add_subplot(1, 2, 1)
        metrics = [("availability", "A", "#1b5faa"),
                   ("performance", "P", "#217ca3"),
                   ("quality", "Q", "#27ae60"),
                   ("oee", "OEE", "#9467bd")]
        import numpy as np
        x = np.arange(len(labels))
        width = 0.19
        for k, (key, name, color) in enumerate(metrics):
            vals = [(b[key] if b[key] is not None else 0) for b in buckets]
            bars = ax1.bar(x + (k - 1.5) * width, vals, width,
                           label=name, color=color)
            for xi, v, b in zip(x, vals, buckets):
                if b[key] is not None and v > 0:
                    ax1.text(xi + (k - 1.5) * width, v + 0.015, f"{v:.0%}",
                             ha="center", fontsize=7, color=tc["text_secondary"])
        ax1.axhline(OEE_WORLD_CLASS, color="#e74c3c", linestyle="--", linewidth=1.2)
        ax1.text(len(labels) - 0.5, OEE_WORLD_CLASS + 0.015, f"世界级 {OEE_WORLD_CLASS:.0%}", fontsize=8,
                 color="#e74c3c", ha="right")
        ax1.set_xticks(x)
        ax1.set_xticklabels(labels)
        ax1.set_ylim(0, 1.12)
        ax1.set_title("OEE 三大指标", color=tc["text_primary"], fontsize=11)
        ax1.legend(fontsize=8, ncol=4, facecolor=tc["bg_card"],
                   edgecolor=tc["border"], labelcolor=tc["text_primary"])
        self._style_axis(ax1, tc)

        # ── 右: 时间损失瀑布 ──
        ax2 = fig.add_subplot(1, 2, 2)
        ov = result["overall"]
        losses = ov["losses"]
        stages = ["计划时间", "停机损失", "速度损失", "质量损失", "有效时间"]
        planned = ov["available_h"]
        down = losses["停机损失(h)"]
        speed = losses["速度/小停损失(h)"]
        qual = losses["质量损失(h)"]
        value = losses["有效产出时间(h)"] if ov["has_performance"] else max(
            planned - down - speed - qual, 0.0)

        # 瀑布: planned → -down → -speed → -qual → value
        starts = [0, planned - down, planned - down - speed,
                  planned - down - speed - qual, 0]
        heights = [planned, down, speed, qual, value]
        colors = ["#1b5faa", "#e74c3c", "#e67e22", "#9467bd", "#27ae60"]
        for i, (s, h, c) in enumerate(zip(starts, heights, colors)):
            ax2.bar(stages[i], h, bottom=s, color=c, width=0.58)
            ax2.text(stages[i], s + h + planned * 0.015, f"{h:.2f}h",
                     ha="center", fontsize=8, color=tc["text_primary"])
        # 连接线
        level = planned
        for i, h in enumerate(heights[1:4], 1):
            level -= h
            ax2.plot([i - 0.79, i - 0.21 + 1], [level + h, level + h],
                     color=tc["text_muted"], linewidth=0.8, linestyle=":")
        ax2.set_title(f"时间损失分解 — {ov['label']}（OEE {ov['oee']:.1%}）",
                      color=tc["text_primary"], fontsize=11)
        ax2.set_ylabel("小时", color=tc["text_secondary"], fontsize=9)
        ax2.set_ylim(0, planned * 1.15)
        self._style_axis(ax2, tc, rotate=12)

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
        self.title_label.setText(i18n.tr("ie.oee.title"))
