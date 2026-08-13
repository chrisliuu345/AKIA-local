"""Dashboard 汇总面板 — 统一KPI提取器 + 实时刷新 + 卡片布局自定义 + 批量导出

v2.4 第一阶段 (F0/F1/F2):
- F0: 改用 core/kpi_extractor 渲染卡片 (修复 OEE/%GRR/SPC违规 3 项坏指标)
- F1: 信号驱动 (MainWindow._notify_dashboard) + QTimer(5s) 轮询兜底 + 自动刷新开关
- F2: 布局设置对话框 — 卡片显隐 + 排序, QSettings 持久化
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGridLayout, QFrame, QScrollArea, QFileDialog, QMessageBox, QCheckBox,
)
from PySide6.QtCore import QTimer, QSettings
from ui.tabs.base_tab import BaseAnalysisTab
from ui.theme import BUTTON_PRIMARY_STRETCH, BUTTON_SECONDARY, FONT_18B, FONT_10
from ui.theme import colors as theme_colors
from ui.widgets.elided_label import ElidedLabel
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
}

_REFRESH_INTERVAL_MS = 5000


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

        self.btn_export = QPushButton(i18n.tr("dashboard.export"))
        self.btn_export.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.btn_export.clicked.connect(self._batch_export)
        hdr.addWidget(self.btn_export)
        layout.addLayout(hdr)

        # 卡片网格
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self.card_container = QWidget()
        self.grid = QGridLayout(self.card_container)
        self.grid.setSpacing(12)
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
        self.grid.addWidget(empty, 0, 0)
        self._cards.append(empty)  # 加入统一管理, 下次 refresh 一并清理

    def refresh(self):
        # 清除旧卡片
        for c in self._cards:
            if c.parent():
                c.setParent(None)
        self._cards.clear()
        # 移除 layout 项的同时销毁 widget — 否则孤儿 widget 残留在容器上叠加显示
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
        # 空态早退也更新指纹, 避免每 5s 重复重建空标签
        self._last_fp = self._analyses_fingerprint()

        parent = self.window()
        if not parent or not hasattr(parent, "analyses") or not parent.analyses:
            self._show_empty()
            return

        metrics_map = extract_metrics(parent.analyses)
        if not metrics_map:
            self._show_empty()
            return

        # F2: 用户布局顺序 + 隐藏过滤 (QSettings 数据损坏防御)
        order = self._settings.value("order", [])
        hidden_raw = self._settings.value("hidden", [])
        if not isinstance(order, (list, tuple)):
            order = []
        hidden = set(hidden_raw) if isinstance(hidden_raw, (list, tuple)) else set()
        ordered = [k for k in order if k in metrics_map and k not in hidden]
        rest = [k for k in sorted(metrics_map) if k not in ordered and k not in hidden]
        keys = ordered + rest

        col = 0
        row = 0

        # F3: 自定义公式卡片排最前
        for card in self._make_formula_cards():
            self.grid.addWidget(card, row, col)
            self._cards.append(card)
            col += 1
            if col > 2:
                col = 0
                row += 1

        for atype in keys:
            card = self._make_card(atype, metrics_map[atype])
            if card is None:
                continue  # 无可显示指标的卡片 (防御)
            self.grid.addWidget(card, row, col)
            self._cards.append(card)
            col += 1
            if col > 2:
                col = 0
                row += 1

    # ── F0: 指标卡片 (从提取器数据渲染) ──────────────────
    def _make_card(self, atype: str, metrics: dict):
        tc = theme_colors()
        # 先收集可显示指标行 — 无可显示指标时不建卡 (避免空标题卡片)
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
                continue  # 非标量或格式不符的指标静默跳过
            rows.append(f"{i18n.tr(key)}: {text}")
            if len(rows) >= 6:  # 卡片高度上限
                break
        if not rows:
            return None

        frame = QFrame()
        frame.setFixedSize(240, 170)
        frame.setStyleSheet(
            f"QFrame {{ background:{tc['bg_card']}; border:1px solid {tc['border']};"
            f"border-radius:10px; padding:10px; }}"
        )
        l = QVBoxLayout(frame)
        l.setSpacing(4)

        title = QLabel(atype[:25] + (".." if len(atype) > 25 else ""))
        title.setFont(FONT_10)
        title.setStyleSheet(f"color:{tc['accent_bright']}; font-weight:bold;")
        title.setWordWrap(True)
        title.setToolTip(atype)
        l.addWidget(title)

        # 指标行用 ElidedLabel 单行显示 — 超宽自动省略, tooltip 全文 (v2.3.1 组件复用)
        for text in rows:
            lbl = ElidedLabel(text)
            lbl.setToolTip(f"{atype} — {text}")
            l.addWidget(lbl)
        l.addStretch()
        return frame

    # ── F3: 公式编辑器与自定义卡片 ───────────────────────
    def _get_analysis_df(self):
        """从主窗口当前数据取主数据表 (供公式变量列统计)

        带缓存 — DataParser.prepare 是重清洗操作, 同一数据源不重复解析。
        id() 键安全: 缓存持有 df 引用, 旧对象 id 不可能被复用。
        """
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

    def _make_formula_cards(self):
        """渲染自定义公式卡片 — 求值失败显示 '无法求值'"""
        from ui.dialogs.formula_dialog import FormulaDialog
        # 注意: 公式存储于 QSettings("QA-Tool", "Formulas") 作用域,
        # 与布局设置的 "Dashboard" 作用域分离, 不可传入 self._settings
        formulas = FormulaDialog.load_formulas()
        if not formulas:
            return []
        parent = self.window()
        analyses = parent.analyses if parent and hasattr(parent, "analyses") else {}
        variables = describe_variables(analyses, self._get_analysis_df())

        tc = theme_colors()
        cards = []
        for name, expr in formulas.items():
            frame = QFrame()
            frame.setFixedSize(240, 170)
            frame.setStyleSheet(
                f"QFrame {{ background:{tc['bg_card']};"
                f"border:1px solid {tc['accent_bright']}; border-radius:10px; padding:10px; }}"
            )
            l = QVBoxLayout(frame)
            l.setSpacing(6)
            title = ElidedLabel(name)
            title.setFont(FONT_10)
            title.setStyleSheet(f"color:{tc['accent_bright']}; font-weight:bold;")
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
            cards.append(frame)
        return cards

    # ── F2: 布局对话框 ───────────────────────────────────
    def _open_layout_dialog(self):
        parent = self.window()
        items = []
        if parent and hasattr(parent, "analyses"):
            items = list(extract_metrics(parent.analyses).keys())
        if not items:
            QMessageBox.information(self, i18n.tr("dashboard.layout"), i18n.tr("dashboard.empty"))
            return  # 空列表时不打开对话框, 防止覆盖已保存布局
        from ui.dialogs.layout_dialog import LayoutDialog
        dlg = LayoutDialog(self, items, self._settings)
        if dlg.exec() == dlg.Accepted:
            self.refresh()

    # ── 批量导出 (保留) ───────────────────────────────────
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
                # Excel 导出
                try:
                    from output.excel_report import ExcelReport
                    buf = io.BytesIO()
                    ExcelReport().generate([r], buf)
                    buf.seek(0)
                    zf.writestr(f"{atype}.xlsx", buf.read())
                except Exception:
                    import logging
                    logging.warning(f"dashboard: 导出 {atype} 失败", exc_info=True)
                # 图表 PNG
                tab = parent._get_tabs().get(idx)
                if tab and hasattr(tab, "current_figure") and tab.current_figure:
                    buf = figure_to_bytes(tab.current_figure, "png")
                    zf.writestr(f"{atype}_chart.png", buf.read())
        QMessageBox.information(self, i18n.tr("dashboard.export"), f"{path}")

    def closeEvent(self, event):
        # 注: tab 常驻 QStackedWidget, 此方法当前不会被调用; 保留以防御
        # 未来 tab 从 stack 移除时定时器空转
        self._timer.stop()
        super().closeEvent(event)
