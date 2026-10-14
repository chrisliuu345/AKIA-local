"""抽样批检验 UI 接线测试（v4.4.0 B3，离屏）。"""

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
        "raw_data": {"S": pd.DataFrame({
            "x": range(300), "g": ["A", "B", "C"] * 100})},
    }
    try:
        yield window
    finally:
        window.close()


def _batch_tab(main_window):
    tab = main_window._lazy_load_tab(26)  # 抽样检验
    tab.set_data(main_window.current_data["raw_data"]["S"])
    tab._switch(5)
    tab.batch_supplier.setText("供应商A")
    tab.batch_product.setText("P100")
    tab.batch_lot_size.setValue(2000)
    tab.batch_aql.setCurrentText("1.0")
    return tab


class TestTabWiring:
    def test_tab_receives_manager(self, main_window):
        tab = main_window._lazy_load_tab(26)
        assert tab is not None
        assert tab._sampling_manager is main_window.sampling_manager

    def test_standalone_without_manager_warns(self, monkeypatch):
        from PySide6.QtWidgets import QMessageBox

        from ui.tabs.sampling_tab import SamplingTab

        notices = []
        monkeypatch.setattr(QMessageBox, "information",
                            staticmethod(lambda *a, **k: notices.append(a)))
        tab = SamplingTab()
        try:
            tab._do_batch_plan()
            assert notices, "未接入编排器应提示"
        finally:
            tab.close()


class TestBatchFlow:
    def test_plan_query_writes_result_and_timeline(self, main_window):
        tab = _batch_tab(main_window)
        tab._do_batch_plan()
        assert tab.result.item(0, 0).text() == "K"
        assert tab.result.item(0, 1).text() == "125"
        assert "正常" in tab.batch_state_label.text()
        kinds = [tab.batch_timeline.item(i, 1).text()
                 for i in range(tab.batch_timeline.rowCount())]
        assert "方案" in kinds
        types = [e.event_type for e in main_window.ledger.events]
        assert "sampling_plan_selected" in types

    def test_sampling_reproducible_through_ui(self, main_window):
        tab = _batch_tab(main_window)
        tab.batch_method.setCurrentText("分层")
        idx = tab.batch_strat_col.findText("g")
        tab.batch_strat_col.setCurrentIndex(idx)
        tab.batch_seed.setValue(42)
        tab._do_batch_plan()
        tab._do_batch_sample()
        first = main_window.sampling_manager.decision_for(
            "供应商A|P100").row_fingerprint
        tab._do_batch_sample()
        second = main_window.sampling_manager.decision_for(
            "供应商A|P100").row_fingerprint
        assert first.startswith("pd-hash-v1:")
        assert first == second
        assert first in tab.batch_fingerprint_label.text()

    def test_two_rejects_trigger_tightened_in_ui(self, main_window):
        tab = _batch_tab(main_window)
        tab._do_batch_plan()
        tab.batch_inspected.setValue(50)
        tab.batch_defects.setValue(2)
        tab.batch_decision.setCurrentText("拒收")
        tab._do_batch_record()
        assert "加严" not in tab.batch_state_label.text()
        tab._do_batch_record()
        assert "加严" in tab.batch_state_label.text()
        assert "发生转移" in tab.batch_result_label.text()
        assert "连续 2 批拒收" in tab.batch_result_label.text()
        assert main_window.sampling_manager.state_for("供应商A|P100").state == \
            "tightened"
        kinds = [tab.batch_timeline.item(i, 1).text()
                 for i in range(tab.batch_timeline.rowCount())]
        assert "状态转移" in kinds
        types = [e.event_type for e in main_window.ledger.events]
        assert types.count("lot_inspected") == 2
        assert types.count("sampling_transfer_changed") == 1

    def test_override_requires_reason(self, main_window, monkeypatch):
        from PySide6.QtWidgets import QMessageBox

        warnings = []
        monkeypatch.setattr(QMessageBox, "warning",
                            staticmethod(lambda *a, **k: warnings.append(a)))
        tab = _batch_tab(main_window)
        tab._do_batch_override()
        assert warnings, "空原因应告警"
        assert main_window.sampling_manager.snapshot(
            "供应商A|P100")["state"] == "normal"
        tab.batch_override_state.setCurrentText("加严")
        tab.batch_override_reason.setText("供应商临时整改要求")
        tab._do_batch_override()
        snapshot = main_window.sampling_manager.snapshot("供应商A|P100")
        assert snapshot["state"] == "tightened"
        assert snapshot["override_reason"] == "供应商临时整改要求"

    def test_project_roundtrip_restores_sampling_state(self, main_window,
                                                       tmp_path, monkeypatch):
        from PySide6.QtWidgets import QFileDialog, QMessageBox

        from core.project_manager import ProjectManager

        monkeypatch.setattr(QMessageBox, "information",
                            staticmethod(lambda *a, **k: None))
        tab = _batch_tab(main_window)
        tab._do_batch_plan()
        tab.batch_decision.setCurrentText("拒收")
        tab._do_batch_record()
        tab._do_batch_record()
        path = str(tmp_path / "sampling.qap")
        monkeypatch.setattr(
            QFileDialog, "getSaveFileName",
            staticmethod(lambda *a, **k: (path, "")))
        main_window._on_save_project()
        project = ProjectManager.load_project(path)
        assert project["sampling"]["lots"]
        main_window._apply_loaded_project(project, path)
        restored = main_window.sampling_manager
        assert restored.state_for("供应商A|P100").state == "tightened"
        assert len(restored.lots_for("供应商A|P100")) == 2
        # 已加载的 Tab 重新接入新编排器
        assert main_window._tab_cache[26]._sampling_manager is restored
