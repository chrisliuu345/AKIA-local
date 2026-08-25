"""Dashboard 汇总面板 v3.0 — 垂直滚动 + 图表嵌入 + KPI 提取器 + 批量导出

v3.0 重构:
- 从卡片网格改为垂直滚动窗口，每张分析卡片纵向排列
- 卡片内嵌入 matplotlib 图表快照 (QPixmap)
- 增强 KPI 提取器覆盖所有分析类型
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QFileDialog, QMessageBox, QCheckBox,
)
from PySide6.QtCore import QTimer, QSettings, Qt
from PySide6.QtGui import QFont
from ui.tabs.base_tab import BaseAnalysisTab
from ui.theme import BUTTON_PRIMARY_STRETCH, BUTTON_SECONDARY, FONT_18B
from ui.theme import colors as theme_colors
from ui.widgets.elided_label import ElidedLabel
from ui.widgets.animate import fade_in
from ui.widgets.analysis_card import AnalysisCard
from core.formatting import format_cp, format_pvalue, format_pct
from core.i18n import i18n
from core.kpi_extractor import extract_metrics
from core.kpi_formula import evaluate, describe_variables, FormulaError

# 指标显示名 (i18n 键) + 格式化器
# 百分比类指标统一为 0-1 分数 (extractor 已归一化), format_pct 直接使用
_METRIC_SPECS = {
    "cp":           ("dashboard.metric.cp",        format_cp),
    "cpk":          ("dashboard.metric.cpk",       format_cp),
    "pp":           ("dashboard.metric.pp",        format_cp),
    "ppk":          ("dashboard.metric.ppk",       format_cp),
    "sigma_level":  ("dashboard.metric.sigma",     lambda v: f"{v:.2f}"),
    "ppm_total":    ("dashboard.metric.ppm",       lambda v: f"{v:,.0f}"),
    "grade":        ("dashboard.metric.grade",     lambda v: str(v)),
    "oee":          ("dashboard.metric.oee",       format_pct),
    "availability": ("dashboard.metric.avail",     format_pct),
    "performance":  ("dashboard.metric.perf",      format_pct),
    "quality":      ("dashboard.metric.qual",      format_pct),
    "grr_pct":      ("dashboard.metric.grr",       format_pct),
    "ndc":          ("dashboard.metric.ndc",       lambda v: f"{v:.0f}"),
    "acceptance":   ("dashboard.metric.accept",    lambda v: str(v)),
    "p_value":      ("dashboard.metric.p",         format_pvalue),
    "is_significant": ("dashboard.metric.signif",  lambda v: i18n.tr("dashboard.significant") if v else i18n.tr("dashboard.not_significant")),
    "r_squared":    ("dashboard.metric.r2",        lambda v: f"{v:.3f}"),
    "violations":   ("dashboard.metric.viol",      lambda v: f"{v}"),
    "mtbf":         ("dashboard.metric.mtbf",      lambda v: f"{v:.1f}"),
    "mttr":         ("dashboard.metric.mttr",      lambda v: f"{v:.1f}"),
    "balance_rate": ("dashboard.metric.balance",   format_pct),
    "efficiency":   ("dashboard.metric.efficiency", format_pct),
    "va_ratio":     ("dashboard.metric.va_ratio",  format_pct),
    "lead_time_days": ("dashboard.metric.lead_time", lambda v: f"{v:.1f}"),
    "lead_time":    ("dashboard.metric.lead_time",  lambda v: f"{v:.1f}"),
    "b10_life":     ("dashboard.metric.b10",       lambda v: f"{v:.1f}"),
    "characteristic_life": ("dashboard.metric.char_life", lambda v: f"{v:.1f}"),
    "mean_life":    ("dashboard.metric.mean_life",  lambda v: f"{v:.1f}"),
    "cycle_time":   ("dashboard.metric.cycle_time", lambda v: f"{v:.2f}"),
    "takt_time":    ("dashboard.metric.takt",       lambda v: f"{v:.2f}"),
    "standard_time": ("dashboard.metric.std_time",  lambda v: f"{v:.2f}"),
    "bottleneck_count": ("dashboard.metric.bottleneck", lambda v: f"{v}"),
    "worker_utilization": ("dashboard.metric.utilization", format_pct),
    # v3.0 新增: 公差区间 / SMED / 多工厂 / 时间研究
    "tolerance_lower":  ("dashboard.metric.tol_lower", lambda v: f"{v:.2f}"),
    "tolerance_upper":  ("dashboard.metric.tol_upper", lambda v: f"{v:.2f}"),
    "tolerance_width":  ("dashboard.metric.tol_width", lambda v: f"{v:.2f}"),
    "confidence":       ("dashboard.metric.confidence", format_pct),
    "proportion":       ("dashboard.metric.proportion", format_pct),
    "improvement_pct":  ("dashboard.metric.improve",    format_pct),
    "total_before":     ("dashboard.metric.total_before", lambda v: f"{v:.1f}s"),
    "total_after":      ("dashboard.metric.total_after",  lambda v: f"{v:.1f}s"),
    "best_cpk":         ("dashboard.metric.best_cpk",    format_cp),
    "worst_cpk":        ("dashboard.metric.worst_cpk",   format_cp),
    "total_violations": ("dashboard.metric.total_viol",  lambda v: f"{v}"),
}

_REFRESH_INTERVAL_MS = 5000

_STATUS_RANK = {"na": 0, "good": 1, "warn": 2, "bad": 3}
_STATUS_COLORS = {"na": "#6e7080", "good": "#27ae60", "warn": "#ffa726", "bad": "#e74c3c"}


def _cpk_status(cpk):
    if cpk is None:
        return None
    if cpk < 1.0:
        return "bad"
    if cpk < 1.33:
        return "warn"
    return "good"


def _oee_status(oee):
    if oee is None:
        return None
    if oee < 0.6:
        return "bad"
    if oee < 0.8:
        return "warn"
    return "good"


def _grr_status(grr):
    if grr is None:
        return None
    if grr >= 0.3:
        return "bad"
    if grr >= 0.1:
        return "warn"
    return "good"


class DashboardTab(BaseAnalysisTab):
    def __init__(self, p=None):
        super().__init__(p)
        self._cards = []
        self._last_fp = ""
        self._df_cache = None
        self._df_cache_key = None
        self._settings = QSettings("QA-Tool", "Dashboard")
        # F1: 轮询兜底定时器
        self._timer = QTimer(self)
        self._timer.setInterval(_REFRESH_INTERVAL_MS)
        self._timer.timeout.connect(self._poll_refresh)
        self._setup_ui()
        self._timer.start()

    def _setup_ui(self):
        tc = theme_colors()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        hdr = QHBoxLayout()
        self.title_label = QLabel(i18n.tr("dashboard.title"))
        self.title_label.setFont(FONT_18B)
        hdr.addWidget(self.title_label)
        hdr.addStretch()

        self.auto_refresh_cb = QCheckBox(i18n.tr("dashboard.auto_refresh"))
        self.auto_refresh_cb.setChecked(self._settings.value("auto_refresh", True, type=bool))
        self.auto_refresh_cb.toggled.connect(
            lambda on: self._settings.setValue("auto_refresh", on))
        hdr.addWidget(self.auto_refresh_cb)

        self.btn_refresh = QPushButton(i18n.tr("dashboard.refresh"))
        self.btn_refresh.setStyleSheet(BUTTON_SECONDARY)
        self.btn_refresh.clicked.connect(self.refresh)
        hdr.addWidget(self.btn_refresh)

        self.btn_layout = QPushButton(i18n.tr("dashboard.layout"))
        self.btn_layout.setStyleSheet(BUTTON_SECONDARY)
        self.btn_layout.clicked.connect(self._open_layout_dialog)
        hdr.addWidget(self.btn_layout)

        self.btn_formula = QPushButton(i18n.tr("dashboard.formula"))
        self.btn_formula.setStyleSheet(BUTTON_SECONDARY)
        self.btn_formula.clicked.connect(self._open_formula_dialog)
        hdr.addWidget(self.btn_formula)

        self.btn_display = QPushButton(i18n.tr("dashboard.display_mode"))
        self.btn_display.setStyleSheet(BUTTON_SECONDARY)
        self.btn_display.clicked.connect(self._open_display_mode)
        hdr.addWidget(self.btn_display)

        self.btn_export = QPushButton(i18n.tr("dashboard.export"))
        self.btn_export.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.btn_export.clicked.connect(self._batch_export)
        hdr.addWidget(self.btn_export)
        layout.addLayout(hdr)

        # 垂直滚动卡片容器
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self.card_container = QWidget()
        self.card_layout = QVBoxLayout(self.card_container)
        self.card_layout.setContentsMargins(0, 0, 0, 0)
        self.card_layout.setSpacing(16)
        self.card_layout.addStretch()
        scroll.setWidget(self.card_container)
        layout.addWidget(scroll, 1)

    # ── F1: 刷新 ─────────────────────────────────────────
    @staticmethod
    def _sig(obj, depth: int = 0) -> str:
        """轻量内容签名 — O(1) 深度受限, 替代全量 str() (大数组场景避免 O(n))"""
        if depth >= 3:
            return type(obj).__name__
        if isinstance(obj, dict):
            return "{" + ",".join(f"{k}:{DashboardTab._sig(v, depth + 1)}"
                                  for k, v in sorted(obj.items(), key=lambda kv: str(kv[0]))[:40]) + "}"
        if isinstance(obj, (list, tuple)):
            return f"[{len(obj)}:{DashboardTab._sig(obj[0], depth + 1) if obj else ''}]"
        if isinstance(obj, float):
            return f"{obj:.4g}"
        if isinstance(obj, str):
            return obj[:60]
        return repr(obj)[:60]

    def _analyses_fingerprint(self) -> str:
        parent = self.window()
        if not parent or not hasattr(parent, "analyses"):
            return ""
        parts = []
        for idx in sorted(parent.analyses):
            entry = parent.analyses[idx]
            if not isinstance(entry, dict):
                continue
            parts.append(f"{idx}:{entry.get('analysis_type', '')}:{self._sig(entry.get('result', {}))}")
        return "|".join(parts)

    def _poll_refresh(self):
        if not self.auto_refresh_cb.isChecked():
            return
        self.refresh_if_changed()

    def refresh_if_changed(self):
        """指纹变化才重建 — 供信号通知与轮询共用, 避免 N+1 次全量重绘"""
        fp = self._analyses_fingerprint()
        if fp == self._last_fp and self._cards:
            return
        self.refresh()

    def _show_empty(self):
        empty = QLabel(i18n.tr("dashboard.empty"))
        empty.setStyleSheet("color: #6e7080; font-size: 14px; padding: 40px;")
        empty.setAlignment(Qt.AlignCenter)
        self.card_layout.insertWidget(0, empty)
        self._cards.append(empty)

    def refresh(self):
        # 清除旧卡片
        for c in self._cards:
            if c.parent():
                c.setParent(None)
                c.deleteLater()
        self._cards.clear()
        # 清空 layout (保留末尾 stretch)
        while self.card_layout.count():
            item = self.card_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
        # 空态早退也更新指纹, 避免每 5s 重复重建空标签
        self._last_fp = self._analyses_fingerprint()

        parent = self.window()
        if not parent or not hasattr(parent, "analyses") or not parent.analyses:
            self._show_empty()
            self.card_layout.addStretch()
            return

        metrics_map = extract_metrics(parent.analyses)
        if not metrics_map:
            self._show_empty()
            self.card_layout.addStretch()
            return

        # F2: 用户布局顺序 + 隐藏过滤
        order = self._settings.value("order", [])
        hidden_raw = self._settings.value("hidden", [])
        if not isinstance(order, (list, tuple)):
            order = []
        hidden = set(hidden_raw) if isinstance(hidden_raw, (list, tuple)) else set()
        ordered = [k for k in order if k in metrics_map and k not in hidden]
        rest = [k for k in sorted(metrics_map) if k not in ordered and k not in hidden]
        keys = ordered + rest

        # 收集公式卡片
        from ui.dialogs.formula_dialog import FormulaDialog
        formulas = FormulaDialog.load_formulas()
        variables = describe_variables(parent.analyses, self._get_analysis_df())

        # 收集 tab 实例映射 (用于获取图表)
        tabs = parent._get_tabs() if hasattr(parent, "_get_tabs") else {}

        card_idx = 0

        # 先添加公式卡片
        for name, expr in formulas.items():
            card = self._make_formula_card(name, expr, variables)
            self.card_layout.insertWidget(card_idx, card)
            self._cards.append(card)
            fade_in(card)
            card_idx += 1

        # 再添加分析卡片 (带图表)
        for atype in keys:
            rows = self._collect_rows(metrics_map[atype])
            metrics = metrics_map[atype]

            # 查找对应的 tab 实例和图表
            fig = None
            timestamp = ""
            for idx, entry in parent.analyses.items():
                if isinstance(entry, dict) and entry.get("analysis_type") == atype:
                    ts = entry.get("_completed_at", "")
                    if ts and (not timestamp or ts > timestamp):
                        timestamp = ts
                    tab = tabs.get(idx)
                    if tab and hasattr(tab, "current_figure") and tab.current_figure is not None:
                        fig = tab.current_figure

            ts_str = self._format_time(timestamp) if timestamp else ""
            status = self._status_color(metrics)

            card = AnalysisCard(
                atype=atype,
                rows=rows,
                figure=fig,
                status_color=status,
                timestamp=ts_str,
            )
            self.card_layout.insertWidget(card_idx, card)
            self._cards.append(card)
            fade_in(card)
            card_idx += 1

        self.card_layout.addStretch()

    # ── 指标收集 ──────────────────────────────────────────
    @staticmethod
    def _collect_rows(metrics: dict):
        """收集可显示指标行"""
        rows = []
        for name, value in metrics.items():
            if value is None or value == "":
                continue
            spec = _METRIC_SPECS.get(name)
            if spec is None:
                continue
            key, fmt = spec
            try:
                text = fmt(value)
            except (TypeError, ValueError):
                continue
            rows.append(f"{i18n.tr(key)}: {text}")
        return rows

    @staticmethod
    def _status_color(metrics: dict) -> str:
        """状态色点 — 取最差等级 (红 > 橙 > 绿 > 灰)"""
        worst = "na"
        candidates = (
            _cpk_status(metrics.get("cpk")),
            _oee_status(metrics.get("oee")),
            _grr_status(metrics.get("grr_pct")),
            "bad" if (metrics.get("violations") or 0) > 0 else None,
        )
        for v in candidates:
            if v and _STATUS_RANK[v] > _STATUS_RANK[worst]:
                worst = v
        return _STATUS_COLORS[worst]

    def _latest_time(self, atype: str):
        """该分析类型最近一次完成时间 (ISO 字符串, _completed_at)"""
        parent = self.window()
        entries = getattr(parent, "analyses", {}) or {}
        ts = None
        for e in entries.values():
            if isinstance(e, dict) and e.get("analysis_type") == atype:
                v = e.get("_completed_at")
                if v and (ts is None or v > ts):
                    ts = v
        return ts

    @staticmethod
    def _format_time(ts: str) -> str:
        """ISO '2026-08-14T14:23:45' → '14:23'"""
        if len(ts) >= 16:
            return ts[11:16]
        return ts

    # ── 大屏模式 ──────────────────────────────────────────
    def _open_display_mode(self):
        parent = self.window()
        if not parent or not hasattr(parent, "analyses") or not parent.analyses:
            QMessageBox.information(self, i18n.tr("dashboard.display_mode"),
                                    i18n.tr("dashboard.empty"))
            return
        if hasattr(parent, "_open_display_mode"):
            parent._open_display_mode()
        else:
            from ui.dialogs.display_mode import DisplayModeWindow
            self._display_window = DisplayModeWindow(parent)
            self._display_window.showFullScreen()

    # ── 公式编辑器 ───────────────────────────────────────
    def _get_analysis_df(self):
        parent = self.window()
        if not parent or not hasattr(parent, "current_data"):
            return None
        raw = parent.current_data.get("raw_data")
        if not raw:
            return None
        first = next(iter(raw.values()))
        key = (id(first), len(first))
        if getattr(self, "_df_cache_key", None) == key and self._df_cache is not None:
            return self._df_cache
        try:
            from core.data_parser import DataParser
            df, _ = DataParser().prepare(first)
            self._df_cache = df
            self._df_cache_key = key
            return df
        except Exception:
            return None

    def _open_formula_dialog(self):
        parent = self.window()
        analyses = parent.analyses if parent and hasattr(parent, "analyses") else {}
        from ui.dialogs.formula_dialog import FormulaDialog
        dlg = FormulaDialog(self, analyses=analyses, df=self._get_analysis_df())
        dlg.exec()
        self.refresh()

    def _make_formula_card(self, name: str, expr: str, variables: dict):
        """渲染单张自定义公式卡片"""
        tc = theme_colors()
        frame = QFrame()
        frame.setStyleSheet(
            f"QFrame {{ background:{tc['bg_card']};"
            f"border:1px solid {tc['accent_bright']}; border-radius:10px; padding:10px; }}"
        )
        l = QVBoxLayout(frame)
        l.setSpacing(6)
        title = ElidedLabel(name)
        title.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        title.setStyleSheet(f"color:{tc['accent_bright']};")
        title.setToolTip(f"{name} = {expr}")
        l.addWidget(title)
        try:
            value = evaluate(str(expr), variables)
            text = f"{value:.4g}"
        except FormulaError as e:
            text = i18n.tr("formula.eval_failed")
            frame.setToolTip(str(e))
        val = ElidedLabel(text)
        val.setFont(FONT_18B)
        val.setToolTip(f"{name} = {expr}\n{text}")
        l.addWidget(val)
        hint = QLabel(i18n.tr("formula.card_hint"))
        hint.setStyleSheet(f"color: {tc['text_muted']}; font-size: 9px;")
        l.addWidget(hint)
        l.addStretch()
        return frame

    # ── 布局对话框 ───────────────────────────────────────
    def _open_layout_dialog(self):
        parent = self.window()
        items = []
        if parent and hasattr(parent, "analyses"):
            items = list(extract_metrics(parent.analyses).keys())
        if not items:
            QMessageBox.information(self, i18n.tr("dashboard.layout"), i18n.tr("dashboard.empty"))
            return
        from ui.dialogs.layout_dialog import LayoutDialog
        dlg = LayoutDialog(self, items, self._settings)
        if dlg.exec() == dlg.Accepted:
            self.refresh()

    # ── 批量导出 ─────────────────────────────────────────
    def _batch_export(self):
        parent = self.window()
        if not parent or not hasattr(parent, "analyses") or not parent.analyses:
            QMessageBox.information(self, i18n.tr("dashboard.export"), i18n.tr("dashboard.empty"))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, i18n.tr("dashboard.export"), "dashboard_export.zip", "ZIP (*.zip)")
        if not path:
            return
        import zipfile
        import io
        from output.chart_engine import figure_to_bytes
        with zipfile.ZipFile(path, "w") as zf:
            for idx, r in parent.analyses.items():
                atype = r.get("analysis_type", f"analysis_{idx}")
                try:
                    from output.excel_report import ExcelReport
                    buf = io.BytesIO()
                    ExcelReport().generate([r], buf)
                    buf.seek(0)
                    zf.writestr(f"{atype}.xlsx", buf.read())
                except Exception:
                    import logging
                    logging.warning(f"dashboard: 导出 {atype} 失败", exc_info=True)
                tab = parent._get_tabs().get(idx)
                if tab and hasattr(tab, "current_figure") and tab.current_figure:
                    buf = figure_to_bytes(tab.current_figure, "png")
                    zf.writestr(f"{atype}_chart.png", buf.read())
        QMessageBox.information(self, i18n.tr("dashboard.export"), f"{path}")

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)
