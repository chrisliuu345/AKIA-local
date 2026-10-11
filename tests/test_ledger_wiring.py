"""主窗口证据账本接线测试（v4.3.0 B4-1，离屏）。"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pandas as pd
import pytest

pytest.importorskip("PySide6")

from core.evidence import make_credential
from core.evidence_ledger import EvidenceLedger
from core.measurement_event import MeasurementEvent
from core.project_manager import ProjectManager


@pytest.fixture
def main_window():
    from ui.main_window import MainWindow

    window = MainWindow()
    window.current_data = {
        "source": "/tmp/line_a.xlsx",
        "file_path": "/tmp/line_a.xlsx",
        "raw_data": {"工时": pd.DataFrame({"cycle": [31.0, 32.0, 33.0]})},
    }
    try:
        yield window
    finally:
        window.close()


class TestActionEvents:
    def test_analysis_measurement_and_standard_events(self, main_window):
        main_window._store_analysis(2, {
            "analysis_type": "正态过程能力", "params": {"column": "cycle"},
            "result": {"cpk": 1.2}})
        main_window.measurement_store.add(
            MeasurementEvent.from_manual(32.0, characteristic_id="cycle"))
        main_window.project_context.record_specification(
            "cycle", usl=33.0, lsl=31.0, change_reason="初始版本")
        types = [event.event_type for event in main_window.ledger.events]
        assert "analysis_run" in types
        assert "measurement_recorded" in types
        assert "standard_changed" in types
        analysis = next(e for e in main_window.ledger.events
                        if e.event_type == "analysis_run")
        assert analysis.payload["analysis_type"] == "正态过程能力"
        assert analysis.payload["data_fingerprint"]

    def test_case_lifecycle_events(self, main_window):
        workflow = main_window._create_case_from_current_data()
        frame = pd.DataFrame({"before": [32.0, 31.0], "after": [28.0, 27.0]})
        workflow.record_step("remeasure", {"mean": 27.5}, frame=frame)
        workflow.record_step("verify", {"p_value": 0.001, "is_significant": True},
                             frame=frame)
        workflow.close_case("复测显著")
        types = [event.event_type for event in main_window.ledger.events]
        assert types[0] == "case_created"
        assert types.count("case_step") == 3
        assert "case_closed" in types

    def test_import_and_report_events(self, main_window):
        main_window._record_data_imported("/tmp/a.xlsx", {"S": pd.DataFrame({"x": [1]})})
        credential = make_credential("cap@1", {"usl": 1},
                                     df=pd.DataFrame({"x": [1.0]})).to_dict()
        main_window._record_report_exported(
            "pdf", "/tmp/report.pdf", analyses=[{"credential": credential}])
        types = [event.event_type for event in main_window.ledger.events]
        assert "data_imported" in types
        assert "report_exported" in types
        report = next(e for e in main_window.ledger.events
                      if e.event_type == "report_exported")
        assert any(ref.startswith("trace:") for ref in report.object_refs)

    def test_alert_ack_event(self, main_window, tmp_path, monkeypatch):
        import time

        from core.streaming import alert_journal as module

        monkeypatch.setattr(module, "default_journal_path",
                            lambda: tmp_path / "alerts.jsonl")
        main_window._alert_journal = None
        journal = main_window._get_alert_journal()
        entry = module.JournalEntry(id="ALT-1", ts=time.time(), device="dev-1",
                                    channel="CH0", kind="ooc")
        journal.record(entry)
        assert journal.ack("ALT-1", "tester") is True
        acks = [e for e in main_window.ledger.events if e.event_type == "alert_ack"]
        assert acks and acks[0].payload["device"] == "dev-1"


class TestPersistenceAndIsolation:
    def test_save_project_includes_ledger(self, main_window, tmp_path, monkeypatch):
        from PySide6.QtWidgets import QFileDialog, QMessageBox

        main_window._record_data_imported("/tmp/a.xlsx",
                                          {"S": pd.DataFrame({"x": [1]})})
        path = str(tmp_path / "ledger.qap")
        monkeypatch.setattr(QFileDialog, "getSaveFileName",
                            staticmethod(lambda *a, **k: (path, "")))
        monkeypatch.setattr(QMessageBox, "information",
                            staticmethod(lambda *a, **k: None))
        main_window._on_save_project()
        project = ProjectManager.load_project(path)
        assert project["manifest"]["evidence_event_count"] >= 1
        restored = EvidenceLedger.from_events(project["evidence_events"])
        assert restored.verify()["ok"] is True

    def test_ledger_failure_is_isolated(self, main_window):
        def _boom(*args, **kwargs):
            raise RuntimeError("disk full")

        main_window.ledger.append = _boom
        assert main_window._ledger_append("case_created") is None
        assert main_window._ledger_failures == 1

    def test_save_shared_includes_all_segments(self, main_window, tmp_path,
                                               monkeypatch):
        """共享保存必须与项目保存同段位（案例/标准/测量/账本），不得抛错。"""
        from PySide6.QtWidgets import QFileDialog, QMessageBox

        from core import project_manager as pm

        monkeypatch.setattr(pm, "SHARED_DIR", str(tmp_path / "shared"))
        main_window._record_data_imported(
            "/tmp/a.xlsx", {"S": pd.DataFrame({"x": [1]})})
        main_window._create_case_from_current_data()
        main_window.project_context.record_specification(
            "cycle", usl=33.0, lsl=31.0, change_reason="共享初始版本")
        monkeypatch.setattr(
            QFileDialog, "getSaveFileName",
            staticmethod(lambda *a, **k: (str(tmp_path / "shared.qap"), "")))
        monkeypatch.setattr(QMessageBox, "information",
                            staticmethod(lambda *a, **k: None))

        def _fail(*args, **kwargs):
            raise AssertionError(f"共享保存出现错误弹窗: {args[2:]}")

        monkeypatch.setattr(QMessageBox, "critical", staticmethod(_fail))
        main_window._on_save_shared()
        loaded = pm.ProjectManager.load_project(
            str(tmp_path / "shared" / "公共" / "shared.qap"))
        assert loaded["manifest"]["evidence_event_count"] >= 1
        assert loaded["cases"]
        assert loaded["standards"]["records"]


class TestMenuEntry:
    def test_tools_menu_has_evidence_view(self, main_window):
        tools_menu = next(action.menu() for action in main_window.menuBar().actions()
                          if "工具" in action.text())
        texts = [action.text() for action in tools_menu.actions()]
        assert any("证据视图" in text for text in texts)


class TestWorkbenchExchange:
    @staticmethod
    def _host():
        from PySide6.QtWidgets import QWidget

        from core.measurement_store import MeasurementStore
        from core.project_context import ProjectContext

        class _Host(QWidget):
            def __init__(self):
                super().__init__()
                self.ledger = EvidenceLedger()
                self.ledger.append("analysis_run", object_refs=["tab:2"],
                                   payload={"analysis_type": "capability"})
                self.analyses = {
                    2: {"analysis_type": "正态过程能力", "params": {"column": "cycle"},
                        "result": {"cpk": 1.2},
                        "credential": make_credential(
                            "cap@1", {"usl": 33}, df=pd.DataFrame(
                                {"cycle": [31.0, 32.0, 33.0]})).to_dict()},
                }
                self.project_context = ProjectContext()
                self.measurement_store = MeasurementStore()
                self.current_data = {
                    "file_path": "/tmp/line_a.xlsx",
                    "raw_data": {"工时": pd.DataFrame({"cycle": [31.0, 32.0, 33.0]})},
                }
                self._ledger_failures = 0

            def _analysis_source_frame(self, idx):
                return self.current_data["raw_data"]["工时"]

            def _ledger_append(self, event_type, **kwargs):
                return self.ledger.append(event_type, **kwargs)

        return _Host()

    def test_export_evidence_pack_action(self, tmp_path, monkeypatch):
        from PySide6.QtWidgets import QFileDialog, QMessageBox

        from core.case_workflow import CaseWorkflow
        from core.evidence_pack import verify_evidence_pack
        from ui.dialogs.case_workflow_dialog import CaseWorkflowDialog

        path = str(tmp_path / "evidence.zip")
        monkeypatch.setattr(QFileDialog, "getSaveFileName",
                            staticmethod(lambda *a, **k: (path, "")))
        monkeypatch.setattr(QMessageBox, "information",
                            staticmethod(lambda *a, **k: None))
        monkeypatch.setattr(QMessageBox, "warning",
                            staticmethod(lambda *a, **k: None))
        host = self._host()
        dialog = CaseWorkflowDialog(CaseWorkflow(title="交换"), host)
        try:
            dialog._on_export_evidence_pack()
            assert verify_evidence_pack(path)["ok"] is True
            assert any(event.event_type == "evidence_pack_exported"
                       for event in host.ledger.events)
        finally:
            dialog.close()

    def test_export_share_pack_action(self, tmp_path, monkeypatch):
        from PySide6.QtWidgets import QFileDialog, QMessageBox

        from core.case_workflow import CaseWorkflow
        from ui.dialogs.case_workflow_dialog import CaseWorkflowDialog

        path = str(tmp_path / "share.zip")
        monkeypatch.setattr(QFileDialog, "getSaveFileName",
                            staticmethod(lambda *a, **k: (path, "")))
        monkeypatch.setattr(QMessageBox, "information",
                            staticmethod(lambda *a, **k: None))
        monkeypatch.setattr(QMessageBox, "warning",
                            staticmethod(lambda *a, **k: None))
        host = self._host()
        dialog = CaseWorkflowDialog(CaseWorkflow(title="交换"), host)
        try:
            dialog._on_export_share_pack()
            assert os.path.exists(path)
            assert any(event.event_type == "share_pack_exported"
                       for event in host.ledger.events)
        finally:
            dialog.close()
