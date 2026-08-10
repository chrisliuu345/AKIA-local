"""Dashboard 汇总面板 — Cp/Cpk仪表盘 + OEE KPI + SPC违规统计 + 批量导出"""

from PySide6.QtWidgets import (
    QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QGroupBox,
    QGridLayout,QFrame,QScrollArea,QFileDialog,QMessageBox,QProgressBar,
    QCheckBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont,QColor
from ui.tabs.base_tab import BaseAnalysisTab
from ui.theme import BUTTON_PRIMARY_STRETCH,BUTTON_SECONDARY,FONT_18B,FONT_12B,FONT_14B,FONT_10
from ui.theme import colors as theme_colors
from core.formatting import format_cp,format_pvalue

class DashboardTab(BaseAnalysisTab):
    def __init__(self,p=None): super().__init__(p); self._cards=[]; self._setup_ui()
    def _setup_ui(self):
        tc=theme_colors(); layout=QVBoxLayout(self); layout.setContentsMargins(12,12,12,12)
        hdr=QHBoxLayout()
        self.title_label=QLabel("Dashboard 分析汇总"); self.title_label.setFont(FONT_18B); hdr.addWidget(self.title_label)
        hdr.addStretch()
        self.btn_refresh=QPushButton("刷新"); self.btn_refresh.setStyleSheet(BUTTON_SECONDARY); self.btn_refresh.clicked.connect(self.refresh); hdr.addWidget(self.btn_refresh)
        self.btn_export=QPushButton("批量导出"); self.btn_export.setStyleSheet(BUTTON_PRIMARY_STRETCH); self.btn_export.clicked.connect(self._batch_export); hdr.addWidget(self.btn_export)
        layout.addLayout(hdr)
        # 卡片网格
        scroll=QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
        self.card_container=QWidget(); self.grid=QGridLayout(self.card_container); self.grid.setSpacing(12)
        scroll.setWidget(self.card_container); layout.addWidget(scroll,1)

    def refresh(self):
        # 清除旧卡片
        for c in self._cards:
            if c.parent(): c.setParent(None)
        self._cards.clear()
        while self.grid.count(): self.grid.takeAt(0)
        # 从父窗口获取分析结果
        parent=self.window()
        if not parent or not hasattr(parent,'analyses'):
            self.grid.addWidget(QLabel("请先运行分析"),0,0); return
        analyses=parent.analyses
        if not analyses:
            self.grid.addWidget(QLabel("请先运行分析"),0,0); return
        tc=theme_colors(); col=0; row=0
        for idx,result in sorted(analyses.items()):
            atype=result.get("analysis_type","Unknown")
            r=result.get("result",{}); params=result.get("params",{})
            card=self._make_card(atype,params,r,idx,tc)
            self.grid.addWidget(card,row,col); self._cards.append(card)
            col+=1
            if col>2: col=0; row+=1

    def _make_card(self,atype,params,r,idx,tc):
        frame=QFrame(); frame.setFixedSize(230,150)
        frame.setStyleSheet(f"QFrame {{ background:{tc['bg_card']}; border:1px solid {tc['border']}; border-radius:10px; padding:10px; }}")
        l=QVBoxLayout(frame); l.setSpacing(4)
        # 标题
        title=QLabel(atype[:25]+(".." if len(atype)>25 else "")); title.setFont(FONT_10); title.setStyleSheet(f"color:{tc['accent_bright']}; font-weight:bold;")
        l.addWidget(title)
        # 关键指标
        cap=r.get("capability",{})
        if cap:
            cp=cap.get("cp"); cpk=cap.get("cpk"); grade=cap.get("grade","")
            l.addWidget(QLabel(f"Cp={format_cp(cp) if cp else '-'}  Cpk={format_cp(cpk) if cpk else '-'}"))
            l.addWidget(QLabel(f"等级: {grade}"))
        oee=r.get("oee"); avail=r.get("availability"); perf=r.get("performance"); qual=r.get("quality")
        if oee is not None:
            l.addWidget(QLabel(f"OEE: {oee*100:.1f}%  A:{avail*100:.0f}% P:{perf*100:.0f}% Q:{qual*100:.0f}%"))
        pv=r.get("p_value")
        if pv is not None:
            l.addWidget(QLabel(f"p值: {format_pvalue(pv)}"))
        grr=r.get("grr_percent")
        if grr:
            l.addWidget(QLabel(f"%GRR: {grr*100:.1f}%"))
        viols=r.get("violations",[])
        if viols:
            l.addWidget(QLabel(f"违规点: {len(viols)}个"))
        l.addStretch()
        return frame

    def _batch_export(self):
        parent=self.window()
        if not parent or not hasattr(parent,'analyses') or not parent.analyses:
            QMessageBox.information(self,"提示","请先运行分析")
            return
        path,_=QFileDialog.getSaveFileName(self,"导出ZIP","dashboard_export.zip","ZIP (*.zip)")
        if not path: return
        import zipfile,io
        from output.chart_engine import figure_to_bytes
        with zipfile.ZipFile(path,'w') as zf:
            for idx,r in parent.analyses.items():
                atype=r.get("analysis_type",f"analysis_{idx}")
                # Excel 导出
                try:
                    from output.excel_report import ExcelReport
                    buf=io.BytesIO()
                    ExcelReport().generate([r],buf)
                    buf.seek(0); zf.writestr(f"{atype}.xlsx",buf.read())
                except Exception:
                    import logging
                    logging.warning(f"dashboard: 导出 {atype} 失败", exc_info=True)
                # 图表 PNG
                tab=parent._get_tabs().get(idx)
                if tab and hasattr(tab,'current_figure') and tab.current_figure:
                    buf=figure_to_bytes(tab.current_figure,'png')
                    zf.writestr(f"{atype}_chart.png",buf.read())
        QMessageBox.information(self,"导出完成",f"已保存到 {path}")
