"""
QA-Tool — 主窗口
"""

import os
from datetime import datetime
from typing import Dict, Any
import pandas as pd

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QMessageBox, QFileDialog,
    QPushButton, QApplication, QFrame,
    QScrollArea,
)
from PySide6.QtCore import Qt, QSettings, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QAction, QIcon, QFont, QPixmap, QDragEnterEvent, QDropEvent

from config.settings import APP_NAME, APP_VERSION, CHART_FIGSIZE, tab_allowed
from core.data_loader import DataLoader
from core.data_parser import DataParser
from core.data_validator import DataValidator
from core.template_parser import TemplateParser
from core.session_manager import SessionManager
from core.i18n import i18n
from core.data_profiler import DataProfiler
from core.project_manager import ProjectManager
from core.project_context import ProjectContext
from core.audit import audit

from ui.sidebar import Sidebar
from ui._tab_registry import INDEX_MAP
_PLUGIN_TAB_START = max(INDEX_MAP.keys()) + 1
from ui.theme import colors as theme_colors
from ui.font_config import get_ui_font
from ui.widgets.elided_label import ElidedLabel
# Tab 类按需通过 _lazy_load_tab() + importlib 加载，无需顶层导入
from ui.welcome_page import WelcomePage
from ui.dialogs.import_dialog import ImportDialog
from ui.dialogs.settings_dialog import SettingsDialog
from ui.dialogs.db_connection_dialog import DbConnectionDialog
from core.sql_loader import SqlLoader
from core.plugin_manager import PluginManager


def _tab_has_data(tab) -> bool:
    """Tab 是否有可分析数据 — 不能用 not df 测试 DataFrame 真值 (恒抛 ValueError)"""
    df = getattr(tab, 'df', None)
    return df is not None and len(df) != 0


def _tab_is_runnable(tab) -> bool:
    """Tab 能否参与批量分析 — 有数据且定义了 run_and_display (Dashboard 等文档型 Tab 无此方法)"""
    return _tab_has_data(tab) and callable(getattr(tab, 'run_and_display', None))


class MainWindow(QMainWindow):
    def __init__(self, splash=None):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.resize(1300, 880)
        self.setMinimumSize(1040, 700)

        logo_path = os.path.join(os.path.dirname(__file__), "..", "logo.png")
        if os.path.exists(logo_path):
            self.setWindowIcon(QIcon(logo_path))

        def _step(pct, msg):
            if splash:
                from main import _update_splash, _splash_base
                _update_splash(splash, pct, _splash_base)
                QApplication.processEvents()

        _step(71, "初始化数据加载器...")
        self.data_loader = DataLoader()
        self.data_parser = DataParser()
        self.data_profiler = DataProfiler()
        self.data_validator = DataValidator()
        self.template_parser = TemplateParser()
        self.session_manager = SessionManager()

        self.current_data: Dict[str, Any] = {}
        self.profile_result: Dict[str, Any] = {}
        self.analyses: Dict[int, Dict[str, Any]] = {}
        self.project_context = ProjectContext()

        _step(73, "构建界面布局...")
        self._setup_ui()
        # 保留所有 QMenu 的 Python 强引用，防止 PySide6 GC 提前释放 C++ QMenu
        self._menu_refs: list = []

        _step(76, "初始化菜单栏...")
        self._setup_menu()

        _step(78, "初始化状态栏...")
        self._setup_statusbar()

        _step(80, "连接信号与路由...")
        self._connect_signals()

        _step(83, "恢复窗口布局...")
        self._restore_window_state()
        self.setAcceptDrops(True)

        # 插件发现与注册 — 从 _PLUGIN_TAB_START 开始
        self._pm = PluginManager()
        self._pm.discover()
        self._plugin_tabs = {}
        self._plugin_tab_start = _PLUGIN_TAB_START
        for name, p in self._pm.plugins.items():
            idx = self._plugin_tab_start + len(self._plugin_tabs)
            self._plugin_tabs[idx] = p
            placeholder = QWidget()
            placeholder.setObjectName(f"placeholder_plugin_{idx}")
            self.stack.addWidget(placeholder)
            self.sidebar.add_plugin_entry(idx, name)

        _step(85, "主窗口初始化完成")


    def _setup_ui(self):
        divider_color = "#3a3a3a"
        tc = theme_colors()

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.expand_strip = QFrame()
        self.expand_strip.setFixedWidth(26)
        self.expand_strip.setStyleSheet(
            f"QFrame {{ background-color: {tc['bg_header']}; border: none; }}"
        )
        strip_layout = QVBoxLayout(self.expand_strip)
        strip_layout.setContentsMargins(0, 14, 0, 0)
        strip_layout.setSpacing(0)
        self.expand_btn = QPushButton("»")
        self.expand_btn.setFont(QFont(get_ui_font(), 12, QFont.Bold))
        self.expand_btn.setFixedSize(26, 40)
        self.expand_btn.setCursor(Qt.PointingHandCursor)
        self.expand_btn.setToolTip(i18n.tr("sidebar.expand") + " (Ctrl+B)")
        self.expand_btn.setStyleSheet(
            f"QPushButton {{ background-color: transparent; color: {tc['text_muted']};"
            f"border: none; border-radius: 0; }}"
            f"QPushButton:hover {{ color: {tc['accent_bright']}; background-color: {tc['bg_hover']}; }}"
        )
        self.expand_btn.clicked.connect(lambda: self._toggle_sidebar(False))
        strip_layout.addWidget(self.expand_btn)
        strip_layout.addStretch()
        self.expand_strip.setVisible(False)

        self.sidebar = Sidebar()
        self.sidebar.setFixedWidth(210)

        vdivider = QFrame()
        vdivider.setFrameShape(QFrame.VLine)
        vdivider.setStyleSheet(f"color: {divider_color};")
        vdivider.setMaximumWidth(1)

        self.stack = QStackedWidget()
        self._tab_cache = {}  # 懒加载缓存: idx → tab实例

        # 首页始终立即加载 (轻量)
        self.welcome_page = WelcomePage()
        self.stack.addWidget(self.welcome_page)  # 0

        # 内置 Tab 占位符 (1..max)，首次切换时懒加载
        for idx in range(1, _PLUGIN_TAB_START):  # v2.5: indices 1-35 (含设备监控)
            placeholder = QWidget()
            placeholder.setObjectName(f"placeholder_{idx}")
            self.stack.addWidget(placeholder)

        # 插件 Tab (动态) — 起始索引在 __init__ 末尾统一设为 _PLUGIN_TAB_START
        self._plugin_tab_start = _PLUGIN_TAB_START

        layout.addWidget(self.expand_strip)
        layout.addWidget(self.sidebar)
        layout.addWidget(vdivider)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.stack)
        scroll.setFrameShape(QFrame.NoFrame)
        layout.addWidget(scroll, 1)

    def _toggle_sidebar(self, collapsed: bool):
        self.sidebar.setVisible(not collapsed)
        self.expand_strip.setVisible(collapsed)
        if hasattr(self, "toggle_sidebar_action"):
            self.toggle_sidebar_action.blockSignals(True)
            self.toggle_sidebar_action.setChecked(not collapsed)
            self.toggle_sidebar_action.blockSignals(False)

    def _setup_menu(self):
        menubar = self.menuBar()

        def _pin(menu):
            self._menu_refs.append(menu)
            return menu

        file_menu = _pin(menubar.addMenu(i18n.tr("menu.file")))

        import_quality_action = QAction("📂 " + i18n.tr("sidebar.import_quality"), self)
        import_quality_action.setShortcut("Ctrl+O")
        import_quality_action.triggered.connect(self._on_import_quality)
        file_menu.addAction(import_quality_action)

        import_ie_action = QAction("🏭 " + i18n.tr("sidebar.import_ie"), self)
        import_ie_action.triggered.connect(self._on_import_ie)
        file_menu.addAction(import_ie_action)

        import_db_action = QAction("🗄️ " + i18n.tr("sidebar.import_db"), self)
        import_db_action.triggered.connect(self._on_import_db)
        file_menu.addAction(import_db_action)

        file_menu.addSeparator()

        template_action = QAction("📋 " + i18n.tr("menu.import_template"), self)
        template_action.triggered.connect(self._on_import_template)
        file_menu.addAction(template_action)

        file_menu.addSeparator()

        export_menu = _pin(file_menu.addMenu(i18n.tr("menu.export")))
        export_xlsx = QAction("📊 " + i18n.tr("menu.export_xlsx"), self)
        export_xlsx.triggered.connect(lambda: self._on_export_all("xlsx"))
        export_menu.addAction(export_xlsx)
        export_docx = QAction("📝 " + i18n.tr("menu.export_docx"), self)
        export_docx.triggered.connect(lambda: self._on_export_all("docx"))
        export_menu.addAction(export_docx)
        export_pdf = QAction("📄 " + i18n.tr("menu.export_pdf"), self)
        export_pdf.triggered.connect(lambda: self._on_export_all("pdf"))
        export_menu.addAction(export_pdf)

        try:
            from output.compliance_report import ComplianceReportGenerator
            templates = ComplianceReportGenerator.list_templates()
            if templates:
                export_menu.addSeparator()
                comply_menu = _pin(export_menu.addMenu(i18n.tr("menu.compliance")))
                for t in templates:
                    ac = comply_menu.addAction(f"{t['name']} ({t['standard']})")
                    ac.setData(t["id"])
                    ac.triggered.connect(lambda checked, tid=t["id"]: self._on_export_compliance(tid))
        except Exception:
            pass

        file_menu.addSeparator()
        # .qap 项目文件
        save_project_action = QAction("💾 " + i18n.tr("menu.save_project"), self)
        save_project_action.setShortcut("Ctrl+Shift+S")
        save_project_action.triggered.connect(self._on_save_project)
        file_menu.addAction(save_project_action)
        open_project_action = QAction("📂 " + i18n.tr("menu.open_project"), self)
        open_project_action.setShortcut("Ctrl+Shift+O")
        open_project_action.triggered.connect(self._on_load_project)
        file_menu.addAction(open_project_action)
        save_shared_action = QAction("📤 " + i18n.tr("menu.save_shared"), self)
        save_shared_action.triggered.connect(self._on_save_shared)
        file_menu.addAction(save_shared_action)
        load_shared_action = QAction("📥 " + i18n.tr("menu.load_shared"), self)
        load_shared_action.triggered.connect(self._on_load_shared)
        file_menu.addAction(load_shared_action)

        # 最近项目
        recent = ProjectManager.recent_projects()
        if recent:
            self.recent_menu = _pin(file_menu.addMenu("📋 " + i18n.tr("menu.recent")))
            self._rebuild_recent_menu(recent)
            # A5: 欢迎页填充 (转换 dict → tuple)
            recent_items = [(r["name"], r["path"]) for r in recent]
            self.welcome_page.set_recent_projects(recent_items)

        file_menu.addSeparator()

        save_session = QAction("💾 " + i18n.tr("menu.save_session"), self)
        save_session.setShortcut("Ctrl+S")
        save_session.triggered.connect(self._on_save_session)
        file_menu.addAction(save_session)
        load_session = QAction("📂 " + i18n.tr("menu.load_session"), self)
        load_session.triggered.connect(self._on_load_session)
        file_menu.addAction(load_session)

        file_menu.addSeparator()
        exit_action = QAction("🚪 " + i18n.tr("menu.exit"), self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = _pin(menubar.addMenu(i18n.tr("menu.view")))
        self.toggle_sidebar_action = QAction(i18n.tr("menu.toggle_sidebar"), self)
        self.toggle_sidebar_action.setCheckable(True)
        self.toggle_sidebar_action.setChecked(True)
        self.toggle_sidebar_action.setShortcut("Ctrl+B")
        self.toggle_sidebar_action.triggered.connect(
            lambda checked: self._toggle_sidebar(not checked)
        )
        view_menu.addAction(self.toggle_sidebar_action)

        # ── 分析 — 全Tab分类子菜单 (v2.3.1: 全部走 i18n) ──
        analysis_menu = _pin(menubar.addMenu(i18n.tr("menu.analysis")))
        # 质量分析
        quality_sub = _pin(analysis_menu.addMenu(i18n.tr("sidebar.quality_tools")))
        for idx, key in [(1, "sidebar.spc"), (2, "sidebar.capability"), (3, "sidebar.msa"),
                         (4, "sidebar.hypothesis"), (5, "sidebar.doe"), (6, "sidebar.regression")]:
            a = QAction(i18n.tr(key), self)
            a.triggered.connect(lambda _, i=idx: self._switch_tab(i))
            quality_sub.addAction(a)
        # IE 工具
        ie_sub = _pin(analysis_menu.addMenu(i18n.tr("sidebar.ie_tools")))
        for idx, key in [(7, "sidebar.time_study"), (8, "sidebar.work_sampling"),
                         (9, "sidebar.line_balance"), (10, "sidebar.oee"),
                         (11, "menu.vsm"), (21, "sidebar.worker_machine"),
                         (22, "sidebar.std_work_combo"), (29, "sidebar.smed"), (31, "sidebar.tpm")]:
            a = QAction(i18n.tr(key), self)
            a.triggered.connect(lambda _, i=idx: self._switch_tab(i))
            ie_sub.addAction(a)
        # 图表工具
        chart_sub = _pin(analysis_menu.addMenu(i18n.tr("sidebar.chart_tools")))
        for idx, key in [(12, "sidebar.chart_tab"), (18, "sidebar.cap_comparison"),
                         (19, "sidebar.trend"), (20, "sidebar.summary_panel")]:
            a = QAction(i18n.tr(key), self)
            a.triggered.connect(lambda _, i=idx: self._switch_tab(i))
            chart_sub.addAction(a)
        # 工程工具
        eng_sub = _pin(analysis_menu.addMenu(i18n.tr("sidebar.engineering_tools")))
        for idx, key in [(13, "sidebar.reliability"), (14, "sidebar.fishbone"),
                         (15, "sidebar.pareto"), (16, "sidebar.fmea"),
                         (17, "sidebar.control_plan"), (30, "sidebar.8d"), (32, "sidebar.ppap")]:
            a = QAction(i18n.tr(key), self)
            a.triggered.connect(lambda _, i=idx: self._switch_tab(i))
            eng_sub.addAction(a)
        # 工作表/抽样/数据
        sheet_sub = _pin(analysis_menu.addMenu(i18n.tr("sidebar.sheet_tools")))
        for idx, key in [(23, "sidebar.sheet_merge"), (24, "sidebar.sheet_split"),
                         (25, "sidebar.layered_form")]:
            a = QAction(i18n.tr(key), self)
            a.triggered.connect(lambda _, i=idx: self._switch_tab(i))
            sheet_sub.addAction(a)
        analysis_menu.addSeparator()
        for idx, key in [(26, "sidebar.sampling"), (28, "sidebar.data_tools_tab"),
                         (27, "sidebar.dashboard"), (33, "sidebar.monitor"),
                         (34, "sidebar.multi_plant")]:
            a = QAction(i18n.tr(key), self)
            a.triggered.connect(lambda _, i=idx: self._switch_tab(i))
            analysis_menu.addAction(a)
        analysis_menu.addSeparator()
        run_all = QAction(i18n.tr("menu.run"), self)
        run_all.setShortcut("F5")
        run_all.triggered.connect(self._on_run_all_analyses)
        analysis_menu.addAction(run_all)

        # ── AI — 从工具菜单拆出 ──
        ai_menu = _pin(menubar.addMenu(i18n.tr("menu.ai")))
        ai_chat = QAction(i18n.tr("sidebar.llm"), self)
        ai_chat.triggered.connect(self._on_llm_assist)
        ai_menu.addAction(ai_chat)
        one_click = QAction(i18n.tr("menu.one_click"), self)
        one_click.triggered.connect(self._on_one_click_analysis)
        ai_menu.addAction(one_click)
        ai_menu.addSeparator()
        template_act = QAction(i18n.tr("menu.template"), self)
        template_act.triggered.connect(self._on_template_dialog)
        ai_menu.addAction(template_act)
        html_act = QAction(i18n.tr("menu.html_export"), self)
        html_act.triggered.connect(self._on_html_export)
        ai_menu.addAction(html_act)

        # ── 工具 — 精简后 ──
        tools_menu = _pin(menubar.addMenu(i18n.tr("menu.tools")))
        settings_act = QAction(i18n.tr("menu.settings"), self, triggered=self._on_settings)
        tools_menu.addAction(settings_act)
        batch_act = QAction(i18n.tr("menu.batch"), self, triggered=self._on_batch_scheduler)
        tools_menu.addAction(batch_act)
        tools_menu.addSeparator()
        clean_act = QAction(i18n.tr("sidebar.data_clean"), self, triggered=self._on_data_cleaner)
        tools_menu.addAction(clean_act)
        clean_wiz_act = QAction(i18n.tr("menu.data_clean_wizard"), self, triggered=self._on_data_clean_wizard)
        tools_menu.addAction(clean_wiz_act)
        tools_menu.addAction(QAction(i18n.tr("sidebar.template_help_tip"), self,
                                     triggered=self._on_template_help))
        tools_menu.addSeparator()
        tools_menu.addAction(QAction(i18n.tr("sidebar.diagnose"), self,
                                     triggered=self._on_diagnose))
        kb_action = QAction(i18n.tr("menu.kb_search"), self)
        kb_action.triggered.connect(self._on_llm_assist)
        tools_menu.addAction(kb_action)

        help_menu = _pin(menubar.addMenu(i18n.tr("menu.help")))
        about_action = QAction(i18n.tr("menu.about"), self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    def _on_llm_assist(self):
        from core.llm_client import LLMClient
        client = LLMClient()
        if not client.available:
            reply = QMessageBox.question(
                self, "AI 助手",
                "Ollama 服务未运行或未安装。\n\n"
                "安装步骤:\n"
                "1. 访问 https://ollama.com 下载并安装\n"
                "2. 终端运行: ollama pull qwen2.5:7b\n"
                "3. 启动: ollama serve\n\n"
                "是否仍然打开离线模式 (内置常见问答)?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes,
            )
            if reply != QMessageBox.Yes:
                return
        from ui.dialogs.llm_dialog import LLMDialog
        dlg = LLMDialog(self)
        dlg.exec()

    def _on_one_click_analysis(self):
        """一键智能分析 — 画像 → 推荐 → 执行 → 报告"""
        raw_data = self.current_data.get("raw_data", {})
        if not raw_data:
            QMessageBox.warning(self, "无数据", "请先导入数据文件后再运行一键分析")
            return
        from ui.dialogs.one_click_dialog import OneClickDialog
        dlg = OneClickDialog(raw_data, self)
        dlg.exec()

    def _on_template_dialog(self):
        from ui.dialogs.template_dialog import TemplateDialog
        dlg = TemplateDialog(self, analyses=self.analyses)
        dlg.exec()

    def _on_html_export(self):
        if not self.analyses:
            QMessageBox.warning(self, "无数据", "请先导入数据并运行分析")
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出 HTML 报告", "qa_report.html", "HTML 报告 (*.html)")
        if not path:
            return
        try:
            from output.html_export import export_html
            charts = self._collect_charts(list(self.analyses.keys()))
            export_html(list(self.analyses.values()), charts=charts, output_path=path)
            self.status_label.setText("HTML 报告已导出")
            QMessageBox.information(self, "导出完成", "HTML 报告已导出")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))

    def _setup_statusbar(self):
        self.statusBar().setStyleSheet(
            "QStatusBar { min-height: 24px; background: #13131c; } QStatusBar::item { border: none; }"
        )
        # 长消息自动省略号, tooltip 显示全文 (v2.3.1)
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
        self.sidebar.collapse_requested.connect(lambda: self._toggle_sidebar(True))
        self.welcome_page.import_data_clicked.connect(self._on_import_quality)
        self.welcome_page.import_ie_clicked.connect(self._on_import_ie)
        self.welcome_page.import_template_clicked.connect(self._on_import_template)
        self.welcome_page.new_analysis_clicked.connect(lambda: self._switch_tab(1))
        self.welcome_page.diagnose_clicked.connect(self._on_diagnose)
        self.welcome_page.open_project_clicked.connect(self._on_load_project)
        # Tab 导出/分析信号由 _lazy_load_tab() 在首次创建时动态连接

    def _switch_tab(self, index: int):
        if 0 <= index < self.stack.count():
            # 懒加载: 首次访问时按需创建
            if index > 0:
                self._lazy_load_tab(index)
            target = self.stack.widget(index)
            if not target:
                return
            # 淡入动画 (200ms)
            from PySide6.QtWidgets import QGraphicsOpacityEffect
            # C2: 停止旧动画并清理残留 effect
            if hasattr(self, '_tab_anim_widget') and self._tab_anim_widget:
                self._tab_anim_widget.setGraphicsEffect(None)
            if hasattr(self, '_tab_anim') and self._tab_anim:
                self._tab_anim.stop()
            effect = QGraphicsOpacityEffect()
            effect.setOpacity(0.0)
            target.setGraphicsEffect(effect)
            self._tab_anim_widget = target  # 记录 widget 待下次清理
            self.stack.setCurrentIndex(index)
            self.sidebar.set_active(index)

            anim = QPropertyAnimation(effect, b"opacity")
            anim.setDuration(200)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.OutCubic)

            def cleanup(tgt=target):
                tgt.setGraphicsEffect(None)
            anim.finished.connect(cleanup)
            self._tab_anim = anim  # 防止被 GC
            anim.start()

            # v2.4 F1: 切到 Dashboard (27) 时刷新 (指纹去重)
            if index == 27 and hasattr(self, '_tab_cache'):
                tab = self._tab_cache.get(27)
                if tab is not None and hasattr(tab, 'refresh_if_changed'):
                    tab.refresh_if_changed()

    def _import_cp_from_fmea(self, cp_rows: list):
        """从 FMEA 导入控制计划行"""
        # 控制计划 Tab 在 _tab_registry 中的索引
        from ui._tab_registry import TAB_REGISTRY
        cp_idx = None
        for idx, entry in enumerate(TAB_REGISTRY):
            if "控制计划" in str(entry):
                cp_idx = idx
                break
        if cp_idx is None:
            return

        # 懒加载控制计划 Tab
        self._lazy_load_tab(cp_idx)
        cp_tab = self._tab_cache.get(cp_idx)
        if cp_tab is None:
            return

        # 导入数据
        if hasattr(cp_tab, '_rows'):
            cp_tab._rows.extend(cp_rows)
            cp_tab._rebuild_table()

        # 切换到控制计划 Tab
        self._switch_tab(cp_idx)

    def _import_spc_from_cp(self, spc_items: list):
        """从控制计划导入 SPC 监控清单"""
        self._spc_monitoring_list = spc_items

        # 注入到 SPC Tab
        spc_tab = self._tab_cache.get(1)
        if spc_tab and hasattr(spc_tab, 'import_from_cp'):
            spc_tab.import_from_cp(spc_items)

        # 切换到 SPC Tab
        self._switch_tab(1)

    def _on_import_quality(self):
        dialog = ImportDialog(self, mode="quality")
        if dialog.exec():
            file_path, sheet_names = dialog.get_selection()
            try:
                self.status_label.setText(f"{i18n.tr('status.loading')}{file_path}...")
                raw_data = self.data_loader.load(file_path)
                audit("import_data", "user",
                      f"质量数据 {os.path.basename(file_path)}")
                self.current_data = {
                    "file_path": file_path,
                    "raw_data": raw_data,
                    "metadata": self.data_loader.metadata,
                }
                self.session_manager.create_session(file_path=file_path)
                try:
                    self._route_sheets_to_tabs(raw_data, worksheet_mode=True)
                except Exception as re:
                    import logging
                    logging.getLogger(__name__).exception("Sheet 分发失败")
                    QMessageBox.critical(self, "路由失败", f"Sheet 分发异常:\n{str(re)}")
                self.data_label.setText(f" {os.path.basename(file_path)} [{len(raw_data)} sheets]")

                try:
                    self.profile_result = self.data_profiler.profile(raw_data)
                except Exception:
                    self.profile_result = {}

                tabs = self._get_tabs()
                all_warnings = 0
                for idx, tab in tabs.items():
                    if idx > 6:
                        continue
                    df = getattr(tab, 'df', None)
                    if df is None or len(df) == 0:
                        continue
                    # A8: 用 pd.to_numeric 替代 select_dtypes (数据以 str 加载)
                    # 使用 iloc 按位置访问避免重复列名返回 DataFrame 导致 TypeError
                    num_cols = []
                    for i, c in enumerate(df.columns):
                        try:
                            s = pd.to_numeric(df.iloc[:, i], errors="coerce").dropna()
                            if len(s) > 0:
                                num_cols.append(c)
                        except (ValueError, TypeError):
                            pass
                    num_cols = num_cols[:20]
                    if num_cols:
                        v = self.data_validator.validate(df, num_cols)
                        all_warnings += v.get("warning_count", 0)

                if all_warnings > 0:
                    self.statusBar().showMessage(
                        f"{i18n.tr('status.loaded')}: {len(self.data_loader.metadata['sheet_names'])} 个工作表  |  数据校验: {all_warnings} 个警告",
                        8000,
                    )
                else:
                    self.status_label.setText(f"{i18n.tr('status.loaded')}: {len(self.data_loader.metadata['sheet_names'])} 个工作表")
            except Exception as e:
                import logging
                logging.getLogger(__name__).exception("导入工作表失败")
                QMessageBox.critical(self, i18n.tr("msg.import_failed"), f"{i18n.tr('msg.cannot_load')}\n{str(e)}")
                self.status_label.setText(i18n.tr("status.failed"))

    def _on_import_ie(self):
        dialog = ImportDialog(self, mode="ie")
        if dialog.exec():
            file_path, sheet_names = dialog.get_selection()
            try:
                self.status_label.setText(f"{i18n.tr('status.loading')}{file_path}...")
                raw_data = self.data_loader.load(file_path)
                audit("import_data", "user",
                      f"IE 数据 {os.path.basename(file_path)}")
                ie_data = self.data_loader.load_ie_data()

                if not ie_data:
                    from core.ie_parser import IEDataParser
                    QMessageBox.warning(self, "格式不匹配", IEDataParser.format_help())
                    self.status_label.setText(i18n.tr("status.ready"))
                    return

                self.current_data = {
                    "file_path": file_path,
                    "raw_data": raw_data,
                    "metadata": self.data_loader.metadata,
                    "ie_data": ie_data,
                }
                self.data_label.setText(f" {os.path.basename(file_path)} [{len(raw_data)} sheets]")

                if ie_data.get("TimeObservation"):
                    ts_tab = self._lazy_load_tab(7)
                    if ts_tab and hasattr(ts_tab, 'set_ie_data'):
                        ts_tab.set_ie_data(ie_data["TimeObservation"])
                if ie_data.get("Process"):
                    for tab_idx in (9, 11):
                        t = self._lazy_load_tab(tab_idx)
                        if t is None:
                            continue
                        if tab_idx == 9:
                            t.set_ie_data(ie_data["Process"])
                        else:
                            t.set_ie_data(processes=ie_data["Process"])
                if ie_data.get("MaterialFlow"):
                    t = self._lazy_load_tab(11)
                    if t is not None:
                        t.set_ie_data(flows=ie_data["MaterialFlow"])
                if ie_data.get("Resource"):
                    t = self._lazy_load_tab(10)
                    if t is not None:
                        t.set_ie_data(ie_data["Resource"])

                parts = []
                for obj_type, objects in ie_data.items():
                    type_labels = {
                        "Process": "工序表", "TimeObservation": "时间观测",
                        "QualityRecord": "质量记录", "MaterialFlow": "物流", "Resource": "资源",
                    }
                    parts.append(f"{type_labels.get(obj_type, obj_type)}: {len(objects)} 条")
                self.status_label.setText(f"已加载 IE 数据: {' | '.join(parts)}")
                try:
                    self.profile_result = self.data_profiler.profile(raw_data)
                except Exception:
                    self.profile_result = {}
            except Exception as e:
                QMessageBox.critical(self, "导入失败", f"无法加载 IE 数据:\n{str(e)}")
                self.status_label.setText(i18n.tr("status.failed"))

    def _on_import_db(self):
        dialog = DbConnectionDialog(self)
        if dialog.exec():
            config, table_names = dialog.get_selection()
            if not config or not table_names:
                return
            try:
                self.status_label.setText(f"正在从数据库加载 {len(table_names)} 个表...")
                loader = SqlLoader()
                try:
                    loader.connect(config)
                    raw_data = loader.load(table_names)
                finally:
                    try:
                        loader.disconnect()
                    except Exception:
                        pass
                audit("import_db", "user",
                      f"数据库 {config.get('database', '')} 表数={len(raw_data)}")

                self.current_data = {
                    "source": "database",
                    "db_config": config,
                    "raw_data": raw_data,
                    "metadata": loader.metadata,
                }
                self.data_loader.raw_data = raw_data
                self.data_loader.metadata = loader.metadata

                self._route_sheets_to_tabs(raw_data, worksheet_mode=False)
                db_label = f"{config.get('database', 'DB')}"
                self.data_label.setText(f" DB: {db_label} [{len(raw_data)} tables]")

                try:
                    self.profile_result = self.data_profiler.profile(raw_data)
                except Exception:
                    self.profile_result = {}

                self.status_label.setText(
                    f"数据库加载完成: {len(table_names)} 个表, "
                    f"{loader.metadata.get('total_rows', 0)} 行"
                )
            except Exception as e:
                QMessageBox.critical(
                    self, "数据库导入失败",
                    f"从数据库加载数据失败:\n{str(e)}"
                )
                self.status_label.setText("数据库导入失败")

    def _on_template_help(self):
        from ui.dialogs.template_help_dialog import TemplateHelpDialog
        dlg = TemplateHelpDialog(self)
        dlg.exec()

    def _on_import_data(self):
        """兼容旧调用 — 默认质量导入"""
        self._on_import_quality()

    def _route_sheets_to_tabs(self, raw_data: Dict[str, pd.DataFrame], worksheet_mode: bool = False):
        """将导入的 Sheet 分配到各分析 Tab。
        worksheet_mode=True: 分配到除 IE 工具(7-11,21-22)外的所有 Tab。
        worksheet_mode=False: 分配到所有 Tab（含 IE）。"""
        # IE 专用索引 (工时研究/工作抽样/线平衡/OEE/VSM/人机/标准作业)
        IE_INDICES = {7, 8, 9, 10, 11, 21, 22}

        # Sheet → Tab 自动匹配关键词 (sheet名含这些关键词则优先分配到对应Tab)
        sheet_map = {
            1:  ["spc", "控制图", "control chart"],
            2:  ["能力", "capability", "cpk", "ppk"],
            3:  ["msa", "gage", "量具", "r&r", "grr"],
            4:  ["假设", "hypothesis", "t_test", "anova", "检验"],
            5:  ["doe", "因子", "实验设计", "design"],
            6:  ["regression", "回归", "reg"],
            12: ["chart", "图表", "chart_tab", "可视化"],
            13: ["reliability", "可靠性", "weibull", "mtbf", "寿命"],
            14: ["fishbone", "鱼骨", "因果", "ishikawa"],
            15: ["pareto", "帕累托", "柏拉图", "abc"],
            16: ["fmea", "失效", "fmea"],
            17: ["control_plan", "控制计划", "cp"],
            18: ["cap_comparison", "能力对比", "comparison"],
            19: ["trend", "趋势", "trend"],
            20: ["summary", "摘要", "汇总", "summary_panel"],
            23: ["merge", "合并", "sheet_merge"],
            24: ["split", "拆分", "sheet_split"],
            25: ["layered", "lpa", "分层", "审核"],
            26: ["sampling", "抽样", "aql", "采样"],
            27: ["dashboard", "仪表盘", "dashboard", "汇总报告"],
            28: ["data_tools", "数据工具", "生成", "转换"],
        }

        # 1) 将所有 Sheet 填入各 Tab 的 sheet_combo / set_raw_data
        #    遍历 sheet_map 中所有索引，按需懒加载 Tab
        all_indices = set(sheet_map.keys()) | {16, 17}  # 补充 FMEA(16)/控制计划(17)
        for idx in all_indices:
            if worksheet_mode and idx in IE_INDICES:
                continue
            tab = self._lazy_load_tab(idx)
            if tab and hasattr(tab, 'set_raw_data'):
                tab.set_raw_data(raw_data, self.data_parser)

        # 2) 按关键词自动匹配 Sheet 到对应 Tab
        assigned = set()
        for tab_idx, keywords in sheet_map.items():
            if worksheet_mode and tab_idx in IE_INDICES:
                continue
            tab = self._lazy_load_tab(tab_idx)
            if not tab or not hasattr(tab, 'sheet_combo'):
                continue
            for sname in raw_data:
                if sname in assigned:
                    continue
                if any(kw in sname.lower() for kw in keywords):
                    pos = tab.sheet_combo.findText(sname)
                    if pos >= 0:
                        tab.sheet_combo.setCurrentIndex(pos)
                        assigned.add(sname)
                        break

        sheets_info = ", ".join(f"{s} ({len(raw_data[s])}r)" for s in assigned)
        if sheets_info:
            self.status_label.setText(f"Sheet 已自动匹配: {sheets_info}")

    def _on_import_template(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, i18n.tr("menu.import_template"), "",
            "Excel/JSON (*.xlsx *.xls *.xlsm *.json);;All (*.*)",
        )
        if file_path:
            try:
                self.template_parser.load(file_path)
                analyses_list = self.template_parser.get_analysis_list()
                if not analyses_list:
                    QMessageBox.warning(self, "模板为空", "未解析到有效的分析配置")
                    return

                atype_to_tab = {
                    "xbar_r": 1, "xbar_s": 1, "imr": 1,
                    "p_chart": 1, "np_chart": 1, "c_chart": 1, "u_chart": 1,
                    "cusum": 1, "ewma": 1,
                    "normal_capability": 2, "non_normal_capability": 2,
                    "between_within_capability": 2,
                    "gage_rr_crossed": 3, "gage_rr_nested": 3,
                    "linearity_bias": 3, "attribute_agreement": 3,
                    "t_test_1sample": 4, "t_test_2sample": 4, "t_test_paired": 4,
                    "anova_oneway": 4, "anova_twoway": 4,
                    "normality_test": 4, "variance_test": 4,
                    "factorial_design": 5, "response_surface": 5, "doe_analysis": 5,
                    "box_behnken": 5,
                    "linear_regression": 6, "correlation_heatmap": 6,
                }
                tabs = self._get_tabs()
                applied = 0

                for analysis in analyses_list:
                    atype = analysis.get("analysis_type", "").lower().strip()
                    tab_idx = atype_to_tab.get(atype)
                    if tab_idx is None:
                        continue
                    tab = tabs.get(tab_idx)
                    if tab is None:
                        continue

                    col = analysis.get("measurement_column", "")
                    usl = analysis.get("usl")
                    lsl = analysis.get("lsl")
                    subgroup = analysis.get("subgroup_size")

                    self._apply_template_to_tab(tab, tab_idx, atype, col, usl, lsl, subgroup, analysis)
                    applied += 1

                self.statusBar().showMessage(f"模板已应用: {applied}/{len(analyses_list)} 项", 5000)
                if applied > 0:
                    QMessageBox.information(
                        self, "模板应用完成",
                        f"成功应用 {applied} 个分析配置到对应模块\n\n"
                        + "\n".join(f" - {a.get('analysis_type', '?')}"
                                    for a in analyses_list[:10])
                    )
            except Exception as e:
                QMessageBox.critical(self, i18n.tr("msg.template_failed"), str(e))

    def _apply_template_to_tab(self, tab, tab_idx: int, atype: str,
                                 col: str, usl, lsl, subgroup, analysis: dict):
        method_maps = {
            1: {"xbar_r": "XBar-R", "xbar_s": "XBar-S", "imr": "I-MR",
                "p_chart": "P Chart", "np_chart": "NP Chart",
                "c_chart": "C Chart", "u_chart": "U Chart"},
            2: {"normal_capability": "正态过程能力",
                "non_normal_capability": "非正态 (Box-Cox)",
                "between_within_capability": "组间/组内能力"},
            3: {"gage_rr_crossed": "Gage R&R (交叉)",
                "gage_rr_nested": "Gage R&R (嵌套)",
                "linearity_bias": "线性与偏倚",
                "attribute_agreement": "属性一致性"},
            4: {"t_test_1sample": "单样本 t检验",
                "t_test_2sample": "双样本 t检验",
                "t_test_paired": "配对 t检验",
                "anova_oneway": "单因素 ANOVA",
                "anova_twoway": "双因素 ANOVA",
                "normality_test": "正态性检验",
                "variance_test": "方差齐性检验"},
             5: {"factorial_design": "因子设计分析",
                 "response_surface": "响应曲面分析 (CCD)",
                 "doe_analysis": "DOE 分析",
                 "box_behnken": "Box-Behnken 设计"},
             6: {"linear_regression": "回归分析",
                 "correlation_heatmap": "相关性热力图"},
        }

        method_name = method_maps.get(tab_idx, {}).get(atype, "")

        if tab_idx == 1:
            col_combo = getattr(tab, 'col_combo', None)
            if col_combo and col:
                idx = col_combo.findText(col)
                if idx >= 0:
                    col_combo.setCurrentIndex(idx)
            if method_name:
                chart_combo = getattr(tab, 'chart_type_combo', None)
                if chart_combo:
                    idx = chart_combo.findText(method_name)
                    if idx >= 0:
                        chart_combo.setCurrentIndex(idx)
            if subgroup and hasattr(tab, 'subgroup_spin'):
                tab.subgroup_spin.setValue(int(subgroup))
            if usl is not None and hasattr(tab, 'usl_spin'):
                tab.usl_spin.setValue(float(usl))
            if lsl is not None and hasattr(tab, 'lsl_spin'):
                tab.lsl_spin.setValue(float(lsl))

        elif tab_idx == 2:
            col_combo = getattr(tab, 'col_combo', None)
            if col_combo and col:
                idx = col_combo.findText(col)
                if idx >= 0:
                    col_combo.setCurrentIndex(idx)
            if method_name:
                method_combo = getattr(tab, 'method_combo', None)
                if method_combo:
                    idx = method_combo.findText(method_name)
                    if idx >= 0:
                        method_combo.setCurrentIndex(idx)
            if usl is not None and hasattr(tab, 'usl_spin'):
                tab.usl_spin.setValue(float(usl))
            if lsl is not None and hasattr(tab, 'lsl_spin'):
                tab.lsl_spin.setValue(float(lsl))
            target = analysis.get("target")
            if target is not None and hasattr(tab, 'target_spin'):
                tab.target_spin.setValue(float(target))

        elif tab_idx == 3:
            measure_col = getattr(tab, 'measure_col', None)
            if measure_col and col:
                idx = measure_col.findText(col)
                if idx >= 0:
                    measure_col.setCurrentIndex(idx)
            if method_name:
                method_combo = getattr(tab, 'method_combo', None)
                if method_combo:
                    idx = method_combo.findText(method_name)
                    if idx >= 0:
                        method_combo.setCurrentIndex(idx)

        elif tab_idx == 4:
            col1 = getattr(tab, 'col1_combo', None)
            if col1 and col:
                idx = col1.findText(col)
                if idx >= 0:
                    col1.setCurrentIndex(idx)
            if method_name:
                method_combo = getattr(tab, 'method_combo', None)
                if method_combo:
                    idx = method_combo.findText(method_name)
                    if idx >= 0:
                        method_combo.setCurrentIndex(idx)
            confidence = analysis.get("confidence_level")
            if confidence is not None and hasattr(tab, 'confidence_spin'):
                tab.confidence_spin.setValue(float(confidence))

        elif tab_idx == 5:
            response = getattr(tab, 'response_combo', None)
            if response and col:
                idx = response.findText(col)
                if idx >= 0:
                    response.setCurrentIndex(idx)
            if method_name:
                method_combo = getattr(tab, 'method_combo', None)
                if method_combo:
                    idx = method_combo.findText(method_name)
                    if idx >= 0:
                        method_combo.setCurrentIndex(idx)

        elif tab_idx == 6:
            response = getattr(tab, 'response_combo', None)
            if response and col:
                idx = response.findText(col)
                if idx >= 0:
                    response.setCurrentIndex(idx)
            factor1 = analysis.get("factor1")
            factor2 = analysis.get("factor2")
            factor3 = analysis.get("factor3")
            for i, fc in enumerate([factor1, factor2, factor3], 1):
                if fc:
                    combo = getattr(tab, f'factor{i}_combo', None)
                    if combo:
                        idx = combo.findText(fc)
                        if idx >= 0:
                            combo.setCurrentIndex(idx)

    def _on_analysis_finished(self, idx: int):
        """分析完成统一收纳点: analyses + 会话 + 侧栏历史 + Dashboard

        v2.4 修复: 补上 session_manager.add_analysis (原死代码 _on_run_analysis
        携带, 迁移到此处后删除死代码)
        """
        tabs = self._get_tabs()
        tab = tabs.get(idx)
        result = getattr(tab, 'current_result', None)
        if result:
            self.analyses[idx] = result.copy()
            self.analyses[idx]["_completed_at"] = datetime.now().isoformat(timespec="seconds")
            self.session_manager.add_analysis(
                result.get("analysis_type", "Unknown"),
                result.get("params", {}),
                result.get("result", {})
            )
            atype = result.get("analysis_type", "")
            key_res = self._summarize_result(result.get("result", {}))
            self.sidebar.add_history(idx, atype, key_res)
        self._notify_dashboard()

    def _notify_dashboard(self):
        """v2.4 F1: 分析完成后通知 Dashboard 刷新 (仅当已懒加载时)

        用 refresh_if_changed 去重 — 批量分析时 N 次通知只重建一次
        """
        tab = self._tab_cache.get(27)
        if tab is not None and hasattr(tab, 'refresh_if_changed'):
            tab.refresh_if_changed()

    def _on_run_all_analyses(self):
        if not self.current_data:
            QMessageBox.warning(self, i18n.tr("msg.no_data"), i18n.tr("msg.no_data_file"))
            return

        from PySide6.QtWidgets import QApplication
        tabs = self._get_tabs(force_load=True)
        success = 0
        failed = 0

        for i, (idx, tab) in enumerate(tabs.items()):
            # W49: 每个 Tab 让出事件循环，防止 UI 完全冻结
            QApplication.processEvents()
            if not _tab_is_runnable(tab):
                continue
            try:
                tab.run_and_display()
                result = getattr(tab, 'current_result', None)
                if result:
                    self.analyses[idx] = result.copy()
                    self.analyses[idx]["_completed_at"] = datetime.now().isoformat(timespec="seconds")
                    atype = result.get("analysis_type", "")
                    key_res = self._summarize_result(result.get("result", {}))
                    self.sidebar.add_history(idx, atype, key_res)
                success += 1
            except Exception:
                import logging
                logging.getLogger(__name__).exception(f"批量分析 tab idx={idx} 失败")
                failed += 1

        self.statusBar().showMessage(
            f"批量分析完成: 成功 {success}, 失败 {failed}", 5000
        )
        self._notify_dashboard()
        if success > 0:
            self.stack.setCurrentIndex(1)
            self.sidebar.set_active(1)

    def _lazy_load_tab(self, idx: int):
        """按需加载 Tab — 首次访问时 import + 实例化 + 替换占位符"""
        if idx in self._tab_cache:
            return self._tab_cache[idx]

        # 插件 Tab (index >= 100)
        if idx >= self._plugin_tab_start:
            if idx in self._plugin_tabs:
                p = self._plugin_tabs[idx]
                tab = p.create_tab()
                self._tab_cache[idx] = tab
                old = self.stack.widget(idx)
                if old:
                    self.stack.removeWidget(old)
                self.stack.insertWidget(idx, tab)
                if old and old.objectName().startswith("placeholder"):
                    old.deleteLater()
                self._connect_tab_signals(idx, tab)
                return tab
            return None

        # 内置 Tab
        from ui._tab_registry import INDEX_MAP
        entry = INDEX_MAP.get(idx)
        if not entry or not tab_allowed(idx):
            return None

        _, _, class_name, module_path, _ = entry
        try:
            import importlib
            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name)
            tab = cls()
        except Exception:
            import logging
            logging.getLogger(__name__).exception(
                f"懒加载 Tab 失败: idx={idx} {class_name} from {module_path}"
            )
            return None

        self._tab_cache[idx] = tab
        # 替换占位符（先同步移除再插入，防止 insertWidget 导致索引错位）
        old = self.stack.widget(idx)
        if old:
            self.stack.removeWidget(old)
        self.stack.insertWidget(idx, tab)
        if old and old.objectName().startswith("placeholder"):
            old.deleteLater()

        # 连接信号
        self._connect_tab_signals(idx, tab)
        return tab

    def _connect_tab_signals(self, idx: int, tab):
        """为新创建的 Tab 建立信号连接"""
        if hasattr(tab, 'export_clicked'):
            tab.export_clicked.connect(lambda tid=idx: self._on_export_single(tid, "docx"))
        if hasattr(tab, 'analysis_completed'):
            tab.analysis_completed.connect(lambda tid=idx: self._on_analysis_finished(tid))
        # 注入 project_context 到五链相关 Tab
        _CONTEXT_TABS = {1, 16, 17, 30, 32}  # SPC, FMEA, CP, 8D, PPAP
        if idx in _CONTEXT_TABS and hasattr(tab, 'set_project_context'):
            tab.set_project_context(self.project_context)

    def _get_tabs(self, force_load: bool = False):
        """获取 Tab 字典。force_load=False 仅返回已缓存的(懒加载友好)；force_load=True 全量加载"""
        result = {}
        if force_load:
            idx_range = list(range(1, _PLUGIN_TAB_START))  # v2.5: 35 tabs
        else:
            idx_range = sorted(self._tab_cache.keys())
        for idx in idx_range:
            tab = self._lazy_load_tab(idx)
            if tab:
                result[idx] = tab
        for idx in self._plugin_tabs:
            tab = self._lazy_load_tab(idx)
            if tab:
                result[idx] = tab
        return result

    def _collect_charts(self, indices: list):
        charts = {}
        tabs = self._get_tabs()
        for idx in indices:
            tab = tabs.get(idx)
            if tab and hasattr(tab, 'current_figure') and tab.current_figure:
                fig = tab.current_figure
                fig.set_size_inches(*CHART_FIGSIZE)
                atype = self.analyses[idx].get("analysis_type", "")
                from output.chart_engine import figure_to_bytes
                charts[atype] = figure_to_bytes(fig)
                tab.canvas.draw()
        return charts

    def _on_export_single(self, idx: int, fmt: str = "docx"):
        result = self.analyses.get(idx)
        if not result:
            QMessageBox.warning(self, i18n.tr("msg.no_results"), i18n.tr("msg.run_first"))
            return

        filters = {"xlsx": "Excel (*.xlsx)", "docx": "Word (*.docx)", "pdf": "PDF (*.pdf)"}
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出报告", f"分析报告.{fmt}", filters.get(fmt, "")
        )

        if file_path:
            try:
                self.status_label.setText(f"{i18n.tr('status.exporting')} {fmt.upper()}...")
                if fmt == "xlsx":
                    from output.excel_report import ExcelReport
                    ExcelReport().generate([result], file_path)
                elif fmt == "docx":
                    charts = self._collect_charts([idx])
                    from output.word_report import WordReport
                    WordReport().generate([result], file_path, charts=charts)
                elif fmt == "pdf":
                    charts = self._collect_charts([idx])
                    from output.pdf_report import generate_pdf_report
                    generate_pdf_report([result], file_path, charts=charts)
                self.status_label.setText(f"{i18n.tr('status.exported')}{file_path}")
                audit("export", "user",
                      f"单Tab导出 {fmt} {os.path.basename(file_path)}")
                QMessageBox.information(self, i18n.tr("msg.export_complete"), f"{i18n.tr('msg.export_saved')}\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, i18n.tr("msg.export_failed"), str(e))

    def _on_export_all(self, fmt: str = "docx"):
        if not self.analyses:
            QMessageBox.warning(self, i18n.tr("msg.no_results"), i18n.tr("msg.run_first"))
            return

        filters = {"xlsx": "Excel (*.xlsx)", "docx": "Word (*.docx)", "pdf": "PDF (*.pdf)"}
        file_path, _ = QFileDialog.getSaveFileName(
            self, "汇总导出", f"Quality_Report.{fmt}", filters.get(fmt, "")
        )

        if file_path:
            try:
                self.status_label.setText(f"{i18n.tr('status.exporting')} {fmt.upper()}...")
                analyses_list = list(self.analyses.values())
                if fmt == "xlsx":
                    from output.excel_report import ExcelReport
                    ExcelReport().generate(analyses_list, file_path)
                elif fmt == "docx":
                    charts = self._collect_charts(list(self.analyses.keys()))
                    from output.word_report import WordReport
                    WordReport().generate(analyses_list, file_path, charts=charts)
                elif fmt == "pdf":
                    charts = self._collect_charts(list(self.analyses.keys()))
                    from output.pdf_report import generate_pdf_report
                    generate_pdf_report(analyses_list, file_path, charts=charts)
                self.status_label.setText(f"{i18n.tr('status.exported')}{file_path}")
                audit("export", "user",
                      f"汇总导出 {fmt} {os.path.basename(file_path)}")
                QMessageBox.information(self, i18n.tr("msg.export_complete"), f"{i18n.tr('msg.export_saved')}\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, i18n.tr("msg.export_failed"), str(e))

    def _on_export_compliance(self, template_id: str):
        if not self.analyses:
            QMessageBox.warning(self, i18n.tr("msg.no_results"), i18n.tr("msg.run_first"))
            return
        from output.compliance_report import ComplianceReportGenerator
        t = ComplianceReportGenerator.load_template(template_id)
        fmt = t.get("format", "docx")
        filters = {"docx": "Word (*.docx)", "pdf": "PDF (*.pdf)"}
        ext = "docx" if fmt != "pdf" else "pdf"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出合规报告", f"Compliance_Report.{ext}", filters.get(fmt, ""),
        )
        if file_path:
            try:
                self.status_label.setText("正在导出合规报告...")
                charts = self._collect_charts(list(self.analyses.keys()))
                ComplianceReportGenerator.generate(
                    template_id, list(self.analyses.values()),
                    file_path, charts=charts,
                )
                self.status_label.setText(f"{i18n.tr('status.exported')}{file_path}")
                audit("export", "user",
                      f"合规报告 {template_id} {os.path.basename(file_path)}")
                QMessageBox.information(self, i18n.tr("msg.export_complete"),
                                        f"{i18n.tr('msg.export_saved')}\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, i18n.tr("msg.export_failed"), str(e))

    def _on_save_project(self):
        if not self.current_data:
            QMessageBox.warning(self, "无数据", "请先导入数据并运行分析")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存项目", "QA_Project.qap", "QA-Tool 项目 (*.qap)"
        )
        if not path:
            return
        try:
            self.status_label.setText("正在保存项目...")
            raw = self.current_data.get("raw_data", {})
            charts = {}
            for label, buf in self._collect_charts(list(self.analyses.keys())).items():
                charts[label] = buf.getvalue() if hasattr(buf, 'getvalue') else buf
            ProjectManager.save_project(
                path, raw, self.analyses, charts, "",
                project_context=self.project_context.to_dict() if self.project_context else None,
            )
            self.status_label.setText(f"项目已保存: {path}")
            recent = ProjectManager.recent_projects()
            self._rebuild_recent_menu(recent)
            recent_items = [(r["name"], r["path"]) for r in recent]
            self.welcome_page.set_recent_projects(recent_items)
            QMessageBox.information(self, "保存完成", f"项目已保存到:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))

    def _apply_loaded_project(self, project: dict, path: str,
                              status_msg: str | None = None,
                              data_label_suffix: bool = True,
                              success_msg: str | None = None):
        """应用已加载的 .qap 项目: 恢复数据/分析结果/最近菜单并刷新 Dashboard"""
        raw_data = project["raw_data"]
        self.current_data = {
            "file_path": path,
            "raw_data": raw_data,
            "metadata": {"sheet_names": list(raw_data.keys()), "total_rows": sum(len(df) for df in raw_data.values())},
        }
        self.data_loader.raw_data = raw_data
        self.data_loader.metadata = self.current_data["metadata"]
        self._route_sheets_to_tabs(raw_data)
        self.analyses = project["analyses"]

        # 恢复 project_context
        ctx_dict = project.get("project_context")
        if ctx_dict:
            from core.project_context import ProjectContext as PC
            self.project_context = PC.from_dict(ctx_dict)
        else:
            self.project_context = ProjectContext()
        # 重新注入到已加载的 Tab
        _CONTEXT_TABS = {1, 16, 17, 30, 32}
        for idx in _CONTEXT_TABS:
            tab = self._tab_cache.get(idx)
            if tab and hasattr(tab, 'set_project_context'):
                tab.set_project_context(self.project_context)

        info = project["manifest"]
        suffix = f" [{info.get('sheet_count', 0)} sheets]" if data_label_suffix else ""
        self.data_label.setText(f" {os.path.basename(path)}{suffix}")
        recent = ProjectManager.recent_projects()
        self._rebuild_recent_menu(recent)
        recent_items = [(r["name"], r["path"]) for r in recent]
        self.welcome_page.set_recent_projects(recent_items)
        self.status_label.setText(
            status_msg or f"项目已加载: {info.get('analysis_count', 0)} 个分析"
        )
        self._notify_dashboard()
        if success_msg:
            QMessageBox.information(self, "加载完成", success_msg)

    def _on_load_project(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "打开项目", "", "QA-Tool 项目 (*.qap)"
        )
        if not path:
            return
        try:
            self.status_label.setText("正在加载项目...")
            project = ProjectManager.load_project(path)
            self._apply_loaded_project(
                project, path,
                success_msg=f"已恢复 {len(project['raw_data'])} 个数据表、{len(self.analyses)} 个分析结果",
            )
        except Exception as e:
            QMessageBox.critical(self, "加载失败", str(e))

    def _load_project_by_path(self, path: str):
        """通过路径直接加载项目（供欢迎页最近项目使用）"""
        try:
            self.status_label.setText("正在加载项目...")
            project = ProjectManager.load_project(path)
            self._apply_loaded_project(project, path)
        except Exception as e:
            QMessageBox.critical(self, "加载失败", str(e))

    def _rebuild_recent_menu(self, recent: list):
        if not hasattr(self, 'recent_menu'):
            return
        self.recent_menu.clear()
        for r in recent:
            name = r.get("name", "?")[:50]
            action = QAction(name, self)
            p = r["path"]
            action.triggered.connect(lambda checked, path=p: self._on_load_recent(path))
            self.recent_menu.addAction(action)

    def _on_load_recent(self, path: str):
        if os.path.exists(path):
            # 直接使用已知路径加载（不弹文件对话框）
            try:
                self.status_label.setText("正在加载项目...")
                project = ProjectManager.load_project(path)
                self._apply_loaded_project(
                    project, path,
                    status_msg=f"项目已加载: {len(project['raw_data'])} sheets",
                    data_label_suffix=False,
                    success_msg=f"已恢复 {len(project['analyses'])} 个分析",
                )
            except Exception as e:
                QMessageBox.critical(self, "加载失败", str(e))
        else:
            QMessageBox.warning(self, "文件不存在", f"项目文件已移动或删除:\n{path}")

    def _on_save_session(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, i18n.tr("menu.save_session"), "session.json", "JSON (*.json)"
        )
        if file_path:
            tabs = self._get_tabs()
            self.session_manager.current_session["tab_params"] = {}
            for idx, tab in tabs.items():
                params = {}
                if idx == 1:
                    if hasattr(tab, 'col_combo'):
                        params["column"] = tab.col_combo.currentText()
                    if hasattr(tab, 'chart_type_combo'):
                        params["chart_type"] = tab.chart_type_combo.currentText()
                    if hasattr(tab, 'subgroup_spin'):
                        params["subgroup_size"] = tab.subgroup_spin.value()
                    if hasattr(tab, 'usl_spin'):
                        params["usl"] = tab.usl_spin.value()
                    if hasattr(tab, 'lsl_spin'):
                        params["lsl"] = tab.lsl_spin.value()
                elif idx == 2:
                    if hasattr(tab, 'col_combo'):
                        params["column"] = tab.col_combo.currentText()
                    if hasattr(tab, 'method_combo'):
                        params["method"] = tab.method_combo.currentText()
                    if hasattr(tab, 'usl_spin'):
                        params["usl"] = tab.usl_spin.value()
                    if hasattr(tab, 'lsl_spin'):
                        params["lsl"] = tab.lsl_spin.value()
                elif idx == 3:
                    if hasattr(tab, 'measure_col'):
                        params["column"] = tab.measure_col.currentText()
                    if hasattr(tab, 'method_combo'):
                        params["method"] = tab.method_combo.currentText()
                elif idx == 4:
                    if hasattr(tab, 'col1_combo'):
                        params["col1"] = tab.col1_combo.currentText()
                    if hasattr(tab, 'col2_combo'):
                        params["col2"] = tab.col2_combo.currentText()
                    if hasattr(tab, 'method_combo'):
                        params["method"] = tab.method_combo.currentText()
                elif idx == 5:
                    if hasattr(tab, 'response_combo'):
                        params["response"] = tab.response_combo.currentText()
                    if hasattr(tab, 'method_combo'):
                        params["method"] = tab.method_combo.currentText()
                elif idx == 6:
                    if hasattr(tab, 'response_combo'):
                        params["response"] = tab.response_combo.currentText()
                    if hasattr(tab, 'factor1_combo'):
                        params["factor1"] = tab.factor1_combo.currentText()
                    if hasattr(tab, 'factor2_combo'):
                        params["factor2"] = tab.factor2_combo.currentText()
                    if hasattr(tab, 'factor3_combo'):
                        params["factor3"] = tab.factor3_combo.currentText()
                if params:
                    self.session_manager.current_session["tab_params"][str(idx)] = params

            # v2.4 修复 (遗留 #3): 内存分析结果快照写入会话
            self.session_manager.set_analyses(self.analyses)

            path = self.session_manager.save(file_path)
            self.status_label.setText(f"{i18n.tr('status.session_saved')}{path}")

    def _on_load_session(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, i18n.tr("menu.load_session"), "", "JSON (*.json)"
        )
        if file_path:
            try:
                data = self.session_manager.load(file_path)
                src_file = data.get("file_path", "")
                if src_file and os.path.exists(src_file):
                    raw_data = self.data_loader.load(src_file)
                    self.current_data = {
                        "file_path": src_file,
                        "raw_data": raw_data,
                        "metadata": self.data_loader.metadata,
                    }
                    self._route_sheets_to_tabs(raw_data)
                    self.data_label.setText(f" {os.path.basename(src_file)}")

                tab_params = data.get("tab_params", {})
                tabs = self._get_tabs()
                for idx_str, params in tab_params.items():
                    idx = int(idx_str)
                    tab = tabs.get(idx)
                    if tab is None:
                        continue
                    col = params.get("column") or params.get("col1") or params.get("response")
                    if col:
                        combo_attrs = {
                            1: "col_combo", 2: "col_combo",
                            3: "measure_col", 4: "col1_combo", 5: "response_combo",
                            6: "response_combo",
                        }
                        combo = getattr(tab, combo_attrs.get(idx, ""), None)
                        if combo:
                            ci = combo.findText(col)
                            if ci >= 0:
                                combo.setCurrentIndex(ci)

                    method = params.get("method") or params.get("chart_type")
                    if method and hasattr(tab, 'method_combo'):
                        mi = tab.method_combo.findText(method)
                        if mi >= 0:
                            tab.method_combo.setCurrentIndex(mi)
                    if method and idx == 1 and hasattr(tab, 'chart_type_combo'):
                        mi = tab.chart_type_combo.findText(method)
                        if mi >= 0:
                            tab.chart_type_combo.setCurrentIndex(mi)

                    usl = params.get("usl")
                    if usl is not None and hasattr(tab, 'usl_spin'):
                        tab.usl_spin.setValue(float(usl))
                    lsl = params.get("lsl")
                    if lsl is not None and hasattr(tab, 'lsl_spin'):
                        tab.lsl_spin.setValue(float(lsl))
                    subgroup = params.get("subgroup_size")
                    if subgroup is not None and hasattr(tab, 'subgroup_spin'):
                        tab.subgroup_spin.setValue(int(subgroup))

                # v2.4 修复 (遗留 #3): 恢复分析结果快照 + 刷新 Dashboard
                self.analyses = self.session_manager.get_analyses()
                self._notify_dashboard()
                count = len(self.analyses)
                self.statusBar().showMessage(
                    f"会话已加载: {data.get('name', '')} ({count} 个分析)", 5000
                )
            except Exception as e:
                QMessageBox.critical(self, i18n.tr("msg.import_failed"), str(e))

    def _on_settings(self):
        from config.settings import save_config
        dialog = SettingsDialog(self)
        if dialog.exec():
            save_config(dialog.get_values())
            from output.chart_engine import setup_chinese_font
            setup_chinese_font()
            self.statusBar().showMessage("设置已保存", 3000)

    def _on_data_cleaner(self):
        idx = self.stack.currentIndex()
        tabs = self._get_tabs()
        current_tab = tabs.get(idx)
        if current_tab is None or getattr(current_tab, 'df', None) is None or len(current_tab.df) == 0:
            QMessageBox.warning(self, "无数据", "请先导入数据文件并选择一个分析模块")
            return
        from ui.dialogs.data_cleaner import DataCleaner
        dialog = DataCleaner(current_tab.df, self)
        if dialog.exec():
            cleaned = dialog.get_cleaned_df()
            if cleaned is not None:
                current_df_id = id(current_tab.df)
                updated = set()
                for ti, tab in tabs.items():
                    df = getattr(tab, 'df', None)
                    if df is not None and id(df) == current_df_id:
                        info = getattr(tab, 'parsed_info', None)
                        if info:
                            info = info.copy()
                            info["numeric_columns"] = list(cleaned.select_dtypes(include="number").columns)
                        tab.set_data(cleaned.copy(), info or {})
                        updated.add(ti)
                self.statusBar().showMessage(
                    f"数据清洗已完成，已更新 {len(updated)} 个分析模块", 5000
                )

    def _on_data_clean_wizard(self):
        if not self.current_data:
            QMessageBox.information(self, "提示", "请先导入数据文件")
            return
        raw = self.current_data.get("raw_data", {})
        # 取第一个 sheet
        first_key = next(iter(raw.keys()), None)
        if first_key is None:
            return
        df = raw[first_key]
        from ui.dialogs.data_clean_wizard import DataCleanWizard
        wiz = DataCleanWizard(df, self)
        if wiz.exec() == DataCleanWizard.Accepted:
            cleaned = wiz.get_result()
            raw[first_key] = cleaned
            self.current_data["raw_data"] = raw
            self._route_sheets_to_tabs(raw, worksheet_mode=False)
            audit("data_clean", "user",
                  f"清洗 {first_key}")
            self.statusBar().showMessage("数据清洗向导完成", 5000)

    def _summarize_result(self, result: dict) -> str:
        cap = result.get("capability", {})
        if cap.get("grade"):
            return cap["grade"]
        acceptance = result.get("acceptance", {})
        if acceptance.get("message"):
            return acceptance["message"][:8]
        if "p_value" in result:
            return "显著" if result.get("is_significant") else "不显著"
        if "model" in result:
            r2 = result["model"].get("r_squared", 0)
            return f"R²={r2:.2f}"
        return ""

    def _restore_window_state(self):
        settings = QSettings("QA-Tool", "MainWindow")
        geo = settings.value("geometry")
        state = settings.value("windowState")
        if geo:
            self.restoreGeometry(geo)
        if state:
            self.restoreState(state)
        collapsed = settings.value("sidebarCollapsed", False, type=bool)
        if collapsed:
            self._toggle_sidebar(True)
        from ui.theme import apply_dark_palette
        apply_dark_palette()

    def closeEvent(self, event):
        settings = QSettings("QA-Tool", "MainWindow")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        settings.setValue("sidebarCollapsed", not self.sidebar.isVisible())
        super().closeEvent(event)

    def _on_batch_scheduler(self):
        from ui.dialogs.batch_dialog import BatchDialog
        dlg = BatchDialog(self)
        dlg.exec()

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

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F11:
            self._open_display_mode()
            return
        super().keyPressEvent(event)

    def _on_save_shared(self):
        if not self.current_data:
            QMessageBox.warning(self, "无数据", "请先导入数据并运行分析")
            return
        from core.project_manager import SharedProjectManager
        dept = "公共"
        path, _ = QFileDialog.getSaveFileName(
            self, "保存到共享目录", "QA_Shared.qap", "QA-Tool 项目 (*.qap)"
        )
        if not path:
            return
        try:
            raw = self.current_data.get("raw_data", {})
            charts = {}
            for label, buf in self._collect_charts(list(self.analyses.keys())).items():
                charts[label] = buf.getvalue() if hasattr(buf, 'getvalue') else buf
            SharedProjectManager.save_shared(path, raw, self.analyses, charts, dept)
            audit("share_project", "user",
                  f"保存 {os.path.basename(path)}")
            self.status_label.setText("共享项目已保存")
            QMessageBox.information(self, "保存完成", f"项目已共享到部门: {dept}")
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))

    def _on_load_shared(self):
        from core.project_manager import SharedProjectManager
        dept = ""
        role = ""
        projects = SharedProjectManager.list_shared(department=dept, role=role)
        if not projects:
            QMessageBox.information(self, "共享项目", "共享目录中没有可用的项目")
            return
        from PySide6.QtWidgets import QInputDialog
        names = [f"{p['name']} ({p['department']})" for p in projects]
        name, ok = QInputDialog.getItem(self, "打开共享项目", "选择项目:", names, 0, False)
        if ok and name:
            idx = names.index(name)
            proj = projects[idx]
            try:
                loaded = SharedProjectManager.load_shared(proj['path'])
                raw_data = loaded["raw_data"]
                self.current_data = {"file_path": proj['path'], "raw_data": raw_data,
                    "metadata": {"sheet_names": list(raw_data.keys()), "total_rows": sum(len(df) for df in raw_data.values())}}
                self.data_loader.raw_data = raw_data
                self.data_loader.metadata = self.current_data["metadata"]
                self._route_sheets_to_tabs(raw_data)
                self.analyses = loaded["analyses"]
                self.data_label.setText(proj['name'])
                self.status_label.setText(f"共享项目已加载: {len(raw_data)} sheets")
                self._notify_dashboard()
            except Exception as e:
                QMessageBox.critical(self, "加载失败", str(e))

    def _on_diagnose(self):
        if not self.profile_result or not self.profile_result.get("sheets"):
            QMessageBox.information(self, "智能诊断", "请先导入数据文件，系统将自动分析数据特征")
            return
        from ui.dialogs.diagnosis_dialog import DiagnosisDialog
        dlg = DiagnosisDialog(self.profile_result, self)
        dlg.apply_clicked.connect(self._apply_diagnosis)
        dlg.exec()

    def _apply_diagnosis(self, recommendation: dict):
        tab_idx = recommendation.get("tab_index", 1)
        params = recommendation.get("params", {})
        self._switch_tab(tab_idx)
        tabs = self._get_tabs()
        tab = tabs.get(tab_idx)
        if tab is None:
            return

        col = params.get("column") or params.get("response") or params.get("col1")
        if col and tab_idx == 1:
            combo = getattr(tab, 'col_combo', None)
            if combo:
                idx = combo.findText(col)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
            if params.get("subgroup_size") and hasattr(tab, 'subgroup_spin'):
                tab.subgroup_spin.setValue(int(params["subgroup_size"]))
            if params.get("usl") and hasattr(tab, 'usl_spin'):
                tab.usl_spin.setValue(float(params["usl"]))
            if params.get("lsl") and hasattr(tab, 'lsl_spin'):
                tab.lsl_spin.setValue(float(params["lsl"]))
            method = recommendation.get("method", "")
            if method and hasattr(tab, 'chart_type_combo'):
                mi = tab.chart_type_combo.findText(method)
                if mi >= 0:
                    tab.chart_type_combo.setCurrentIndex(mi)
        elif col and tab_idx == 2:
            combo = getattr(tab, 'col_combo', None)
            if combo:
                idx = combo.findText(col)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
            if params.get("usl") and hasattr(tab, 'usl_spin'):
                tab.usl_spin.setValue(float(params["usl"]))
            if params.get("lsl") and hasattr(tab, 'lsl_spin'):
                tab.lsl_spin.setValue(float(params["lsl"]))
        elif col and tab_idx in (3, 4, 5, 6):
            combo_attrs = {3: 'measure_col', 4: 'col1_combo', 5: 'response_combo', 6: 'response_combo'}
            combo = getattr(tab, combo_attrs.get(tab_idx, ''), None)
            if combo:
                idx = combo.findText(col)
                if idx >= 0:
                    combo.setCurrentIndex(idx)

        self.status_label.setText(f"依诊断推荐已配置 '{recommendation.get('tab_name', '')}', 可运行分析")

    def _on_about(self):
        import os
        logo_path = os.path.join(os.path.dirname(__file__), "..", "logo.png")
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(f"关于 {APP_NAME}")
        msg_box.setIconPixmap(
            QPixmap(logo_path).scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            if os.path.exists(logo_path) else QPixmap()
        )
        msg_box.setText(
            f"<h2>{APP_NAME} v{APP_VERSION}</h2>"
            f"<p>AI 工业质量 + IE 分析平台</p>"
            f"<p>25+ 质量分析 · 5 IE 工具 · AI 根因分析 · 知识库 RAG</p>"
            f"<p>企业特性: .qap 项目文件 · SQL 直连 · 批量调度 · 多用户协同</p>"
            f"<br><p style='color:#888'>技术栈: Python 3.14 · PySide6 · pandas · scipy · scikit-learn · SHAP</p>"
        )
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec()

    # ── 拖拽导入 ──
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
            raw_data = self.data_loader.load(file_path)
            audit("import_data",
                  "user",
                  f"拖拽导入 {os.path.basename(file_path)}")
            self.current_data = {"file_path": file_path, "raw_data": raw_data}
            self.data_label.setText(os.path.basename(file_path))
            self._route_sheets_to_tabs(raw_data, worksheet_mode=True)
            self.status_label.setText(f"已加载: {os.path.basename(file_path)}")
        except Exception as e:
            self.status_label.setText(f"加载失败: {e}")
