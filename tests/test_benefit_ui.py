"""收益账本 UI 接线测试（v4.4.0 B4，离屏）。"""

import os
from datetime import datetime, timedelta
from types import SimpleNamespace

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
        "raw_data": {"S": pd.DataFrame({"x": [1.0, 2.0, 3.0]})},
    }
    try:
        yield window
    finally:
        window.close()


def _closed_ready_workflow(window) -> tuple:
    from core.case_workflow import CaseWorkflow

    workflow = CaseWorkflow(title="收益案例", ledger=window.ledger)
    frame = pd.DataFrame({"x": [31.0, 32.0, 33.0]})
    workflow.record_step("baseline", {"n": 3}, frame=frame)
    workflow.record_step("re_measure", {"n": 3}, frame=frame)
    workflow.record_step("verify", {"p_value": 0.01, "is_significant": True},
                         frame=frame, measurement_refs=["MEV-1"])
    return workflow, frame


def _seed_basic_records(window) -> None:
    from core.benefit_ledger import BenefitRecord

    window.benefit_ledger.add(BenefitRecord(
        case_id="C1", month="2026-10", ledger_kind="improvement",
        category="改善收益", confidence="A",
        basis={"baseline_value": 10, "new_value": 8, "quantity": 100,
               "unit_cost": 1}))
    window.benefit_ledger.add(BenefitRecord(
        case_id="C2", month="2026-10", ledger_kind="cost_of_quality",
        category="内部失败", confidence="C",
        basis={"quantity": 5, "unit_cost": 2}))


class TestMenuEntry:
    def test_tools_menu_has_benefit_ledger(self, main_window):
        tools_menu = next(action.menu() for action in main_window.menuBar().actions()
                          if "工具" in action.text())
        texts = [action.text() for action in tools_menu.actions()]
        assert any("收益账本" in text for text in texts)


class TestCaseCloseBenefitFlow:
    def test_close_then_record_benefit(self, main_window, monkeypatch):
        from PySide6.QtWidgets import QInputDialog, QMessageBox

        from ui.dialogs import benefit_entry_dialog as entry_module
        from ui.dialogs.case_workflow_dialog import CaseWorkflowDialog

        workflow, _frame = _closed_ready_workflow(main_window)
        monkeypatch.setattr(QInputDialog, "getMultiLineText",
                            staticmethod(lambda *a, **k: ("复测显著", True)))
        infos = []
        monkeypatch.setattr(QMessageBox, "information",
                            staticmethod(lambda *a, **k: infos.append(a)))

        draft = {"month": datetime.now().astimezone().strftime("%Y-%m"),
                 "category": "改善收益", "ledger_kind": "improvement",
                 "confidence": "A", "baseline_value": 32.0, "new_value": 30.0,
                 "quantity": 1000, "unit_cost": 0.5, "unit": "s",
                 "currency": "CNY", "note": ""}

        class _FakeEntry:
            Accepted = 1

            def __init__(self, parent=None, **kwargs):
                pass

            def exec(self):
                return 1

            def draft(self):
                return dict(draft)

        monkeypatch.setattr(entry_module, "BenefitEntryDialog", _FakeEntry)
        dialog = CaseWorkflowDialog(workflow, main_window)
        try:
            dialog._on_close_case()
            assert workflow.case.status == "closed"
            records = main_window.benefit_ledger.for_case(workflow.case.id)
            assert len(records) == 1
            assert records[0].amount == pytest.approx(1000.0)
            assert any("收益已入账" in str(item) for item in infos)
            types = [e.event_type for e in main_window.ledger.events]
            assert "benefit_recorded" in types
            # 工作台显示累计收益（回答"这条改善省了多少"）
            assert "累计收益" in dialog.browser.toPlainText()
            assert "改善收益" in dialog.browser.toPlainText()
        finally:
            dialog.close()

    def test_cancel_entry_records_nothing(self, main_window, monkeypatch):
        from PySide6.QtWidgets import QInputDialog, QMessageBox

        from ui.dialogs import benefit_entry_dialog as entry_module
        from ui.dialogs.case_workflow_dialog import CaseWorkflowDialog

        workflow, _frame = _closed_ready_workflow(main_window)
        monkeypatch.setattr(QInputDialog, "getMultiLineText",
                            staticmethod(lambda *a, **k: ("复测显著", True)))
        infos = []
        monkeypatch.setattr(QMessageBox, "information",
                            staticmethod(lambda *a, **k: infos.append(a)))

        class _CancelEntry:
            Accepted = 1

            def __init__(self, parent=None, **kwargs):
                pass

            def exec(self):
                return 0

        monkeypatch.setattr(entry_module, "BenefitEntryDialog", _CancelEntry)
        dialog = CaseWorkflowDialog(workflow, main_window)
        try:
            dialog._on_close_case()
            assert workflow.case.status == "closed"
            assert len(main_window.benefit_ledger) == 0
            assert any("未登记收益" in str(item) for item in infos)
        finally:
            dialog.close()


class TestLedgerDialog:
    def test_rows_summary_and_pending(self, main_window):
        from ui.dialogs.benefit_ledger_dialog import BenefitLedgerDialog

        _seed_basic_records(main_window)
        dialog = BenefitLedgerDialog(main_window.benefit_ledger)
        try:
            assert dialog.table.rowCount() == 2
            text = dialog.summary_label.text()
            assert "200.00" in text  # 改善收益 (10-8)*100*1
            assert "待完善(C) 1 条" in text
            confidences = [dialog.table.item(r, 4).text()
                           for r in range(dialog.table.rowCount())]
            assert any("（待完善）" in value for value in confidences)
        finally:
            dialog.close()

    def test_recompute_flow(self, main_window, monkeypatch):
        from PySide6.QtWidgets import QMessageBox

        from core.benefit_ledger import record_case_benefit
        from ui.dialogs.benefit_ledger_dialog import BenefitLedgerDialog

        registry = main_window.project_context.standards
        first = registry.record_change("standard_time", "OP10",
                                       {"standard_time_s": 30.0},
                                       change_reason="初始", changed_by="user")
        month = datetime.now().astimezone().strftime("%Y-%m")
        record_case_benefit(
            main_window.benefit_ledger,
            SimpleNamespace(id="CASE-R", standard_refs=["OP10"]),
            month=month, baseline_value=32.0, new_value=30.0, quantity=10,
            unit_cost=1.0, confidence="A", standards=registry)
        assert main_window.benefit_ledger.records[0].basis["standard_ref"] == \
            first.record_id
        registry.record_change("standard_time", "OP10",
                               {"standard_time_s": 28.0},
                               change_reason="升版", changed_by="user")
        infos = []
        monkeypatch.setattr(QMessageBox, "information",
                            staticmethod(lambda *a, **k: infos.append(a)))
        dialog = BenefitLedgerDialog(main_window.benefit_ledger, main_window,
                                     recompute=main_window.recompute_benefits)
        try:
            dialog.month_edit.setText(month)
            dialog._on_recompute()
            assert any("更新 1 条" in str(item) for item in infos)
            events = [e.event_type for e in main_window.ledger.events]
            assert "benefit_recomputed" in events
            # 历史月冻结提示
            dialog.month_edit.setText("2020-01")
            dialog._on_recompute()
            assert any("冻结" in str(item) for item in infos)
        finally:
            dialog.close()


class TestProjectRoundtrip:
    def test_save_load_restores_ledger(self, main_window, tmp_path, monkeypatch):
        from PySide6.QtWidgets import QFileDialog, QMessageBox

        from core.project_manager import ProjectManager

        monkeypatch.setattr(QMessageBox, "information",
                            staticmethod(lambda *a, **k: None))
        _seed_basic_records(main_window)
        path = str(tmp_path / "benefits.qap")
        monkeypatch.setattr(
            QFileDialog, "getSaveFileName",
            staticmethod(lambda *a, **k: (path, "")))
        main_window._on_save_project()
        project = ProjectManager.load_project(path)
        assert project["manifest"]["benefit_count"] == 2
        main_window._apply_loaded_project(project, path)
        restored = main_window.benefit_ledger
        assert len(restored) == 2
        assert restored.summary()["pending_count"] == 1
        past_month = (datetime.now().astimezone().replace(day=1)
                      - timedelta(days=1)).strftime("%Y-%m")
        frozen = main_window.recompute_benefits(past_month)
        assert frozen["frozen"] is True
