"""智能辅助与模型审计 UI 回归。"""
import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pandas as pd
import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from core.agent.audit import ModelCallAudit
from core.agent.engine import AgentEngine
from core.agent.tools import AgentContext, build_default_registry


class _LLM:
    available = True
    provider = "ollama"
    protocol = "ollama"
    model = "fake"
    api_base = "http://localhost:11434"

    def generate(self, prompt):
        yield "4 分，需人工确认"


def _pump(worker):
    app = QApplication.instance()
    deadline = time.time() + 10
    while time.time() < deadline:
        app.processEvents()
        if worker is None or not worker.isRunning():
            app.processEvents()
            return
        time.sleep(0.02)
    raise AssertionError("智能辅助 worker 超时")


def test_assistance_button_runs_advisory_flow(tmp_path, _qt_application):
    from ui.dialogs.llm_dialog import QAMHarnessDialog

    audit = ModelCallAudit(tmp_path / "audit.jsonl")
    context = AgentContext(
        data_frames={"S": pd.DataFrame({"x": [1, 2]})},
        analyses={2: {"analysis_type": "capability", "params": {},
                      "result": {"cpk": 1.2}, "credential": {"rule_version": "cap"}}})
    engine = AgentEngine(build_default_registry(context), llm=_LLM(), context=context,
                         audit_sink=audit, assistance_enabled=lambda: True)
    dialog = QAMHarnessDialog(None, engine=engine)
    try:
        dialog._send_assistance("online_scoring")
        _pump(dialog.worker)
        text = dialog.chat_view.toPlainText()
        assert "4 分" in text
        assert "统计判定未修改" in text
        assert audit.records()[0]["kind"] == "online_scoring"
    finally:
        dialog.close()
        dialog.deleteLater()


def test_model_audit_dialog_lists_and_exports(tmp_path, monkeypatch, _qt_application):
    from ui.dialogs.model_audit_dialog import ModelAuditDialog

    audit = ModelCallAudit(tmp_path / "audit.jsonl")
    audit.record({"kind": "chat", "status": "completed", "config": {"model": "fake"},
                  "input": {"question": "test"}})
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))
    dialog = ModelAuditDialog(audit)
    try:
        assert dialog.table.rowCount() == 1
        assert "test" in dialog.detail.toPlainText()
        target = tmp_path / "export.json"
        monkeypatch.setattr(QFileDialog, "getSaveFileName",
                            staticmethod(lambda *a, **k: (str(target), "json")))
        dialog._export()
        assert target.exists()
    finally:
        dialog.close()
        dialog.deleteLater()
