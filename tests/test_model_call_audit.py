"""模型调度写入本机操作日志，回复可追溯输入、模型、配置和审计行。"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from core.agent.engine import AgentEngine, AgentReply
from core.agent.tools import AgentContext, ToolRegistry, ToolResult, ToolSpec
from core.audit import MODEL_CALL_ACTION, read_log, record_model_call
from core import audit as audit_module


def _registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(ToolSpec(
        name="echo", title="echo", description="echo",
        handler=lambda context, **kwargs: ToolResult(name="echo", ok=True, text="ok"),
    ))
    return registry


class _LLM:
    def __init__(self, script=None, *, fail=False):
        self.script = list(script or ["直接回答。"])
        self.fail = fail
        self.available = True
        self.provider = "ollama"
        self.model = "gpt-test"
        self.protocol = "ollama"
        self.api_base = "http://127.0.0.1:11434?api_key=super-secret"
        self.api_key = "sk-live-secret"
        self.prompts = []

    def config_summary(self):
        return {
            "provider": self.provider,
            "label": "Ollama",
            "protocol": self.protocol,
            "model": self.model,
            "api_base": self.api_base,
            "available": True,
            "key": "sk-***ret",
        }

    def generate(self, prompt):
        self.prompts.append(prompt)
        if self.fail:
            raise RuntimeError("connection refused")
        text = self.script.pop(0) if self.script else "（无更多脚本）"
        yield text


@pytest.fixture
def log_file(tmp_path, monkeypatch):
    target = tmp_path / "audit.log"
    monkeypatch.setattr(audit_module, "LOG_FILE", str(target))
    return target


def test_record_strips_secrets_and_keeps_trace(log_file):
    recorded = record_model_call(
        "user",
        question="  用当前数据\n做能力分析  ",
        model="gpt-test",
        config={
            "provider": "openai",
            "label": "OpenAI 兼容",
            "protocol": "openai",
            "model": "gpt-test",
            "api_base": "https://example.test/v1?api_key=super-secret",
            "available": True,
            "key": "sk-***ret",
        },
        outcome="ok",
        elapsed_ms=12.34,
        tools=["echo"],
    )
    text = log_file.read_text(encoding="utf-8")
    assert text.strip() == recorded.line
    assert recorded.input == "用当前数据 做能力分析"
    assert recorded.model == "gpt-test"
    assert recorded.config["api_base"] == "https://example.test/v1"
    assert "key" not in recorded.config
    assert "super-secret" not in text
    assert "sk-" not in text
    assert "OpenAI 兼容" in text
    assert _line_is_model_call(text)
    assert read_log(action=MODEL_CALL_ACTION) == [recorded.line]
    assert read_log(action="import_data") == []


def test_long_input_is_truncated(log_file):
    question = "问" * 400
    recorded = record_model_call("user", question=question, model="m", config={})
    assert len(recorded.input) < len(question)
    assert recorded.input.endswith("…")
    assert question not in log_file.read_text(encoding="utf-8")


def test_online_reply_is_traceable_without_touching_as_dict(log_file):
    llm = _LLM(["结论: 过程受控。"])
    engine = AgentEngine(_registry(), llm=llm, context=AgentContext())
    reply = engine.respond("什么是 Cpk")
    assert reply.offline is False
    trace = reply.trace()
    assert trace["input"] == "什么是 Cpk"
    assert trace["model"] == "gpt-test"
    assert trace["config"]["provider"] == "ollama"
    assert trace["config"]["api_base"] == "http://127.0.0.1:11434"
    assert "key" not in trace["config"]
    assert trace["audit_record"] == reply.audit_record
    assert reply.audit_record in log_file.read_text(encoding="utf-8")
    assert "super-secret" not in reply.audit_record
    assert set(reply.as_dict()) == {
        "text", "offline", "provider", "model", "elapsed_ms", "tool_calls",
    }
    for key in ("input", "config", "audit_record"):
        assert key not in reply.as_dict()


def test_fallback_still_records_the_attempt(log_file):
    engine = AgentEngine(_registry(), llm=_LLM(fail=True), context=AgentContext())
    reply = engine.respond("今天天气怎么样")
    assert reply.offline is True
    assert reply.model == "gpt-test"
    assert "outcome='fallback'" in reply.audit_record
    assert reply.input == "今天天气怎么样"
    assert reply.config["protocol"] == "ollama"


def test_offline_and_refused_calls_are_not_model_audits(log_file):
    engine = AgentEngine(_registry(), context=AgentContext())
    reply = engine.respond("有哪些数据表")
    assert reply.audit_record == ""
    assert reply.trace()["config"] == {}

    llm = _LLM(["不应被调用"])
    forced = AgentEngine(_registry(), llm=llm, context=AgentContext())
    forced.force_offline = True
    refused = forced.respond("什么是 Cpk")
    assert refused.offline is True
    assert refused.audit_record == ""
    assert llm.prompts == []
    assert not log_file.exists()


def test_audit_write_failure_does_not_break_the_reply(log_file, monkeypatch):
    monkeypatch.setattr(audit_module, "LOG_FILE", str(log_file.parent))  # 目录不可当文件写
    before = audit_module.write_failures()
    llm = _LLM(["仍然回答。"])
    engine = AgentEngine(_registry(), llm=llm, context=AgentContext())
    reply = engine.respond("什么是 Cpk")
    assert "仍然回答" in reply.text
    assert reply.input == "什么是 Cpk"
    assert reply.model == "gpt-test"
    assert reply.audit_record
    assert "model_call" in reply.audit_record
    assert audit_module.write_failures() == before + 1


def test_sdk_envelope_does_not_carry_call_audit():
    from akia_sdk.client import SDK_API_VERSION, SDKResult

    data = SDKResult(tool="list_data", ok=True).as_dict()
    assert data["schema_version"] == "1.0"
    assert data["sdk_api_version"] == SDK_API_VERSION == "1.0"
    for key in ("input", "config", "audit_record", "audit"):
        assert key not in data


def test_menu_and_dialog_show_local_records(log_file, _qt_application):
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QDialog

    from ui.dialogs.model_call_audit_dialog import ModelCallAuditDialog
    from ui.main_window import MainWindow

    record_model_call("user", question="菜单里能看到", model="gpt-test",
                      config={"provider": "openai", "model": "gpt-test"})
    window = MainWindow()
    try:
        ai_menu = next(action.menu() for action in window.menuBar().actions()
                       if "QAM Harness" in action.text())
        labels = [action.text() for action in ai_menu.actions()]
        assert "调用审计" in labels
        entries = window._build_command_entries()
        match = next(entry for entry in entries if entry["label"] == "调用审计")
        assert match["kind"] == "action"
        assert match["category"] == "Agent"

        dialog = ModelCallAuditDialog(window)
        assert "菜单里能看到" in dialog.view.toPlainText()
        assert "gpt-test" in dialog.view.toPlainText()
        dialog.reload()
        assert dialog.count_label.text().startswith("1")
        dialog.close()
    finally:
        window.close()

    # 菜单动作本身能打开对话框；exec 被桩掉后不应抛错。
    window = MainWindow()
    try:
        opened = []

        def _exec(self):
            opened.append(type(self).__name__)
            return QDialog.DialogCode.Rejected

        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(QDialog, "exec", _exec)
        try:
            window._on_model_call_audit()
        finally:
            monkeypatch.undo()
        assert "ModelCallAuditDialog" in opened
    finally:
        window.close()


def _line_is_model_call(text: str) -> bool:
    line = text.strip()
    return f": {MODEL_CALL_ACTION} " in line


def test_manual_reply_trace_defaults_empty():
    reply = AgentReply(text="ok")
    assert reply.trace() == {
        "input": "", "model": "", "config": {}, "audit_record": "",
    }
