"""SMED 快速换模分析 Tab — 内外作业分离 + 甘特图 + 改善对比"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
import numpy as np

from ui.tabs.base_tab import BaseAnalysisTab
from ui.theme import BUTTON_PRIMARY_STRETCH, BUTTON_SECONDARY, FONT_12B
from analysis.ie.smed import SMEDEngine, SMEDTask


def truncate_label(name: str, max_len: int = 8) -> str:
    """甘特图 y 轴标签截断: 超长作业名截为 max_len-1 字 + 省略号"""
    return name if len(name) <= max_len else name[: max_len - 1] + "…"


class SMEDTab(BaseAnalysisTab):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine = SMEDEngine()
        self.current_figure = None
        self.canvas = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        # — 顶部操作栏 —
        top = QHBoxLayout()
        top.addWidget(QLabel("SMED 快速换模分析"))
        top.addStretch()
        self.add_btn = QPushButton("+ 添加作业")
        self.add_btn.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.add_btn.clicked.connect(self._add_row)
        top.addWidget(self.add_btn)
        self.del_btn = QPushButton("- 删除选中")
        self.del_btn.setStyleSheet(BUTTON_SECONDARY)
        self.del_btn.clicked.connect(self._del_row)
        top.addWidget(self.del_btn)
        layout.addLayout(top)

        # — 作业编辑表 —
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["作业名称", "类型", "改善前(s)", "改善后(s)", "转外部"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 5):
            self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        layout.addWidget(self.table)

        # — 预设模板 —
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("预设:"))
        presets = ["换模5S准备", "工具检查", "模具拆卸", "模具安装", "首件调试", "参数调整", "质量确认", "清理收尾"]
        for p in presets:
            btn = QPushButton(p)
            btn.setFixedHeight(32)  # 足够容纳 9pt+ 中文, 避免垂直裁切
            btn.clicked.connect(lambda _, n=p: self._add_preset(n))
            preset_row.addWidget(btn)
        preset_row.addStretch()
        layout.addLayout(preset_row)

        # — 分析按钮 —
        btn_row = QHBoxLayout()
        self.run_btn = QPushButton("生成 SMED 分析图")
        self.run_btn.setFont(FONT_12B)
        self.run_btn.setMinimumHeight(38)
        self.run_btn.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.run_btn.clicked.connect(self.run_and_display)
        btn_row.addWidget(self.run_btn)
        self.save_btn = QPushButton("保存图表 PNG")
        self.save_btn.setMinimumHeight(38)
        self.save_btn.setStyleSheet(BUTTON_SECONDARY)
        self.save_btn.clicked.connect(self._on_save_png)
        btn_row.addWidget(self.save_btn)
        layout.addLayout(btn_row)

        # — 图表区 —
        self.canvas_widget = QWidget()
        self.canvas_layout = QVBoxLayout(self.canvas_widget)
        layout.addWidget(self.canvas_widget, 1)

        # — 改善摘要 —
        self.summary_label = QLabel("")
        self.summary_label.setFont(QFont("Microsoft YaHei", 11))
        layout.addWidget(self.summary_label)

    def _add_row(self, name="", ttype="internal", t=0, imp=0, conv=False):
        r = self.table.rowCount()
        self.table.setRowCount(r + 1)
        self.table.setItem(r, 0, QTableWidgetItem(name))
        cb = QComboBox()
        cb.addItems(["internal", "external"])
        cb.setCurrentText(ttype)
        self.table.setCellWidget(r, 1, cb)
        for col, val in [(2, t), (3, imp)]:
            item = QTableWidgetItem(str(val))
            item.setData(Qt.EditRole, val)
            self.table.setItem(r, col, item)
        chk = QTableWidgetItem()
        chk.setCheckState(Qt.Checked if conv else Qt.Unchecked)
        self.table.setItem(r, 4, chk)

    def _add_preset(self, name: str):
        mapping = {"换模5S准备": ("external", 300), "工具检查": ("external", 120),
                   "模具拆卸": ("internal", 480), "模具安装": ("internal", 600),
                   "首件调试": ("internal", 900), "参数调整": ("internal", 300),
                   "质量确认": ("internal", 180), "清理收尾": ("external", 120)}
        t, s = mapping.get(name, ("internal", 60))
        self._add_row(name, t, s)

    def _del_row(self):
        for r in sorted(set(i.row() for i in self.table.selectedIndexes()), reverse=True):
            self.table.removeRow(r)

    def _read_table(self):
        self.engine.tasks.clear()
        for r in range(self.table.rowCount()):
            name = self.table.item(r, 0)
            cb = self.table.cellWidget(r, 1)
            if not name or not cb:
                continue
            ttype = cb.currentText()
            try:
                t = float(self.table.item(r, 2).text()) if self.table.item(r, 2) else 0
            except ValueError:
                t = 0
            try:
                imp = float(self.table.item(r, 3).text()) if self.table.item(r, 3) else 0
            except ValueError:
                imp = 0
            conv = self.table.item(r, 4).checkState() == Qt.Checked if self.table.item(r, 4) else False
            task = SMEDTask(name=name.text(), task_type=ttype, time_sec=t, improved_time=imp, convert_to_external=conv)
            self.engine.tasks.append(task)

    def run_and_display(self):
        """标准入口 — 各 Tab 统一接口"""
        result = self.run_analysis()
        if result:
            self.display_result(result)
            # W59-W62: 标准化 current_result 三件套
            self.current_result = {
                "analysis_type": result.get("analysis_type", "SMED"),
                "params": {},
                "result": result.get("result", result),
            }
            self.analysis_completed.emit()

    def run_analysis(self):
        self._read_table()
        result = self.engine.analyze()
        if not result.tasks:
            self.current_figure = None
            return {"analysis_type": "SMED", "result": {}, "summary": "无数据"}

        all_tasks = list(reversed(result.tasks))

        fig, (ax_gantt, ax_compare) = plt.subplots(1, 2, figsize=(14, 7), dpi=100, gridspec_kw={'width_ratios': [1.5, 1]})
        fig.patch.set_facecolor('#181822')

        # —— 甘特图 ——
        y = 0
        colors_map = {'internal': '#e74c3c', 'external': '#3498db'}
        labels, colors_list, starts, widths_after = [], [], [], []
        for t in all_tasks:
            labels.append(truncate_label(t.name))
            colors_list.append(colors_map.get(t.task_type, '#888'))
            starts.append(0)
            widths_after.append(max(t.improved_time, 0) if t.improved_time > 0 else t.time_sec)
            y += 1
        y_positions = range(len(all_tasks))
        ax_gantt.barh(y_positions, widths_after, left=starts, height=0.6, color=colors_list, edgecolor='white', linewidth=0.3)
        for i, t in enumerate(all_tasks):
            ws = widths_after[i] if t.improved_time > 0 else t.time_sec
            ax_gantt.text(ws / 2, i, f'{ws:.0f}s', ha='center', va='center', fontsize=8, color='white')
        ax_gantt.set_yticks(list(y_positions))
        gantt_fs = 9 if len(all_tasks) <= 8 else 7  # 任务多时缩小字号防挤叠
        ax_gantt.set_yticklabels(labels, fontsize=gantt_fs)
        ax_gantt.set_xlabel("时间 (秒)", fontsize=10)
        ax_gantt.set_title("改善后时间分布", fontsize=12, fontweight='bold', color='#e1e2e6')
        ax_gantt.set_facecolor('#1c1c26')
        ax_gantt.tick_params(colors='#a0a3ae')
        ax_gantt.legend([plt.Rectangle((0,0),1,1,color='#e74c3c'), plt.Rectangle((0,0),1,1,color='#3498db')],
                        ['内部作业', '外部作业'], fontsize=8, loc='lower right')

        # —— 改善前后对比柱状图 ——
        cats = ['内部作业', '外部作业', '总时间']
        before_vals = [result.total_internal_before, result.total_external_before, result.total_before]
        after_vals = [result.total_internal_after, result.total_external_after, result.total_after]
        x = np.arange(len(cats))
        w = 0.35
        ax_compare.bar(x - w/2, before_vals, w, color='#e74c3c', alpha=0.8, label='改善前')
        ax_compare.bar(x + w/2, after_vals, w, color='#2ecc71', alpha=0.8, label='改善后')
        ax_compare.set_xticks(x)
        ax_compare.set_xticklabels(cats, fontsize=9)
        ax_compare.set_ylabel("时间 (秒)", fontsize=10)
        ax_compare.set_title(f"改善对比 (-{result.improvement_pct:.1f}%)", fontsize=12, fontweight='bold', color='#e1e2e6')
        ax_compare.set_facecolor('#1c1c26')
        ax_compare.tick_params(colors='#a0a3ae')
        ax_compare.legend(fontsize=8)
        for i in range(3):
            ax_compare.text(x[i] - w/2, before_vals[i] + 5, f'{before_vals[i]:.0f}', ha='center', fontsize=8, color='#e1e2e6')
            ax_compare.text(x[i] + w/2, after_vals[i] + 5, f'{after_vals[i]:.0f}', ha='center', fontsize=8, color='#e1e2e6')

        fig.tight_layout(rect=[0.18, 0, 1, 1])  # 左侧预留 y 轴标签宽度
        self.current_figure = fig
        summary = (f"换模总时间: {result.total_before:.0f}s → {result.total_after:.0f}s "
                   f"(改善 {result.improvement_pct:.1f}%)\n"
                   f"内部作业: {result.total_internal_before:.0f}s → {result.total_internal_after:.0f}s "
                   f"(-{result.internal_reduction_pct:.1f}%)")
        return {"analysis_type": "SMED", "params": {"task_count": len(result.tasks)},
                "result": result.to_dict(), "summary": summary}

    def display_result(self, result):
        if self.current_figure:
            import matplotlib.pyplot as plt
            for i in reversed(range(self.canvas_layout.count())):
                w = self.canvas_layout.itemAt(i).widget()
                if w:
                    w.setParent(None)
            plt.close("all")
            self.canvas = FigureCanvasQTAgg(self.current_figure)
            self.canvas_layout.addWidget(self.canvas)
            self.canvas.draw()
        self.summary_label.setText(result.get("summary", ""))

    def _on_save_png(self):
        if not self.current_figure:
            QMessageBox.information(self, "提示", "请先生成分析图")
            return
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "保存 SMED 图表", "smed_analysis.png", "PNG (*.png)")
        if path:
            self.current_figure.savefig(path, dpi=150, facecolor='#181822')
