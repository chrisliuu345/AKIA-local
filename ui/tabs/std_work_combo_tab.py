"""标准作业组合票 V2 — 可编辑表格 + 预设 + 余力统计"""

from PySide6.QtWidgets import (
    QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,
    QSpinBox,QDoubleSpinBox,QTableWidget,
    QTableWidgetItem,QScrollArea,QFrame,QComboBox,
)
from PySide6.QtCore import Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt, matplotlib.patches as mpatches
from ui.tabs.base_tab import BaseAnalysisTab
from ui.theme import BUTTON_PRIMARY_STRETCH,FONT_18B,FONT_10
from ui.theme import colors as theme_colors

C_W="#4da6ff"; C_A="#51cf66"; C_WK="#ffa726"; C_I="#363648"
PRESETS={"CNC加工":[(5,10,3),(4,45,0),(8,0,2),(3,8,0),(3,5,2),(4,0,0)],"装配线":[(6,0,2),(5,0,1),(4,0,3),(7,0,0),(3,0,2),(8,0,1)],"冲压":[(3,15,2),(2,20,0),(4,0,3),(5,10,0)]}

class StdWorkComboTab(BaseAnalysisTab):
    def __init__(self,p=None): super().__init__(p); self._ready=False; self._setup_ui(); self._ready=True
    def _setup_ui(self):
        tc=theme_colors(); layout=QVBoxLayout(self); layout.setContentsMargins(12,12,12,12)
        self.title_label = QLabel("标准作业组合票"); self.title_label.setFont(FONT_18B); layout.addWidget(self.title_label)
        tb=QHBoxLayout(); tb.addWidget(QLabel("预设:"))
        self.preset=QComboBox(); self.preset.addItems(["自定义"]+list(PRESETS.keys())); self.preset.currentTextChanged.connect(self._on_preset)
        tb.addWidget(self.preset); tb.addSpacing(12)
        tb.addWidget(QLabel("工序数:")); self.step_spin=QSpinBox(); self.step_spin.setRange(2,12); self.step_spin.setValue(6); self.step_spin.valueChanged.connect(self._resize_table)
        tb.addWidget(self.step_spin); tb.addWidget(QLabel("节拍(s):"))
        self.takt_spin=QDoubleSpinBox(); self.takt_spin.setRange(10,9999); self.takt_spin.setValue(90)
        tb.addWidget(self.takt_spin); tb.addStretch()
        self.btn_run=QPushButton("生成组合票"); self.btn_run.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.btn_run.setCursor(Qt.PointingHandCursor); self.btn_run.clicked.connect(self._run)
        tb.addWidget(self.btn_run); layout.addLayout(tb)
        # 统计
        self.stats_lbl=QLabel(""); self.stats_lbl.setFont(FONT_10)
        self.stats_lbl.setStyleSheet(f"color: {tc['text_secondary']}; padding: 2px 0;")
        layout.addWidget(self.stats_lbl)
        # 可编辑表格
        self.table=QTableWidget(); self.table.setAlternatingRowColors(True); self.table.cellChanged.connect(self._on_cell_edit)
        self._resize_table(); layout.addWidget(self.table)
        # 图表
        cw=QScrollArea(); cw.setWidgetResizable(True); cw.setFrameShape(QFrame.NoFrame)
        self.chart_container=QWidget(); self.chart_layout=QVBoxLayout(self.chart_container); self.chart_layout.setContentsMargins(0,0,0,0)
        cw.setWidget(self.chart_container); layout.addWidget(cw,1)

    def _resize_table(self):
        n=self.step_spin.value(); headers=["工序名","手动(s)","自动(s)","步行(s)"]
        self.table.blockSignals(True)
        self.table.setColumnCount(4); self.table.setHorizontalHeaderLabels(headers); self.table.setRowCount(n)
        defaults=["取料","装夹","加工","测量","调整","卸料","清洁","搬运"]
        for i in range(min(8,n)):
            if not self.table.item(i,0): self.table.setItem(i,0,QTableWidgetItem(defaults[i]))
            if not self.table.item(i,1): self.table.setItem(i,1,QTableWidgetItem("5"))
            if not self.table.item(i,2): self.table.setItem(i,2,QTableWidgetItem("10"))
            if not self.table.item(i,3): self.table.setItem(i,3,QTableWidgetItem("2"))
        self.table.resizeColumnsToContents()
        self.table.blockSignals(False)

    def _on_preset(self,name:str):
        if name=="自定义": return
        data=PRESETS[name]; self.step_spin.setValue(len(data))
        for i,(man,auto,walk) in enumerate(data):
            self.table.setItem(i,0,QTableWidgetItem(f"工序{i+1}"))
            self.table.setItem(i,1,QTableWidgetItem(str(man))); self.table.setItem(i,2,QTableWidgetItem(str(auto))); self.table.setItem(i,3,QTableWidgetItem(str(walk)))
        self._run()

    def _on_cell_edit(self,row,col):
        if self._ready and col==0: self._run()

    def _run(self):
        n=self.step_spin.value(); takt=self.takt_spin.value()
        rows=[]
        for i in range(n):
            name=self.table.item(i,0)
            m_text=self.table.item(i,1); a_text=self.table.item(i,2); wk_text=self.table.item(i,3)
            try: man=int(m_text.text()) if m_text and m_text.text() else 0
            except (ValueError, TypeError, AttributeError): man=0
            try: auto=int(a_text.text()) if a_text and a_text.text() else 0
            except (ValueError, TypeError, AttributeError): auto=0
            try: walk=int(wk_text.text()) if wk_text and wk_text.text() else 0
            except (ValueError, TypeError, AttributeError): walk=0
            rows.append((name.text() if name else f"OP{i+1}",man,auto,walk))
        total_man=sum(r[1] for r in rows); total_auto=sum(r[2] for r in rows)
        total_walk=sum(r[3] for r in rows); total=total_man+total_auto+total_walk
        slack=max(0,takt-total)
        self.stats_lbl.setText(f"手动: {total_man}s | 自动: {total_auto}s | 步行: {total_walk}s | 合计: {total}s | 余力: {slack}s ({(1-total/takt)*100:.0f}%)")
        # 图表
        self._clear_canvas(); tc=theme_colors()
        plt.rcParams["font.sans-serif"]=["Microsoft YaHei"]; plt.rcParams["axes.unicode_minus"]=False
        fig=Figure(figsize=(10,max(4.5,n*0.9)),dpi=100); fig.set_facecolor(tc["bg_card"])
        ax=fig.add_subplot(111); ax.set_facecolor(tc["bg_body"])
        y_labels=[]
        for i,(name,man,auto,walk) in enumerate(rows):
            y=n-1-i; y_labels.append(name); left=0
            if man>0: ax.barh(y,man,height=0.55,color=C_W,edgecolor="white",linewidth=0.5); left+=man
            if auto>0: ax.barh(y,auto,left=left,height=0.55,color=C_A,edgecolor="white",linewidth=0.5); left+=auto
            if walk>0: ax.barh(y,walk,left=left,height=0.55,color=C_WK,edgecolor="white",linewidth=0.5,alpha=0.8); left+=walk
            gap=takt-left
            if gap>0: ax.barh(y,gap,left=left,height=0.35,color=C_I,alpha=0.3)
            ax.text(left+gap/2,y+0.15,f"{left}s",fontsize=7,color=tc["text_secondary"],ha="center")
        ax.axvline(x=takt,color="#ff6b6b",linestyle="--",linewidth=1.5)
        ax.text(takt+0.5,n-0.2,f"Takt {takt}s",fontsize=9,color="#ff6b6b")
        ax.set_yticks(range(n)); ax.set_yticklabels(y_labels,fontsize=9)
        ax.set_xlabel("时间(秒)",fontsize=10); ax.set_xlim(0,takt*1.15)
        ax.set_title(f"标准作业组合票 (节拍 {takt}s)",fontsize=12,fontweight="bold")
        ax.grid(True,alpha=0.3,axis="x")
        ax.legend(handles=[mpatches.Patch(color=C_W,label="手动"),mpatches.Patch(color=C_A,label="自动"),mpatches.Patch(color=C_WK,label="步行"),mpatches.Patch(color=C_I,label="余力",alpha=0.3)],fontsize=8,ncol=4,loc="upper right")
        fig.subplots_adjust(left=0.1,right=0.95,top=0.92,bottom=0.08)
        canvas=FigureCanvasQTAgg(fig); self.chart_layout.addWidget(canvas)
        self.canvas=canvas; self.current_figure=fig
        self._add_chart_toolbar(); self.analysis_completed.emit()
