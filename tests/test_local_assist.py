"""本机评分与异常辅助：默认关闭，启用后只引用已有判定并写入操作日志。"""
import copy
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from core import audit as audit_module
from core.audit import LOCAL_ASSIST_ACTION, MODEL_CALL_ACTION, read_log
from core.local_assist import LOCAL_METHOD, advise


@pytest.fixture
def log_file(tmp_path, monkeypatch):
    target = tmp_path / "audit.log"
    monkeypatch.setattr(audit_module, "LOG_FILE", str(target))
    return target


def _analysis():
    return {
        "analysis_type": "I-MR",
        "result": {
            "capability": {"cpk": 1.45, "grade": "A (良好)"},
            "i_chart": {
                "cl": 5.0,
                "violations": [{"point": 3, "desc": "一点超出3σ控制限", "value": 9.0}],
            },
        },
    }


def test_disabled_assistance_does_not_audit(log_file):
    entry = _analysis()
    before = copy.deepcopy(entry)
    result = advise(enabled=False, analyses=[entry], alerts=[{"ack": False, "desc": "超差"}],
                    question="看一下")
    assert result.enabled is False
    assert result.confirmed is False
    assert result.audit_record == ""
    assert result.trace() == {
        "input": "", "model": "",
        "config": {"enabled": False, "external_model": False, "method": LOCAL_METHOD},
        "audit_record": "",
    }
    assert entry == before
    assert not log_file.exists()


def test_enabled_advice_quotes_judgement_and_records_local_method(log_file):
    entry = _analysis()
    before = copy.deepcopy(entry)
    alert = {"id": "a1", "ack": False, "device": "L1", "channel": "厚度", "desc": "超差"}
    result = advise(enabled=True, analyses={"2": entry}, alerts=[alert],
                    question="看厚度", )
    assert entry == before
    assert alert["ack"] is False
    assert result.confirmed is False
    assert result.advisory is True
    assert "A (良好)" in result.text
    assert "1.45" in result.text
    assert "一点超出3σ控制限" in result.text
    assert "不替代统计判定" in result.text
    assert "不会代为确认" in result.text
    assert "外部模型" in result.text
    trace = result.trace()
    assert set(trace) == {"input", "model", "config", "audit_record"}
    assert trace["input"] == "看厚度"
    assert trace["model"] == LOCAL_METHOD
    assert trace["config"]["external_model"] is False
    assert trace["config"]["advisory"] is True
    assert trace["audit_record"] == result.audit_record
    assert result.audit_record in log_file.read_text(encoding="utf-8")
    assert f": {LOCAL_ASSIST_ACTION} " in result.audit_record
    assert "method='local:spc-alerts'" in result.audit_record
    assert " model=" not in result.audit_record
    assert MODEL_CALL_ACTION not in result.audit_record
    assert read_log(action=LOCAL_ASSIST_ACTION) == [result.audit_record]
    assert read_log(action=MODEL_CALL_ACTION) == []


def test_missing_grade_is_not_invented(log_file):
    entry = {"analysis_type": "能力", "result": {"capability": {"cpk": 0.5}}}
    result = advise(enabled=True, analyses=[entry], question="只有 Cpk")
    assert "0.5" in result.text
    assert "D (" not in result.text
    assert result.judgements[0]["cpk"] == 0.5
    assert "grade" not in result.judgements[0]


def test_acked_alert_is_left_alone(log_file):
    alert = {"ack": True, "desc": "已处理"}
    result = advise(enabled=True, analyses=[], alerts=[alert], question="告警")
    assert alert["ack"] is True
    assert "已处理" not in result.text
    assert "无未确认告警" in result.text
    assert result.config["alert_count"] == 0


def test_secret_fields_are_not_written(log_file):
    from core.audit import record_local_run

    recorded = record_local_run(
        "user", question="检查", method="spc-alerts",
        config={"key": "sk-live-secret", "api_key": "super-secret", "enabled": True,
                "violations": 1})
    text = log_file.read_text(encoding="utf-8")
    assert recorded.method == "local:spc-alerts"
    assert recorded.config["external_model"] is False
    assert "key" not in recorded.config
    assert "sk-live" not in text
    assert "super-secret" not in text


def test_sdk_envelope_unchanged():
    from akia_sdk.client import SDK_API_VERSION, SDKResult

    data = SDKResult(tool="run_spc", ok=True).as_dict()
    assert data["schema_version"] == "1.0"
    assert data["sdk_api_version"] == SDK_API_VERSION == "1.0"
    for key in ("input", "config", "audit_record", "audit", "advisory"):
        assert key not in data


def test_menu_and_dialog_stay_off_until_enabled(log_file, monkeypatch, _qt_application):
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QDialog

    from ui.main_window import MainWindow

    saved = {}
    with monkeypatch.context() as patched:
        patched.setattr("config.settings.get_setting",
                        lambda key, default=None: saved.get(key, default))
        patched.setattr("config.settings.save_config", saved.update)
        _exercise_dialog(saved, log_file)

    window = MainWindow()
    try:
        tools = next(action.menu() for action in window.menuBar().actions()
                     if action.menu() is not None and "工具" in action.text())
        labels = [action.text() for action in tools.actions()]
        assert "评分与异常辅助" in labels
        match = next(entry for entry in window._build_command_entries()
                     if entry["label"] == "评分与异常辅助")
        assert match["kind"] == "action"
        opened = []

        def _exec(self):
            opened.append(type(self).__name__)
            return QDialog.DialogCode.Rejected

        monkeypatch.setattr(QDialog, "exec", _exec)
        window._on_local_assist()
        assert "LocalAssistDialog" in opened
    finally:
        window.close()


def _exercise_dialog(saved, log_file):
    from ui.dialogs.local_assist_dialog import LocalAssistDialog

    dialog = LocalAssistDialog(
        {"1": _analysis()},
        [{"ack": False, "desc": "超差", "device": "L1"}],
    )
    try:
        assert dialog.enable_box.isChecked() is False
        assert dialog.run_btn.isEnabled() is False
        dialog.run()
        assert dialog._last.audit_record == ""
        assert not log_file.exists()

        dialog.enable_box.setChecked(True)
        assert saved.get("local_assist_enabled") is True
        dialog.note_edit.setText("看厚度")
        dialog.run()
        assert "A (良好)" in dialog.view.toPlainText()
        assert "不代替人工确认" in dialog.view.toPlainText()
        assert dialog._last.model == LOCAL_METHOD
        assert log_file.read_text(encoding="utf-8")
    finally:
        dialog.close()
