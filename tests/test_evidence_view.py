"""证据视图测试（v4.3.0 B4-2，离屏）。"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pandas as pd
import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QMessageBox

from core.evidence import make_credential


@pytest.fixture(autouse=True)
def _silence_dialogs(monkeypatch):
    monkeypatch.setattr(QMessageBox, "information",
                        staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(QMessageBox, "warning",
                        staticmethod(lambda *a, **k: None))


@pytest.fixture
def scene():
    from core.evidence_ledger import EvidenceLedger

    frame = pd.DataFrame({"x": [1.0, 2.0, 3.0]})
    credential = make_credential("capability@1", {"usl": 10}, df=frame).to_dict()
    analyses = {
        2: {"analysis_type": "正态过程能力", "params": {"usl": 10},
            "result": {"cpk": 1.3}, "credential": credential,
            "_completed_at": "2026-10-08T10:00:00+08:00"},
        5: {"analysis_type": "手工分析", "params": {}, "result": {"ok": True}},
    }
    ledger = EvidenceLedger()
    ledger.append("analysis_run", actor="tester", object_refs=["tab:2"],
                  payload={"analysis_type": "正态过程能力"})
    return analyses, ledger, frame


class TestEvidenceView:
    def test_lists_conclusions_and_shows_credential(self, scene):
        from ui.dialogs.evidence_view_dialog import EvidenceViewDialog

        analyses, ledger, frame = scene
        dialog = EvidenceViewDialog(analyses, ledger, frame_provider=lambda idx: frame)
        try:
            assert dialog.list_widget.count() == 2
            dialog.list_widget.setCurrentRow(0)
            text = dialog.detail.toPlainText()
            assert "capability@1" in text
            assert "账本链校验通过" in text
            assert dialog.event_table.rowCount() >= 1
        finally:
            dialog.close()

    def test_missing_credential_marks_not_reviewable(self, scene):
        from ui.dialogs.evidence_view_dialog import EvidenceViewDialog

        analyses, ledger, _frame = scene
        dialog = EvidenceViewDialog(analyses, ledger)
        try:
            dialog.list_widget.setCurrentRow(1)
            assert "不可复核" in dialog.detail.toPlainText()
        finally:
            dialog.close()

    def test_tampered_ledger_is_reported(self, scene):
        from ui.dialogs.evidence_view_dialog import EvidenceViewDialog

        analyses, ledger, _frame = scene
        ledger.events[0].payload["analysis_type"] = "tampered"
        dialog = EvidenceViewDialog(analyses, ledger)
        try:
            dialog.list_widget.setCurrentRow(0)
            assert "校验失败" in dialog.detail.toPlainText()
        finally:
            dialog.close()

    def test_trace_locate_selects_match(self, scene):
        from core.evidence import credential_trace_code
        from ui.dialogs.evidence_view_dialog import EvidenceViewDialog

        analyses, ledger, _frame = scene
        trace = credential_trace_code([analyses[2]["credential"]])
        dialog = EvidenceViewDialog(analyses, ledger)
        try:
            dialog.trace_edit.setText(trace)
            dialog._locate_trace()
            assert dialog._selected_key() == 2
            dialog.trace_edit.setText("000000000000")
            dialog._locate_trace()
            assert dialog._selected_key() == 2  # 未命中不改变选择
        finally:
            dialog.close()

    def test_report_event_linked_by_trace(self, scene):
        from core.evidence import credential_trace_code
        from ui.dialogs.evidence_view_dialog import EvidenceViewDialog

        analyses, ledger, _frame = scene
        trace = credential_trace_code([analyses[2]["credential"]])
        ledger.append("report_exported", object_refs=[f"trace:{trace}"],
                      payload={"format": "pdf", "trace": trace})
        dialog = EvidenceViewDialog(analyses, ledger)
        try:
            dialog.list_widget.setCurrentRow(0)
            types = [dialog.event_table.item(row, 2).text()
                     for row in range(dialog.event_table.rowCount())]
            assert "report_exported" in types
            assert "analysis_run" in types
        finally:
            dialog.close()

    def test_fingerprint_recompute(self, scene):
        from ui.dialogs.evidence_view_dialog import EvidenceViewDialog

        analyses, ledger, frame = scene
        dialog = EvidenceViewDialog(analyses, ledger, frame_provider=lambda idx: frame)
        try:
            dialog.list_widget.setCurrentRow(0)
            dialog._recompute_fingerprint()
            assert dialog._fingerprint_result == "一致"
            changed = frame.copy()
            changed.loc[0, "x"] = 99.0
            dialog.frame_provider = lambda idx: changed
            dialog._recompute_fingerprint()
            assert "不一致" in dialog._fingerprint_result
        finally:
            dialog.close()

    def test_empty_analyses(self, scene):
        from ui.dialogs.evidence_view_dialog import EvidenceViewDialog

        _, ledger, _ = scene
        dialog = EvidenceViewDialog({}, ledger)
        try:
            assert dialog.list_widget.count() == 0
            assert "没有可查看" in dialog.detail.toPlainText()
        finally:
            dialog.close()
