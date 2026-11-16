"""
AKIA — 主窗口
"""

import os
from typing import Any

from PySide6.QtWidgets import (
    QMainWindow, QWidget,
)
from PySide6.QtCore import (
    Signal,
)
from PySide6.QtGui import QIcon

from config.settings import APP_NAME, APP_VERSION
from core.data_loader import DataLoader
from core.data_parser import DataParser
from core.data_validator import DataValidator
from core.template_parser import TemplateParser
from core.session_manager import SessionManager
from core.data_profiler import DataProfiler
from core.project_context import ProjectContext
from core.measurement_store import MeasurementStore
from core.evidence_ledger import EvidenceLedger
from core.alert_case import AlertCaseOrchestrator
from core.benefit_ledger import (
    BenefitLedger,
)
from core.gauge_study import GaugeMonitor
from core.skill_matrix import SkillMatrix
from core.sampling_state import SamplingStateManager
from core.streaming.bus import StreamBus

from core.plugin_manager import PluginManager
from ui.main_window_helpers import (
    _CurrentPageStack, _resolve_llm_client, _tab_has_data, _tab_is_runnable,
)

from ui.main_window_constants import _PLUGIN_TAB_START, project_path
from ui.window.chrome import ChromeMixin
from ui.window.menu import MenuMixin
from ui.window.cases import CaseMixin
from ui.window.assist import AssistMixin
from ui.window.imports import ImportMixin
from ui.window.analysis import AnalysisMixin
from ui.window.projects import ProjectMixin
from ui.window.ledger import LedgerMixin
from ui.window.runtime import RuntimeMixin

__all__ = [
    "MainWindow",
    "_CurrentPageStack",
    "_PLUGIN_TAB_START",
    "_resolve_llm_client",
    "_tab_has_data",
    "_tab_is_runnable",
]


class MainWindow(
    ChromeMixin,
    MenuMixin,
    CaseMixin,
    AssistMixin,
    ImportMixin,
    AnalysisMixin,
    ProjectMixin,
    LedgerMixin,
    RuntimeMixin,
    QMainWindow,
):
    #: 告警自动立案通知（采集线程 emit → 主线程槽显示）
    alert_case_opened = Signal(str, str, str)  # case_id, title, rule_key
    #: 量具漂移通知（采集线程 emit → 主线程槽显示；v4.4.0 B2）
    gauge_drift_alerted = Signal(str, str)     # gauge_id, reasons

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.resize(1300, 880)
        self.setMinimumSize(1040, 700)

        logo_path = project_path("logo.png")
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

