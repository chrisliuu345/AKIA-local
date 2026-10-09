"""案例持久化与 UI 入口测试（v4.3.0 B1-3/B1-4）。"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pandas as pd
import pytest

from core.case_workflow import CaseWorkflow
from core.project_manager import ProjectManager


@pytest.fixture
def main_window():
    pytest.importorskip("PySide6")
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


class TestCasePersistence:
    def test_save_project_includes_cases(self, main_window, tmp_path, monkeypatch):
        from PySide6.QtWidgets import QFileDialog, QMessageBox

        from core.measurement_event import MeasurementEvent

        workflow = main_window._create_case_from_current_data()
        main_window.measurement_store.add(
            MeasurementEvent.from_manual(1.0, characteristic_id="QC-1"))
        path = str(tmp_path / "case_project.qap")
        monkeypatch.setattr(QFileDialog, "getSaveFileName",
                            staticmethod(lambda *a, **k: (path, "")))
        monkeypatch.setattr(QMessageBox, "information",
                            staticmethod(lambda *a, **k: None))
        main_window._on_save_project()

        project = ProjectManager.load_project(path)
        assert project["manifest"]["case_count"] == 1
        assert project["manifest"]["measurement_count"] == 1
        assert project["measurements"][0]["characteristic_id"] == "QC-1"
        assert project["cases"][0]["case"]["id"] == workflow.case.id
        assert project["cases"][0]["case"]["schema_version"] == "1"
        assert project["cases"][0]["case"]["steps"][0]["phase"] == "baseline"

    def test_load_project_restores_cases(self, main_window, tmp_path, monkeypatch):
        from PySide6.QtWidgets import QFileDialog, QMessageBox

        from core.measurement_event import MeasurementEvent
        from core.measurement_store import MeasurementStore

        workflow = CaseWorkflow(title="恢复案例", product="A100", owner="张三")
        workflow.record_step("baseline", {"mean": 32.0}, data_ref="sheet:工时")
        path = str(tmp_path / "restore.qap")
        ProjectManager.save_project(
            path, {"工时": pd.DataFrame({"cycle": [31.0]})}, {}, {},
            cases=[workflow.to_dict()],
            measurements=MeasurementStore([
                MeasurementEvent.from_manual(31.0, characteristic_id="cycle")]))

        monkeypatch.setattr(QFileDialog, "getOpenFileName",
                            staticmethod(lambda *a, **k: (path, "")))
        monkeypatch.setattr(QMessageBox, "information",
                            staticmethod(lambda *a, **k: None))
        main_window._on_load_project()

        assert len(main_window.case_workflows) == 1
        restored = main_window.case_workflows[0]
        assert restored.case.id == workflow.case.id
        assert restored.owner == "张三"
        assert restored.case.steps[0]["phase"] == "baseline"
        assert main_window._last_case_workflow is restored
        assert len(main_window.measurement_store) == 1
        assert main_window.measurement_store.events[0].characteristic_id == "cycle"

    def test_load_project_skips_broken_case(self, main_window, tmp_path, monkeypatch):
        from PySide6.QtWidgets import QFileDialog, QMessageBox

        path = str(tmp_path / "broken.qap")
        ProjectManager.save_project(
            path, {"S": pd.DataFrame({"x": [1]})}, {}, {},
            cases=[{"bogus": True}, CaseWorkflow(title="好案例").to_dict()])
        monkeypatch.setattr(QFileDialog, "getOpenFileName",
                            staticmethod(lambda *a, **k: (path, "")))
        monkeypatch.setattr(QMessageBox, "information",
                            staticmethod(lambda *a, **k: None))
        main_window._on_load_project()
        assert [w.case.title for w in main_window.case_workflows] == ["好案例"]

    def test_legacy_case_roundtrip_through_project(self, tmp_path):
        legacy = {"schema_version": "0", "id": "CASE-OLD", "title": "旧案例",
                  "steps": [{"phase": "baseline", "ref": "sheet:旧",
                             "note": "", "at": "2026-01-01T00:00:00"}]}
        path = str(tmp_path / "legacy_case.qap")
        ProjectManager.save_project(path, {"S": pd.DataFrame({"x": [1]})}, {}, {},
                                    cases=[legacy])
        project = ProjectManager.load_project(path)
        restored = CaseWorkflow.from_dict(project["cases"][0])
        assert restored.case.id == "CASE-OLD"
        assert restored.case.schema_version == "1"

    def test_shared_project_keeps_cases_and_context(self, tmp_path, monkeypatch):
        from core import project_manager as pm
        from core.measurement_event import MeasurementEvent
        from core.measurement_store import MeasurementStore
        from core.project_context import ProjectContext

        monkeypatch.setattr(pm, "SHARED_DIR", str(tmp_path / "shared"))
        workflow = CaseWorkflow(title="共享案例", owner="质量部")
        workflow.record_step("baseline", {"mean": 1.0}, data_ref="sheet:x")
        context = ProjectContext(project_name="共享项目")
        standard = context.record_specification(
            "QC-1", usl=10.1, lsl=9.9, change_reason="共享初始版本")
        measurements = MeasurementStore([
            MeasurementEvent.from_manual(1.0, characteristic_id="QC-1")])
        pm.SharedProjectManager.save_shared(
            "shared.qap", {"S": pd.DataFrame({"x": [1.0]})}, {}, {},
            "公共", "", project_context=context.to_dict(),
            cases=[workflow.to_dict()], standards=context.standards.to_dict(),
            measurements=measurements.to_dicts())
        loaded = pm.SharedProjectManager.load_shared(
            str(tmp_path / "shared" / "公共" / "shared.qap"))
        assert loaded["cases"][0]["case"]["id"] == workflow.case.id
        assert loaded["project_context"]["project_name"] == "共享项目"
        assert loaded["standards"]["records"][0]["record_id"] == standard.record_id
        assert loaded["manifest"]["measurement_count"] == 1


class TestCaseCenterUi:
    def test_menu_actions_exist(self, main_window):
        tools_menu = next(action.menu() for action in main_window.menuBar().actions()
                          if "工具" in action.text())
        texts = [action.text() for action in tools_menu.actions()]
        assert any("改善案例工作台" in text for text in texts)
        assert any("改善案例中心" in text for text in texts)

    def test_home_card_opens_case_center(self, main_window, monkeypatch):
        from ui.dialogs import case_center_dialog as module

        opened = {}

        class _FakeDialog:
            Accepted = 1

            def __init__(self, workflows, parent=None, create_callback=None):
                opened["workflows"] = list(workflows)

            def exec(self):
                return 0

            def selected_workflow(self):
                return None

        monkeypatch.setattr(module, "CaseCenterDialog", _FakeDialog)
        main_window.welcome_page.case_center_clicked.emit()
        assert opened["workflows"] == main_window.case_workflows

    def test_center_lists_and_selects(self):
        pytest.importorskip("PySide6")
        from ui.dialogs.case_center_dialog import CaseCenterDialog

        first = CaseWorkflow(title="案例一")
        second = CaseWorkflow(title="案例二", owner="李四")
        dialog = CaseCenterDialog([first, second])
        try:
            assert dialog.table.rowCount() == 2
            dialog.table.selectRow(1)
            assert dialog.selected_workflow() is second
            assert dialog.open_button.isEnabled()
        finally:
            dialog.close()

    def test_workbench_actions_enabled_with_host_data(self):
        pytest.importorskip("PySide6")
        from PySide6.QtWidgets import QWidget

        from ui.dialogs.case_workflow_dialog import CaseWorkflowDialog

        class _Host(QWidget):
            def __init__(self):
                super().__init__()
                self.current_data = {"raw_data": {"S": pd.DataFrame({"x": [1.0]})}}
                self.analyses = {1: {"analysis_type": "时间研究", "params": {},
                                     "result": {"summary": {"n": 1}}}}

        workflow = CaseWorkflow(title="工作台")
        dialog = CaseWorkflowDialog(workflow, _Host())
        try:
            assert dialog.record_button.isEnabled()
            assert dialog.analysis_button.isEnabled()
            assert dialog.pair_button.isEnabled()
            text = dialog.browser.toPlainText()
            assert "关闭门禁" in text
        finally:
            dialog.close()

    def test_workbench_pair_test_action(self, monkeypatch):
        pytest.importorskip("PySide6")
        from PySide6.QtWidgets import QInputDialog, QWidget

        from ui.dialogs.case_workflow_dialog import CaseWorkflowDialog

        class _Host(QWidget):
            def __init__(self):
                super().__init__()
                self.current_data = {"raw_data": {"S": pd.DataFrame({
                    "before": [32.0, 31.0, 33.0, 30.0],
                    "after": [28.0, 27.0, 29.0, 26.0]})}}
                self.analyses = {}

        answers = iter([("before", True), ("after", True)])
        monkeypatch.setattr(QInputDialog, "getItem",
                            staticmethod(lambda *a, **k: next(answers)))
        dialog = CaseWorkflowDialog(CaseWorkflow(title="配对"), _Host())
        try:
            dialog._on_paired_test()
            phases = [step["phase"] for step in dialog.workflow.case.steps]
            assert phases == ["paired_test"]
            assert dialog.workflow.case.steps[0]["result"]["p_value"] < 0.01
        finally:
            dialog.close()

    def test_workbench_manual_measurement_action(self, monkeypatch):
        pytest.importorskip("PySide6")
        from PySide6.QtWidgets import QInputDialog, QWidget

        from core.measurement_store import MeasurementStore
        from ui.dialogs.case_workflow_dialog import CaseWorkflowDialog

        class _Host(QWidget):
            def __init__(self):
                super().__init__()
                self.current_data = {}
                self.analyses = {}
                self.measurement_store = MeasurementStore()

        monkeypatch.setattr(QInputDialog, "getDouble",
                            staticmethod(lambda *a, **k: (1.5, True)))
        monkeypatch.setattr(QInputDialog, "getText",
                            staticmethod(lambda *a, **k: ("cycle", True)))
        monkeypatch.setattr(QInputDialog, "getItem",
                            staticmethod(lambda *a, **k: ("复测", True)))

        host = _Host()
        dialog = CaseWorkflowDialog(CaseWorkflow(title="手工测量"), host)
        try:
            dialog._on_manual_measurement()
            assert len(host.measurement_store) == 1
            event = host.measurement_store.events[0]
            assert event.source_kind == "manual"
            assert event.characteristic_id == "cycle"
            step = dialog.workflow.case.steps[0]
            assert step["phase"] == "remeasure"
            assert step["measurement_refs"] == [event.event_id]
        finally:
            dialog.close()

    def test_workbench_file_measurement_action(self, monkeypatch):
        pytest.importorskip("PySide6")
        from PySide6.QtWidgets import QInputDialog, QWidget

        from core.measurement_store import MeasurementStore
        from ui.dialogs.case_workflow_dialog import CaseWorkflowDialog

        class _Host(QWidget):
            def __init__(self):
                super().__init__()
                self.current_data = {"raw_data": {"工时": pd.DataFrame(
                    {"cycle": [32.0, 31.5, 32.5]})}}
                self.analyses = {}
                self.measurement_store = MeasurementStore()

        answers = iter([("基线测量", True), ("", True)])
        monkeypatch.setattr(QInputDialog, "getItem",
                            staticmethod(lambda *a, **k: next(answers)))
        monkeypatch.setattr(QInputDialog, "getText",
                            staticmethod(lambda *a, **k: ("", True)))

        host = _Host()
        dialog = CaseWorkflowDialog(CaseWorkflow(title="文件测量"), host)
        try:
            dialog._on_record_current()
            assert len(host.measurement_store) == 1
            event = host.measurement_store.events[0]
            assert event.source_kind == "file"
            assert event.channel == "工时"
            assert event.raw_ref == "sheet://工时"
            step = dialog.workflow.case.steps[0]
            assert step["phase"] == "baseline"
            assert step["measurement_refs"] == [event.event_id]
        finally:
            dialog.close()

    def test_workbench_plugin_measurement_action(self, monkeypatch):
        pytest.importorskip("PySide6")
        from PySide6.QtWidgets import QInputDialog, QWidget

        from core.measurement_event import MeasurementEvent
        from core.measurement_store import MeasurementStore
        from core.plugin_manager import PluginManager
        from ui.dialogs.case_workflow_dialog import CaseWorkflowDialog

        class _Host(QWidget):
            def __init__(self):
                super().__init__()
                self.current_data = {}
                self.analyses = {}
                self.measurement_store = MeasurementStore()

        class _Record:
            id = "vision"
            name = "视觉插件"

        event = MeasurementEvent.from_manual(2.0, characteristic_id="cycle")
        monkeypatch.setattr(PluginManager, "discover", lambda self, *a, **k: self)
        monkeypatch.setattr(PluginManager, "data_source_plugins",
                            lambda self: [_Record()])
        monkeypatch.setattr(PluginManager, "collect_measurements",
                            lambda self, context=None, timeout_s=None: [event])
        monkeypatch.setattr(QInputDialog, "getItem",
                            staticmethod(lambda *a, **k: ("基线测量", True)))

        host = _Host()
        dialog = CaseWorkflowDialog(CaseWorkflow(title="插件测量"), host)
        try:
            dialog._on_plugin_measurements()
            assert len(host.measurement_store) == 1
            step = dialog.workflow.case.steps[0]
            assert step["phase"] == "baseline"
            assert step["measurement_refs"] == [event.event_id]
            assert "plugin:视觉插件" == step["ref"]
        finally:
            dialog.close()

    def test_workbench_connector_measurement_action(self, monkeypatch):
        pytest.importorskip("PySide6")
        from PySide6.QtWidgets import QInputDialog, QWidget

        from core.measurement_event import MeasurementEvent
        from core.measurement_store import MeasurementStore
        from ui.dialogs.case_workflow_dialog import CaseWorkflowDialog

        class _Host(QWidget):
            def __init__(self):
                super().__init__()
                self.current_data = {}
                self.analyses = {}
                self.measurement_store = MeasurementStore()

            def connector_topics(self):
                return ["dev-1"]

            def recent_measurements(self, topic, n=1000):
                return [MeasurementEvent.from_manual(3.0, device=topic)]

        answers = iter([("dev-1", True), ("复测", True)])
        monkeypatch.setattr(QInputDialog, "getItem",
                            staticmethod(lambda *a, **k: next(answers)))

        host = _Host()
        dialog = CaseWorkflowDialog(CaseWorkflow(title="连接器测量"), host)
        try:
            dialog._on_connector_measurements()
            assert len(host.measurement_store) == 1
            step = dialog.workflow.case.steps[0]
            assert step["ref"] == "connector:dev-1"
            assert step["measurement_refs"] == [
                host.measurement_store.events[0].event_id]
        finally:
            dialog.close()
