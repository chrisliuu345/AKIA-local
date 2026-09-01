"""
价值流分析页 (VSM) — 工序框 + 库存三角 + 时间阶梯线
"""

from typing import Dict, Any, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDoubleSpinBox, QGroupBox, QFormLayout,
    QTableWidget, QTableWidgetItem, QSplitter, QHeaderView,
    QStackedWidget, QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle, Polygon
import matplotlib.pyplot as plt

from core.i18n import i18n
from ui.tabs.base_tab import BaseAnalysisTab
from ui.theme import BUTTON_PRIMARY_STRETCH, BUTTON_SECONDARY, BUTTON_TOGGLE
from ui.theme import colors as theme_colors
from ui.font_config import get_ui_font
from core.data_objects import MaterialFlow, Process
from analysis.ie.vsm import VSMEngine


class VSMTab(BaseAnalysisTab):

    def __init__(self, parent=None):
        self.ie_processes: List[Process] = []
        self.ie_flows: List[MaterialFlow] = []
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self.title_label = QLabel(i18n.tr("ie.vsm.title"))
        self.title_label.setFont(QFont(get_ui_font(), 18, QFont.Bold))
        layout.addWidget(self.title_label)
        layout.addSpacing(4)

        splitter = QSplitter(Qt.Vertical)

        top = QWidget()
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(0, 0, 0, 0)

        config_group = QGroupBox("分析参数")
        config_layout = QFormLayout(config_group)

        self.demand_spin = QDoubleSpinBox()
        self.demand_spin.setRange(1, 1e7)
        self.demand_spin.setValue(1000)
        self.demand_spin.setDecimals(0)
        self.demand_spin.setSuffix(" 件/天")
        config_layout.addRow("日需求量:", self.demand_spin)

        self.btn_analyze = QPushButton(i18n.tr("ie.run_btn"))
        self.btn_analyze.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.btn_analyze.setCursor(Qt.PointingHandCursor)
        self.btn_analyze.setMinimumHeight(44)
        self.btn_analyze.setFont(QFont(get_ui_font(), 12, QFont.Bold))
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

    def set_ie_data(self, processes: List[Process] = None,
                    flows: List[MaterialFlow] = None):
        if processes is not None:
            self.ie_processes = processes
        if flows is not None:
            self.ie_flows = flows
        self._populate_preview()

    def _populate_preview(self):
        procs, flows = self.ie_processes, self.ie_flows
        cols = ["类别", "内容"]
        rows = []
        for p in procs[:25]:
            rows.append(["工序", f"{p.process_id} {p.process_name}  "
                         f"CT={p.cycle_time:.1f}s  {p.labor_count}人"])
        for f in flows[:25]:
            rows.append(["物流", f"{f.from_process} → {f.to_process}  "
                         f"{f.quantity:.0f}件"])
        self.preview_table.setColumnCount(2)
        self.preview_table.setHorizontalHeaderLabels(cols)
        self.preview_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, val in enumerate(row):
                self.preview_table.setItem(i, j, QTableWidgetItem(str(val)))
        self.preview_label.setText(
            f"工序: {len(procs)} 个 | 物流记录: {len(flows)} 条")

    def _on_one_click_analyze(self):
        if not self.ie_processes:
            QMessageBox.warning(self, "无数据", "请先导入包含工序表的 Excel 文件")
            return

        demand = self.demand_spin.value()
        engine = VSMEngine()
        result = engine.analyze(self.ie_processes, self.ie_flows, demand)

        if result.get("error"):
            QMessageBox.warning(self, "分析失败", result["error"])
            return

        self.current_result = {
            "analysis_type": "价值流分析",
            "params": {"daily_demand": demand},
            "result": result,
        }
        self._display_result(result)
        self.analysis_completed.emit()

    # ── 结果展示 ──
    def _display_result(self, result: Dict[str, Any]):
        self._fill_table(result)
        self._draw_vsm(result)

    def _fill_table(self, result: Dict[str, Any]):
        s = result["summary"]
        headers = ["类别", "项目", "值"]
        rows = [
            ["汇总", "Lead Time", f"{s['lead_time_days']:.2f} 天"],
            ["汇总", "Σ增值时间 (VA)", f"{s['total_va_sec']:.0f} s"],
            ["汇总", "增值比", f"{s['va_ratio']:.2%}"],
            ["汇总", "在制品库存", f"{s['total_inventory_qty']:.0f} 件 "
                                    f"({s['inventory_days']:.2f} 天)"],
            ["汇总", "节拍时间", f"{s['takt_sec']:.1f} s "
                                  f"(日需求 {s['daily_demand']:.0f} 件)"],
        ]
        if s.get("over_takt"):
            rows.append(["汇总", "超节拍工序", ", ".join(s["over_takt"])])
        for st in result["steps"]:
            inv = (f"  后库存 {st['inv_qty']:.0f}件 ({st['inv_days']:.2f}天)"
                   if st["inv_qty"] > 0 else "")
            rows.append(["工序", st["process_name"],
                         f"CT={st['ct']:.1f}s, {st['labor']}人{inv}"])
        for w in result.get("warnings", []):
            rows.append(["警告", "-", w])

        self.result_table.setColumnCount(3)
        self.result_table.setHorizontalHeaderLabels(headers)
        self.result_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, val in enumerate(row):
                self.result_table.setItem(i, j, QTableWidgetItem(str(val)))
        self.result_table.resizeColumnsToContents()

    def _draw_vsm(self, result: Dict[str, Any]):
        self._clear_canvas()
        tc = theme_colors()
        # plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]  # redundant, handled by chart_engine.setup_chinese_font()
        plt.rcParams["axes.unicode_minus"] = False

        steps = result["steps"]
        s = result["summary"]
        n = len(steps)

        fig = Figure(figsize=(12, 5.4), dpi=100)
        fig.set_facecolor(tc["bg_card"])
        ax = fig.add_axes([0.02, 0.03, 0.96, 0.90])
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        ax.axis("off")

        # ── 汇总框 ──
        summary_text = (
            f"Lead Time: {s['lead_time_days']:.2f} 天\n"
            f"ΣVA: {s['total_va_sec']:.0f} s   增值比: {s['va_ratio']:.2%}\n"
            f"节拍: {s['takt_sec']:.1f} s (日需求 {s['daily_demand']:.0f} 件)"
        )
        ax.text(98, 97, summary_text, ha="right", va="top", fontsize=9,
                color=tc["text_primary"],
                bbox=dict(boxstyle="round,pad=0.5", facecolor=tc["bg_body"],
                          edgecolor=tc["accent"], linewidth=1.2))

        # ── 工序框 ──
        x0, x1 = 6, 84
        box_w = min(13.0, (x1 - x0) / n - 1.5)
        gap = ((x1 - x0) - n * box_w) / max(n - 1, 1) if n > 1 else 0
        y_box, box_h = 62, 18

        box_color = "#262632"
        for i, st in enumerate(steps):
            x = x0 + i * (box_w + gap)
            over = st["process_name"] in s.get("over_takt", [])
            rect = Rectangle((x, y_box), box_w, box_h,
                             facecolor=box_color,
                             edgecolor="#e74c3c" if over else tc["accent"],
                             linewidth=1.6)
            ax.add_patch(rect)
            cx = x + box_w / 2
            ax.text(cx, y_box + box_h - 3.2, st["process_name"] or st["process_id"],
                    ha="center", va="center", fontsize=9, fontweight="bold",
                    color=tc["text_primary"])
            ax.text(cx, y_box + box_h - 8.6, f"CT = {st['ct']:.1f} s",
                    ha="center", va="center", fontsize=8,
                    color=tc["accent_bright"])
            ax.text(cx, y_box + box_h - 13.4,
                    f"{st['labor']}人" + (f"  {st['equipment']}" if st["equipment"] else ""),
                    ha="center", va="center", fontsize=7.5,
                    color=tc["text_secondary"])

            # 箭头到下一工序
            if i < n - 1:
                ax.annotate("", xy=(x + box_w + gap, y_box + box_h / 2),
                            xytext=(x + box_w, y_box + box_h / 2),
                            arrowprops=dict(arrowstyle="->",
                                            color=tc["text_secondary"], lw=1.2))

            # 库存三角（工序之后）
            if st["inv_qty"] > 0 and i < n - 1:
                tri_cx = x + box_w + gap / 2
                tri_y = y_box + 1
                ax.add_patch(Polygon(
                    [(tri_cx - 2.6, tri_y), (tri_cx + 2.6, tri_y), (tri_cx, tri_y + 6)],
                    closed=True, facecolor="#e67e22", edgecolor="#e67e22", alpha=0.85))
                ax.text(tri_cx, tri_y + 2, "I", ha="center", va="center",
                        fontsize=7, color="#ffffff", fontweight="bold")
                ax.text(tri_cx, tri_y - 3.4, f"{st['inv_qty']:.0f}件",
                        ha="center", va="center", fontsize=7.5, color="#e67e22")
                ax.text(tri_cx, tri_y - 7.2, f"{st['inv_days']:.2f}天",
                        ha="center", va="center", fontsize=7, color="#e67e22")

        # ── 时间阶梯线 ──
        y_lad = 26
        x_cur = x0
        ladder_end = x1
        va_w = 2.6
        nva_total = s["inventory_days"]
        nva_avail = (ladder_end - x0) - n * va_w
        nva_scale = nva_avail / nva_total if nva_total > 0 else 0

        for st in steps:
            # VA 凸起（增值时间，秒）
            ax.plot([x_cur, x_cur, x_cur + va_w, x_cur + va_w],
                    [y_lad, y_lad + 5, y_lad + 5, y_lad],
                    color="#27ae60", linewidth=1.8)
            ax.text(x_cur + va_w / 2, y_lad + 7, f"{st['ct']:.0f}s",
                    ha="center", fontsize=7.5, color="#27ae60")
            x_cur += va_w
            # NVA 段（库存等待，天）
            if st["inv_days"] > 0 and nva_scale > 0:
                w = st["inv_days"] * nva_scale
                ax.plot([x_cur, x_cur + w], [y_lad, y_lad],
                        color="#e67e22", linewidth=2.2)
                ax.text(x_cur + w / 2, y_lad - 4.5, f"{st['inv_days']:.2f}天",
                        ha="center", fontsize=7.5, color="#e67e22")
                x_cur += w

        ax.plot([x0, x_cur], [y_lad, y_lad], color=tc["text_muted"],
                linewidth=0.6, linestyle="-", zorder=0)
        ax.text(x_cur + 1.5, y_lad + 1,
                f"ΣVA {s['total_va_sec']:.0f}s\nLT {s['lead_time_days']:.2f}天",
                va="center", fontsize=8.5, color=tc["text_primary"], fontweight="bold")

        # 图例
        ax.plot([x0, x0 + 4], [8, 8], color="#27ae60", linewidth=1.8)
        ax.text(x0 + 5, 8, "增值时间 (VA, 秒)", fontsize=8, va="center",
                color=tc["text_secondary"])
        ax.plot([x0 + 24, x0 + 28], [8, 8], color="#e67e22", linewidth=2.2)
        ax.text(x0 + 29, 8, "库存等待 (NVA, 天)", fontsize=8, va="center",
                color=tc["text_secondary"])

        self.current_figure = fig
        self.canvas = FigureCanvasQTAgg(fig)
        self.chart_layout.addWidget(self.canvas)
        self._switch_result_view(0)

    def refresh_texts(self):
        self.title_label.setText(i18n.tr("ie.vsm.title"))
