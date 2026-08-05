"""抽样检验 Tab — AQL查表 + 随机/分层/系统抽样 + 序贯"""

import numpy as np, pandas as pd
from typing import Dict, Any
from PySide6.QtWidgets import (
    QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QGroupBox,
    QFormLayout,QComboBox,QSpinBox,QDoubleSpinBox,QTableWidget,
    QTableWidgetItem,QHeaderView,QStackedWidget,QFrame,QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from ui.tabs.base_tab import BaseAnalysisTab
from ui.theme import BUTTON_PRIMARY_STRETCH,BUTTON_SECONDARY,BUTTON_TOGGLE,FONT_18B,FONT_12B
from ui.theme import colors as theme_colors
from core.sampling_engine import SamplingEngine

class SamplingTab(BaseAnalysisTab):
    def __init__(self,p=None): super().__init__(p); self._setup_ui()
    def set_data(self,df,info=None):
        BaseAnalysisTab.set_data(self,df,info)
        if df is not None: self._populate()
    def _setup_ui(self):
        tc=theme_colors(); layout=QVBoxLayout(self); layout.setContentsMargins(12,12,12,12)
        self.title_label=QLabel("抽样检验"); self.title_label.setFont(FONT_18B); layout.addWidget(self.title_label)
        # 模式切换
        mb=QHBoxLayout()
        self.btn_aql=QPushButton("AQL 查表"); self.btn_aql.setCheckable(True); self.btn_aql.setChecked(True); self.btn_aql.setStyleSheet(BUTTON_TOGGLE); self.btn_aql.clicked.connect(lambda:self._switch(0))
        self.btn_rand=QPushButton("随机抽样"); self.btn_rand.setCheckable(True); self.btn_rand.setStyleSheet(BUTTON_TOGGLE); self.btn_rand.clicked.connect(lambda:self._switch(1))
        self.btn_seq=QPushButton("序贯检验"); self.btn_seq.setCheckable(True); self.btn_seq.setStyleSheet(BUTTON_TOGGLE); self.btn_seq.clicked.connect(lambda:self._switch(2))
        mb.addWidget(self.btn_aql); mb.addWidget(self.btn_rand); mb.addWidget(self.btn_seq); mb.addStretch()
        layout.addLayout(mb)
        self.stack=QStackedWidget()
        self.stack.addWidget(self._aql_panel(tc))
        self.stack.addWidget(self._random_panel(tc))
        self.stack.addWidget(self._sequential_panel(tc))
        layout.addWidget(self.stack)
        # 结果表
        self.result=QTableWidget(); self.result.setAlternatingRowColors(True); layout.addWidget(self.result,1)
    def _switch(self,i):
        for b,j in [(self.btn_aql,0),(self.btn_rand,1),(self.btn_seq,2)]: b.setChecked(j==i)
        self.stack.setCurrentIndex(i)

    # ── AQL 面板 ──
    def _aql_panel(self,tc):
        w=QWidget(); l=QFormLayout(w)
        self.aql_lot=QSpinBox(); self.aql_lot.setRange(1,9999999); self.aql_lot.setValue(1000)
        l.addRow("批量:",self.aql_lot)
        self.aql_val=QComboBox(); self.aql_val.addItems(["0.01","0.015","0.025","0.04","0.065","0.10","0.15","0.25","0.40","0.65","1.0","1.5","2.5","4.0","6.5","10","15","25","40","65","100"])
        self.aql_val.setCurrentText("1.0"); l.addRow("AQL:",self.aql_val)
        self.btn_lookup=QPushButton("查表"); self.btn_lookup.setStyleSheet(BUTTON_PRIMARY_STRETCH); self.btn_lookup.clicked.connect(self._do_aql)
        l.addRow(self.btn_lookup); return w

    def _do_aql(self):
        r=SamplingEngine.aql_lookup(self.aql_lot.value(),float(self.aql_val.currentText()))
        self.result.setColumnCount(6); self.result.setHorizontalHeaderLabels(["字码","样本量","Ac","Re","AQL","批量"])
        self.result.setRowCount(1)
        for j,v in enumerate([r["code"],str(r["sample_size"]),str(r["accept"]),str(r["reject"]),str(r["aql_actual"]),str(r["lot_size"])]):
            self.result.setItem(0,j,QTableWidgetItem(v))
        self.result.resizeColumnsToContents()

    # ── 随机抽样面板 ──
    def _random_panel(self,tc):
        w=QWidget(); l=QFormLayout(w)
        self.rand_col=QComboBox(); l.addRow("分层列(可选):",self.rand_col)
        self.rand_n=QSpinBox(); self.rand_n.setRange(1,99999); self.rand_n.setValue(10)
        l.addRow("抽样数量:",self.rand_n)
        self.rand_mode=QComboBox(); self.rand_mode.addItems(["随机","分层","系统"])
        l.addRow("方式:",self.rand_mode)
        self.btn_sample=QPushButton("执行抽样"); self.btn_sample.setStyleSheet(BUTTON_PRIMARY_STRETCH); self.btn_sample.clicked.connect(self._do_sample)
        l.addRow(self.btn_sample); return w
    def _populate(self):
        if self.df is None: return
        self.rand_col.clear(); self.rand_col.addItem("(无)")
        for c in self.df.columns: self.rand_col.addItem(str(c))
    def _do_sample(self):
        if self.df is None: QMessageBox.information(self,"提示","请先导入数据"); return
        n=self.rand_n.value(); m=self.rand_mode.currentText()
        col=self.rand_col.currentText()
        if m=="分层" and col!="(无)":
            df=SamplingEngine.stratified_sample(self.df,col,n)
        elif m=="系统":
            df=SamplingEngine.systematic_sample(self.df,n)
        else:
            df=SamplingEngine.random_sample(self.df,n)
        self._show_df(df)
    def _show_df(self,df):
        self.result.setColumnCount(len(df.columns)); self.result.setHorizontalHeaderLabels(list(df.columns))
        m=min(100,len(df)); self.result.setRowCount(m)
        for i in range(m):
            for j,c in enumerate(df.columns): self.result.setItem(i,j,QTableWidgetItem(str(df.iloc[i,j])))
        self.result.resizeColumnsToContents()

    # ── 序贯面板 ──
    def _sequential_panel(self,tc):
        w=QWidget(); l=QFormLayout(w)
        self.seq_ac=QSpinBox(); self.seq_ac.setRange(0,99); self.seq_ac.setValue(2)
        l.addRow("Ac(接收):",self.seq_ac)
        self.seq_re=QSpinBox(); self.seq_re.setRange(1,99); self.seq_re.setValue(5)
        l.addRow("Re(拒收):",self.seq_re)
        self.seq_n=QSpinBox(); self.seq_n.setRange(1,9999); self.seq_n.setValue(20)
        l.addRow("模拟样本数:",self.seq_n)
        self.btn_seq_run=QPushButton("模拟序贯判定"); self.btn_seq_run.setStyleSheet(BUTTON_PRIMARY_STRETCH); self.btn_seq_run.clicked.connect(self._do_seq)
        l.addRow(self.btn_seq_run); return w

    def _do_seq(self):
        ac=self.seq_ac.value(); re=self.seq_re.value(); n=self.seq_n.value()
        # 模拟缺陷: 缺陷率 ~10%
        results=np.random.choice([0,1],size=n,p=[0.9,0.1]).tolist()
        dec,d,ins=SamplingEngine.sequential_decision(results,ac,re)
        self.result.setColumnCount(4); self.result.setHorizontalHeaderLabels(["判定","缺陷数","检查数","Ac/Re"])
        self.result.setRowCount(1)
        for j,v in enumerate([dec,str(d),str(ins),f"{ac}/{re}"]):
            item=QTableWidgetItem(v)
            if dec=="accept": item.setForeground(QColor("#27ae60"))
            elif dec=="reject": item.setForeground(QColor("#e74c3c"))
            self.result.setItem(0,j,item)
        self.result.resizeColumnsToContents()
