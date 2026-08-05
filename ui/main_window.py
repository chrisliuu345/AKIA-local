"""
QA-Tool — 主窗口
"""

import os
from typing import Dict, Any

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QMessageBox, QFileDialog,
    QLabel, QPushButton, QApplication, QSizePolicy, QFrame,
    QScrollArea,
)
from PySide6.QtCore import Qt, QSettings, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QAction, QIcon, QFont, QPixmap, QDragEnterEvent, QDropEvent

from config.settings import APP_NAME, APP_VERSION, CHART_FIGSIZE
from core.data_loader import DataLoader
from core.data_parser import DataParser
from core.data_validator import DataValidator
from core.template_parser import TemplateParser
from core.session_manager import SessionManager
from core.i18n import i18n
from core.data_profiler import DataProfiler
from core.project_manager import ProjectManager
from core.auth import AuthManager

from ui.sidebar import Sidebar
from ui.theme import colors as theme_colors
from ui.tabs.spc_tab import SPCTab
from ui.tabs.capability_tab import CapabilityTab
from ui.tabs.msa_tab import MSATab
from ui.tabs.hypothesis_tab import HypothesisTab
from ui.tabs.doe_tab import DOETab
from ui.tabs.regression_tab import RegressionTab
from ui.tabs.time_study_tab import TimeStudyTab
from ui.tabs.work_sampling_tab import WorkSamplingTab
from ui.tabs.line_balance_tab import LineBalanceTab
from ui.tabs.oee_tab import OEETab
from ui.tabs.vsm_tab import VSMTab
from ui.tabs.chart_tab import ChartTab
from ui.tabs.reliability_tab import ReliabilityTab
from ui.tabs.fishbone_tab import FishboneTab
from ui.tabs.pareto_tab import ParetoTab
from ui.tabs.fmea_tab import FMEATab
from ui.tabs.control_plan_tab import ControlPlanTab
from ui.tabs.cap_comparison_tab import CapComparisonTab
from ui.tabs.trend_tab import TrendTab
from ui.tabs.summaries_panel_tab import SummaryPanelTab
from ui.tabs.worker_machine_tab import WorkerMachineTab
from ui.tabs.std_work_combo_tab import StdWorkComboTab
from ui.tabs.sheet_merge_tab import SheetMergeTab
from ui.tabs.sheet_split_tab import SheetSplitTab
from ui.tabs.layered_form_tab import LayeredFormTab
from ui.tabs.sampling_tab import SamplingTab
from ui.tabs.dashboard_tab import DashboardTab
from ui.tabs.data_tools_tab import DataToolsTab
from ui.welcome_page import WelcomePage
from ui.dialogs.import_dialog import ImportDialog
from ui.dialogs.settings_dialog import SettingsDialog
from ui.dialogs.db_connection_dialog import DbConnectionDialog
from core.sql_loader import SqlLoader
from core.plugin_manager import PluginManager


class MainWindow(QMainWindow):
    def __init__(self, user=None, splash=None):
        super().__init__()
        self.current_user = user
        role_suffix = f" — {user.role}" if user else ""
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}{role_suffix}")
        self.resize(1300, 880)
        self.setMinimumSize(1040, 700)

        logo_path = os.path.join(os.path.dirname(__file__), "..", "logo.png")
        if os.path.exists(logo_path):
            self.setWindowIcon(QIcon(logo_path))

        def _step(pct, msg):
            if splash:
                from main import _update_splash
                _update_splash(splash, pct, msg)
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

        _step(73, "构建界面布局...")
        self._setup_ui()

        _step(76, "初始化菜单栏...")
        self._setup_menu()

        _step(78, "初始化状态栏...")
        self._setup_statusbar()

        _step(80, "连接信号与路由...")
        self._connect_signals()

        _step(83, "恢复窗口布局...")
        self._restore_window_state()
        self.setAcceptDrops(True)

        # 插件发现与注册
        self._pm = PluginManager()
        self._pm.discover()
        self._plugin_tabs = {}
        for name, p in self._pm.plugins.items():
            idx = 100 + len(self._plugin_tabs)
            self._plugin_tabs[idx] = p
            tab = p.create_tab()
            self.stack.addWidget(tab)
            self.sidebar.add_plugin_entry(idx, name)
        # 重建导航映射
        for idx in self._plugin_tabs:
            self.sidebar.nav_buttons[idx] = self.stack.widget(idx)

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
        self.expand_btn.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
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
        self.welcome_page = WelcomePage()
        self.spc_tab = SPCTab()
        self.capability_tab = CapabilityTab()
        self.msa_tab = MSATab()
        self.hypothesis_tab = HypothesisTab()
        self.doe_tab = DOETab()
        self.regression_tab = RegressionTab()
        self.time_study_tab = TimeStudyTab()
        self.work_sampling_tab = WorkSamplingTab()
        self.line_balance_tab = LineBalanceTab()
        self.oee_tab = OEETab()
        self.vsm_tab = VSMTab()
        self.chart_tab = ChartTab()
        self.reliability_tab = ReliabilityTab()
        self.fishbone_tab = FishboneTab()
        self.pareto_tab = ParetoTab()
        self.fmea_tab = FMEATab()
        self.control_plan_tab = ControlPlanTab()
        self.cap_comparison_tab = CapComparisonTab()
        self.trend_tab = TrendTab()
        self.summary_panel_tab = SummaryPanelTab()
        self.worker_machine_tab = WorkerMachineTab()
        self.std_work_combo_tab = StdWorkComboTab()
        self.sheet_merge_tab = SheetMergeTab()
        self.sheet_split_tab = SheetSplitTab()
        self.layered_form_tab = LayeredFormTab()
        self.sampling_tab = SamplingTab()
        self.dashboard_tab = DashboardTab()
        self.data_tools_tab = DataToolsTab()

        self.stack.addWidget(self.welcome_page)  # 0
        self.stack.addWidget(self.spc_tab)
        self.stack.addWidget(self.capability_tab)
        self.stack.addWidget(self.msa_tab)
        self.stack.addWidget(self.hypothesis_tab)
        self.stack.addWidget(self.doe_tab)
        self.stack.addWidget(self.regression_tab)
        self.stack.addWidget(self.time_study_tab)
        self.stack.addWidget(self.work_sampling_tab)
        self.stack.addWidget(self.line_balance_tab)
        self.stack.addWidget(self.oee_tab)
        self.stack.addWidget(self.vsm_tab)
        self.stack.addWidget(self.chart_tab)        # 12
        self.stack.addWidget(self.reliability_tab)  # 13
        self.stack.addWidget(self.fishbone_tab)     # 14
        self.stack.addWidget(self.pareto_tab)         # 15
        self.stack.addWidget(self.fmea_tab)           # 16
        self.stack.addWidget(self.control_plan_tab)     # 17
        self.stack.addWidget(self.cap_comparison_tab)   # 18
        self.stack.addWidget(self.trend_tab)            # 19
        self.stack.addWidget(self.summary_panel_tab)      # 20
        self.stack.addWidget(self.worker_machine_tab)     # 21
        self.stack.addWidget(self.std_work_combo_tab)     # 22
        self.stack.addWidget(self.sheet_merge_tab)        # 23
        self.stack.addWidget(self.sheet_split_tab)        # 24
        self.stack.addWidget(self.layered_form_tab)       # 25
        self.stack.addWidget(self.sampling_tab)           # 26
        self.stack.addWidget(self.dashboard_tab)          # 27
        self.stack.addWidget(self.data_tools_tab)         # 28

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

        file_menu = menubar.addMenu(i18n.tr("menu.file"))

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

        export_menu = file_menu.addMenu(i18n.tr("menu.export"))
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
                comply_menu = export_menu.addMenu(i18n.tr("menu.compliance"))
                for t in templates:
                    ac = comply_menu.addAction(f"{t['name']} ({t['standard']})")
                    ac.setData(t["id"])
                    ac.triggered.connect(lambda checked, tid=t["id"]: self._on_export_compliance(tid))
        except Exception:
            pass

        file_menu.addSeparator()
        # .qap 项目文件
        save_project_action = QAction("💾 保存项目 (.qap)", self)
        save_project_action.setShortcut("Ctrl+Shift+S")
        save_project_action.triggered.connect(self._on_save_project)
        file_menu.addAction(save_project_action)
        open_project_action = QAction("📂 打开项目 (.qap)", self)
        open_project_action.setShortcut("Ctrl+Shift+O")
        open_project_action.triggered.connect(self._on_load_project)
        file_menu.addAction(open_project_action)

        # 最近项目
        recent = ProjectManager.recent_projects()
        if recent:
            self.recent_menu = file_menu.addMenu("📋 最近项目")
            self._rebuild_recent_menu(recent)

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

        view_menu = menubar.addMenu(i18n.tr("menu.view"))
        self.toggle_sidebar_action = QAction(i18n.tr("menu.toggle_sidebar"), self)
        self.toggle_sidebar_action.setCheckable(True)
        self.toggle_sidebar_action.setChecked(True)
        self.toggle_sidebar_action.setShortcut("Ctrl+B")
        self.toggle_sidebar_action.triggered.connect(
            lambda checked: self._toggle_sidebar(not checked)
        )
        view_menu.addAction(self.toggle_sidebar_action)

        analysis_menu = menubar.addMenu(i18n.tr("menu.analysis"))
        spc_action = QAction(i18n.tr("menu.spc"), self)
        spc_action.triggered.connect(lambda: self._switch_tab(1))
        analysis_menu.addAction(spc_action)
        cap_action = QAction(i18n.tr("menu.capability"), self)
        cap_action.triggered.connect(lambda: self._switch_tab(2))
        analysis_menu.addAction(cap_action)
        msa_action = QAction(i18n.tr("menu.msa"), self)
        msa_action.triggered.connect(lambda: self._switch_tab(3))
        analysis_menu.addAction(msa_action)
        hyp_action = QAction(i18n.tr("menu.hypothesis"), self)
        hyp_action.triggered.connect(lambda: self._switch_tab(4))
        analysis_menu.addAction(hyp_action)
        doe_action = QAction(i18n.tr("menu.doe"), self)
        doe_action.triggered.connect(lambda: self._switch_tab(5))
        analysis_menu.addAction(doe_action)

        analysis_menu.addSeparator()
        run_all = QAction(i18n.tr("menu.run"), self)
        run_all.setShortcut("F5")
        run_all.triggered.connect(self._on_run_all_analyses)
        analysis_menu.addAction(run_all)

        tools_menu = menubar.addMenu(i18n.tr("menu.tools"))
        settings_action = QAction(i18n.tr("menu.settings"), self)
        settings_action.triggered.connect(self._on_settings)
        tools_menu.addAction(settings_action)
        tools_menu.addSeparator()
        batch_action = QAction("批量调度", self)
        batch_action.triggered.connect(self._on_batch_scheduler)
        tools_menu.addAction(batch_action)
        if self.current_user and self.current_user.can_manage_users:
            user_mgmt_action = QAction("用户管理", self)
            user_mgmt_action.triggered.connect(self._on_user_management)
            tools_menu.addAction(user_mgmt_action)
        clean_action = QAction(i18n.tr("sidebar.data_clean"), self)
        clean_action.triggered.connect(self._on_data_cleaner)
        tools_menu.addAction(clean_action)
        wizard_action = QAction("数据清洗向导 (一键)", self)
        wizard_action.triggered.connect(self._on_data_clean_wizard)
        tools_menu.addAction(wizard_action)
        template_help_action = QAction(i18n.tr("sidebar.template_help_tip"), self)
        template_help_action.triggered.connect(self._on_template_help)
        tools_menu.addAction(template_help_action)
        tools_menu.addSeparator()
        diagnose_action = QAction(i18n.tr("sidebar.diagnose"), self)
        diagnose_action.triggered.connect(self._on_diagnose)
        tools_menu.addAction(diagnose_action)
        ai_action = QAction(i18n.tr("sidebar.llm"), self)
        ai_action.triggered.connect(self._on_llm_assist)
        tools_menu.addAction(ai_action)

        help_menu = menubar.addMenu(i18n.tr("menu.help"))
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

    def _setup_statusbar(self):
        self.statusBar().setStyleSheet(
            "QStatusBar { min-height: 24px; background: #13131c; } QStatusBar::item { border: none; }"
        )
        self.status_label = QLabel(i18n.tr("status.ready"))
        self.status_label.setSizePolicy(
            self.status_label.sizePolicy().horizontalPolicy(), QSizePolicy.Preferred
        )
        self.statusBar().addWidget(self.status_label, 1)
        self.data_label = QLabel("")
        self.data_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.data_label.setMaximumWidth(300)
        self.statusBar().addPermanentWidget(self.data_label)

    def _connect_signals(self):
        self.sidebar.navigation_changed.connect(self._switch_tab)
        self.sidebar.diagnose_clicked.connect(self._on_diagnose)
        self.sidebar.llm_clicked.connect(self._on_llm_assist)
        self.sidebar.collapse_requested.connect(lambda: self._toggle_sidebar(True))
        self.welcome_page.import_data_clicked.connect(self._on_import_quality)
        self.welcome_page.import_template_clicked.connect(self._on_import_template)
        self.spc_tab.export_clicked.connect(lambda: self._on_export_single(1, "docx"))
        self.capability_tab.export_clicked.connect(lambda: self._on_export_single(2, "docx"))
        self.msa_tab.export_clicked.connect(lambda: self._on_export_single(3, "docx"))
        self.hypothesis_tab.export_clicked.connect(lambda: self._on_export_single(4, "docx"))
        self.doe_tab.export_clicked.connect(lambda: self._on_export_single(5, "docx"))
        self.regression_tab.export_clicked.connect(lambda: self._on_export_single(6, "docx"))
        self.time_study_tab.export_clicked.connect(lambda: self._on_export_single(7, "docx"))
        self.work_sampling_tab.export_clicked.connect(lambda: self._on_export_single(8, "docx"))
        self.line_balance_tab.export_clicked.connect(lambda: self._on_export_single(9, "docx"))
        self.oee_tab.export_clicked.connect(lambda: self._on_export_single(10, "docx"))
        self.vsm_tab.export_clicked.connect(lambda: self._on_export_single(11, "docx"))
        self.chart_tab.export_clicked.connect(lambda: self._on_export_single(12, "docx"))
        self.reliability_tab.export_clicked.connect(lambda: self._on_export_single(13, "docx"))

        self.spc_tab.analysis_completed.connect(lambda: self._on_analysis_finished(1))
        self.capability_tab.analysis_completed.connect(lambda: self._on_analysis_finished(2))
        self.msa_tab.analysis_completed.connect(lambda: self._on_analysis_finished(3))
        self.hypothesis_tab.analysis_completed.connect(lambda: self._on_analysis_finished(4))
        self.doe_tab.analysis_completed.connect(lambda: self._on_analysis_finished(5))
        self.regression_tab.analysis_completed.connect(lambda: self._on_analysis_finished(6))
        self.time_study_tab.analysis_completed.connect(lambda: self._on_analysis_finished(7))
        self.work_sampling_tab.analysis_completed.connect(lambda: self._on_analysis_finished(8))
        self.line_balance_tab.analysis_completed.connect(lambda: self._on_analysis_finished(9))
        self.oee_tab.analysis_completed.connect(lambda: self._on_analysis_finished(10))
        self.vsm_tab.analysis_completed.connect(lambda: self._on_analysis_finished(11))
        self.chart_tab.analysis_completed.connect(lambda: self._on_analysis_finished(12))
        self.reliability_tab.analysis_completed.connect(lambda: self._on_analysis_finished(13))

    def _switch_tab(self, index: int):
        if 0 <= index < self.stack.count():
            target = self.stack.widget(index)
            # 淡入动画 (200ms, 防止太快看不见)
            from PySide6.QtWidgets import QGraphicsOpacityEffect
            old_effect = target.graphicsEffect()
            effect = QGraphicsOpacityEffect()
            effect.setOpacity(0.0)
            target.setGraphicsEffect(effect)
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

    def _on_import_quality(self):
        dialog = ImportDialog(self, mode="quality")
        if dialog.exec():
            file_path, sheet_names = dialog.get_selection()
            try:
                self.status_label.setText(f"{i18n.tr('status.loading')}{file_path}...")
                raw_data = self.data_loader.load(file_path)
                self.current_data = {
                    "file_path": file_path,
                    "raw_data": raw_data,
                    "metadata": self.data_loader.metadata,
                }
                self.session_manager.create_session(file_path=file_path)
                self._route_sheets_to_tabs(raw_data, quality_only=True)
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
                    num_cols = df.select_dtypes(include="number").columns.tolist()
                    if num_cols:
                        v = self.data_validator.validate(df, num_cols)
                        all_warnings += v.get("warning_count", 0)

                if all_warnings > 0:
                    self.statusBar().showMessage(
                        f"{i18n.tr('status.loaded')}: {len(self.data_loader.metadata['sheet_names'])} Sheets  |  数据校验: {all_warnings} 个警告",
                        8000,
                    )
                else:
                    self.status_label.setText(f"{i18n.tr('status.loaded')}: {len(self.data_loader.metadata['sheet_names'])} Sheets")
            except Exception as e:
                QMessageBox.critical(self, i18n.tr("msg.import_failed"), f"{i18n.tr('msg.cannot_load')}\n{str(e)}")
                self.status_label.setText(i18n.tr("status.failed"))

    def _on_import_ie(self):
        dialog = ImportDialog(self, mode="ie")
        if dialog.exec():
            file_path, sheet_names = dialog.get_selection()
            try:
                self.status_label.setText(f"{i18n.tr('status.loading')}{file_path}...")
                raw_data = self.data_loader.load(file_path)
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
                    if hasattr(self.time_study_tab, 'set_ie_data'):
                        self.time_study_tab.set_ie_data(ie_data["TimeObservation"])

                if ie_data.get("Process"):
                    self.line_balance_tab.set_ie_data(ie_data["Process"])
                    self.vsm_tab.set_ie_data(processes=ie_data["Process"])
                if ie_data.get("MaterialFlow"):
                    self.vsm_tab.set_ie_data(flows=ie_data["MaterialFlow"])
                if ie_data.get("Resource"):
                    self.oee_tab.set_ie_data(ie_data["Resource"])

                parts = []
                for obj_type, objects in ie_data.items():
                    type_labels = {
                        "Process": "工序表", "TimeObservation": "时间观测",
                        "QualityRecord": "质量记录", "MaterialFlow": "物流", "Resource": "资源",
                    }
                    parts.append(f"{type_labels.get(obj_type, obj_type)}: {len(objects)} 条")
                self.status_label.setText(f"已加载 IE 数据: {' | '.join(parts)}")
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
                loader.connect(config)
                raw_data = loader.load(table_names)
                loader.disconnect()

                self.current_data = {
                    "source": "database",
                    "db_config": config,
                    "raw_data": raw_data,
                    "metadata": loader.metadata,
                }
                self.data_loader.raw_data = raw_data
                self.data_loader.metadata = loader.metadata

                self._route_sheets_to_tabs(raw_data, quality_only=False)
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

    def _route_sheets_to_tabs(self, raw_data: Dict[str, pd.DataFrame], quality_only: bool = False):
        sheet_map = {
            self.spc_tab: ["spc", "控制图", "control"],
            self.capability_tab: ["能力", "capability"],
            self.msa_tab: ["msa", "gage", "量具", "r&r"],
            self.hypothesis_tab: ["假设", "hypothesis", "检验", "t_test", "anova"],
            self.doe_tab: ["doe", "因子", "设计", "实验"],
            self.regression_tab: ["regression", "回归", "reg"],
        }

        tabs = self._get_tabs()
        for idx, tab in tabs.items():
            if quality_only and idx > 6 and idx not in (12, 13, 14, 15, 18, 19, 20, 28):
                continue
            if hasattr(tab, 'set_raw_data') and (idx <= 6 or idx in (12, 13, 15, 18, 19, 20, 28)):
                tab.set_raw_data(raw_data, self.data_parser)

        assigned = set()
        for tab, keywords in sheet_map.items():
            if not hasattr(tab, 'sheet_combo'):
                continue
            for sname in raw_data:
                if sname in assigned:
                    continue
                if any(kw in sname.lower() for kw in keywords):
                    idx = tab.sheet_combo.findText(sname)
                    if idx >= 0:
                        tab.sheet_combo.setCurrentIndex(idx)
                        assigned.add(sname)
                        break

        sheets_info = ", ".join(f"{s} ({len(raw_data[s])}r)" for s in assigned)
        if sheets_info:
            self.status_label.setText(f"{i18n.tr('status.sheets_matched')}{sheets_info}")

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

    def _on_run_analysis(self):
        idx = self.stack.currentIndex()
        if idx == 0:
            QMessageBox.information(self, i18n.tr("msg.select_module"), i18n.tr("msg.select_module"))
            return
        if not self.current_data:
            QMessageBox.warning(self, i18n.tr("msg.no_data"), i18n.tr("msg.no_data_file"))
            return

        tabs = self._get_tabs()
        tab = tabs.get(idx)
        if tab is None:
            return

        self.status_label.setText(i18n.tr("status.running"))
        try:
            tab.run_and_display()
            result = getattr(tab, 'current_result', None)
            if result:
                self.analyses[idx] = result.copy()
                self.session_manager.add_analysis(
                    result.get("analysis_type", "Unknown"),
                    result.get("params", {}),
                    result.get("result", {})
                )
                atype = result.get("analysis_type", "")
                key_res = self._summarize_result(result.get("result", {}))
                self.sidebar.add_history(idx, atype, key_res)
            self.status_label.setText(i18n.tr("status.done"))
        except Exception as e:
            self.status_label.setText(i18n.tr("status.failed"))

    def _on_analysis_finished(self, idx: int):
        tabs = self._get_tabs()
        tab = tabs.get(idx)
        result = getattr(tab, 'current_result', None)
        if result:
            self.analyses[idx] = result.copy()
            atype = result.get("analysis_type", "")
            key_res = self._summarize_result(result.get("result", {}))
            self.sidebar.add_history(idx, atype, key_res)

    def _on_run_all_analyses(self):
        if not self.current_data:
            QMessageBox.warning(self, i18n.tr("msg.no_data"), i18n.tr("msg.no_data_file"))
            return

        tabs = self._get_tabs()
        success = 0
        failed = 0

        for idx, tab in tabs.items():
            if not getattr(tab, 'df', None) or len(tab.df) == 0:
                continue
            try:
                tab.run_and_display()
                result = getattr(tab, 'current_result', None)
                if result:
                    self.analyses[idx] = result.copy()
                    atype = result.get("analysis_type", "")
                    key_res = self._summarize_result(result.get("result", {}))
                    self.sidebar.add_history(idx, atype, key_res)
                success += 1
            except Exception:
                failed += 1

        self.statusBar().showMessage(
            f"批量分析完成: 成功 {success}, 失败 {failed}", 5000
        )
        if success > 0:
            self.stack.setCurrentIndex(1)
            self.sidebar.set_active(1)

    def _get_tabs(self):
        return {1: self.spc_tab, 2: self.capability_tab, 3: self.msa_tab,
                4: self.hypothesis_tab, 5: self.doe_tab, 6: self.regression_tab,
                7: self.time_study_tab, 8: self.work_sampling_tab,
                9: self.line_balance_tab, 10: self.oee_tab, 11: self.vsm_tab,
                12: self.chart_tab, 13: self.reliability_tab,
                14: self.fishbone_tab, 15: self.pareto_tab,
                16: self.fmea_tab, 17: self.control_plan_tab,
                18: self.cap_comparison_tab,
                19: self.trend_tab, 20: self.summary_panel_tab,
                21: self.worker_machine_tab, 22: self.std_work_combo_tab,
                23: self.sheet_merge_tab, 24: self.sheet_split_tab,
                25: self.layered_form_tab, 26: self.sampling_tab,
                27: self.dashboard_tab, 28: self.data_tools_tab,
                **{idx: self.stack.widget(idx) for idx in range(100, 100+len(self._plugin_tabs))}}

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
            self, "导出报告", f"Analysis_Report.{fmt}", filters.get(fmt, "")
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
                self.status_label.setText(f"正在导出合规报告...")
                charts = self._collect_charts(list(self.analyses.keys()))
                ComplianceReportGenerator.generate(
                    template_id, list(self.analyses.values()),
                    file_path, charts=charts,
                )
                self.status_label.setText(f"{i18n.tr('status.exported')}{file_path}")
                QMessageBox.information(self, i18n.tr("msg.export_complete"),
                                        f"{i18n.tr('msg.export_saved')}\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, i18n.tr("msg.export_failed"), str(e))

    def _on_save_project(self):
        if not self.current_data:
            QMessageBox.warning(self, "无数据", "请先导入数据并运行分析")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存项目", "QA_Project.qap", "QA-Tool Project (*.qap)"
        )
        if not path:
            return
        try:
            self.status_label.setText("正在保存项目...")
            raw = self.current_data.get("raw_data", {})
            charts = {}
            for label, buf in self._collect_charts(list(self.analyses.keys())).items():
                charts[label] = buf.getvalue() if hasattr(buf, 'getvalue') else buf
            ProjectManager.save_project(path, raw, self.analyses, charts, "")
            self.status_label.setText(f"项目已保存: {path}")
            self._rebuild_recent_menu(ProjectManager.recent_projects())
            QMessageBox.information(self, "保存完成", f"项目已保存到:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))

    def _on_load_project(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "打开项目", "", "QA-Tool Project (*.qap)"
        )
        if not path:
            return
        try:
            self.status_label.setText("正在加载项目...")
            project = ProjectManager.load_project(path)
            # 恢复数据
            raw_data = project["raw_data"]
            self.current_data = {
                "file_path": path,
                "raw_data": raw_data,
                "metadata": {"sheet_names": list(raw_data.keys()), "total_rows": sum(len(df) for df in raw_data.values())},
            }
            self.data_loader.raw_data = raw_data
            self.data_loader.metadata = self.current_data["metadata"]
            self._route_sheets_to_tabs(raw_data)
            # 恢复分析结果
            self.analyses = project["analyses"]
            info = project["manifest"]
            self.data_label.setText(f" {os.path.basename(path)} [{info.get('sheet_count',0)} sheets]")
            self._rebuild_recent_menu(ProjectManager.recent_projects())
            self.status_label.setText(f"项目已加载: {info.get('analysis_count', 0)} 个分析")
            QMessageBox.information(self, "加载完成",
                                    f"已恢复 {len(raw_data)} 个数据表、{len(self.analyses)} 个分析结果")
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
            self._on_load_project()  # 复用标准加载流程(会弹出文件对话框——跳过)
            # 直接使用已知路径加载
            from core.project_manager import ProjectManager
            try:
                project = ProjectManager.load_project(path)
                raw_data = project["raw_data"]
                self.current_data = {"file_path": path, "raw_data": raw_data, "metadata": {"sheet_names": list(raw_data.keys()), "total_rows": sum(len(df) for df in raw_data.values())}}
                self.data_loader.raw_data = raw_data
                self.data_loader.metadata = self.current_data["metadata"]
                self._route_sheets_to_tabs(raw_data)
                self.analyses = project["analyses"]
                self.data_label.setText(f" {os.path.basename(path)}")
                self._rebuild_recent_menu(ProjectManager.recent_projects())
                self.status_label.setText(f"项目已加载: {len(raw_data)} sheets")
                QMessageBox.information(self, "加载完成", f"已恢复 {len(self.analyses)} 个分析")
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

                count = len(data.get("analyses", []))
                self.statusBar().showMessage(
                    f"会话已加载: {data.get('name', '')} ({count} 个分析)", 5000
                )
            except Exception as e:
                QMessageBox.critical(self, i18n.tr("msg.import_failed"), str(e))

    def _on_settings(self):
        from config.settings import save_config
        from core.auth import AuthManager
        dialog = SettingsDialog(self, user=self.current_user)
        if dialog.exec():
            save_config(dialog.get_values())
            # 保存账户设置
            if self.current_user:
                acct = dialog.get_account_values()
                if acct:
                    auth = AuthManager()
                    auth.update_user(self.current_user.username, **acct)
                    self.current_user.department = acct.get("department", "")
                    self.current_user.team = acct.get("team", "")
                    self.current_user.display_name = acct.get("display_name", "")
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

    def refresh_menu_for_user(self):
        """登录后刷新菜单: 根据角色显示/隐藏用户管理入口"""
        menubar = self.menuBar()
        tools_menu = None
        for action in menubar.actions():
            if action.text() == i18n.tr("menu.tools") or "工具" in action.text():
                tools_menu = action.menu()
                break
        if not tools_menu: return
        # 查找并移除旧的用户管理项
        for a in tools_menu.actions():
            if "用户管理" in a.text():
                tools_menu.removeAction(a)
                break
        # admin/dept_admin 添加用户管理
        if self.current_user and self.current_user.can_manage_users:
            # 在设置后、批量前插入
            actions = tools_menu.actions()
            insert_at = None
            for i, a in enumerate(actions):
                if "批量" in a.text():
                    insert_at = actions[i] if i + 1 < len(actions) else None
                    break
            if insert_at is None and actions:
                insert_at = actions[1]  # fallback: 第二个位置
            user_mgmt_action = QAction("用户管理", self)
            user_mgmt_action.triggered.connect(self._on_user_management)
            if insert_at:
                tools_menu.insertAction(insert_at, user_mgmt_action)
            else:
                tools_menu.addAction(user_mgmt_action)

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
            self._route_sheets_to_tabs(raw, quality_only=False)
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

    def _on_user_management(self):
        from ui.dialogs.user_management_dialog import UserManagementDialog
        dlg = UserManagementDialog(self.current_user, self)
        dlg.exec()

    def _on_save_shared(self):
        if not self.current_data or not self.current_user:
            QMessageBox.warning(self, "无数据", "请先导入数据并运行分析")
            return
        from core.project_manager import SharedProjectManager
        dept = self.current_user.department or "公共"
        path, _ = QFileDialog.getSaveFileName(
            self, "保存到共享目录", f"QA_Shared.qap", "QA-Tool Project (*.qap)"
        )
        if not path:
            return
        try:
            raw = self.current_data.get("raw_data", {})
            charts = {}
            for label, buf in self._collect_charts(list(self.analyses.keys())).items():
                charts[label] = buf.getvalue() if hasattr(buf, 'getvalue') else buf
            SharedProjectManager.save_shared(path, raw, self.analyses, charts, dept)
            self.status_label.setText("共享项目已保存")
            QMessageBox.information(self, "保存完成", f"项目已共享到部门: {dept}")
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))

    def _on_load_shared(self):
        from core.project_manager import SharedProjectManager
        dept = self.current_user.department if self.current_user else ""
        role = self.current_user.role if self.current_user else ""
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
            self.current_data = {"file_path": file_path, "raw_data": raw_data}
            self.data_label.setText(os.path.basename(file_path))
            self._route_sheets_to_tabs(raw_data, quality_only=True)
            self.status_label.setText(f"已加载: {os.path.basename(file_path)}")
        except Exception as e:
            self.status_label.setText(f"加载失败: {e}")
