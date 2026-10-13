"""量具在线监控 UI 接线测试（v4.4.0 B2，离屏）。"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pandas as pd
import pytest

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


def _set_policy(window, gauge_id="caliper:value", expected=10.0, window_n=50,
                drift_rule=None):
    from core.gauge_study import GaugeStudyPolicy

    window.gauge_monitor.set_policy(GaugeStudyPolicy(
        gauge_id=gauge_id, expected_value=expected, window_n=window_n,
        drift_rule=drift_rule if drift_rule is not None
        else {"bias_limit": 0.1}))


class TestMainWindowWiring:
    def test_submit_goes_through_store_and_monitor(self, main_window):
        _set_policy(main_window)
        outcome = main_window._submit_gauge_measurement("caliper:value", 10.02)
        assert outcome is not None
        assert outcome.gauge_id == "caliper:value"
        assert len(main_window.measurement_store) == 1
        event = list(main_window.measurement_store)[0]
        assert event.characteristic_id == "caliper:value"
        assert main_window.gauge_monitor.event_ids_for(
            "caliper:value") == [event.event_id]
        types = [item.event_type for item in main_window.ledger.events]
        assert "measurement_recorded" in types

    def test_drift_prompt_records_and_cools_down(self, main_window, tmp_path):
        from core.streaming.alert_journal import AlertJournal

        main_window._alert_journal = AlertJournal(str(tmp_path / "alerts.jsonl"))
        _set_policy(main_window)
        first = main_window._submit_gauge_measurement("caliper:value", 10.5)
        assert first.state == "drift" and first.prompt is True
        assert "量具漂移提示" in main_window.statusBar().currentMessage()
        types = [item.event_type for item in main_window.ledger.events]
        assert types.count("gauge_drift_alerted") == 1
        entries = main_window._get_alert_journal().entries()
        assert any(entry.kind == "gauge_drift" for entry in entries)
        # 冷却窗口内不重复提示/记账
        second = main_window._submit_gauge_measurement("caliper:value", 10.6)
        assert second.state == "drift" and second.prompt is False
        types = [item.event_type for item in main_window.ledger.events]
        assert types.count("gauge_drift_alerted") == 1

    def test_project_roundtrip_restores_monitor(self, main_window, tmp_path,
                                                monkeypatch):
        from PySide6.QtWidgets import QFileDialog, QMessageBox

        from core.project_manager import ProjectManager

        monkeypatch.setattr(QMessageBox, "information",
                            staticmethod(lambda *a, **k: None))
        _set_policy(main_window, window_n=50, drift_rule={"bias_limit": 1.0})
        for value in (10.0, 10.001, 10.002):
            main_window._submit_gauge_measurement("caliper:value", value)
        path = str(tmp_path / "gauge.qap")
        monkeypatch.setattr(
            QFileDialog, "getSaveFileName",
            staticmethod(lambda *a, **k: (path, "")))
        main_window._on_save_project()
        project = ProjectManager.load_project(path)
        assert project["gauge_studies"]["studies"][0]["gauge_id"] == "caliper:value"
        main_window._apply_loaded_project(project, path)
        restored = main_window.gauge_monitor
        assert restored.policies["caliper:value"].window_n == 50
        assert restored.states["caliper:value"].n == 3
        assert restored.frame_for("caliper:value") is not None
        assert main_window._last_gauge_outcome == {}

    def test_gauge_event_ids_referencable_by_case(self, main_window):
        _set_policy(main_window)
        first = main_window._submit_gauge_measurement("caliper:value", 10.0)
        second = main_window._submit_gauge_measurement("caliper:value", 10.01)
        refs = main_window.gauge_monitor.event_ids_for("caliper:value")
        assert refs == [first.event_id, second.event_id]
        from core.case_workflow import CaseWorkflow

        workflow = CaseWorkflow(title="案例引用 gauge 事件")
        frame = pd.DataFrame({"x": [10.0, 10.01]})
        workflow.record_step("baseline", {"n": 2}, frame=frame,
                             measurement_refs=refs)
        step = workflow.case.steps[0]
        assert step["measurement_refs"] == refs
        assert main_window.measurement_store.get(refs[0]) is not None


class TestMsaTabEntry:
    def test_tab_receives_monitor_and_opens_dialog(self, main_window,
                                                   monkeypatch):
        from ui.dialogs import gauge_online_dialog as module

        tab = main_window._lazy_load_tab(3)  # MSA Tab
        assert tab is not None
        assert tab._gauge_monitor is main_window.gauge_monitor
        captured = {}

        class _FakeDialog:
            def __init__(self, monitor, parent=None, submit_measurement=None):
                captured["monitor"] = monitor
                captured["submit"] = submit_measurement

            def exec(self):
                return 0

        monkeypatch.setattr(module, "GaugeOnlineDialog", _FakeDialog)
        tab._open_gauge_online()
        assert captured["monitor"] is main_window.gauge_monitor
        assert captured["submit"] == main_window._submit_gauge_measurement


class TestDialogFlow:
    def test_policy_save_and_record(self, main_window):
        from ui.dialogs.gauge_online_dialog import GaugeOnlineDialog

        dialog = GaugeOnlineDialog(
            main_window.gauge_monitor, None,
            submit_measurement=main_window._submit_gauge_measurement)
        try:
            dialog.gauge_id_edit.setText("mic:size")
            dialog.expected_spin.setValue(5.0)
            dialog.window_spin.setValue(5)
            dialog.bias_limit_edit.setText("0.05")
            dialog._on_save_policy()
            policy = main_window.gauge_monitor.policies["mic:size"]
            assert policy.expected_value == 5.0
            assert policy.drift_rule["bias_limit"] == 0.05
            outcome = dialog._record_value(5.01)
            assert outcome is not None and outcome.gauge_id == "mic:size"
            assert "mic:size" in dialog.status_label.text()
            drifting = dialog._record_value(5.5)
            assert drifting.state == "drift"
            assert "漂移" in dialog.status_label.text()
        finally:
            dialog.close()

    def test_invalid_form_rejected(self, main_window, monkeypatch):
        from PySide6.QtWidgets import QMessageBox

        from ui.dialogs.gauge_online_dialog import GaugeOnlineDialog

        warnings = []
        monkeypatch.setattr(QMessageBox, "warning",
                            staticmethod(lambda *a, **k: warnings.append(a)))
        dialog = GaugeOnlineDialog(main_window.gauge_monitor, None)
        try:
            dialog.gauge_id_edit.setText(" ")
            dialog._on_save_policy()
            assert warnings, "空量具 ID 应告警"
            dialog.gauge_id_edit.setText("g1")
            dialog.bias_limit_edit.setText("abc")
            dialog._on_save_policy()
            assert len(warnings) == 2
            assert "g1" not in main_window.gauge_monitor.policies
        finally:
            dialog.close()
