"""LPA分层审核表 — 模板选择 + Excel导出"""

from PySide6.QtWidgets import (QVBoxLayout,QLabel,QPushButton,
    QGroupBox,QFormLayout,QLineEdit,QTextEdit,QFileDialog,QMessageBox,
    QCheckBox)
from PySide6.QtGui import QFont
from ui.tabs.base_tab import BaseAnalysisTab
from ui.theme import BUTTON_PRIMARY_STRETCH
from ui.theme import colors as theme_colors
from ui.font_config import get_ui_font
from core.layered_form import LPAEngine,LPA_TEMPLATES

class LayeredFormTab(BaseAnalysisTab):
    def __init__(self,parent=None):
        super().__init__(parent); self._setup_ui()
    def _setup_ui(self):
        tc=theme_colors()
        layout=QVBoxLayout(self); layout.setContentsMargins(12,12,12,12)
        self.title_label=QLabel("LPA 分层审核表"); self.title_label.setFont(QFont(get_ui_font(), 18,QFont.Bold))
        layout.addWidget(self.title_label); layout.addSpacing(4)
        cfg=QGroupBox("模板配置")
        cl=QFormLayout(cfg)
        self.proc_edit=QLineEdit(); self.proc_edit.setPlaceholderText("工序1,工序2,工序3 (逗号分隔)")
        self.proc_edit.setText("来料检验,CNC加工,热处理,最终检验")
        cl.addRow("工序列表:",self.proc_edit)
        self.auditor_edit=QLineEdit(); self.auditor_edit.setPlaceholderText("审核员A,审核员B")
        self.auditor_edit.setText("审核员A,审核员B")
        cl.addRow("审核员:",self.auditor_edit)
        layout.addWidget(cfg)
        # 检查项选择
        cg=QGroupBox("检查项类别")
        cgl=QVBoxLayout(cg)
        self.checks={}
        for cat,items in LPA_TEMPLATES.items():
            cb=QCheckBox(f"{cat} ({len(items)}项)"); cb.setChecked(True)
            cb.setStyleSheet(f"color: {tc['text_primary']};")
            self.checks[cat]=cb; cgl.addWidget(cb)
        layout.addWidget(cg)
        self.btn=QPushButton("生成 LPA 检查表 (Excel)")
        self.btn.setStyleSheet(BUTTON_PRIMARY_STRETCH); self.btn.clicked.connect(self._run)
        layout.addWidget(self.btn)
        # 预览
        self.preview=QTextEdit(); self.preview.setReadOnly(True); layout.addWidget(self.preview,1)
        self._show_preview()
    def _show_preview(self):
        lines=["=== LPA 分层审核表预览 ===\n"]
        for cat,items in LPA_TEMPLATES.items():
            lines.append(f"[{cat}]")
            for name,desc,method in items:
                lines.append(f"  • {name}: {desc}  [{method}]")
        self.preview.setText("\n".join(lines))
    def _run(self):
        procs=[p.strip() for p in self.proc_edit.text().split(",") if p.strip()]
        auditors=[a.strip() for a in self.auditor_edit.text().split(",") if a.strip()]
        cats=[c for c,cb in self.checks.items() if cb.isChecked()]
        if not procs or not cats: return
        path,_=QFileDialog.getSaveFileName(self,"保存","LPA_Checklist.xlsx","Excel (*.xlsx)")
        if path:
            LPAEngine.generate_excel(procs,cats,auditors,path)
            QMessageBox.information(self,"完成",f"已生成 {path}")
