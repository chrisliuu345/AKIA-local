"""人机配合分析 V2 — 可编辑表格 + 预设 + 利用率统计"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QDoubleSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QScrollArea,
    QFrame,
    QComboBox,
)
from PySide6.QtCore import Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt, matplotlib.patches as mpatches
from ui.tabs.base_tab import BaseAnalysisTab
from ui.theme import BUTTON_PRIMARY_STRETCH, FONT_18B, FONT_10
from ui.theme import colors as theme_colors

C = {
    "worker": "#4da6ff",
    "idle": "#363648",
    "machine": "#ff6b6b",
    "walk": "#ffa726",
    "load": "#51cf66",
}
PRESETS = {
    "单机单工": [(8, 5, 0), (0, 25, 0), (0, 20, 5), (5, 0, 3), (3, 2, 0), (2, 0, 0)],
    "多机操作": [(5, 15, 2), (3, 20, 0), (4, 10, 3), (6, 0, 4), (2, 18, 0)],
    "流水线": [
        (6, 0, 2),
        (5, 0, 1),
        (4, 0, 3),
        (7, 0, 0),
        (3, 0, 2),
        (8, 0, 1),
        (5, 0, 0),
    ],
}


class WorkerMachineTab(BaseAnalysisTab):
    def __init__(self, p=None):
        super().__init__(p)
        self._ready = False
        self._setup_ui()
        self._ready = True

    def _setup_ui(self):
        tc = theme_colors()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        self.title_label = QLabel("人机配合分析")
        self.title_label.setFont(FONT_18B)
        layout.addWidget(self.title_label)
        tb = QHBoxLayout()
        tb.addWidget(QLabel("预设:"))
        self.preset = QComboBox()
        self.preset.addItems(["自定义"] + list(PRESETS.keys()))
        self.preset.currentTextChanged.connect(self._on_preset)
        tb.addWidget(self.preset)
        tb.addSpacing(12)
        tb.addWidget(QLabel("工序数:"))
        self.task_spin = QSpinBox()
        self.task_spin.setRange(1, 12)
        self.task_spin.setValue(4)
        self.task_spin.valueChanged.connect(self._resize_table)
        tb.addWidget(self.task_spin)
        tb.addWidget(QLabel("节拍(s):"))
        self.takt_spin = QDoubleSpinBox()
        self.takt_spin.setRange(1, 9999)
        self.takt_spin.setValue(60)
        tb.addWidget(self.takt_spin)
        tb.addStretch()
        self.btn_run = QPushButton("生成时间线")
        self.btn_run.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.btn_run.setCursor(Qt.PointingHandCursor)
        self.btn_run.clicked.connect(self._run)
        tb.addWidget(self.btn_run)
        layout.addLayout(tb)
        self.stats_lbl = QLabel("")
        self.stats_lbl.setFont(FONT_10)
        self.stats_lbl.setStyleSheet(f"color: {tc['text_secondary']}; padding: 2px 0;")
        layout.addWidget(self.stats_lbl)
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.cellChanged.connect(self._on_cell_edit)
        self._resize_table()
        layout.addWidget(self.table)
        cw = QScrollArea()
        cw.setWidgetResizable(True)
        cw.setFrameShape(QFrame.NoFrame)
        self.chart_container = QWidget()
        self.chart_layout = QVBoxLayout(self.chart_container)
        self.chart_layout.setContentsMargins(0, 0, 0, 0)
        cw.setWidget(self.chart_container)
        layout.addWidget(cw, 1)

    def _resize_table(self):
        n = self.task_spin.value()
        headers = ["工序名", "人工(s)", "机器(s)", "步行(s)"]
        self.table.blockSignals(True)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(n)
        defaults = ["装夹", "粗加工", "精加工", "测量", "卸料", "清理", "换刀"]
        for i in range(min(7, n)):
            if not self.table.item(i, 0):
                self.table.setItem(i, 0, QTableWidgetItem(defaults[i]))
            if not self.table.item(i, 1):
                self.table.setItem(i, 1, QTableWidgetItem("5"))
            if not self.table.item(i, 2):
                self.table.setItem(i, 2, QTableWidgetItem("10"))
            if not self.table.item(i, 3):
                self.table.setItem(i, 3, QTableWidgetItem("0"))
        self.table.resizeColumnsToContents()
        self.table.blockSignals(False)

    def _on_preset(self, name: str):
        if name == "自定义":
            return
        data = PRESETS[name]
        self.task_spin.setValue(len(data))
        for i, (w, m, walk) in enumerate(data):
            self.table.setItem(i, 0, QTableWidgetItem(f"工序{i + 1}"))
            self.table.setItem(i, 1, QTableWidgetItem(str(w)))
            self.table.setItem(i, 2, QTableWidgetItem(str(m)))
            self.table.setItem(i, 3, QTableWidgetItem(str(walk)))
        self._run()

    def _on_cell_edit(self, row, col):
        if self._ready and col == 0:
            self._run()

    def _run(self):
        n = self.task_spin.value()
        takt = self.takt_spin.value()
        rows = []
        for i in range(n):
            name = self.table.item(i, 0)
            w_text = self.table.item(i, 1)
            m_text = self.table.item(i, 2)
            walk_text = self.table.item(i, 3)
            try:
                w = int(w_text.text()) if w_text and w_text.text() else 0
            except (ValueError, TypeError, AttributeError):
                w = 0
            try:
                m = int(m_text.text()) if m_text and m_text.text() else 0
            except (ValueError, TypeError, AttributeError):
                m = 0
            try:
                walk = int(walk_text.text()) if walk_text and walk_text.text() else 0
            except (ValueError, TypeError, AttributeError):
                walk = 0
            rows.append((name.text() if name else f"OP{i + 1}", w, m, walk))
        total_work = sum(r[1] for r in rows)
        total_machine = sum(r[2] for r in rows)
        total_walk = sum(r[3] for r in rows)
        cycle = max(takt, total_work + total_machine + total_walk)
        util_worker = total_work / cycle * 100
        util_machine = total_machine / cycle * 100
        self.stats_lbl.setText(
            f"总人工作业: {total_work}s | 总机器: {total_machine}s | 步行: {total_walk}s | 人工利用率: {util_worker:.0f}% | 机器利用率: {util_machine:.0f}%"
        )
        self._clear_canvas()
        tc = theme_colors()
        plt.rcParams["axes.unicode_minus"] = False
        fig = Figure(figsize=(12, max(4, n * 1.2)), dpi=100)
        fig.set_facecolor(tc["bg_card"])
        ax = fig.add_subplot(111)
        ax.set_facecolor(tc["bg_body"])
        cum = 0
        y_labels = []
        for i, (name, wt, mt, walk) in enumerate(rows):
            y = n - 1 - i
            y_labels.append(name)
            if wt > 0:
                ax.barh(
                    y,
                    wt,
                    left=cum,
                    height=0.35,
                    color=C["worker"],
                    edgecolor="white",
                    linewidth=0.5,
                )
            if walk > 0:
                ax.barh(
                    y,
                    walk,
                    left=cum + wt,
                    height=0.25,
                    color=C["walk"],
                    edgecolor="white",
                    linewidth=0.5,
                    alpha=0.7,
                )
            if mt > 0:
                ax.barh(
                    y - 0.35,
                    mt,
                    left=cum + wt + walk,
                    height=0.35,
                    color=C["machine"],
                    edgecolor="white",
                    linewidth=0.5,
                )
            gap = takt - (wt + mt + walk)
            if gap > 0:
                ax.barh(
                    y,
                    gap,
                    left=cum + wt + walk + mt,
                    height=0.3,
                    color=C["idle"],
                    alpha=0.4,
                    hatch="//",
                )
            cum += wt + mt + walk
        ax.axvline(x=takt, color="#ff6b6b", linestyle="--", linewidth=1.5)
        ax.text(takt + 1, n - 0.3, f"Takt {takt}s", fontsize=9, color="#ff6b6b")
        ax.set_yticks([i - 0.17 for i in range(n)])
        ax.set_yticklabels(y_labels, fontsize=9)
        ax.set_xlabel("时间(秒)", fontsize=10)
        ax.set_title("人机配合时间线图", fontsize=12, fontweight="bold")
        ax.grid(True, alpha=0.3, axis="x")
        ax.legend(
            handles=[
                mpatches.Patch(color=C["worker"], label="人工"),
                mpatches.Patch(color=C["machine"], label="机器"),
                mpatches.Patch(color=C["walk"], label="步行"),
                mpatches.Patch(color=C["idle"], label="空闲", alpha=0.4),
            ],
            fontsize=8,
            ncol=4,
            loc="upper right",
        )
        fig.subplots_adjust(left=0.1, right=0.95, top=0.92, bottom=0.08)
        canvas = FigureCanvasQTAgg(fig)
        self.chart_layout.addWidget(canvas)
        self.canvas = canvas
        self.current_figure = fig
        self._add_chart_toolbar()
        self.analysis_completed.emit()
