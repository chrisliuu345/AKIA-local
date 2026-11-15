"""主窗口外壳：布局、侧栏、命令面板、滚动和窗口状态。"""

import os

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout,
    QMessageBox, QFrame,
    QScrollArea,
)
from PySide6.QtCore import (
    Qt, QSettings, QPropertyAnimation, QEasingCurve, QTimer, QVariantAnimation,
)
from PySide6.QtGui import QPixmap, QDragEnterEvent, QDropEvent

from config.settings import APP_FULL_NAME, APP_NAME, APP_VERSION
from core.i18n import i18n
from ui.worker import run_in_worker
from core.audit import audit

from ui.sidebar import (
    SIDEBAR_COLLAPSED_WIDTH,
    SIDEBAR_EXPANDED_WIDTH,
    Sidebar,
)
from ui.widgets.elided_label import ElidedLabel
from ui.welcome_page import WelcomePage
from ui.main_window_helpers import (
    _CurrentPageStack, _tab_has_data,
)

from ui.main_window_constants import (
    _IE_IMPORT_TAB_INDICES,
    _PLUGIN_TAB_START,
    project_path,
)


class ChromeMixin:
    def _setup_ui(self):
        divider_color = "#2A2A2A"

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = Sidebar()
        self._sidebar_collapsed = False
        self._sidebar_anim = None
        from ui.widgets.chart_wheel import install_chart_wheel_filter
        install_chart_wheel_filter()
        self.sidebar.setFixedWidth(SIDEBAR_EXPANDED_WIDTH)

        vdivider = QFrame()
        vdivider.setFrameShape(QFrame.VLine)
        vdivider.setStyleSheet(f"color: {divider_color};")
        vdivider.setMaximumWidth(1)

        self.stack = _CurrentPageStack()
        self._tab_cache = {}

        self.welcome_page = WelcomePage()
        self.stack.addWidget(self.welcome_page)

        for idx in range(1, _PLUGIN_TAB_START):
            placeholder = QWidget()
            placeholder.setObjectName(f"placeholder_{idx}")
            self.stack.addWidget(placeholder)

        self._plugin_tab_start = _PLUGIN_TAB_START

        layout.addWidget(self.sidebar)
        layout.addWidget(vdivider)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.stack)
        scroll.setFrameShape(QFrame.NoFrame)
        self.scroll_area = scroll
        layout.addWidget(scroll, 1)

    # ------------------------------------------------------------ 命令面板
    def _build_command_entries(self) -> list:
        """构建命令面板条目：全部 Tab（含插件）+ 常用操作。"""
        from ui._tab_registry import TAB_REGISTRY

        entries = []
        for idx, key, _cls, _mod, _cat in TAB_REGISTRY:
            entries.append({"label": i18n.tr(key), "category": "跳转",
                            "hint": f"Tab {idx}", "kind": "tab",
                            "payload": idx, "keywords": key})
        for idx, record in getattr(self, "_plugin_tabs", {}).items():
            manifest = getattr(record, "manifest", None)
            name = (getattr(manifest, "name", "") or "插件")
            entries.append({"label": str(name), "category": "插件",
                            "hint": f"Tab {idx}", "kind": "tab",
                            "payload": idx, "keywords": f"plugin {name}"})

        actions = [
            ("导入数据文件", "操作", "Ctrl+O", self._on_import_quality, "import excel"),
            ("导入 IE 数据", "操作", "", self._on_import_ie, "import ie"),
            ("导入数据库", "操作", "", self._on_import_db, "sql database"),
            ("打开项目", "操作", "Ctrl+Shift+O", self._on_load_project, "open project qap"),
            ("保存项目", "操作", "Ctrl+Shift+S", self._on_save_project, "save project qap"),
            ("导出本地数据资产", "操作", "", self._on_export_data_asset, "export data asset qda"),
            ("导入本地数据资产", "操作", "", self._on_import_data_asset, "import data asset qda"),
            ("批量分析", "操作", "", self._on_run_all_analyses, "batch run all"),
            ("导出报告 (Word)", "操作", "", lambda: self._on_export_all("docx"),
             "export report word"),
            ("数据清洗", "操作", "", self._on_data_cleaner, "clean data"),
            ("数据清洗向导", "操作", "", self._on_data_clean_wizard, "clean wizard"),
            ("产线配置 (plant.json)", "操作", "", self._on_plant_config, "plant config"),
            ("告警中心", "操作", "", self._on_alert_center, "alerts center"),
            ("连接器健康", "操作", "", self._on_connector_health, "connector health"),
            ("设置", "操作", "", self._on_settings, "settings preferences"),
            ("使用指南", "操作", "F1", self._on_open_guide, "help guide manual"),
            ("显示模式", "视图", "F11", self._open_display_mode, "display mode fullscreen"),
            ("QAM Harness", "Agent", "", self._on_llm_assist, "ai agent chat llm"),
        ]
        for label, category, hint, callback, keywords in actions:
            entries.append({"label": label, "category": category, "hint": hint,
                            "kind": "action", "callback": callback,
                            "keywords": keywords})
        return entries

    def _open_command_palette(self):
        """Ctrl+K / Ctrl+P — 全局命令面板。"""
        from ui.dialogs.command_palette import CommandPaletteDialog

        dialog = CommandPaletteDialog(self._build_command_entries(), self)
        dialog.triggered.connect(self._execute_command)
        dialog.exec()

    def _execute_command(self, entry: dict):
        if entry.get("kind") == "tab":
            self._switch_tab(int(entry.get("payload", 0)))
            return
        callback = entry.get("callback")
        if callable(callback):
            callback()

    def _set_sidebar_width(self, width: int):
        self.sidebar.setFixedWidth(int(width))

    def _toggle_sidebar(self, collapsed: bool, *, animate: bool = True):
        """侧栏宽度动画。开关始终钉在底边，展开和收起不换位置。"""
        collapsed = bool(collapsed)
        if self._sidebar_anim is not None:
            self._sidebar_anim.stop()
            self._sidebar_anim = None
        self._sidebar_collapsed = collapsed
        self.sidebar.set_collapsed(collapsed)
        if hasattr(self, "toggle_sidebar_action"):
            self.toggle_sidebar_action.blockSignals(True)
            self.toggle_sidebar_action.setChecked(not collapsed)
            self.toggle_sidebar_action.blockSignals(False)
        end = SIDEBAR_COLLAPSED_WIDTH if collapsed else SIDEBAR_EXPANDED_WIDTH
        start = self.sidebar.width() or end
        if not animate or start == end:
            self._set_sidebar_width(end)
            return
        anim = QVariantAnimation(self)
        anim.setDuration(240)
        anim.setStartValue(int(start))
        anim.setEndValue(int(end))
        anim.setEasingCurve(QEasingCurve.InOutCubic)
        anim.valueChanged.connect(self._set_sidebar_width)
        self._sidebar_anim = anim
        anim.start()

    def _setup_statusbar(self):
        self.statusBar().setStyleSheet(
            "QStatusBar { min-height: 24px; background: #181818; } QStatusBar::item { border: none; }"
        )
        self.status_label = ElidedLabel(i18n.tr("status.ready"))
        self.statusBar().addWidget(self.status_label, 1)
        self.data_label = ElidedLabel("")
        self.data_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.data_label.setMaximumWidth(300)
        self.statusBar().addPermanentWidget(self.data_label)

    def _connect_signals(self):
        self.sidebar.navigation_changed.connect(self._switch_tab)
        self.sidebar.diagnose_clicked.connect(self._on_diagnose)
        self.sidebar.llm_clicked.connect(self._on_llm_assist)
        self.sidebar.collapse_requested.connect(
            lambda: self._toggle_sidebar(not self._sidebar_collapsed)
        )
        self.welcome_page.import_data_clicked.connect(self._on_import_quality)
        self.welcome_page.import_ie_clicked.connect(self._on_import_ie)
        self.welcome_page.import_template_clicked.connect(self._on_import_template)
        self.welcome_page.new_analysis_clicked.connect(lambda: self._switch_tab(1))
        self.welcome_page.diagnose_clicked.connect(self._on_diagnose)
        self.welcome_page.open_project_clicked.connect(self._on_load_project)
        self.welcome_page.case_center_clicked.connect(self._on_case_center)

    def _switch_tab(self, index: int):
        if 0 <= index < self.stack.count():
            if index > 0:
                self._lazy_load_tab(index)
            target = self.stack.widget(index)
            if not target:
                return
            from PySide6.QtWidgets import QGraphicsOpacityEffect
            if hasattr(self, '_tab_anim_widget') and self._tab_anim_widget:
                self._tab_anim_widget.setGraphicsEffect(None)
            if hasattr(self, '_tab_anim') and self._tab_anim:
                self._tab_anim.stop()
            effect = QGraphicsOpacityEffect()
            effect.setOpacity(0.0)
            target.setGraphicsEffect(effect)
            self._tab_anim_widget = target
            self.stack.setCurrentIndex(index)
            self.sidebar.set_active(index)
            self._update_tab_empty_state(index)
            # 切换后按当前页重算共享滚动范围，并回到顶部（隐藏页残留不再起作用）
            self._sync_scroll_range(reset_scroll=True)
            self._schedule_scroll_sync()

            anim = QPropertyAnimation(effect, b"opacity")
            anim.setDuration(200)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.OutCubic)

            def cleanup(tgt=target):
                tgt.setGraphicsEffect(None)
            anim.finished.connect(cleanup)
            self._tab_anim = anim
            anim.start()

            if index == 27 and hasattr(self, '_tab_cache'):
                tab = self._tab_cache.get(27)
                if tab is not None and hasattr(tab, 'refresh_if_changed'):
                    tab.refresh_if_changed()

    def _sync_scroll_range(self, reset_scroll: bool = False):
        """按当前页重算共享滚动范围（隐藏页残留高度不再影响滚动条）。

        QScrollArea 只在收到布局请求时重算范围；Tab 内容（参数面板/图表/数据表）
        变化后不会自动触发，因此需要显式把当前页的最小高度写入 stack 并
        updateGeometry，保证"运行分析 → 切走"后滚动条回落到当前页长度。
        """
        if not hasattr(self, "stack"):
            return
        page = self.stack.currentWidget()
        height = 0
        if page is not None:
            layout = page.layout()
            if layout is not None:      # 激活布局，拿到分析渲染后的真实最小高度
                layout.activate()
            hint = page.minimumSizeHint()
            height = hint.height() if hint.isValid() else page.sizeHint().height()
        self.stack.setMinimumHeight(max(0, int(height)))
        self.stack.updateGeometry()
        if reset_scroll and getattr(self, "scroll_area", None) is not None:
            self.scroll_area.verticalScrollBar().setValue(0)

    #: 不显示"未导入数据"空状态的 Tab：
    #: - 文档/监控型页面：0 / 27 / 33-35
    #: - 自包含工具（手工录入 / 预设 / 项目上下文驱动，工作表导入非必需）：
    #:   8 工作抽样 · 14 鱼骨图 · 16 FMEA · 17 控制计划 · 21 人机配合 ·
    #:   22 标准作业组合票 · 25 分层审核 · 26 抽样 · 29 SMED · 30 8D ·
    #:   31 TPM · 32 PPAP
    _EMPTY_STATE_SKIP = frozenset({
        0, 8, 14, 16, 17, 21, 22, 25, 26, 27, 29, 30, 31, 32, 33, 34, 35,
    })

    def _update_tab_empty_state(self, index: int):
        """统一空状态：无数据的分析 Tab 显示"导入数据"遮罩，有数据则隐藏。"""
        if index in self._EMPTY_STATE_SKIP:
            return
        tab = self.stack.widget(index)
        if tab is None or not hasattr(tab, "show_empty_state"):
            return
        if _tab_has_data(tab):
            hide = getattr(tab, "_hide_empty_state", None)
            if callable(hide):
                hide()
        elif index in _IE_IMPORT_TAB_INDICES:
            tab.show_empty_state(message="请先导入 IE 数据",
                                 button_text="导入 IE 数据")
        else:
            tab.show_empty_state()

    def _schedule_scroll_sync(self, delays=(0, 120, 260)):
        """分批延后同步滚动范围。

        Qt 的 minimumSizeHint 有缓存：图表渲染 / show-hide 重新 pin 之后，
        同一拍内读到的仍是旧值。这里在 0/120/260ms 各同步一次，覆盖布局、
        动画与图表首帧完成的时间点，成本仅为几次 setMinimumHeight。
        """
        for delay in delays:
            if delay <= 0:
                self._sync_scroll_range()
            else:
                QTimer.singleShot(int(delay), self._sync_scroll_range)

    def _show_toast(self, message: str, toast_type: str = "info"):
        """统一轻提示（替代阻塞式弹窗）。"""
        try:
            from ui.widgets.toast import Toast
            Toast.show(self, message, toast_type=toast_type, duration=2600)
        except Exception:  # 提示失败不影响主流程
            pass

    def _restore_window_state(self):
        settings = QSettings("AKIA", "MainWindow")
        geo = settings.value("geometry")
        state = settings.value("windowState")
        if geo:
            self.restoreGeometry(geo)
        if state:
            self.restoreState(state)
        collapsed = settings.value("sidebarCollapsed", False, type=bool)
        if collapsed:
            self._toggle_sidebar(True, animate=False)
        from ui.theme import apply_dark_palette
        apply_dark_palette()

    def closeEvent(self, event):
        settings = QSettings("AKIA", "MainWindow")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        settings.setValue("sidebarCollapsed", self._sidebar_collapsed)
        self._shutdown_runtime()
        super().closeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F11:
            self._open_display_mode()
            return
        super().keyPressEvent(event)

    def _open_display_mode(self):
        """v2.4 F4: 车间大屏模式 (F11)"""
        if getattr(self, "_display_window", None) is not None and \
                self._display_window.isVisible():
            self._display_window.raise_()
            self._display_window.activateWindow()
            return
        if not self.analyses:
            QMessageBox.information(self, i18n.tr("dashboard.display_mode"),
                                    i18n.tr("dashboard.empty"))
            return
        from ui.dialogs.display_mode import DisplayModeWindow
        self._display_window = DisplayModeWindow(self)
        self._display_window.showFullScreen()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                ext = os.path.splitext(url.toLocalFile())[1].lower()
                if ext in (".xlsx", ".xls", ".xlsm", ".csv"):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            ext = os.path.splitext(path)[1].lower()
            if ext in (".xlsx", ".xls", ".xlsm", ".csv"):
                self._load_and_route(path)
                return
        event.ignore()

    def _load_and_route(self, file_path: str):
        try:
            self.status_label.setText(f"加载中... {file_path}")
            loader = self.data_loader

            def _load_dropped():
                raw = loader.load(file_path)
                return raw, dict(loader.metadata or {})

            raw_data, metadata = run_in_worker(self, _load_dropped)
            self.data_loader.metadata = metadata
            audit("import_data",
                  "user",
                  f"拖拽导入 {os.path.basename(file_path)}")
            self._record_data_imported(file_path, raw_data, kind="file")
            self.current_data = {"file_path": file_path, "raw_data": raw_data}
            self.data_label.setText(os.path.basename(file_path))
            self._route_sheets_to_tabs(raw_data, worksheet_mode=True)
            self.status_label.setText(f"已加载: {os.path.basename(file_path)}")
        except Exception as e:
            self.status_label.setText(f"加载失败: {e}")

    def _on_about(self):
        import os
        logo_path = project_path("logo.png")
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(f"关于 {APP_NAME}")
        msg_box.setIconPixmap(
            QPixmap(logo_path).scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            if os.path.exists(logo_path) else QPixmap()
        )
        msg_box.setText(
            f"<h2>{APP_NAME} v{APP_VERSION}</h2>"
            f"<p>{APP_FULL_NAME}</p>"
            f"<p>开源个人工业工程与质量分析工具</p>"
            f"<p>本地优先 · 可选 AI 助手 · 插件扩展 · Apache License 2.0</p>"
            f"<br><p style='color:#888'>技术栈: Python 3.14 · PySide6 · pandas · scipy · scikit-learn · SHAP</p>"
        )
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec()
