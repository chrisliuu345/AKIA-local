"""工作表拆分 — 按列值/行数/条件/分组"""

import pandas as pd
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,
    QGroupBox,QFormLayout,QComboBox,QLineEdit,QSpinBox,QDoubleSpinBox,
    QFileDialog,QMessageBox)
from PySide6.QtGui import QFont
from ui.tabs.base_tab import BaseAnalysisTab
from ui.theme import BUTTON_PRIMARY_STRETCH,BUTTON_SECONDARY
from core.sheet_splitter import SheetSplitter

class SheetSplitTab(BaseAnalysisTab):
    def __init__(self,parent=None):
        super().__init__(parent); self._file=""; self._output=""; self._setup_ui()
    def _setup_ui(self):
        layout=QVBoxLayout(self); layout.setContentsMargins(12,12,12,12)
        self.title_label=QLabel("工作表拆分"); self.title_label.setFont(QFont("Microsoft YaHei",18,QFont.Bold))
        layout.addWidget(self.title_label); layout.addSpacing(4)
        fg=QGroupBox("源文件")
        fl=QHBoxLayout(fg)
        self.file_lbl=QLabel("未选择文件"); fl.addWidget(self.file_lbl,1)
        btn_open=QPushButton("打开文件"); btn_open.setStyleSheet(BUTTON_SECONDARY); btn_open.clicked.connect(self._open)
        fl.addWidget(btn_open); layout.addWidget(fg)
        cfg=QGroupBox("拆分选项")
        cl=QFormLayout(cfg)
        self.mode=QComboBox(); self.mode.addItems(["按列值","按行数","按条件","按分组"])
        cl.addRow("模式:",self.mode)
        self.col_edit=QLineEdit(); self.col_edit.setPlaceholderText("拆分列名")
        cl.addRow("列名:",self.col_edit)
        self.row_spin=QSpinBox(); self.row_spin.setRange(100,100000); self.row_spin.setValue(5000)
        cl.addRow("每文件行数:",self.row_spin)
        self.op=QComboBox(); self.op.addItems(["<",">","<=",">=","=="])
        self.threshold=QDoubleSpinBox(); self.threshold.setRange(-9999,9999); self.threshold.setValue(1.0)
        cl.addRow("条件:",QWidget())
        cl.addRow(self.op,self.threshold)
        self.btn=QPushButton("执行拆分"); self.btn.setStyleSheet(BUTTON_PRIMARY_STRETCH); self.btn.clicked.connect(self._run)
        cl.addRow(self.btn); layout.addWidget(cfg)
    def _open(self):
        f,_=QFileDialog.getOpenFileName(self,"打开","","Excel (*.xlsx *.xls *.xlsm)")
        if f: self._file=f; self.file_lbl.setText(f); self.df=pd.read_excel(f)
    def _run(self):
        if not self._file:
            QMessageBox.information(self, "提示", "请先打开一个Excel文件")
            return
        out=QFileDialog.getExistingDirectory(self,"输出目录")
        if not out: return
        m=self.mode.currentText()
        try:
            if m=="按列值":
                paths=SheetSplitter.split_by_column(self.df,self.col_edit.text(),out)
            elif m=="按行数":
                paths=SheetSplitter.split_by_rows(self.df,self.row_spin.value(),out)
            elif m=="按条件":
                paths=SheetSplitter.split_by_condition(self.df,self.col_edit.text(),self.op.currentText(),self.threshold.value(),out)
            else:
                cols=[c.strip() for c in self.col_edit.text().split(",") if c.strip()]
                paths=SheetSplitter.split_by_group(self.df,cols,out)
            QMessageBox.information(self,"完成",f"已生成 {len(paths)} 个文件到 {out}")
        except Exception as e: QMessageBox.critical(self,"错误",str(e))
