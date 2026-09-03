"""车间大屏模式 — 全屏深色仪表盘 + 大字 KPI + 图表轮播 (v2.4 F4, P2-2 提前)

- showFullScreen 无边框窗口, ESC 退出
- 左侧大数字 KPI 区: 整体 OEE / 最优 Cpk / 违规总数 / 自定义公式值
- 右侧图表轮播: 分析结果图表 8s 自动切换 + 指示圆点 + 手动切换 + 滚轮缩放/拖拽平移
- 顶部信息条: 实时时钟 + 数据文件摘要
- 1920×1080 优化, 布局按比例伸缩自适应
"""

from io import BytesIO
from copy import deepcopy
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QFrame, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QPainter

from core.i18n import i18n
from core.kpi_extractor import extract_metrics
from config.settings import CAPABILITY_GRADES, MSA_GRR_ACCEPTABLE, MSA_GRR_MARGINAL
from ui.theme import FONT_36B, FONT_18B, FONT_14B, FONT_12
from ui.widgets.animate import fade_in, count_up, cross_fade
from ui.widgets.elided_label import ElidedLabel

BG_BIG_SCREEN = "#0c0c12"
BG_KPI_CARD = "#161620"
ACCENT = "#4da6ff"
ACCENT_WARN = "#ffa726"
TEXT_DIM = "#6e7080"

CAROUSEL_INTERVAL_MS = 8000
CLOCK_INTERVAL_MS = 1000
CHART_DPI = 150


class ZoomPixmapView(QGraphicsView):
    """可交互大屏图表查看器 — 滚轮缩放 + 拖拽平移 + 双击复位

    替代静态位图 QLabel: QGraphicsView 场景承载 150dpi 渲染位图,
    支持滚轮以鼠标为锚点缩放、左键拖拽平移、双击回到全图适配。
    """

    MIN_ZOOM = 0.2
    MAX_ZOOM = 10.0

    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self._item = QGraphicsPixmapItem(pixmap)
        self._scene.addItem(self._item)
        self.setScene(self._scene)
        self.setStyleSheet("background: transparent; border: none;")
        self.setFrameShape(QFrame.NoFrame)
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self._user_zoomed = False
        self._zoom = 1.0

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._user_zoomed:
            self._fit()

    def showEvent(self, event):
        super().showEvent(event)
        if not self._user_zoomed:
            self._fit()

    def _fit(self):
        if self.viewport().width() <= 0 or self.viewport().height() <= 0:
            return
        self.resetTransform()
        self.fitInView(self._item, Qt.KeepAspectRatio)
        self._zoom = self.transform().m11()
        self._user_zoomed = False

    def wheelEvent(self, event):
        factor = 1.25 if event.angleDelta().y() > 0 else 0.8
        new_zoom = self._zoom * factor
        if self.MIN_ZOOM <= new_zoom <= self.MAX_ZOOM:
            self.scale(factor, factor)
            self._zoom = new_zoom
            self._user_zoomed = True
        event.accept()

    def mouseDoubleClickEvent(self, event):
        self._fit()


class DisplayModeWindow(QWidget):
    """全屏车间大屏窗口 — 数据来自 MainWindow.analyses 与各 Tab 图表"""

    def __init__(self, main_window):
        super().__init__(None, Qt.Window)
        self._main = main_window
        self._charts = []
        self._figures = []
        self._chart_idx = 0
        self._setup_ui()
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(300)
        self._resize_timer.timeout.connect(self._render_all)
        self._load_data()
        self._start_timers()
        self.setStyleSheet(
            f"QWidget {{ background-color: {BG_BIG_SCREEN}; color: #e1e2e6; }}"
            f"QPushButton {{ background-color: #1b1b28; color: #a0a3ae;"
            f"border: 1px solid #3a3a48; border-radius: 6px; padding: 8px 18px; }}"
            f"QPushButton:hover {{ color: #fff; border-color: {ACCENT}; }}"
        )

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 18, 28, 18)
        root.setSpacing(14)

        top = QHBoxLayout()
        title = QLabel("QA-Tool · " + i18n.tr("display.title"))
        title.setFont(FONT_18B)
        title.setStyleSheet(f"color: {ACCENT}; background: transparent;")
        top.addWidget(title)
        top.addStretch()

        self.data_summary = ElidedLabel("")
        self.data_summary.setFont(FONT_12)
        self.data_summary.setMaximumWidth(600)
        self.data_summary.setStyleSheet(f"color: {TEXT_DIM}; background: transparent;")
        top.addWidget(self.data_summary)
        top.addSpacing(24)

        self.clock_label = QLabel("")
        self.clock_label.setFont(FONT_14B)
        self.clock_label.setStyleSheet(f"color: #e1e2e6; background: transparent;")
        top.addWidget(self.clock_label)
        root.addLayout(top)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background: #262633; border: none;")
        root.addWidget(divider)

        body = QHBoxLayout()
        body.setSpacing(20)

        self.kpi_layout = QVBoxLayout()
        self.kpi_layout.setSpacing(14)
        self.kpi_layout.addStretch()
        body.addLayout(self.kpi_layout, 3)

        chart_wrap = QVBoxLayout()
        chart_wrap.setSpacing(10)
        self.chart_stack = QStackedWidget()
        self.chart_stack.setStyleSheet(
            f"QStackedWidget {{ background: {BG_KPI_CARD}; border: 1px solid #262633;"
            f"border-radius: 10px; }}"
        )
        chart_wrap.addWidget(self.chart_stack, 1)

        ctrl = QHBoxLayout()
        prev_btn = QPushButton("◀ " + i18n.tr("display.prev"))
        prev_btn.clicked.connect(lambda: self._step_chart(-1))
        ctrl.addWidget(prev_btn)
        ctrl.addStretch()
        self.dots_label = QLabel("")
        self.dots_label.setFont(FONT_12)
        self.dots_label.setStyleSheet(f"color: {TEXT_DIM}; background: transparent;")
        ctrl.addWidget(self.dots_label)
        ctrl.addStretch()
        next_btn = QPushButton(i18n.tr("display.next") + " ▶")
        next_btn.clicked.connect(lambda: self._step_chart(1))
        ctrl.addWidget(next_btn)
        chart_wrap.addLayout(ctrl)
        body.addLayout(chart_wrap, 7)

        root.addLayout(body, 1)

        hint = QLabel(i18n.tr("display.hint"))
        hint.setFont(FONT_12)
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet(f"color: {TEXT_DIM}; background: transparent;")
        root.addWidget(hint)

    def _load_data(self):
        data = getattr(self._main, "current_data", {}) or {}
        fpath = data.get("file_path", "")
        if fpath:
            import os
            self.data_summary.setText("📊 " + os.path.basename(fpath))
        else:
            self.data_summary.setText("")

        analyses = getattr(self._main, "analyses", {}) or {}
        metrics_map = extract_metrics(analyses)
        self._build_kpi_tiles(metrics_map, analyses)

        self._build_charts()

    def _build_kpi_tiles(self, metrics_map: dict, analyses: dict):
        while self.kpi_layout.count() > 1:
            item = self.kpi_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        oee_vals = [m["oee"] for m in metrics_map.values() if m.get("oee") is not None]
        cpk_vals = [m["cpk"] for m in metrics_map.values() if m.get("cpk") is not None]
        viol_sum = sum(m.get("violations", 0) or 0 for m in metrics_map.values())
        grr_vals = [m["grr_pct"] for m in metrics_map.values() if m.get("grr_pct") is not None]

        if oee_vals:
            self._add_kpi_tile(i18n.tr("display.kpi_oee"),
                               max(oee_vals) * 100, lambda v: f"{v:.1f}%", ACCENT)
        if cpk_vals:
            best = max(cpk_vals)
            cpk_a = CAPABILITY_GRADES["A"][0]
            cpk_b = CAPABILITY_GRADES["B"][0]
            color = "#27ae60" if best >= cpk_a else (ACCENT_WARN if best >= cpk_b else "#e74c3c")
            self._add_kpi_tile(i18n.tr("display.kpi_cpk"), best, lambda v: f"{v:.3f}", color)
        if grr_vals:
            grr = min(grr_vals)
            color = "#27ae60" if grr < MSA_GRR_ACCEPTABLE else (ACCENT_WARN if grr < MSA_GRR_MARGINAL else "#e74c3c")
            self._add_kpi_tile(i18n.tr("display.kpi_grr"), grr * 100, lambda v: f"{v:.1f}%", color)
        if viol_sum > 0:
            self._add_kpi_tile(i18n.tr("display.kpi_violations"), float(viol_sum),
                               lambda v: f"{int(v)}",
                               "#27ae60" if viol_sum < 10 else "#e74c3c")

        from ui.dialogs.formula_dialog import FormulaDialog
        from core.kpi_formula import evaluate, describe_variables, FormulaError
        formulas = FormulaDialog.load_formulas()
        if formulas:
            variables = describe_variables(analyses)
            shown = 0
            for name, expr in formulas.items():
                try:
                    value = evaluate(str(expr), variables)
                except FormulaError:
                    continue
                self._add_kpi_tile(name, float(value), lambda v: f"{v:.4g}", ACCENT)
                shown += 1
                if shown >= 3:
                    break

    def _add_kpi_tile(self, label: str, value: float, fmt, color: str):
        tile = QFrame()
        tile.setStyleSheet(
            f"QFrame {{ background: {BG_KPI_CARD}; border: 1px solid #262633;"
            f"border-radius: 12px; }}"
        )
        l = QVBoxLayout(tile)
        l.setContentsMargins(22, 16, 22, 16)
        name_lbl = QLabel(label)
        name_lbl.setFont(FONT_14B)
        name_lbl.setStyleSheet(f"color: {TEXT_DIM}; background: transparent;")
        l.addWidget(name_lbl)
        val_lbl = QLabel("")
        val_lbl.setFont(FONT_36B)
        val_lbl.setStyleSheet(f"color: {color}; background: transparent;")
        l.addWidget(val_lbl)
        self.kpi_layout.insertWidget(self.kpi_layout.count() - 1, tile)
        count_up(val_lbl, value, fmt)
        fade_in(tile)

    def _build_charts(self):
        self._figures.clear()
        tabs = getattr(self._main, "_get_tabs", lambda: {})()
        analyses = getattr(self._main, "analyses", {}) or {}
        for idx in sorted(analyses.keys()):
            tab = tabs.get(idx)
            fig = getattr(tab, "current_figure", None) if tab else None
            if fig is None:
                continue
            atype = analyses[idx].get("analysis_type", f"analysis_{idx}")
            self._figures.append((atype, fig))
        self._render_all()

    def _target_chart_size(self):
        w = self.chart_stack.width()
        h = self.chart_stack.height()
        if w <= 0 or h <= 0:
            w, h = 1344, 900
        return w, h

    def _render_figure(self, fig, target_w, target_h):
        try:
            fig2 = deepcopy(fig)
            fig2.set_size_inches(target_w / CHART_DPI, target_h / CHART_DPI,
                                 forward=False)
        except Exception:
            fig2 = fig
        try:
            buf = BytesIO()
            fig2.savefig(buf, format="png", dpi=CHART_DPI,
                         bbox_inches="tight", facecolor="white")
            buf.seek(0)
            pm = QPixmap()
            if pm.loadFromData(buf.read()):
                return pm
        except Exception:
            pass
        return None

    def _render_all(self):
        self._charts.clear()
        target_w, target_h = self._target_chart_size()
        for atype, fig in self._figures:
            pm = self._render_figure(fig, target_w, target_h)
            if pm is not None:
                self._charts.append((atype, pm))

        while self.chart_stack.count() > 0:
            w = self.chart_stack.widget(0)
            self.chart_stack.removeWidget(w)
            w.setParent(None)
            w.deleteLater()

        for _label, pm in self._charts:
            view = ZoomPixmapView(pm)
            self.chart_stack.addWidget(view)

        if not self._charts:
            empty = QLabel(i18n.tr("display.no_charts"))
            empty.setFont(FONT_18B)
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(f"color: {TEXT_DIM}; background: transparent;")
            self.chart_stack.addWidget(empty)
        if self._chart_idx >= max(len(self._charts), 1):
            self._chart_idx = 0
        self._update_carousel()

    def _step_chart(self, delta: int):
        if not self._charts:
            return
        self._chart_idx = (self._chart_idx + delta) % len(self._charts)
        self._update_carousel()

    def _update_carousel(self):
        if self._charts:
            cross_fade(self.chart_stack, self._chart_idx)
            dots = " ".join(
                "●" if i == self._chart_idx else "○"
                for i in range(len(self._charts))
            )
            self.dots_label.setText(
                f"{self._charts[self._chart_idx][0]}   {dots}")
        else:
            self.chart_stack.setCurrentIndex(0)
            self.dots_label.setText("")

    def _start_timers(self):
        self._clock_timer = QTimer(self)
        self._clock_timer.setInterval(CLOCK_INTERVAL_MS)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start()
        self._update_clock()

        self._carousel_timer = QTimer(self)
        self._carousel_timer.setInterval(CAROUSEL_INTERVAL_MS)
        self._carousel_timer.timeout.connect(lambda: self._step_chart(1))
        self._carousel_timer.start()

    def _update_clock(self):
        now = datetime.now()
        self.clock_label.setText(now.strftime("%Y-%m-%d  %H:%M:%S  %A"))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_timer.start()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
            return
        if event.key() == Qt.Key_Left:
            self._step_chart(-1)
            return
        if event.key() == Qt.Key_Right:
            self._step_chart(1)
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        self._carousel_timer.stop()
        self._clock_timer.stop()
        super().closeEvent(event)
