"""
AKIA — 主窗口
"""

import contextlib
import os
from datetime import datetime
from typing import Any
import pandas as pd

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QMessageBox, QFileDialog,
    QPushButton, QFrame,
    QScrollArea,
)
from PySide6.QtCore import (
    Qt, QSettings, QPropertyAnimation, QEasingCurve, QUrl, QTimer, Signal,
)
from PySide6.QtGui import QAction, QIcon, QFont, QPixmap, QDragEnterEvent, QDropEvent, QDesktopServices

from config.settings import APP_FULL_NAME, APP_NAME, APP_VERSION, CHART_FIGSIZE, tab_allowed
from core.data_loader import DataLoader
from core.data_parser import DataParser
from core.data_validator import DataValidator
from core.template_parser import TemplateParser
from core.session_manager import SessionManager
from core.i18n import i18n
from core.data_profiler import DataProfiler
from core.project_manager import ProjectManager
from core.project_context import ProjectContext
from core.measurement_store import MeasurementStore
from core.evidence_ledger import EvidenceLedger
from core.alert_case import AlertCaseOrchestrator
from core.benefit_ledger import (
    BenefitLedger,
    record_case_benefit as core_record_case_benefit,
)
from core.gauge_study import GaugeMonitor
from core.skill_matrix import SkillMatrix
from core.sampling_state import SamplingStateManager
from core.time_utils import now_iso
from core.audit import audit
from core.streaming.bus import StreamBus

from ui.sidebar import Sidebar
from ui._tab_registry import INDEX_MAP, TAB_INDEX, CHAIN_TABS
from ui.theme import colors as theme_colors
from ui.font_config import get_ui_font
from ui.widgets.elided_label import ElidedLabel
from ui.welcome_page import WelcomePage
from ui.dialogs.import_dialog import ImportDialog
from ui.dialogs.settings_dialog import SettingsDialog
from core.plugin_manager import PluginManager
from ui.main_window_helpers import (
    _CurrentPageStack, _resolve_llm_client, _tab_has_data, _tab_is_runnable,
)

_PLUGIN_TAB_START = max(INDEX_MAP.keys()) + 1

# 五链贯通涉及的 Tab 索引（FMEA → CP → SPC → PPAP → 8D），需要注入项目上下文
_CONTEXT_TAB_INDICES = {TAB_INDEX[key] for key in (
    *CHAIN_TABS, "capability", "time_study", "std_work_combo")}

#: IE 工具 Tab — 工作表导入时分发跳过（IE 数据走「导入 IE 数据」）
_IE_TAB_INDICES = frozenset({7, 8, 9, 10, 11, 21, 22})
#: 消费 IE 数据对象（TimeObservation/Process/Resource/MaterialFlow）的 Tab
_IE_IMPORT_TAB_INDICES = frozenset({7, 9, 10, 11})


class MainWindow(QMainWindow):
    #: 告警自动立案通知（采集线程 emit → 主线程槽显示）
    alert_case_opened = Signal(str, str, str)  # case_id, title, rule_key
    #: 量具漂移通知（采集线程 emit → 主线程槽显示；v4.4.0 B2）
    gauge_drift_alerted = Signal(str, str)     # gauge_id, reasons

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.resize(1300, 880)
        self.setMinimumSize(1040, 700)

        logo_path = os.path.join(os.path.dirname(__file__), "..", "logo.png")
        if os.path.exists(logo_path):
            self.setWindowIcon(QIcon(logo_path))

        self.data_loader = DataLoader()
        self.data_parser = DataParser()
        self.data_profiler = DataProfiler()
        self.data_validator = DataValidator()
        self.template_parser = TemplateParser()
        self.session_manager = SessionManager()

        self.current_data: dict[str, Any] = {}
        self.profile_result: dict[str, Any] = {}
        self.analyses: dict[int, dict[str, Any]] = {}
        self.project_context = ProjectContext()
        self.case_workflows: list = []
        self._last_case_workflow = None
        self.measurement_store = MeasurementStore()
        # 决策落地（2026-10-14）：连接器常驻采集默认**不写**
        # 项目测量集合——避免长时运行撑大 `.qap` 与证据账本；案例按最近窗口
        # 显式采集（工作台「采集连接器测量」）。如需常开，需先评估 FIFO 截断
        # 与账本增长的现场影响，故暂不提供 UI 开关（迁移手册有记录）。
        self.measurement_capture = False
        self._chart_dependency_warned = False
        self.ledger = EvidenceLedger()
        self._ledger_failures = 0
        self.measurement_store.event_sink = self._on_measurement_event
        self.project_context.event_sink = self._on_standard_event
        self.alert_case_orchestrator = AlertCaseOrchestrator(
            ledger=self.ledger,
            context=self.project_context,
            create_case=self._create_alert_case,
            case_lookup=self._find_case_by_id,
        )
        self.alert_case_opened.connect(self._on_alert_case_opened_ui)
        self.gauge_monitor = GaugeMonitor()
        self._last_gauge_outcome: dict = {}
        self.gauge_drift_alerted.connect(self._on_gauge_drift_ui)
        self.sampling_manager = SamplingStateManager(
            ledger=self.ledger, standards=self.project_context.standards)
        self.benefit_ledger = BenefitLedger()
        self.skill_matrix = SkillMatrix()
        # 从 .qap 读到的数据资产。None 表示旧项目没有该段；保存时原样交回，
        # 由 ProjectManager 写成带版本号的信封，不在界面层迁入特性/批次/工时。
        self.data_asset: dict[str, Any] | None = None

        self._setup_ui()
        self._menu_refs: list = []

        self._setup_menu()

        self._setup_statusbar()

        self._connect_signals()

        self._restore_window_state()
        self.setAcceptDrops(True)

        self._pm = PluginManager()
        self._pm.discover()
        from ui.plugin_host import PluginHost
        self._plugin_host = PluginHost(self)
        self._pm.set_host(self._plugin_host)
        self._pm.on_load_all()
        self._plugin_tabs = {}
        self._agent_dialog = None
        self._plugin_tab_start = _PLUGIN_TAB_START
        # v3.7.0: 全局数据流总线（实时 SPC / 云看板消费同一数据）
        self.stream_bus = StreamBus()
        for record in self._pm.tab_plugins():
            idx = self._plugin_tab_start + len(self._plugin_tabs)
            self._plugin_tabs[idx] = record
            placeholder = QWidget()
            placeholder.setObjectName(f"placeholder_plugin_{idx}")
            self.stack.addWidget(placeholder)
            self.sidebar.add_plugin_entry(
                idx,
                record.name,
                icon=record.icon,
                tooltip=record.description,
            )

        self._start_alert_engine()
        self._start_streaming_runtime()

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

        self.stack = _CurrentPageStack()
        self._tab_cache = {}

        self.welcome_page = WelcomePage()
        self.stack.addWidget(self.welcome_page)

        for idx in range(1, _PLUGIN_TAB_START):
            placeholder = QWidget()
            placeholder.setObjectName(f"placeholder_{idx}")
            self.stack.addWidget(placeholder)

        self._plugin_tab_start = _PLUGIN_TAB_START

        layout.addWidget(self.expand_strip)
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

        import_quality_action = QAction(i18n.tr("sidebar.import_quality"), self)
        import_quality_action.setShortcut("Ctrl+O")
        import_quality_action.triggered.connect(self._on_import_quality)
        file_menu.addAction(import_quality_action)

        import_ie_action = QAction(i18n.tr("sidebar.import_ie"), self)
        import_ie_action.triggered.connect(self._on_import_ie)
        file_menu.addAction(import_ie_action)

        import_db_action = QAction(i18n.tr("sidebar.import_db"), self)
        import_db_action.triggered.connect(self._on_import_db)
        file_menu.addAction(import_db_action)

        file_menu.addSeparator()

        template_action = QAction(i18n.tr("menu.import_template"), self)
        template_action.triggered.connect(self._on_import_template)
        file_menu.addAction(template_action)

        file_menu.addSeparator()

        recent = ProjectManager.recent_projects()
        if recent:
            self.recent_menu = _pin(file_menu.addMenu(i18n.tr("menu.recent")))
            self._rebuild_recent_menu(recent)
            recent_items = [(r["name"], r["path"]) for r in recent]
            self.welcome_page.set_recent_projects(recent_items)

        save_session = QAction(i18n.tr("menu.save_session"), self)
        save_session.setShortcut("Ctrl+S")
        save_session.triggered.connect(self._on_save_session)
        file_menu.addAction(save_session)
        load_session = QAction(i18n.tr("menu.load_session"), self)
        load_session.triggered.connect(self._on_load_session)
        file_menu.addAction(load_session)

        save_project_action = QAction(i18n.tr("menu.save_project"), self)
        save_project_action.setShortcut("Ctrl+Shift+S")
        save_project_action.triggered.connect(self._on_save_project)
        file_menu.addAction(save_project_action)
        open_project_action = QAction(i18n.tr("menu.open_project"), self)
        open_project_action.setShortcut("Ctrl+Shift+O")
        open_project_action.triggered.connect(self._on_load_project)
        file_menu.addAction(open_project_action)
        save_shared_action = QAction(i18n.tr("menu.save_shared"), self)
        save_shared_action.triggered.connect(self._on_save_shared)
        file_menu.addAction(save_shared_action)
        load_shared_action = QAction(i18n.tr("menu.load_shared"), self)
        load_shared_action.triggered.connect(self._on_load_shared)
        file_menu.addAction(load_shared_action)

        file_menu.addSeparator()

        export_menu = _pin(file_menu.addMenu(i18n.tr("menu.export")))
        export_xlsx = QAction(i18n.tr("menu.export_xlsx"), self)
        export_xlsx.triggered.connect(lambda: self._on_export_all("xlsx"))
        export_menu.addAction(export_xlsx)
        export_docx = QAction(i18n.tr("menu.export_docx"), self)
        export_docx.triggered.connect(lambda: self._on_export_all("docx"))
        export_menu.addAction(export_docx)
        export_pdf = QAction(i18n.tr("menu.export_pdf"), self)
        export_pdf.triggered.connect(lambda: self._on_export_all("pdf"))
        export_menu.addAction(export_pdf)
        export_pptx = QAction(i18n.tr("menu.export_pptx"), self)
        export_pptx.triggered.connect(lambda: self._on_export_all("pptx"))
        export_menu.addAction(export_pptx)
        export_html = QAction(i18n.tr("menu.html_export"), self)
        export_html.triggered.connect(self._on_html_export)
        export_menu.addAction(export_html)

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
        except Exception:  # 合规报告模板不可用：菜单少一项，不影响其余菜单
            pass

        file_menu.addSeparator()

        exit_action = QAction(i18n.tr("menu.exit"), self)
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
        palette_action = QAction("命令面板", self)
        palette_action.setShortcuts(["Ctrl+K", "Ctrl+P"])
        palette_action.setToolTip("快速跳转模块 / 执行操作")
        palette_action.triggered.connect(self._open_command_palette)
        view_menu.addAction(palette_action)
        display_mode_action = QAction(i18n.tr("menu.display_mode"), self)
        display_mode_action.setShortcut("F11")
        display_mode_action.triggered.connect(self._open_display_mode)
        view_menu.addAction(display_mode_action)

        analysis_menu = _pin(menubar.addMenu(i18n.tr("menu.analysis")))
        quality_sub = _pin(analysis_menu.addMenu(i18n.tr("sidebar.quality_tools")))
        for idx, key in [(1, "sidebar.spc"), (2, "sidebar.capability"), (3, "sidebar.msa"),
                         (4, "sidebar.hypothesis"), (5, "sidebar.doe"), (6, "sidebar.regression"),
                         (36, "sidebar.time_series"), (37, "sidebar.predictive")]:
            a = QAction(i18n.tr(key), self)
            a.triggered.connect(lambda _, i=idx: self._switch_tab(i))
            quality_sub.addAction(a)
        ie_sub = _pin(analysis_menu.addMenu(i18n.tr("sidebar.ie_tools")))
        for idx, key in [(7, "sidebar.time_study"), (8, "sidebar.work_sampling"),
                         (9, "sidebar.line_balance"), (10, "sidebar.oee"),
                         (11, "menu.vsm"), (21, "sidebar.worker_machine"),
                         (22, "sidebar.std_work_combo"), (29, "sidebar.smed"), (31, "sidebar.tpm")]:
            a = QAction(i18n.tr(key), self)
            a.triggered.connect(lambda _, i=idx: self._switch_tab(i))
            ie_sub.addAction(a)
        chart_sub = _pin(analysis_menu.addMenu(i18n.tr("sidebar.chart_tools")))
        for idx, key in [(12, "sidebar.chart_tab"), (18, "sidebar.cap_comparison"),
                         (19, "sidebar.trend"), (20, "sidebar.summary_panel")]:
            a = QAction(i18n.tr(key), self)
            a.triggered.connect(lambda _, i=idx: self._switch_tab(i))
            chart_sub.addAction(a)
        eng_sub = _pin(analysis_menu.addMenu(i18n.tr("sidebar.engineering_tools")))
        for idx, key in [(13, "sidebar.reliability"), (14, "sidebar.fishbone"),
                         (15, "sidebar.pareto"), (16, "sidebar.fmea"),
                         (17, "sidebar.control_plan"), (30, "sidebar.8d"), (32, "sidebar.ppap")]:
            a = QAction(i18n.tr(key), self)
            a.triggered.connect(lambda _, i=idx: self._switch_tab(i))
            eng_sub.addAction(a)
        sheet_sub = _pin(analysis_menu.addMenu(i18n.tr("sidebar.sheet_tools")))
        for idx, key in [(23, "sidebar.sheet_merge"), (24, "sidebar.sheet_split"),
                         (25, "sidebar.layered_form")]:
            a = QAction(i18n.tr(key), self)
            a.triggered.connect(lambda _, i=idx: self._switch_tab(i))
            sheet_sub.addAction(a)
        analysis_menu.addSeparator()
        for idx, key in [(26, "sidebar.sampling"), (28, "sidebar.data_tools_tab"),
                         (27, "sidebar.dashboard"), (33, "sidebar.monitor"),
                         (34, "sidebar.multi_plant"), (35, "sidebar.device")]:
            a = QAction(i18n.tr(key), self)
            a.triggered.connect(lambda _, i=idx: self._switch_tab(i))
            analysis_menu.addAction(a)
        analysis_menu.addSeparator()
        run_all = QAction(i18n.tr("menu.run"), self)
        run_all.setShortcut("F5")
        run_all.triggered.connect(self._on_run_all_analyses)
        run_all.setShortcut("Ctrl+Shift+B")
        analysis_menu.addAction(run_all)

        ai_menu = _pin(menubar.addMenu(i18n.tr("menu.ai")))
        ai_chat = QAction(i18n.tr("sidebar.llm"), self)
        ai_chat.triggered.connect(self._on_llm_assist)
        ai_menu.addAction(ai_chat)
        one_click = QAction(i18n.tr("menu.one_click"), self)
        one_click.triggered.connect(self._on_one_click_analysis)
        ai_menu.addAction(one_click)

        tools_menu = _pin(menubar.addMenu(i18n.tr("menu.tools")))
        settings_act = QAction(i18n.tr("menu.settings"), self, triggered=self._on_settings)
        tools_menu.addAction(settings_act)
        batch_act = QAction(i18n.tr("menu.batch"), self, triggered=self._on_batch_scheduler)
        tools_menu.addAction(batch_act)
        self.case_workbench_act = QAction("改善案例工作台", self,
                                          triggered=self._on_case_workbench)
        tools_menu.addAction(self.case_workbench_act)
        self.case_center_act = QAction("改善案例中心", self,
                                       triggered=self._on_case_center)
        tools_menu.addAction(self.case_center_act)
        self.standard_history_act = QAction("标准版本记录", self,
                                            triggered=self._on_standard_history)
        tools_menu.addAction(self.standard_history_act)
        self.benefit_ledger_act = QAction("收益账本", self,
                                          triggered=self._on_benefit_ledger)
        self.benefit_ledger_act.setToolTip("改善收益 / COPQ 四类 / ROI / 月度复算（v4.4.0 B4）")
        tools_menu.addAction(self.benefit_ledger_act)
        self.evidence_view_act = QAction("证据视图", self,
                                         triggered=self._on_evidence_view)
        tools_menu.addAction(self.evidence_view_act)
        tools_menu.addSeparator()
        clean_act = QAction(i18n.tr("sidebar.data_clean"), self, triggered=self._on_data_cleaner)
        tools_menu.addAction(clean_act)
        clean_wiz_act = QAction(i18n.tr("menu.data_clean_wizard"), self, triggered=self._on_data_clean_wizard)
        tools_menu.addAction(clean_wiz_act)
        tools_menu.addAction(QAction(i18n.tr("sidebar.diagnose"), self,
                                     triggered=self._on_diagnose))
        tools_menu.addSeparator()
        template_act = QAction(i18n.tr("menu.template"), self)
        template_act.triggered.connect(self._on_template_dialog)
        tools_menu.addAction(template_act)
        tools_menu.addSeparator()
        plant_cfg_act = QAction(i18n.tr("menu.plant_config"), self,
                                triggered=self._on_plant_config)
        tools_menu.addAction(plant_cfg_act)
        tools_menu.addAction(QAction(i18n.tr("menu.alert_center"), self,
                                     triggered=self._on_alert_center))
        tools_menu.addAction(QAction(i18n.tr("menu.connector_health"), self,
                                     triggered=self._on_connector_health))
        self.live_dash_act = QAction(i18n.tr("menu.live_dashboard"), self,
                                     checkable=True, triggered=self._on_live_dashboard)
        tools_menu.addAction(self.live_dash_act)

        help_menu = _pin(menubar.addMenu(i18n.tr("menu.help")))
        guide_action = QAction(i18n.tr("menu.guide"), self)
        guide_action.setShortcut("F1")
        guide_action.triggered.connect(self._on_open_guide)
        help_menu.addAction(guide_action)
        help_menu.addAction(QAction(i18n.tr("sidebar.template_help_tip"), self,
                                    triggered=self._on_template_help))
        help_menu.addSeparator()
        about_action = QAction(i18n.tr("menu.about"), self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    def _default_case_frame(self):
        """当前导入数据中的第一张非空表 → (DataFrame, 表名)。"""
        raw = (self.current_data or {}).get("raw_data") or {}
        for name, candidate in raw.items():
            if isinstance(candidate, pd.DataFrame) and not candidate.empty:
                return candidate, str(name)
        return None, "Sheet1"

    def _register_case_workflow(self, workflow):
        """登记案例到当前项目并返回（保存 .qap 时统一落盘）。"""
        self.case_workflows.append(workflow)
        self._last_case_workflow = workflow
        return workflow

    def _create_case_from_current_data(self, title: str = ""):
        """以当前导入数据建立案例基线。"""
        from core.case_workflow import CaseWorkflow

        source = str((self.current_data or {}).get("source", "") or "")
        default_title = (f"改善案例 — {os.path.basename(source)}" if source
                         else "改善案例")
        workflow = CaseWorkflow(title=title or default_title, ledger=self.ledger)
        frame, sheet_name = self._default_case_frame()
        if frame is not None:
            workflow.record_step(
                "baseline", {"params": {"rows": int(len(frame))}},
                data_ref=f"sheet:{sheet_name}",
                frame=frame, note="从当前导入数据建立基线")
        return self._register_case_workflow(workflow)

    def _open_case_workflow_dialog(self, workflow):
        from ui.dialogs.case_workflow_dialog import CaseWorkflowDialog

        CaseWorkflowDialog(workflow, self).exec()

    def _on_case_workbench(self):
        """改善案例工作台（v4.2.0 P5）：以当前导入数据建立案例并打开工作台。"""
        workflow = self._create_case_from_current_data()
        self._open_case_workflow_dialog(workflow)

    def _on_case_center(self):
        """改善案例中心（v4.3.0 B1-4）：查看/新建/打开当前项目的案例。"""
        from ui.dialogs.case_center_dialog import CaseCenterDialog

        dialog = CaseCenterDialog(self.case_workflows, self,
                                  create_callback=self._create_case_from_current_data)
        if dialog.exec() == CaseCenterDialog.Accepted:
            workflow = dialog.selected_workflow()
            if workflow is not None:
                self._last_case_workflow = workflow
                self._open_case_workflow_dialog(workflow)

    # ------------------------------------------------------------ 告警自动立案（v4.4.0 B1）
    def _create_alert_case(self, title: str, product: str = "",
                           owner: str = ""):
        """orchestrator 的案例工厂：创建并登记（保存 .qap 时统一落盘）。"""
        from core.case_workflow import CaseWorkflow

        workflow = CaseWorkflow(title=title, product=product, owner=owner,
                                ledger=self.ledger)
        return self._register_case_workflow(workflow)

    def _find_case_by_id(self, case_id: str):
        target = str(case_id or "").strip()
        for workflow in self.case_workflows:
            if getattr(workflow.case, "id", "") == target:
                return workflow
        return None

    def _on_live_alert(self, event) -> None:
        """告警引擎钩子（采集线程内）：按策略立案/合并；UI 通知经信号回主线程。"""
        try:
            decision = self.alert_case_orchestrator.handle(event)
        except Exception:  # 立案失败不得影响告警通知/留存主链路
            import logging
            logging.getLogger(__name__).exception("告警自动立案失败")
            return
        if decision.action == "opened":
            self.alert_case_opened.emit(decision.case_id, decision.title,
                                        decision.rule_key)

    def _on_alert_case_opened_ui(self, case_id: str, title: str,
                                 rule_key: str) -> None:
        self.statusBar().showMessage(
            f"已自动立案: {title}（{case_id}）", 15000)

    def _open_case_by_id(self, case_id: str) -> bool:
        workflow = self._find_case_by_id(case_id)
        if workflow is None:
            QMessageBox.information(self, "改善案例", f"未找到案例 {case_id}")
            return False
        self._last_case_workflow = workflow
        self._open_case_workflow_dialog(workflow)
        return True

    def open_eight_d_report(self, report_id: str) -> bool:
        """打开项目上下文中的 8D 报告并载入 8D Tab（含自动立案草稿）。"""
        report = None
        for item in list(getattr(self.project_context, "eight_d_reports", []) or []):
            if not isinstance(item, dict):
                continue
            key = str(item.get("id") or item.get("title") or "")
            if key == str(report_id or "").strip():
                report = item
                break
        if report is None:
            QMessageBox.information(self, "8D 报告", f"未找到 8D 报告 {report_id}")
            return False
        tab = self._lazy_load_tab(TAB_INDEX["eight_d"])
        if tab is None or not hasattr(tab, "load_report"):
            return False
        tab.set_project_context(self.project_context)
        tab.load_report(report)
        self._switch_tab(TAB_INDEX["eight_d"])
        return True

    # ------------------------------------------------------------ 收益账本（v4.4.0 B4）
    def _benefit_event_sink(self, event_type: str, object_refs: list,
                            payload: dict) -> None:
        self._ledger_append(event_type, object_refs=object_refs, payload=payload)

    def record_case_benefit(self, workflow, draft: dict):
        """案例收益入账（关闭案例后由工作台调用；口径自动带标准版本）。"""
        record = core_record_case_benefit(
            self.benefit_ledger, workflow.case,
            standards=self.project_context.standards,
            event_sink=self._benefit_event_sink, **draft)
        return record

    def recompute_benefits(self, month: str) -> dict:
        """月度复算（当月口径前移；历史月冻结），复算事件入证据账本。"""
        return self.benefit_ledger.recompute_month(
            month, standards=self.project_context.standards,
            event_sink=self._benefit_event_sink)

    def case_benefit_summary(self, case_id: str) -> str:
        """案例维度的收益摘要（工作台显示，回答"这条改善省了多少"）。"""
        records = self.benefit_ledger.for_case(case_id)
        if not records:
            return ""
        admitted = [record for record in records if record.admits_to_summary]
        total = sum(record.amount for record in admitted
                    if record.ledger_kind == "improvement")
        parts = [f"改善收益 {total:,.2f}（{len(admitted)} 条入账）"]
        pending = len(records) - len(admitted)
        if pending:
            parts.append(f"{pending} 条待完善(C)")
        return " · ".join(parts)

    def _on_benefit_ledger(self):
        from ui.dialogs.benefit_ledger_dialog import BenefitLedgerDialog

        dialog = BenefitLedgerDialog(self.benefit_ledger, self,
                                     recompute=self.recompute_benefits)
        dialog.exec()

    # ------------------------------------------------------------ 技能矩阵（v4.4.0 B5）
    def save_skill_matrix(self, matrix) -> None:
        """保存技能矩阵（对话框回调）并同步已加载的线平衡页签。"""
        if not isinstance(matrix, SkillMatrix):
            raise TypeError("save_skill_matrix 仅接受 SkillMatrix")
        self.skill_matrix = matrix
        tab = self._tab_cache.get(TAB_INDEX["line_balance"])
        if tab is not None and hasattr(tab, "set_skill_context"):
            tab.set_skill_context(self.skill_matrix, self.save_skill_matrix,
                                  self.record_skill_balance_step)

    def record_skill_balance_step(self, phase: str, result: dict, frame=None):
        """把技能约束排班结果记入案例（基线/复测）；凭证含技能矩阵指纹。"""
        key = str(phase or "").strip().lower()
        if key not in ("baseline", "re_measure", "remeasure"):
            raise ValueError(f"不支持的案例阶段: {phase!r}")
        workflow = self._last_case_workflow
        if workflow is None:
            # 技能排班即基线：新建空案例直接记技能步骤（不叠加"当前数据"基线）
            from core.case_workflow import CaseWorkflow

            source = str((self.current_data or {}).get("source", "") or "")
            title = (f"改善案例 — {os.path.basename(source)}" if source
                     else "改善案例")
            workflow = self._register_case_workflow(
                CaseWorkflow(title=title, ledger=self.ledger))
        constraints = result.get("constraints") or {}
        step = workflow.record_step(
            key, result=result, frame=frame, rule_version="skills-lpt@1",
            analysis_type="技能约束线平衡",
            params={"skill_fingerprint": self.skill_matrix.fingerprint(),
                    "headcount_required": constraints.get("headcount_required"),
                    "unmet": list(result.get("unmet") or [])},
            note="技能约束线平衡（含技能矩阵指纹）")
        return step

    def _on_standard_history(self):
        """标准版本时间线（B3）：对象 / 生效区间 / 变更原因 / 变更人。"""
        from ui.dialogs.standard_history_dialog import StandardHistoryDialog

        registry = getattr(self.project_context, "standards", None)
        if registry is None or not len(registry):
            QMessageBox.information(self, "标准版本记录", "当前项目尚无标准版本记录")
            return
        StandardHistoryDialog(registry, self).exec()

    def _on_evidence_view(self):
        """证据视图（B4-2）：结论 → 凭证 → 账本事件 → 原始引用。"""
        from ui.dialogs.evidence_view_dialog import EvidenceViewDialog

        dialog = EvidenceViewDialog(
            self.analyses, self.ledger, parent=self,
            registry=getattr(self.project_context, "standards", None),
            measurements=self.measurement_store,
            frame_provider=self._analysis_source_frame,
            ledger_failures=self._ledger_failures)
        dialog.exec()

    def _on_llm_assist(self):
        """打开 QAM Harness（质量工程 AI Agent）对话窗口。"""
        client = _resolve_llm_client(self)
        if client is None:
            return
        from ui.dialogs.llm_dialog import QAMHarnessDialog
        dlg = getattr(self, "_agent_dialog", None)
        if dlg is not None and dlg.isVisible():
            if dlg.isMinimized():
                dlg.showNormal()
            dlg.raise_()
            dlg.activateWindow()
            return
        dlg = QAMHarnessDialog(self, engine=None)
        dlg.setAttribute(Qt.WA_DeleteOnClose, True)
        dlg.destroyed.connect(lambda *_: setattr(self, "_agent_dialog", None))
        self._agent_dialog = dlg
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()


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
        path, _ = QFileDialog.getSaveFileName(self, "导出 HTML 报告", "akia_report.html", "HTML 报告 (*.html)")
        if not path:
            return
        try:
            from output.html_export import export_html
            charts = self._collect_charts(list(self.analyses.keys()))
            export_html(list(self.analyses.values()), charts=charts, output_path=path)
            audit("export", "user", f"HTML 报告 {os.path.basename(path)}")
            self._record_report_exported("html", path,
                                         analyses=list(self.analyses.values()))
            self.status_label.setText("HTML 报告已导出")
            QMessageBox.information(self, "导出完成", "HTML 报告已导出")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))

    def _setup_statusbar(self):
        self.statusBar().setStyleSheet(
            "QStatusBar { min-height: 24px; background: #13131c; } QStatusBar::item { border: none; }"
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
        self.sidebar.collapse_requested.connect(lambda: self._toggle_sidebar(True))
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

    def _import_cp_from_fmea(self, cp_rows: list) -> bool:
        """FMEA → 控制计划：追加行 → 切换 Tab → 写入项目上下文。

        返回是否成功；失败时由调用方给出提示（不再静默丢弃）。
        """
        cp_idx = TAB_INDEX["control_plan"]
        cp_tab = self._lazy_load_tab(cp_idx)
        if cp_tab is None or not hasattr(cp_tab, 'append_rows'):
            return False

        cp_tab.set_project_context(self.project_context)
        cp_tab.append_rows(cp_rows)
        self._switch_tab(cp_idx)
        return True

    def _import_spc_from_cp(self, spc_items: list) -> bool:
        """控制计划 → SPC：注入监控清单 → 切换 Tab → 写入项目上下文。

        返回是否成功。注意必须先懒加载再取实例（原实现在 Tab 未打开时取到 None）。
        """
        self._spc_monitoring_list = spc_items
        self.project_context.set_analysis_snapshot(
            "spc_monitoring", {"items": spc_items, "source": "control_plan"})

        spc_idx = TAB_INDEX["spc"]
        spc_tab = self._lazy_load_tab(spc_idx)
        if spc_tab is None or not hasattr(spc_tab, 'import_from_cp'):
            return False

        spc_tab.import_from_cp(spc_items)
        self._switch_tab(spc_idx)
        return True

    def _on_import_quality(self):
        dialog = ImportDialog(self, mode="quality")
        if dialog.exec():
            file_path, _sheet_names = dialog.get_selection()
            try:
                self.status_label.setText(f"{i18n.tr('status.loading')}{file_path}...")
                raw_data = self.data_loader.load(file_path)
                audit("import_data", "user",
                      f"质量数据 {os.path.basename(file_path)}")
                self._record_data_imported(file_path, raw_data, kind="quality")
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
                    QMessageBox.critical(self, "路由失败", f"Sheet 分发异常:\n{re!s}")
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
                    num_cols = []
                    for i, c in enumerate(df.columns):
                        try:
                            s = pd.to_numeric(df.iloc[:, i], errors="coerce").dropna()
                            if len(s) > 0:
                                num_cols.append(c)
                        except (ValueError, TypeError):  # 非数值列：不参与校验
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
                QMessageBox.critical(self, i18n.tr("msg.import_failed"), f"{i18n.tr('msg.cannot_load')}\n{e!s}")
                self.status_label.setText(i18n.tr("status.failed"))

    def _on_import_ie(self):
        dialog = ImportDialog(self, mode="ie")
        if dialog.exec():
            file_path, _sheet_names = dialog.get_selection()
            try:
                self.status_label.setText(f"{i18n.tr('status.loading')}{file_path}...")
                raw_data = self.data_loader.load(file_path)
                audit("import_data", "user",
                      f"IE 数据 {os.path.basename(file_path)}")
                self._record_data_imported(file_path, raw_data, kind="ie")
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
                for idx in _IE_IMPORT_TAB_INDICES:
                    self._update_tab_empty_state(idx)

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
                QMessageBox.critical(self, "导入失败", f"无法加载 IE 数据:\n{e!s}")
                self.status_label.setText(i18n.tr("status.failed"))

    def _on_import_db(self):
        # 延迟导入：数据库驱动（sqlalchemy）不进入冷启动路径
        from core.sql_loader import SqlLoader
        from ui.dialogs.db_connection_dialog import DbConnectionDialog
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
                    with contextlib.suppress(Exception):
                        loader.disconnect()
                audit("import_db", "user",
                      f"数据库 {config.get('database', '')} 表数={len(raw_data)}")
                self._record_data_imported(
                    f"db:{config.get('database', '')}", raw_data, kind="database")

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
                    f"从数据库加载数据失败:\n{e!s}"
                )
                self.status_label.setText("数据库导入失败")

    def _on_template_help(self):
        from ui.dialogs.template_help_dialog import TemplateHelpDialog
        dlg = TemplateHelpDialog(self)
        dlg.exec()

    def _on_open_guide(self):
        """在系统默认浏览器中打开使用指南 (config/help/guide.html)"""
        guide = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "config", "help", "guide.html")
        if os.path.exists(guide):
            QDesktopServices.openUrl(QUrl.fromLocalFile(guide))
        else:
            QMessageBox.warning(self, i18n.tr("menu.guide"),
                                "未找到使用指南文件:\nconfig/help/guide.html")

    def _on_import_data(self):
        """兼容旧调用 — 默认质量导入"""
        self._on_import_quality()

    def _route_sheets_to_tabs(self, raw_data: dict[str, pd.DataFrame], worksheet_mode: bool = False):
        """将导入的 Sheet 分配到各分析 Tab。
        worksheet_mode=True: 分配到除 IE 工具(7-11,21-22)外的所有 Tab。
        worksheet_mode=False: 分配到所有 Tab（含 IE）。"""
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
            36: ["时间序列", "时序", "time series", "timeseries"],
            37: ["预测", "predict", "机器学习", "建模"],
        }

        all_indices = set(sheet_map.keys())
        for idx in all_indices:
            if worksheet_mode and idx in _IE_TAB_INDICES:
                continue
            tab = self._lazy_load_tab(idx)
            if tab and hasattr(tab, 'set_raw_data'):
                tab.set_raw_data(raw_data, self.data_parser)
                self._update_tab_empty_state(idx)

        assigned = set()
        for tab_idx, keywords in sheet_map.items():
            if worksheet_mode and tab_idx in _IE_TAB_INDICES:
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
            self._store_analysis(idx, result)
            self._update_tab_empty_state(idx)
            if getattr(self, "_batch_progress", None) is None:
                self._show_toast(f"分析完成：{result.get('analysis_type', '')}",
                                 "success")
        self._notify_dashboard()
        # 渲染完成后布局才稳定，分批延后同步滚动范围（立即读会拿到旧 hint）
        self._schedule_scroll_sync()

    def _on_time_observations_ready(self, observations):
        """外部插件 Tab → 工时研究 Tab：发送作业周期。"""
        tab = self._lazy_load_tab(7)
        if tab is None or not hasattr(tab, "set_ie_data"):
            return
        tab.set_ie_data(observations)
        self._switch_tab(7)
        self.status_label.setText(
            f"已发送 {len(observations)} 个视频作业周期到工时研究")

    def _notify_dashboard(self):
        """v2.4 F1: 分析完成后通知 Dashboard 刷新 (仅当已懒加载时)

        用 refresh_if_changed 去重 — 批量分析时 N 次通知只重建一次
        """
        tab = self._tab_cache.get(27)
        if tab is not None and hasattr(tab, 'refresh_if_changed'):
            tab.refresh_if_changed()

    def _on_run_all_analyses(self):
        """批量分析：逐 Tab 分步执行，带进度与取消（UI 全程可响应）。"""
        if not self.current_data:
            QMessageBox.warning(self, i18n.tr("msg.no_data"), i18n.tr("msg.no_data_file"))
            return

        tabs = self._get_tabs(force_load=True)
        queue = [(idx, tab) for idx, tab in tabs.items() if _tab_is_runnable(tab)]
        if not queue:
            self.statusBar().showMessage("没有可运行的 Tab（请先导入数据）", 5000)
            return

        from PySide6.QtWidgets import QProgressDialog

        self._batch_queue = queue
        self._batch_success = 0
        self._batch_failed = 0
        self._batch_cancelled = False
        progress = QProgressDialog("准备批量分析…", "取消", 0, len(queue), self)
        progress.setWindowTitle("批量分析")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.canceled.connect(self._cancel_batch_analysis)
        self._batch_progress = progress
        progress.setValue(0)
        progress.show()
        QTimer.singleShot(0, self._run_batch_step)

    def _cancel_batch_analysis(self):
        self._batch_cancelled = True

    def _run_batch_step(self):
        """执行一个 Tab 后让出事件循环（保持界面响应与取消可用）。"""
        progress = getattr(self, "_batch_progress", None)
        if progress is None:
            return
        if self._batch_cancelled or not self._batch_queue:
            self._finish_batch_analysis()
            return
        idx, tab = self._batch_queue.pop(0)
        total = progress.maximum()
        progress.setLabelText(
            f"批量分析 {total - len(self._batch_queue)}/{total}：{type(tab).__name__}")
        try:
            tab.run_and_display()
            result = getattr(tab, "current_result", None)
            if result:
                self._store_analysis(idx, result)
            self._batch_success += 1
        except Exception:
            import logging
            logging.getLogger(__name__).exception(f"批量分析 tab idx={idx} 失败")
            self._batch_failed += 1
        progress.setValue(total - len(self._batch_queue))
        QTimer.singleShot(0, self._run_batch_step)

    def _finish_batch_analysis(self):
        progress = getattr(self, "_batch_progress", None)
        if progress is not None:
            progress.close()
            progress.deleteLater()
            self._batch_progress = None
        self._batch_queue = []
        tail = "（已取消）" if self._batch_cancelled else ""
        message = (f"批量分析{tail}完成：成功 {self._batch_success}，"
                   f"失败 {self._batch_failed}")
        self.statusBar().showMessage(message, 6000)
        self._show_toast(message, "warning" if self._batch_failed else "success")
        self._notify_dashboard()
        self._schedule_scroll_sync()

    def _store_analysis(self, idx: int, result: dict):
        """统一收纳分析结果（analyses + 会话历史 + 侧栏历史）。"""
        previous = self.analyses.get(idx)
        self.analyses[idx] = result.copy()
        self.analyses[idx]["_completed_at"] = datetime.now().isoformat(timespec="seconds")
        self.analyses[idx]["credential"] = self._make_analysis_credential(idx, result)
        if previous and previous.get("credential"):
            # 复核模式（v4.2.0 P4-3）：同一 Tab 重跑时自动逐项比对上次结论
            from core.evidence import diff_analysis_records

            self.analyses[idx]["rerun_diff"] = diff_analysis_records(previous,
                                                                     self.analyses[idx])
        self.session_manager.add_analysis(
            result.get("analysis_type", "Unknown"),
            result.get("params", {}),
            result.get("result", {}))
        atype = result.get("analysis_type", "")
        key_res = self._summarize_result(result.get("result", {}))
        self.sidebar.add_history(idx, atype, key_res)
        credential = self.analyses[idx].get("credential") or {}
        params = credential.get("params") or {}
        rerun = self.analyses[idx].get("rerun_diff") or {}
        self._ledger_append(
            "analysis_run",
            object_refs=[f"tab:{idx}", credential.get("data_fingerprint", "")],
            payload={"tab": idx, "analysis_type": atype,
                     "rule_version": credential.get("rule_version", ""),
                     "data_fingerprint": credential.get("data_fingerprint", ""),
                     "standard_ref": params.get("standard_ref", ""),
                     "standard_as_of": params.get("standard_as_of", ""),
                     "rerun_identical": rerun.get("identical"),
                     "completed_at": self.analyses[idx]["_completed_at"]})

    def _make_analysis_credential(self, idx: int, result: dict) -> dict:
        """为该次分析生成结论凭证（规则版本 + 参数 + 数据指纹 + 软件版本）。

        v4.2.0 P4：让"当时是怎么算的"随分析记录一起留存 —— 报告页脚追溯码、
        `.qap` 快照与复核模式（同数据重跑 diff）都以此为单一事实源。
        """
        from core.evidence import make_credential

        rule_version = str(result.get("rule_version")
                           or result.get("analysis_type")
                           or result.get("chart_type")
                           or f"tab_{idx}")
        params = dict(result.get("params", {}) or {})
        params.update(self._standard_context_for(idx, result))
        return make_credential(
            rule_version=rule_version,
            params=params,
            df=self._analysis_source_frame(idx),
            algorithm=str(result.get("analysis_type", "")),
        ).to_dict()

    def _standard_context_for(self, idx: int, result: dict) -> dict:
        """解析该次分析适用的标准版本引用（B3-5），供凭证与 as-of 复判使用。"""
        from core.standard_record import resolve_standard_context

        try:
            registry = self.project_context.standards
        except AttributeError:
            return {}
        if registry is None or not len(registry):
            return {}
        params = result.get("params", {}) or {}
        refs: list[str] = []
        for key in ("standard_ref", "characteristic_id", "column", "process_id"):
            value = params.get(key)
            if value:
                refs.append(str(value))
        tab = self._tab_cache.get(idx)
        for attr in ("standard_object_ref", "characteristic_id"):
            value = getattr(tab, attr, "")
            if value:
                refs.append(str(value))
        resolved = resolve_standard_context(registry, refs)
        if resolved:
            return resolved
        # 兜底：仅当分析数据中恰好一个列名能匹配到标准时才引用，避免张冠李戴
        frame = self._analysis_source_frame(idx)
        if frame is None:
            return {}
        matches = [str(column) for column in frame.columns
                   if registry.current(str(column))
                   or registry.as_of(str(column), now_iso())]
        if len(matches) == 1:
            return resolve_standard_context(registry, matches)
        return {}

    def _analysis_source_frame(self, idx: int):
        """取该 Tab 用于分析的数据作为指纹来源；取不到则返回 None（no-data 指纹）。

        优先 Tab 自身的数据框（分析真正作用的对象），退回当前导入数据的第一张表。
        指纹属附加信息，任何取数异常都不应影响分析流程本身。
        """
        try:
            tab = self._tab_cache.get(idx)
            frame = getattr(tab, "df", None)
            if isinstance(frame, pd.DataFrame) and not frame.empty:
                return frame
        except Exception:  # 当前 Tab 取数失败 → 退回工作簿原始数据
            pass
        try:
            raw = (self.current_data or {}).get("raw_data") or {}
            for candidate in raw.values():
                if isinstance(candidate, pd.DataFrame) and not candidate.empty:
                    return candidate
        except Exception:  # 原始数据不可用 → 返回 None 由调用方兜底
            pass
        return None

    def _show_toast(self, message: str, toast_type: str = "info"):
        """统一轻提示（替代阻塞式弹窗）。"""
        try:
            from ui.widgets.toast import Toast
            Toast.show(self, message, toast_type=toast_type, duration=2600)
        except Exception:  # 提示失败不影响主流程
            pass

    def _lazy_load_tab(self, idx: int):
        """按需加载 Tab — 首次访问时 import + 实例化 + 替换占位符"""
        if idx in self._tab_cache:
            return self._tab_cache[idx]

        if idx >= self._plugin_tab_start:
            if idx in self._plugin_tabs:
                record = self._plugin_tabs[idx]
                tab = self._pm.create_tab(record, self._plugin_host, parent=self)
                if tab is None:
                    return None
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
        except ImportError as exc:
            self._handle_tab_dependency_error(idx, class_name, module_path, exc)
            return None
        except Exception:
            import logging
            logging.getLogger(__name__).exception(
                f"懒加载 Tab 失败: idx={idx} {class_name} from {module_path}"
            )
            return None

        self._tab_cache[idx] = tab
        old = self.stack.widget(idx)
        if old:
            self.stack.removeWidget(old)
        self.stack.insertWidget(idx, tab)
        if old and old.objectName().startswith("placeholder"):
            old.deleteLater()

        self._connect_tab_signals(idx, tab)
        if hasattr(tab, "set_gauge_context"):
            tab.set_gauge_context(self.gauge_monitor,
                                  self._submit_gauge_measurement)
        if hasattr(tab, "set_sampling_context"):
            tab.set_sampling_context(self.sampling_manager)
        if hasattr(tab, "set_skill_context"):
            tab.set_skill_context(self.skill_matrix, self.save_skill_matrix,
                                  self.record_skill_balance_step)
        return tab

    def _handle_tab_dependency_error(self, idx: int, class_name: str,
                                     module_path: str, exc: ImportError):
        """缺依赖导致 Tab 加载失败：展示可操作提示，不打印异常堆栈。"""
        import logging

        from ui.runtime_deps import (
            CHART_DEPENDENCIES, broken_chart_dependencies,
            chart_dependency_hint, missing_chart_dependencies,
        )

        top = (getattr(exc, "name", "") or "").split(".")[0]
        missing = missing_chart_dependencies()
        if not missing:
            if top in CHART_DEPENDENCIES:
                missing = [top]  # 装了一半：find_spec 成功但 import 失败
            elif not top:
                missing = broken_chart_dependencies()

        if missing:
            title = "缺少图表依赖"
            hint = chart_dependency_hint(missing)
            if not self._chart_dependency_warned:
                self._chart_dependency_warned = True
                QMessageBox.warning(self, title, hint)
        else:
            title = "缺少运行依赖"
            name = getattr(exc, "name", None) or str(exc) or class_name
            hint = (
                f"该功能依赖的组件不可用: {name}\n"
                "安装完整依赖后重新点击该功能即可（无需重启）：\n"
                "  pip install -r requirements.txt"
            )
            logging.getLogger(__name__).warning(
                "懒加载 Tab 依赖缺失: idx=%s %s from %s -> %s",
                idx, class_name, module_path, exc,
            )

        self._install_dependency_notice(idx, title, hint)
        self.statusBar().showMessage(hint.splitlines()[0], 15000)

    def _install_dependency_notice(self, idx: int, title: str, message: str):
        """把空白占位页替换为依赖提示页，避免切换后"点了没反应"。"""
        from PySide6.QtWidgets import QLabel, QVBoxLayout

        page = QWidget()
        page.setObjectName(f"dependency_notice_{idx}")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(48, 48, 48, 48)
        layout.addStretch(1)
        title_label = QLabel(title)
        title_label.setFont(QFont(get_ui_font(), 15, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        message_label = QLabel(message)
        message_label.setAlignment(Qt.AlignCenter)
        message_label.setWordWrap(True)
        message_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(title_label)
        layout.addWidget(message_label)
        layout.addStretch(1)

        old = self.stack.widget(idx)
        self.stack.insertWidget(idx, page)
        if old:
            self.stack.removeWidget(old)
            if old.objectName().startswith(("placeholder", "dependency_notice")):
                old.deleteLater()
        return page

    def _connect_tab_signals(self, idx: int, tab):
        """为新创建的 Tab 建立信号连接"""
        if hasattr(tab, 'export_clicked'):
            tab.export_clicked.connect(lambda tid=idx: self._on_export_single(tid, "docx"))
        if hasattr(tab, 'analysis_completed'):
            tab.analysis_completed.connect(lambda tid=idx: self._on_analysis_finished(tid))
        if hasattr(tab, 'import_data_requested'):
            handler = (self._on_import_ie if idx in _IE_IMPORT_TAB_INDICES
                       else self._on_import_quality)
            tab.import_data_requested.connect(handler)
        if hasattr(tab, 'set_stream_source'):
            tab.set_stream_source(self.stream_bus)
        if hasattr(tab, 'send_to_time_study'):
            tab.send_to_time_study.connect(self._on_time_observations_ready)
        if idx in _CONTEXT_TAB_INDICES and hasattr(tab, 'set_project_context'):
            tab.set_project_context(self.project_context)
            if hasattr(tab, 'load_from_context'):
                tab.load_from_context()

    def _get_tabs(self, force_load: bool = False):
        """获取 Tab 字典。force_load=False 仅返回已缓存的(懒加载友好)；force_load=True 全量加载"""
        result = {}
        if force_load:
            idx_range = list(range(1, _PLUGIN_TAB_START))
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

        filters = {"xlsx": "Excel (*.xlsx)", "docx": "Word (*.docx)",
                "pdf": "PDF (*.pdf)", "pptx": "PowerPoint (*.pptx)"}
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
                elif fmt == "pptx":
                    charts = self._collect_charts([idx])
                    from output.pptx_report import PptxReport
                    PptxReport().generate([result], file_path, charts=charts)
                self.status_label.setText(f"{i18n.tr('status.exported')}{file_path}")
                audit("export", "user",
                      f"单Tab导出 {fmt} {os.path.basename(file_path)}")
                self._record_report_exported(fmt, file_path, analyses=[result])
                self._show_toast(f"已导出：{os.path.basename(file_path)}", "success")
                QMessageBox.information(self, i18n.tr("msg.export_complete"), f"{i18n.tr('msg.export_saved')}\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, i18n.tr("msg.export_failed"), str(e))

    def _on_export_all(self, fmt: str = "docx"):
        if not self.analyses:
            QMessageBox.warning(self, i18n.tr("msg.no_results"), i18n.tr("msg.run_first"))
            return

        filters = {"xlsx": "Excel (*.xlsx)", "docx": "Word (*.docx)",
                "pdf": "PDF (*.pdf)", "pptx": "PowerPoint (*.pptx)"}
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
                elif fmt == "pptx":
                    charts = self._collect_charts(list(self.analyses.keys()))
                    from output.pptx_report import PptxReport
                    PptxReport().generate(analyses_list, file_path, charts=charts)
                elif fmt == "pdf":
                    charts = self._collect_charts(list(self.analyses.keys()))
                    from output.pdf_report import generate_pdf_report
                    generate_pdf_report(analyses_list, file_path, charts=charts)
                self.status_label.setText(f"{i18n.tr('status.exported')}{file_path}")
                audit("export", "user",
                      f"汇总导出 {fmt} {os.path.basename(file_path)}")
                self._record_report_exported(fmt, file_path, analyses=analyses_list)
                self._show_toast(f"已导出：{os.path.basename(file_path)}", "success")
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
                self._record_report_exported(
                    fmt, file_path, analyses=list(self.analyses.values()))
                self._show_toast(f"已导出：{os.path.basename(file_path)}", "success")
                QMessageBox.information(self, i18n.tr("msg.export_complete"),
                                        f"{i18n.tr('msg.export_saved')}\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, i18n.tr("msg.export_failed"), str(e))

    def _flush_tab_edits(self) -> None:
        """保存路径统一入口：冲刷各 Tab 节流窗口内的挂起编辑（若有）。

        Tab 侧以 ``flush_pending_edits()`` 暴露冲刷能力（当前：控制计划逐格
        编辑 1.5s 节流）；单个 Tab 冲刷失败不影响保存主链路。
        """
        import logging

        for tab in list(self._tab_cache.values()):
            flush = getattr(tab, "flush_pending_edits", None)
            if not callable(flush):
                continue
            try:
                flush()
            except Exception:
                logging.getLogger(__name__).exception("刷新 Tab 挂起编辑失败")

    def _on_save_project(self):
        if not self.current_data:
            QMessageBox.warning(self, "无数据", "请先导入数据并运行分析")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存项目", "AKIA_Project.qap", "AKIA 项目 (*.qap)"
        )
        if not path:
            return
        try:
            # 冲刷节流窗口内的挂起编辑（如控制计划 1.5s 合并），否则刚编辑的
            # 内容可能不落盘（2026-10-15 审查实测）
            self._flush_tab_edits()
            self.status_label.setText("正在保存项目...")
            raw = self.current_data.get("raw_data", {})
            charts = {}
            for label, buf in self._collect_charts(list(self.analyses.keys())).items():
                charts[label] = buf.getvalue() if hasattr(buf, 'getvalue') else buf
            ProjectManager.save_project(
                path, raw, self.analyses, charts, "",
                project_context=self.project_context.to_dict() if self.project_context else None,
                cases=[workflow.to_dict() for workflow in self.case_workflows],
                standards=(self.project_context.standards.to_dict()
                           if self.project_context else None),
                measurements=self.measurement_store.to_dicts(),
                evidence_events=self.ledger,
                gauge_studies=self.gauge_monitor.to_dict(),
                sampling=self.sampling_manager.to_dict(),
                benefits=self.benefit_ledger.to_dict(),
                skills=self.skill_matrix.to_dict(),
                data_asset=self.data_asset,
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

        ctx_dict = project.get("project_context")
        if ctx_dict:
            from core.project_context import ProjectContext as PC
            self.project_context = PC.from_dict(ctx_dict)
        else:
            self.project_context = ProjectContext()
        self.project_context.event_sink = self._on_standard_event
        standards_payload = project.get("standards")
        if standards_payload and not len(self.project_context.standards):
            from core.standard_record import StandardRegistry
            self.project_context.standards = StandardRegistry.from_dict(standards_payload)
        self._restore_ledger(project.get("evidence_events") or [],
                             project.get("evidence_errors") or [])
        # 告警自动立案编排器持有 context/ledger 引用（v4.4.0 B1）：项目加载
        # 会替换这两个对象，必须显式重绑——否则立案快照/8D 草稿/账本事件会
        # 写入已被丢弃的旧对象（不落盘、不可见；2026-10-15 审查实测）。
        self.alert_case_orchestrator.context = self.project_context
        self.alert_case_orchestrator.ledger = self.ledger
        self._restore_case_workflows(project.get("cases") or [])
        self._restore_measurement_store(project.get("measurements") or [])
        self.gauge_monitor = GaugeMonitor.from_dict(project.get("gauge_studies"))
        self._last_gauge_outcome = {}
        msa_tab = self._tab_cache.get(TAB_INDEX["msa"])
        if msa_tab is not None and hasattr(msa_tab, "set_gauge_context"):
            msa_tab.set_gauge_context(self.gauge_monitor,
                                      self._submit_gauge_measurement)
        self.sampling_manager = SamplingStateManager.from_dict(
            project.get("sampling"), ledger=self.ledger,
            standards=self.project_context.standards)
        self.benefit_ledger = BenefitLedger.from_dict(project.get("benefits"))
        self.skill_matrix = SkillMatrix.from_dict(project.get("skills"))
        loaded_asset = project.get("data_asset")
        self.data_asset = loaded_asset if isinstance(loaded_asset, dict) else None
        line_tab = self._tab_cache.get(TAB_INDEX["line_balance"])
        if line_tab is not None and hasattr(line_tab, "set_skill_context"):
            line_tab.set_skill_context(self.skill_matrix, self.save_skill_matrix,
                                       self.record_skill_balance_step)
        sampling_tab = self._tab_cache.get(TAB_INDEX["sampling"])
        if sampling_tab is not None and hasattr(sampling_tab, "set_sampling_context"):
            sampling_tab.set_sampling_context(self.sampling_manager)
        evidence_errors = project.get("evidence_errors") or []
        measurement_errors = project.get("measurement_errors") or []
        if evidence_errors or measurement_errors:
            self.statusBar().showMessage(
                f"项目加载警告：账本 {len(evidence_errors)} 条 / 测量 "
                f"{len(measurement_errors)} 条记录解析失败（已跳过并留痕）", 20000)
        for idx in _CONTEXT_TAB_INDICES:
            tab = self._tab_cache.get(idx)
            if tab and hasattr(tab, 'set_project_context'):
                tab.set_project_context(self.project_context)
                if hasattr(tab, 'load_from_context'):
                    tab.load_from_context()

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

    def _restore_case_workflows(self, entries: list):
        """从 .qap cases 段恢复案例；单条损坏不影响项目其余内容。"""
        from core.case_workflow import CaseWorkflow

        restored = []
        for entry in entries or []:
            try:
                restored.append(CaseWorkflow.from_dict(entry, ledger=self.ledger))
            except Exception:  # 单条案例损坏 → 跳过并留痕，不阻断项目加载
                import logging
                logging.getLogger(__name__).warning(
                    "跳过无法恢复的改善案例: %r", entry, exc_info=True)
        self.case_workflows = restored
        self._last_case_workflow = restored[-1] if restored else None
        orchestrator = getattr(self, "alert_case_orchestrator", None)
        if orchestrator is not None:
            orchestrator.rebuild(restored)

    # ------------------------------------------------------------ 证据账本（B4）
    def _ledger_append(self, event_type: str, *, actor: str = "user",
                       object_refs: list[str] | None = None,
                       payload: dict | None = None):
        """写入证据账本；失败只计数/留痕，绝不阻断业务动作。"""
        try:
            return self.ledger.append(event_type, actor=actor,
                                      object_refs=object_refs or [],
                                      payload=payload or {})
        except Exception:  # 记账失败不得影响导入/分析/导出等主流程
            import logging
            self._ledger_failures += 1
            logging.getLogger(__name__).warning(
                "证据账本写入失败（累计 %d 次）", self._ledger_failures,
                exc_info=True)
            return None

    def _on_measurement_event(self, event):
        self._ledger_append(
            "measurement_recorded", actor="system",
            object_refs=[event.event_id,
                         event.characteristic_id or event.channel or event.device],
            payload={"source_kind": event.source_kind, "source_id": event.source_id,
                     "channel": event.channel, "n": event.summary.get("n", 0),
                     "fingerprint": event.fingerprint, "raw_ref": event.raw_ref,
                     "ts_start": event.ts_start, "ts_end": event.ts_end})
        try:
            outcome = self.gauge_monitor.ingest_event(event)
        except Exception:  # 量具监控失败不得影响测量写入主链路
            import logging
            logging.getLogger(__name__).exception("量具在线监控摄入失败")
            return
        if outcome is None:
            return
        self._last_gauge_outcome[outcome.gauge_id] = outcome
        if outcome.prompt:
            self._handle_gauge_drift(outcome)

    # ------------------------------------------------------------ 量具在线（v4.4.0 B2）
    def _handle_gauge_drift(self, outcome) -> None:
        """漂移提示：账本事件 + 告警中心留存 + 主线程状态栏（带冷却）。"""
        self.gauge_monitor.note_prompted(outcome.gauge_id)
        reasons = "；".join(outcome.drift_reasons[:3]) or "偏倚/控制图超限"
        refs = [f"gauge:{outcome.gauge_id}"]
        if outcome.event_id:
            refs.append(f"measurement:{outcome.event_id}")
        self._ledger_append(
            "gauge_drift_alerted", actor="system", object_refs=refs,
            payload={"gauge_id": outcome.gauge_id, "bias": outcome.bias,
                     "repeatability_sigma": outcome.repeatability_sigma,
                     "health_score": outcome.health_score,
                     "reasons": outcome.drift_reasons})
        try:
            import time as _time

            from core.streaming.alert_journal import JournalEntry

            self._get_alert_journal().record(JournalEntry(
                id=f"GAUGE-{outcome.gauge_id}-{int(_time.time())}",
                ts=_time.time(), device=outcome.gauge_id, channel="bias",
                kind="gauge_drift", severity="warning",
                desc=f"量具漂移: {reasons}", value=float(outcome.bias)))
        except Exception:  # 留存失败不影响提示
            import logging
            logging.getLogger(__name__).exception("量具漂移写入告警日志失败")
        self.gauge_drift_alerted.emit(outcome.gauge_id, reasons)

    def _on_gauge_drift_ui(self, gauge_id: str, reasons: str) -> None:
        self.statusBar().showMessage(
            f"量具漂移提示：{gauge_id} — {reasons}（建议重做测量系统研究）", 20000)

    def _submit_gauge_measurement(self, gauge_id: str, value: float):
        """量具测量录入（统一走 MeasurementStore：账本/监控/持久化同源）。"""
        from core.measurement_event import MeasurementEvent

        event = MeasurementEvent.from_manual(
            float(value), characteristic_id=str(gauge_id))
        self.measurement_store.add(event)
        return self._last_gauge_outcome.get(str(gauge_id))

    def _on_standard_event(self, event_type: str, object_refs: list[str],
                           payload: dict) -> None:
        self._ledger_append(event_type, object_refs=object_refs, payload=payload)

    def _on_alert_event(self, entry) -> None:
        self._ledger_append(
            "alert_ack", object_refs=[f"alert:{entry.id}", entry.device],
            payload={"device": entry.device, "channel": entry.channel,
                     "kind": entry.kind, "severity": entry.severity,
                     "ack_by": entry.ack_by})

    def _record_data_imported(self, source: str, raw_data: dict,
                              kind: str = "file") -> None:
        sheets = len(raw_data or {})
        rows = sum(len(df) for df in (raw_data or {}).values()
                   if hasattr(df, "__len__"))
        self._ledger_append("data_imported", object_refs=[str(source)],
                            payload={"source": str(source), "kind": kind,
                                     "sheets": sheets, "rows": int(rows)})

    def _record_report_exported(self, fmt: str, file_path: str,
                                analyses=None) -> None:
        from core.evidence import credential_trace_code

        records = analyses if analyses is not None else list(self.analyses.values())
        trace = credential_trace_code(
            [(record or {}).get("credential") for record in records])
        refs = [os.path.basename(file_path)]
        if trace:
            refs.append(f"trace:{trace}")
        self._ledger_append("report_exported", object_refs=refs,
                            payload={"format": fmt,
                                     "file": os.path.basename(file_path),
                                     "trace": trace})

    def _restore_ledger(self, events: list, errors: list | None = None) -> None:
        try:
            self.ledger = EvidenceLedger.from_events(events or [])
        except (TypeError, ValueError):
            import logging
            logging.getLogger(__name__).warning(
                "证据账本恢复失败，回退为空账本", exc_info=True)
            self.ledger = EvidenceLedger()
        # 写入失败计数只统计本会话的追加失败；加载期解析错误由 ledger.verify()
        # 在证据视图中以"链校验失败"呈现（若解析错误在，后续追加会被账本拒绝
        # 并计入写入失败，语义不再混叠）
        self._ledger_failures = 0
        if errors:
            import logging
            logging.getLogger(__name__).warning(
                "证据账本存在 %d 条解析错误: %s", len(errors), errors[:3])
        chain = self.ledger.verify()
        if not chain.get("ok"):
            import logging
            logging.getLogger(__name__).warning(
                "证据账本链校验失败: %s", chain.get("reason", ""))

    def _restore_measurement_store(self, entries: list):
        """从 .qap measurements 段恢复测量事件；单条损坏跳过并留痕。"""
        store = MeasurementStore()
        for entry in entries or []:
            try:
                store.add(entry)
            except (TypeError, ValueError):
                import logging
                logging.getLogger(__name__).warning(
                    "跳过无法恢复的测量事件: %r", entry, exc_info=True)
        store.event_sink = self._on_measurement_event
        self.measurement_store = store

    def _on_stream_measurements(self, events):
        """连接器采集旁路：仅在测量采集开启时写入项目事件集合。"""
        if not getattr(self, "measurement_capture", False):
            return
        self.measurement_store.extend(events)

    def _on_load_project(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "打开项目", "", "AKIA 项目 (*.qap)"
        )
        if not path:
            return
        try:
            self.status_label.setText("正在加载项目...")
            project = ProjectManager.load_project(path)
            self._apply_loaded_project(
                project, path,
                success_msg=(
                    f"已恢复 {len(project['raw_data'])} 个数据表、"
                    f"{len(self.analyses)} 个分析结果、"
                    f"{len(self.case_workflows)} 个改善案例"),
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
                            # 清洗后重算列类型/数值列（DataLoader 全列 dtype=str,
                            # 不能用 select_dtypes 判定数值列 — 结果恒为空）
                            try:
                                info = self.data_parser.refresh_info(cleaned, info)
                            except Exception:
                                info = dict(info)
                        tab.set_data(cleaned.copy(), info or {})
                        self._update_tab_empty_state(ti)
                        updated.add(ti)
                self.statusBar().showMessage(
                    f"数据清洗已完成，已更新 {len(updated)} 个分析模块", 5000
                )
                self._ledger_append(
                    "data_edited", object_refs=[f"tab:{idx}"],
                    payload={"action": "data_cleaner", "updated_tabs": len(updated)})

    def _on_data_clean_wizard(self):
        if not self.current_data:
            QMessageBox.information(self, "提示", "请先导入数据文件")
            return
        raw = self.current_data.get("raw_data", {})
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
            self._ledger_append(
                "data_edited", object_refs=[str(first_key)],
                payload={"action": "data_clean_wizard", "sheet": str(first_key)})
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
        if result.get("summary_text"):
            return str(result["summary_text"])[:16]
        model = result.get("model")
        if isinstance(model, dict):        # 回归等引擎的模型详情字典
            r2 = model.get("r_squared", 0)
            return f"R²={r2:.2f}"
        return ""

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
            self._toggle_sidebar(True)
        from ui.theme import apply_dark_palette
        apply_dark_palette()

    def closeEvent(self, event):
        settings = QSettings("AKIA", "MainWindow")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        settings.setValue("sidebarCollapsed", not self.sidebar.isVisible())
        self._shutdown_runtime()
        super().closeEvent(event)

    def _shutdown_runtime(self):
        """集中释放后台运行资源：看板服务 / 实时 OEE / 告警引擎 / Tab 实时订阅。

        未清理会导致退出后线程池与总线订阅残留（v3.7.1 修复）。
        """
        import logging
        log = logging.getLogger(__name__)

        from server.app import stop_thread
        try:
            stop_thread(getattr(self, "_dash_thread", None))
        except Exception:
            log.exception("停止实时看板服务失败")
        self._dash_thread = None

        oee = getattr(self, "_oee_computer", None)
        if oee is not None:
            try:
                oee.stop()
            except Exception:
                log.exception("停止实时 OEE 计算失败")
            self._oee_computer = None

        engine = getattr(self, "_alert_engine", None)
        if engine is not None:
            try:
                engine.stop()
            except Exception:
                log.exception("停止告警引擎失败")
            self._alert_engine = None

        runner = getattr(self, "_ingest_runner", None)
        if runner is not None:
            try:
                runner.stop()
            except Exception:
                log.exception("停止采集运行时失败")
            self._ingest_runner = None

        store = getattr(self, "_ts_store", None)
        if store is not None:
            try:
                store.close()
            except Exception:
                log.exception("关闭时序库失败")
            self._ts_store = None

        for tab in list(getattr(self, "_tab_cache", {}).values()):
            shutdown = getattr(tab, "shutdown_stream", None)
            if callable(shutdown):
                try:
                    shutdown()
                except Exception:
                    log.exception("Tab 实时流清理失败")

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
            self, "保存到共享目录", "AKIA_Shared.qap", "AKIA 项目 (*.qap)"
        )
        if not path:
            return
        try:
            # 同 _on_save_project：共享保存前冲刷节流窗口内的挂起编辑
            self._flush_tab_edits()
            raw = self.current_data.get("raw_data", {})
            charts = {}
            for label, buf in self._collect_charts(list(self.analyses.keys())).items():
                charts[label] = buf.getvalue() if hasattr(buf, 'getvalue') else buf
            SharedProjectManager.save_shared(
                path, raw, self.analyses, charts, dept,
                project_context=(self.project_context.to_dict()
                                 if self.project_context else None),
                cases=[workflow.to_dict() for workflow in self.case_workflows],
                standards=(self.project_context.standards.to_dict()
                           if self.project_context else None),
                measurements=self.measurement_store.to_dicts(),
                evidence_events=self.ledger,
                gauge_studies=self.gauge_monitor.to_dict(),
                sampling=self.sampling_manager.to_dict(),
                benefits=self.benefit_ledger.to_dict(),
                skills=self.skill_matrix.to_dict(),
                data_asset=self.data_asset)
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
                self._apply_loaded_project(
                    loaded, proj['path'],
                    status_msg=f"共享项目已加载: {len(loaded['raw_data'])} sheets")
            except Exception as e:
                QMessageBox.critical(self, "加载失败", str(e))

    def _on_plant_config(self):
        """产线配置可视化编辑（v3.8.0-②）— 保存后热重载看板/OEE/实时图规格。"""
        from ui.dialogs.plant_config_dialog import PlantConfigDialog
        dlg = PlantConfigDialog(self)
        if dlg.exec():
            self._reload_plant_config()
            self.statusBar().showMessage(
                f"{i18n.tr('plant.saved_tip')}: {dlg.path}", 6000)

    def _reload_plant_config(self):
        """就地重载产线拓扑 — 保持对象标识，运行中的看板/OEE 立即生效。"""
        try:
            oee = getattr(self, "_oee_computer", None)
            if oee is not None and getattr(oee, "plant", None) is not None:
                oee.plant.reload()
            elif getattr(self, "_plant_cfg", None) is not None:
                self._plant_cfg.reload()
            else:
                self._plant_cfg = self._load_plant_safe()
            for tab in list(getattr(self, "_tab_cache", {}).values()):
                if hasattr(tab, "_plant_cfg"):
                    tab._plant_cfg = None  # 实时图下次渲染重读
            if getattr(self, "_alert_engine", None) is not None:
                self._restart_alert_engine()
        except Exception:
            import logging
            logging.getLogger(__name__).exception("产线配置热重载失败")

    def _load_plant_safe(self):
        try:
            from core.plant import PlantConfig
            return PlantConfig.load()
        except Exception:
            return None

    def _restart_alert_engine(self):
        engine = getattr(self, "_alert_engine", None)
        if engine is not None:
            with contextlib.suppress(Exception):
                engine.stop()
            self._alert_engine = None
        self._start_alert_engine()

    def _on_live_dashboard(self, checked: bool):
        """启动/停止内置实时看板服务（v3.7.0-P3）。"""
        if checked:
            try:
                from core.plant import PlantConfig
                from core.streaming.oee_live import LiveOEEComputer
                from server.app import dashboard_config, dashboard_url, start_thread

                cfg = dashboard_config()
                plant = PlantConfig.load()
                self._downtime = self._get_downtime_tracker()
                self._oee_computer = LiveOEEComputer(self.stream_bus, plant,
                                                     downtime=self._downtime)
                self._dash_thread = start_thread(
                    self.stream_bus, None, host=cfg["host"], port=cfg["port"],
                    plant=plant, oee=self._oee_computer,
                    downtime=self._downtime, auth_token=cfg["token"])
                self._dash_url = dashboard_url("127.0.0.1", cfg["port"], cfg["token"])
            except Exception as e:
                QMessageBox.warning(
                    self, i18n.tr("menu.live_dashboard"),
                    f"{e}\n\npip install -r requirements-server.txt")
                self.live_dash_act.setChecked(False)
                return
            QDesktopServices.openUrl(QUrl(getattr(self, "_dash_url",
                                                  "http://127.0.0.1:8765/")))
        else:
            from server.app import stop_thread

            stop_thread(getattr(self, "_dash_thread", None))
            self._dash_thread = None
            oee = getattr(self, "_oee_computer", None)
            if oee:
                oee.stop()
                self._oee_computer = None

    def _start_alert_engine(self):
        """按产线配置 + user_config 设置安装告警引擎（桌面状态栏通知）。"""
        try:
            from config.settings import get_setting, get_secret
            from core.plant import PlantConfig
            from core.streaming.alerts import (
                AlertEngine, DesktopHandler, rules_from_plant,
                build_default_handlers,
            )
            plant = PlantConfig.load()
            rules = rules_from_plant(plant)
            if not rules:
                return
            desktop = DesktopHandler()
            desktop.alert.connect(
                lambda title, msg: self.statusBar().showMessage(f"{title}: {msg}", 8000))
            journal = self._get_alert_journal()
            settings = {
                "alert_journal": journal,
                "alert_min_severity": get_setting("alert_min_severity", "info"),
                "alert_webhook_url": get_setting("alert_webhook_url", ""),
                "alert_smtp_host": get_setting("alert_smtp_host", ""),
                "alert_smtp_port": get_setting("alert_smtp_port", 25),
                "alert_smtp_user": get_setting("alert_smtp_user", ""),
                "alert_smtp_password": get_secret("alert_smtp_password", ""),
                "alert_email_to": get_setting("alert_email_to", ""),
                "alert_actions": get_setting("alert_actions", {}) or {},
                "alert_actions_enabled": bool(
                    get_setting("alert_actions_enabled", False)),
            }
            self._alert_engine = AlertEngine(
                self.stream_bus, rules, [desktop] + build_default_handlers(settings))
            # v4.4.0 B1：critical 告警自动立案（钩子在采集线程内同步回调）
            self._alert_engine.alert_hook = self._on_live_alert
            self._alert_engine.start()
            self._alert_journal = journal
        except Exception:
            import logging
            logging.getLogger(__name__).exception("alert engine init failed")

    def _get_alert_journal(self):
        """告警日志单例（告警中心与引擎共享同一实例）。"""
        journal = getattr(self, "_alert_journal", None)
        if journal is None:
            from core.streaming.alert_journal import AlertJournal
            journal = AlertJournal()
            self._alert_journal = journal
        journal.event_sink = self._on_alert_event
        return journal

    def _get_downtime_tracker(self):
        """停机追踪单例（实时 OEE / 成本损失 / 看板共用）。"""
        tracker = getattr(self, "_downtime", None)
        if tracker is None:
            from config.settings import get_setting
            from core.streaming.downtime import DowntimeTracker
            tracker = DowntimeTracker(
                reason_codes=get_setting("downtime_reason_codes", None))
            self._downtime = tracker
        return tracker

    def _start_streaming_runtime(self):
        """按 user_config.connectors 启动采集运行时（v3.8.0-⑦）。

        未配置 connectors 时不启动（默认零开销）；启动后设备/连接器数据进入
        StreamBus → 实时 SPC / OEE / 看板 / 告警全链路。单项连接器初始化
        失败只记录健康状态，不影响其他数据源。
        """
        try:
            from config.settings import get_setting
            from connectors.health import HealthRegistry
            from connectors.registry import create_drivers, specs_from_settings
            from core.storage.timeseries import TimeseriesStore, default_store_path
            from core.streaming.collector import IngestRunner

            specs = specs_from_settings(get_setting("connectors", []))
            if not specs:
                return
            drivers, errors = create_drivers(specs)
            health = HealthRegistry(
                base_backoff_s=float(get_setting("connector_backoff_base_s", 1.0)),
                max_backoff_s=float(get_setting("connector_backoff_max_s", 60.0)),
            )
            for spec in specs:
                health.register(str(spec.get("name")), kind="connector")
            for name, message in errors:
                health.mark_error(name, f"初始化失败: {message}")
            if not drivers:
                self._connector_health = health
                return

            db_path = get_setting("ts_db_path", "") or default_store_path()
            store = TimeseriesStore(db_path)
            raw_days = float(get_setting("ts_raw_retention_days", 0) or 0)
            rollup_days = float(get_setting("ts_rollup_retention_days", 0) or 0)
            runner = IngestRunner(
                self.stream_bus, store, drivers,
                raw_retention_s=raw_days * 86400 or None,
                rollup_retention_s=rollup_days * 86400 or None,
                health=health,
                event_sink=self._on_stream_measurements,
            )
            runner.start()
            self._connector_health = health
            self._ingest_runner = runner
            self._ts_store = store
        except Exception:
            import logging
            logging.getLogger(__name__).exception("streaming runtime init failed")

    def _on_connector_health(self):
        """连接器健康页（v3.8.0-⑦）— 状态 / 插件可用性 / 手动重连。"""
        from ui.dialogs.connector_health_dialog import ConnectorHealthDialog
        dlg = ConnectorHealthDialog(getattr(self, "_connector_health", None),
                                    getattr(self, "_ingest_runner", None), self)
        dlg.exec()

    def _on_alert_center(self):
        """告警中心（v3.8.0-③）— 等级筛选 / 确认 / 导出。"""
        from ui.dialogs.alert_center_dialog import AlertCenterDialog
        dlg = AlertCenterDialog(
            self._get_alert_journal(), self,
            case_resolver=self.alert_case_orchestrator.case_for_alert,
            open_case=self._open_case_by_id)
        dlg.exec()

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
            f"<p>{APP_FULL_NAME}</p>"
            f"<p>开源个人工业工程与质量分析工具</p>"
            f"<p>本地优先 · 可选 AI 助手 · 插件扩展 · Apache License 2.0</p>"
            f"<br><p style='color:#888'>技术栈: Python 3.14 · PySide6 · pandas · scipy · scikit-learn · SHAP</p>"
        )
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec()

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
            self._record_data_imported(file_path, raw_data, kind="file")
            self.current_data = {"file_path": file_path, "raw_data": raw_data}
            self.data_label.setText(os.path.basename(file_path))
            self._route_sheets_to_tabs(raw_data, worksheet_mode=True)
            self.status_label.setText(f"已加载: {os.path.basename(file_path)}")
        except Exception as e:
            self.status_label.setText(f"加载失败: {e}")
