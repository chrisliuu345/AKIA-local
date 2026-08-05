"""智能诊断对话框 V2 — 健康仪表 + 分组推荐 + 置信度可视化"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QWidget, QGridLayout, QProgressBar,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from ui.theme import colors as theme_colors

ICON_COLORS = {
    "SPC": "#1b5faa", "CPK": "#217ca3", "MSA": "#6b4c9a",
    "TTEST": "#b85c38", "DOE": "#9467bd", "REG": "#17becf",
    "IE7": "#2e7d32", "IE8": "#558b2f", "IE9": "#827717",
    "IE10": "#00695c", "IE11": "#00838f",
    "CHT": "#4a148c", "CPC": "#0277bd", "TRD": "#e65100", "SUM": "#bf360c",
    "REL": "#1a237e", "FMEA": "#880e4f",
}
CONF_COLORS = {"highly_recommended": "#27ae60", "recommended": "#ffa726", "optional": "#6e7080"}


class DiagnosisDialog(QDialog):
    apply_clicked = Signal(dict)

    def __init__(self, profile: dict, parent=None):
        super().__init__(parent)
        self.profile = profile
        self.setWindowTitle("数据智能诊断")
        self.setMinimumSize(720, 600)
        self.resize(780, 680)
        self._setup_ui()

    def _setup_ui(self):
        tc = theme_colors()
        self.setStyleSheet(f"background-color: {tc['bg_body']};")
        root = QVBoxLayout(self); root.setSpacing(10)

        # 标题行
        title_row = QHBoxLayout()
        title = QLabel("数据智能诊断")
        title.setFont(QFont("Microsoft YaHei", 20, QFont.Bold))
        title_row.addWidget(title)
        title_row.addStretch()
        btn_export = QPushButton("导出报告")
        btn_export.setFont(QFont("Microsoft YaHei", 10))
        btn_export.setFixedHeight(32)
        btn_export.setCursor(Qt.PointingHandCursor)
        btn_export.setStyleSheet(
            f"QPushButton {{ background: {tc['bg_card']}; color: {tc['accent_bright']}; border: 1px solid {tc['accent']}; "
            f"border-radius: 6px; padding: 6px 16px; }} QPushButton:hover {{ background: {tc['bg_hover']}; }}")
        btn_export.clicked.connect(self._export_report)
        title_row.addWidget(btn_export)
        btn_all = QPushButton("全部应用")
        btn_all.setFont(QFont("Microsoft YaHei", 10))
        btn_all.setFixedHeight(32)
        btn_all.setCursor(Qt.PointingHandCursor)
        btn_all.setStyleSheet(
            f"QPushButton {{ background: {tc['accent']}; color: white; border: none; "
            f"border-radius: 6px; padding: 6px 20px; }} "
            f"QPushButton:hover {{ background: {tc['accent_dark']}; }}")
        btn_all.clicked.connect(self._apply_all)
        title_row.addWidget(btn_all)
        root.addLayout(title_row)

        # 全局摘要
        gs = self.profile.get("global_summary", {})
        overview = QLabel(
            f"工作表 {gs.get('total_sheets',0)} 个 · "
            f"总行数 {gs.get('total_rows',0):,} · "
            f"数据问题 {gs.get('total_issues',0)} 个")
        overview.setFont(QFont("Microsoft YaHei", 10))
        overview.setStyleSheet(f"color: {tc['text_secondary']}; padding: 2px 0;")
        root.addWidget(overview)

        # ── 健康仪表 ──
        all_health = []
        for s in self.profile.get("sheets", {}).values():
            h = s.get("health", {})
            if h: all_health.append(h)
        if all_health:
            avg_h = {k: sum(x.get(k, 0) for x in all_health) / len(all_health)
                     for k in ("completeness", "normality", "stability", "resolution")}
            gauge_row = QHBoxLayout(); gauge_row.setSpacing(12)
            names = [("completeness", "完整性"), ("normality", "正态性"),
                     ("stability", "稳定性"), ("resolution", "分辨力")]
            for key, label in names:
                v = avg_h[key]
                gauge_row.addWidget(self._make_gauge(label, v, tc), 1)
            root.addLayout(gauge_row)

        # ── 滚动内容 ──
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        clayout = QVBoxLayout(content); clayout.setSpacing(10)

        for sn, sheet in self.profile.get("sheets", {}).items():
            clayout.addWidget(self._make_sheet_section(sn, sheet, tc))

        clayout.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        close_btn = QPushButton("关闭")
        close_btn.setFont(QFont("Microsoft YaHei", 11))
        close_btn.setMinimumHeight(36)
        close_btn.clicked.connect(self.close)
        root.addWidget(close_btn)

    def _make_gauge(self, label: str, value: float, tc: dict) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: {tc['bg_card']}; border: 1px solid {tc['border_light']}; "
            f"border-radius: 8px; padding: 10px; }}")
        layout = QVBoxLayout(card); layout.setSpacing(4)

        title = QLabel(label)
        title.setFont(QFont("Microsoft YaHei", 9))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {tc['text_secondary']}; background: transparent;")
        layout.addWidget(title)

        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(int(value * 100))
        bar.setTextVisible(False)
        bar.setFixedHeight(6)
        bar.setStyleSheet(
            f"QProgressBar {{ background: {tc['bg_body']}; border: none; border-radius: 3px; }} "
            f"QProgressBar::chunk {{ background: {self._gauge_color(value)}; border-radius: 3px; }}")
        layout.addWidget(bar)

        pct = QLabel(f"{int(value * 100)}%")
        pct.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        pct.setAlignment(Qt.AlignCenter)
        pct.setStyleSheet(f"color: {self._gauge_color(value)}; background: transparent;")
        layout.addWidget(pct)
        return card

    @staticmethod
    def _gauge_color(v: float) -> str:
        if v >= 0.8: return "#27ae60"
        if v >= 0.5: return "#ffa726"
        return "#e74c3c"

    def _make_sheet_section(self, sn: str, sheet: dict, tc: dict) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: {tc['bg_card']}; border: 1px solid {tc['border_light']}; "
            f"border-radius: 10px; padding: 14px; }}")
        layout = QVBoxLayout(card); layout.setSpacing(8)

        # Header
        hdr = QHBoxLayout()
        hl = QLabel(f" {sn}")
        hl.setFont(QFont("Microsoft YaHei", 13, QFont.Bold))
        hdr.addWidget(hl)
        info = QLabel(f"{sheet['row_count']} 行  {sheet['column_count']} 列")
        info.setFont(QFont("Microsoft YaHei", 10))
        info.setStyleSheet(f"color: {tc['text_secondary']};")
        hdr.addWidget(info)
        hdr.addStretch()
        layout.addLayout(hdr)

        # 列表格
        cols = sheet.get("columns", [])
        if cols:
            grid = QGridLayout(); grid.setSpacing(3)
            headers = ["列名", "类型", "缺失%", "偏度", "异常点", "分布"]
            for j, h in enumerate(headers):
                lbl = QLabel(h)
                lbl.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
                lbl.setStyleSheet(f"color: {tc['text_secondary']}; padding: 2px 4px;")
                grid.addWidget(lbl, 0, j)
            for i, c in enumerate(cols[:12], 1):
                vals = [
                    c["name"][:20] + (".." if len(c["name"]) > 20 else ""),
                    c["category"], str(c["missing_pct"]),
                    f"{c.get('skewness', '-'):.2f}" if isinstance(c.get("skewness"), float) else "-",
                    str(c.get("outlier_count", "-")),
                    c.get("distribution", "-"),
                ]
                for j, v in enumerate(vals):
                    lbl = QLabel(v)
                    lbl.setFont(QFont("Microsoft YaHei", 9))
                    lbl.setStyleSheet(f"color: {tc['text_primary']}; padding: 1px 4px;")
                    if j == 1 and c["category"] == "measurement":
                        lbl.setStyleSheet(f"color: {tc['accent_bright']}; font-weight: bold; padding: 1px 4px;")
                    if c["missing_pct"] > 10:
                        lbl.setStyleSheet(f"color: #e74c3c; padding: 1px 4px;")
                    if j == 5:
                        dist = c.get("distribution", "-")
                        if dist == "normal":
                            lbl.setStyleSheet("color: #27ae60; font-weight: bold; padding: 1px 4px;")
                        elif dist == "skewed":
                            lbl.setStyleSheet("color: #ffa726; padding: 1px 4px;")
                    grid.addWidget(lbl, i, j)
            layout.addLayout(grid)

        # 推荐 — 按置信度分组
        recs = sheet.get("recommendations", [])
        if recs:
            high_recs = [r for r in recs if r["confidence"]["grade"] == "highly_recommended"]
            mid_recs = [r for r in recs if r["confidence"]["grade"] == "recommended"]
            low_recs = [r for r in recs if r["confidence"]["grade"] == "optional"]

            for group_title, group_recs, star in [
                ("高度推荐", high_recs, "★"),
                ("建议尝试", mid_recs, "☆"),
                ("可选用", low_recs, "·")]:
                if not group_recs: continue
                sec = QLabel(f" {star} {group_title} ({len(group_recs)})")
                sec.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
                sec.setStyleSheet(f"color: {CONF_COLORS.get(group_recs[0]['confidence']['grade'], tc['accent'])}; padding: 4px 0;")
                layout.addWidget(sec)
                for rec in group_recs[:5]:
                    layout.addLayout(self._make_rec_row(rec, tc))

        # 问题
        issues = sheet.get("issues", [])
        if issues:
            layout.addSpacing(4)
            for iss in issues[:5]:
                il = QLabel(f"  {iss}")
                il.setFont(QFont("Microsoft YaHei", 9))
                il.setStyleSheet("color: #e74c3c;")
                layout.addWidget(il)
        return card

    def _make_rec_row(self, rec: dict, tc: dict) -> QHBoxLayout:
        row = QHBoxLayout(); row.setSpacing(8)

        # 图标
        icon_text = rec["icon"][:3]
        icon = QLabel(icon_text)
        icon.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        icon.setFixedSize(38, 38)
        icon.setAlignment(Qt.AlignCenter)
        icolor = ICON_COLORS.get(rec["icon"], tc["accent"])
        icon.setStyleSheet(
            f"color: white; background: {icolor}; border-radius: 8px; font-size: 10px;")
        row.addWidget(icon)

        # 中间文字
        text_col = QVBoxLayout(); text_col.setSpacing(2)
        title = QLabel(f"{rec['tab_name']} · {rec['method']}")
        title.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        title.setStyleSheet(f"color: {tc['text_primary']};")
        text_col.addWidget(title)
        reason = QLabel(rec["reason"])
        reason.setFont(QFont("Microsoft YaHei", 9))
        reason.setStyleSheet(f"color: {tc['text_muted']};")
        text_col.addWidget(reason)

        # 置信度条
        conf = rec.get("confidence", {})
        pct = conf.get("percentage", 0.5)
        cbar = QProgressBar()
        cbar.setRange(0, 100); cbar.setValue(int(pct * 100))
        cbar.setTextVisible(True); cbar.setFormat(f" {int(pct * 100)}%")
        cbar.setFixedSize(60, 16)
        cbar.setFont(QFont("Microsoft YaHei", 8))
        ccolor = CONF_COLORS.get(conf.get("grade", "optional"), "#6e7080")
        cbar.setStyleSheet(
            f"QProgressBar {{ background: {tc['bg_body']}; border: none; border-radius: 3px; text-align: center; }} "
            f"QProgressBar::chunk {{ background: {ccolor}; border-radius: 3px; }}")
        row.addLayout(text_col, 1)
        row.addWidget(cbar)

        btn = QPushButton("配置")
        btn.setFont(QFont("Microsoft YaHei", 9))
        btn.setFixedSize(52, 28)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(
            f"QPushButton {{ background: {tc['accent']}; color: white; border: none; "
            f"border-radius: 5px; }} QPushButton:hover {{ background: {tc['accent_dark']}; }}")
        btn.clicked.connect(lambda checked, r=rec: self.apply_clicked.emit(r))
        row.addWidget(btn)
        return row

    def _export_report(self):
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        import pandas as pd
        path, _ = QFileDialog.getSaveFileName(self, "导出诊断报告", "diagnosis_report.xlsx", "Excel (*.xlsx)")
        if not path: return
        rows = []
        for sn, sheet in self.profile.get("sheets", {}).items():
            for rec in sheet.get("recommendations", []):
                rows.append({"Sheet": sn, "推荐模块": rec["tab_name"], "方法": rec["method"],
                    "置信度": f"{rec['confidence']['percentage']*100:.0f}%", "原因": rec["reason"]})
        if rows:
            pd.DataFrame(rows).to_excel(path, index=False)
            QMessageBox.information(self, "导出完成", f"已保存 {path}")

    def _apply_all(self):
        for sheet in self.profile.get("sheets", {}).values():
            for rec in sheet.get("recommendations", []):
                if rec["confidence"]["grade"] in ("highly_recommended", "recommended"):
                    self.apply_clicked.emit(rec)
                    return  # 应用第一个高/中置信度推荐
