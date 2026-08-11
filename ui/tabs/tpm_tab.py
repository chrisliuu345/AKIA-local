"""TPM 全面生产维护 Tab — KPI 仪表 + 六大损失帕累托 + 维护日历"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QCalendarWidget, QListWidget,
)
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
import numpy as np

from ui.tabs.base_tab import BaseAnalysisTab
from ui.theme import BUTTON_PRIMARY_STRETCH
from analysis.ie.tpm import TPMEngine


class TPMTab(BaseAnalysisTab):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine = TPMEngine()
        self.current_figure = None
        self.canvas = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        # KPI 卡
        kpi_row = QHBoxLayout()
        self.kpi_labels = {}
        for key, label in [("mtbf", "MTBF (h)"), ("mttr", "MTTR (h)"), ("oee", "OEE %"), ("records", "记录数")]:
            card = QWidget()
            card.setStyleSheet("background: #262632; border-radius: 8px; padding: 10px;")
            cl = QVBoxLayout(card)
            cl.addWidget(QLabel(label))
            v = QLabel("--")
            v.setStyleSheet("font-size: 24px; font-weight: bold; color: #4da6ff;")
            cl.addWidget(v)
            self.kpi_labels[key] = v
            kpi_row.addWidget(card)
        layout.addLayout(kpi_row)

        # 数据表
        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels(
            ["日期", "运行(h)", "计划停(h)", "故障停(h)", "换模(h)", "空转(h)",
             "速度损(h)", "不良(h)", "启动损(h)", "总产/良品"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        layout.addWidget(self.table)

        # 按钮行
        btn_row = QHBoxLayout()
        add_btn = QPushButton("+ 添加记录")
        add_btn.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        add_btn.clicked.connect(lambda: self._add_record())
        btn_row.addWidget(add_btn)
        run_btn = QPushButton("生成 TPM 分析")
        run_btn.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        run_btn.clicked.connect(self.run_and_display)
        btn_row.addWidget(run_btn)
        layout.addLayout(btn_row)

        # 图表区
        self.canvas_widget = QWidget()
        self.canvas_layout = QVBoxLayout(self.canvas_widget)
        layout.addWidget(self.canvas_widget, 1)

        # 维护日历
        cal_row = QHBoxLayout()
        self.calendar = QCalendarWidget()
        self.calendar.setMaximumWidth(300)
        cal_row.addWidget(self.calendar)
        self.maint_list = QListWidget()
        cal_row.addWidget(self.maint_list, 1)
        maint_input = QHBoxLayout()
        self.maint_task = QLineEdit()
        self.maint_task.setPlaceholderText("维护任务...")
        maint_input.addWidget(self.maint_task)
        add_maint = QPushButton("添加维护")
        add_maint.clicked.connect(self._add_maintenance)
        maint_input.addWidget(add_maint)
        maint_wrap = QVBoxLayout()
        maint_wrap.addLayout(maint_input)
        maint_wrap.addWidget(self.maint_list)
        cal_row.addLayout(maint_wrap)
        layout.addLayout(cal_row)

    def _add_record(self):
        r = self.table.rowCount()
        self.table.setRowCount(r + 1)
        defaults = ["2026-01-01", "24", "0", "0", "0", "0", "0", "0", "0", "100/100"]
        for c, val in enumerate(defaults):
            self.table.setItem(r, c, QTableWidgetItem(val))

    def _add_maintenance(self):
        task = self.maint_task.text().strip()
        if not task:
            return
        d = self.calendar.selectedDate()
        self.engine.add_maintenance(task, d.toString("yyyy-MM-dd"))
        self._refresh_maint_list()
        self.maint_task.clear()

    def _refresh_maint_list(self):
        self.maint_list.clear()
        for m in self.engine.maintenance_plan:
            self.maint_list.addItem(f"{m['due_date']} — {m['task']}")

    def run_and_display(self):
        self.engine.records.clear()
        for r in range(self.table.rowCount()):
            try:
                rec = {
                    "date": self.table.item(r, 0).text() if self.table.item(r, 0) else "",
                    "operating_time": float(self.table.item(r, 1).text()) if self.table.item(r, 1) else 24,
                    "planned_downtime": float(self.table.item(r, 2).text()) if self.table.item(r, 2) else 0,
                    "breakdown_time": float(self.table.item(r, 3).text()) if self.table.item(r, 3) else 0,
                    "setup_time": float(self.table.item(r, 4).text()) if self.table.item(r, 4) else 0,
                    "idle_time": float(self.table.item(r, 5).text()) if self.table.item(r, 5) else 0,
                    "reduced_speed_loss": float(self.table.item(r, 6).text()) if self.table.item(r, 6) else 0,
                    "defect_loss": float(self.table.item(r, 7).text()) if self.table.item(r, 7) else 0,
                    "startup_loss": float(self.table.item(r, 8).text()) if self.table.item(r, 8) else 0,
                    "breakdown_count": 1 if float(self.table.item(r, 3).text() or 0) > 0 else 0,
                }
                output = (self.table.item(r, 9).text() or "100/100").split("/")
                rec["total_output"] = int(output[0]) if output else 100
                rec["good_output"] = int(output[1]) if len(output) > 1 else rec["total_output"]
                self.engine.add_record(**rec)
            except (ValueError, AttributeError):
                continue
        result = self.engine.analyze()
        self._display(result)
        self.current_result = result.to_dict()

    def _display(self, result):
        # KPI
        self.kpi_labels["mtbf"].setText(f"{result.avg_mtbf:.1f}")
        self.kpi_labels["mttr"].setText(f"{result.avg_mttr:.1f}")
        self.kpi_labels["oee"].setText(f"{result.avg_oee * 100:.0f}")
        self.kpi_labels["records"].setText(str(result.record_count))

        # 图表
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), dpi=100)
        fig.patch.set_facecolor('#181822')

        # Pareto
        losses = result.six_losses
        items = sorted(losses.items(), key=lambda x: x[1], reverse=True)
        names = [i[0] for i in items]
        vals = [i[1] for i in items]
        total_loss = sum(vals) or 1
        cum_pct = np.cumsum(vals) / total_loss * 100
        colors = ['#e74c3c', '#e67e22', '#f1c40f', '#2ecc71', '#3498db', '#9b59b6']
        ax1.bar(names, vals, color=colors[:len(names)])
        ax1.set_title("六大损失帕累托", fontsize=12, fontweight='bold', color='#e1e2e6')
        ax1.tick_params(axis='x', rotation=15, colors='#a0a3ae')
        ax1.set_facecolor('#1c1c26')
        ax2_twin = ax1.twinx()
        ax2_twin.plot(names, cum_pct, 'ro-', linewidth=2, markersize=6)
        ax2_twin.set_ylabel("累计 %", color='#e1e2e6')
        ax2_twin.set_ylim(0, 105)

        # MTBF trend
        if len(result.records) > 1:
            dates = [r.date for r in result.records]
            oees = [r.oee * 100 for r in result.records]
            ax2.plot(dates, oees, 'o-', color='#2ecc71', linewidth=2, markersize=8)
            ax2.axhline(y=85, color='#4da6ff', linestyle='--', alpha=0.7, label='世界级 85%')
            ax2.set_title("OEE 趋势", fontsize=12, fontweight='bold', color='#e1e2e6')
            ax2.tick_params(axis='x', rotation=15, colors='#a0a3ae')
            ax2.set_ylabel("OEE %", color='#e1e2e6')
            ax2.set_facecolor('#1c1c26')
            ax2.legend(fontsize=8)

        fig.tight_layout()
        import matplotlib.pyplot as plt
        for i in reversed(range(self.canvas_layout.count())):
            w = self.canvas_layout.itemAt(i).widget()
            if w:
                w.setParent(None)
        plt.close("all")
        self.canvas = FigureCanvasQTAgg(fig)
        self.canvas_layout.addWidget(self.canvas)
        self.canvas.draw()
        self.current_figure = fig
        self._refresh_maint_list()

    def _on_save_png(self):
        if self.current_figure:
            from PySide6.QtWidgets import QFileDialog
            path, _ = QFileDialog.getSaveFileName(self, "保存 TPM 图表", "tpm_analysis.png", "PNG (*.png)")
            if path:
                self.current_figure.savefig(path, dpi=150, facecolor='#181822')
