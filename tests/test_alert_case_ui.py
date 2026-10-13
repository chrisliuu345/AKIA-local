"""告警自动立案 UI 接线测试（v4.4.0 B1，离屏）。"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pandas as pd
import pytest

from tests.test_alert_case import BASE, _FakeAlert

pytest.importorskip("PySide6")


@pytest.fixture
def main_window():
    from ui.main_window import MainWindow

    window = MainWindow()
    window.current_data = {
        "source": "/tmp/line_a.xlsx",
        "raw_data": {"工时": pd.DataFrame({"cycle": [31.0, 32.0, 33.0]})},
    }
    try:
        yield window
    finally:
        window.close()


class TestMainWindowWiring:
    def test_live_alert_opens_case_and_status(self, main_window):
        before = len(main_window.case_workflows)
        main_window._on_live_alert(_FakeAlert(id="UI-ALERT-1"))
        assert len(main_window.case_workflows) == before + 1
        workflow = main_window.case_workflows[-1]
        assert "auto_alert" in workflow.case.tags
        assert workflow.case.evidence_required is True
        assert "自动立案" in main_window.statusBar().currentMessage()
        # 重复告警在冷却窗口内合并为同案步骤
        main_window._on_live_alert(_FakeAlert(id="UI-ALERT-2"))
        assert len(main_window.case_workflows) == before + 1
        assert len(workflow.case.steps) == 2

    def test_alert_engine_hook_attached_on_start(self, main_window, monkeypatch):
        from types import SimpleNamespace

        captured = {}

        class _FakeEngine:
            def __init__(self, bus, rules, handlers):
                captured["engine"] = self
                self.alert_hook = None
                self.started = False

            def start(self):
                self.started = True

        from core.plant import PlantConfig
        from core.streaming import alerts as alerts_module

        monkeypatch.setattr(alerts_module, "AlertEngine", _FakeEngine)
        monkeypatch.setattr(alerts_module, "rules_from_plant",
                            staticmethod(lambda plant: [object()]))
        monkeypatch.setattr(alerts_module, "build_default_handlers",
                            staticmethod(lambda settings: []))
        monkeypatch.setattr(
            alerts_module, "DesktopHandler",
            lambda *a, **k: SimpleNamespace(
                alert=SimpleNamespace(connect=lambda *a, **k: None)))
        monkeypatch.setattr(PlantConfig, "load", staticmethod(lambda: None))
        main_window._start_alert_engine()
        engine = captured["engine"]
        assert engine.alert_hook == main_window._on_live_alert
        assert engine.started is True

    def test_open_case_by_id_opens_workbench(self, main_window, monkeypatch):
        from ui.dialogs import case_workflow_dialog as module

        main_window._on_live_alert(_FakeAlert(id="UI-ALERT-3"))
        workflow = main_window.case_workflows[-1]
        opened = {}

        class _FakeDialog:
            def __init__(self, wf, parent=None):
                opened["workflow"] = wf

            def exec(self):
                return 0

        monkeypatch.setattr(module, "CaseWorkflowDialog", _FakeDialog)
        assert main_window._open_case_by_id(workflow.case.id) is True
        assert opened["workflow"] is workflow


class TestCaseCenterBadge:
    def test_auto_alert_badge_column(self, main_window):
        from ui.dialogs.case_center_dialog import CaseCenterDialog

        main_window._on_live_alert(_FakeAlert(id="UI-ALERT-4"))
        dialog = CaseCenterDialog(main_window.case_workflows)
        try:
            headers = [dialog.table.horizontalHeaderItem(i).text()
                       for i in range(dialog.table.columnCount())]
            assert "来源" in headers
            source_col = headers.index("来源")
            sources = {dialog.table.item(row, source_col).text()
                       for row in range(dialog.table.rowCount())}
            assert "自动立案" in sources
        finally:
            dialog.close()


class TestProjectRestoreRebuild:
    def test_restore_case_workflows_seeds_orchestrator(self, main_window):
        main_window._on_live_alert(_FakeAlert(id="UI-RESTORE-1"))
        workflow = main_window.case_workflows[-1]
        payload = workflow.to_dict()
        main_window.case_workflows = []
        main_window._restore_case_workflows([payload])
        assert main_window.alert_case_orchestrator.case_for_alert(
            "UI-RESTORE-1") == workflow.case.id
        # 冷却窗口内续报 → 并入恢复的案例（不新开）
        main_window._on_live_alert(_FakeAlert(id="UI-RESTORE-2"))
        assert len(main_window.case_workflows) == 1
        assert len(main_window.case_workflows[0].case.steps) == 2


class TestAlertCenterEntry:
    def test_open_case_resolver_and_callback(self, main_window, monkeypatch):
        from PySide6.QtWidgets import QMessageBox

        from core.streaming.alert_journal import JournalEntry
        from ui.dialogs.alert_center_dialog import AlertCenterDialog

        monkeypatch.setattr(QMessageBox, "information",
                            staticmethod(lambda *a, **k: None))
        main_window._on_live_alert(_FakeAlert(id="UI-ALERT-5"))
        workflow = main_window.case_workflows[-1]
        journal = main_window._get_alert_journal()
        journal.record(JournalEntry(
            id="UI-ALERT-5", ts=BASE.timestamp(), device="line1",
            channel="cycle", kind="oos", severity="critical",
            desc="超规格上界", value=42.0))
        opened = {}
        dialog = AlertCenterDialog(
            journal, main_window,
            auto_refresh_ms=0,
            case_resolver=main_window.alert_case_orchestrator.case_for_alert,
            open_case=lambda case_id: opened.setdefault("case_id", case_id))
        try:
            dialog.refresh()
            row = next(i for i in range(dialog.table.rowCount())
                       if dialog.table.item(i, 0).data(256) == "UI-ALERT-5")
            dialog.table.selectRow(row)
            dialog._on_open_case()
            assert opened["case_id"] == workflow.case.id
        finally:
            dialog.close()


class TestEightDDraftFlow:
    def test_load_report_save_roundtrip_preserves_binding(self, main_window,
                                                          monkeypatch):
        from PySide6.QtWidgets import QMessageBox

        monkeypatch.setattr(QMessageBox, "information",
                            staticmethod(lambda *a, **k: None))
        main_window._on_live_alert(_FakeAlert(id="UI-ALERT-6"))
        workflow = main_window.case_workflows[-1]
        report_id = workflow.case.report_refs[0]

        tab = main_window._lazy_load_tab(30)  # 8D Tab
        tab.set_project_context(main_window.project_context)
        report = main_window.project_context.eight_d_reports[0]
        tab.load_report(report)
        assert tab.report.title.startswith("自动立案")
        assert "超规格上界" in tab._w["d2_statement"].toPlainText()
        assert tab._w["d2_where"].text() == "line1/cycle"
        tab._save()
        saved = main_window.project_context.eight_d_reports[0]
        assert saved["id"] == report_id
        assert saved["case_id"] == workflow.case.id
        assert saved.get("auto") is True

    def test_open_eight_d_report_switches_tab(self, main_window):
        main_window._on_live_alert(_FakeAlert(id="UI-ALERT-7"))
        workflow = main_window.case_workflows[-1]
        report_id = workflow.case.report_refs[0]
        assert main_window.open_eight_d_report(report_id) is True
        assert main_window.stack.currentIndex() == 30
