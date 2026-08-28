"""工作表合并 — 追加/JOIN/批量/Sheet"""

import os, pandas as pd
from PySide6.QtWidgets import (QVBoxLayout,QHBoxLayout,QLabel,QPushButton,
    QGroupBox,QFormLayout,QComboBox,QLineEdit,QTableWidget,QTableWidgetItem,
    QFileDialog,QMessageBox,QTextEdit)
from PySide6.QtGui import QFont
from ui.tabs.base_tab import BaseAnalysisTab
from ui.theme import BUTTON_PRIMARY_STRETCH,BUTTON_SECONDARY
from ui.font_config import get_ui_font
from core.sheet_merger import SheetMerger

class SheetMergeTab(BaseAnalysisTab):
    def __init__(self,parent=None):
        super().__init__(parent); self._files=[]; self._setup_ui()
    def _setup_ui(self):
        layout=QVBoxLayout(self); layout.setContentsMargins(12,12,12,12)
        self.title_label=QLabel("工作表合并"); self.title_label.setFont(QFont(get_ui_font(), 18,QFont.Bold))
        layout.addWidget(self.title_label); layout.addSpacing(4)
        # 文件选择
        fg=QGroupBox("选择文件")
        fl=QVBoxLayout(fg)
        self.file_list=QTextEdit(); self.file_list.setReadOnly(True); self.file_list.setMaximumHeight(80)
        fl.addWidget(self.file_list)
        fb=QHBoxLayout()
        btn_add=QPushButton("+ 添加文件"); btn_add.setStyleSheet(BUTTON_SECONDARY); btn_add.clicked.connect(self._add_files)
        btn_clr=QPushButton("清空"); btn_clr.setStyleSheet(BUTTON_SECONDARY); btn_clr.clicked.connect(lambda:(self._files.clear(),self.file_list.clear()))
        fb.addWidget(btn_add); fb.addWidget(btn_clr); fb.addStretch()
        fl.addLayout(fb); layout.addWidget(fg)
        # 模式+运行
        cfg=QGroupBox("合并选项")
        cl=QFormLayout(cfg)
        self.mode=QComboBox(); self.mode.addItems(["纵向追加","按关键列JOIN","批量文件夹"])
        cl.addRow("模式:",self.mode)
        self.key_edit=QLineEdit(); self.key_edit.setPlaceholderText("JOIN关键列名")
        cl.addRow("关键列:",self.key_edit)
        self.btn=QPushButton("执行合并"); self.btn.setStyleSheet(BUTTON_PRIMARY_STRETCH); self.btn.clicked.connect(self._run)
        cl.addRow(self.btn); layout.addWidget(cfg)
        # 预览
        self.preview=QTableWidget(); self.preview.setAlternatingRowColors(True); layout.addWidget(self.preview)
    def _add_files(self):
        fs,_=QFileDialog.getOpenFileNames(self,"选择文件","","Excel/CSV (*.xlsx *.xls *.xlsm *.csv)")
        self._files.extend(fs); self.file_list.setText("\n".join(self._files))
    def _run(self):
        if not self._files:
            QMessageBox.information(self, "提示", "请先添加要合并的文件")
            return
        m=self.mode.currentText()
        try:
            if m=="纵向追加":
                df=SheetMerger.merge_append(self._files)
            elif m=="批量文件夹":
                df=SheetMerger.merge_folder(os.path.dirname(self._files[0]))
            else:
                if len(self._files)<2 or not self.key_edit.text(): return
                df1=pd.read_excel(self._files[0],dtype=str); df2=pd.read_excel(self._files[1],dtype=str)
                df=SheetMerger.merge_join(df1,df2,self.key_edit.text())
            self._show_preview(df)
            path,_=QFileDialog.getSaveFileName(self,"保存合并结果","merged.xlsx","Excel (*.xlsx)")
            if path: df.to_excel(path,index=False); QMessageBox.information(self,"完成",f"已保存 {path}")
        except Exception as e: QMessageBox.critical(self,"错误",str(e))
    def _show_preview(self,df):
        self.preview.setColumnCount(len(df.columns)); self.preview.setHorizontalHeaderLabels(list(df.columns))
        n=min(50,len(df)); self.preview.setRowCount(n)
        for i in range(n):
            for j,c in enumerate(df.columns):
                self.preview.setItem(i,j,QTableWidgetItem(str(df.iloc[i,j])))
        self.preview.resizeColumnsToContents()
