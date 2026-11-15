"""已确认标准工时进入线平衡，并作为案例基线写入证据账本。"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QMessageBox

from analysis.ie.chain import IE_STANDARD_VERSION
from core.data_objects import Process
from core.project_context import ProjectContext


@pytest.fixture(autouse=True)
def _silence_dialogs(monkeypatch):
    monkeypatch.setattr(QMessageBox, "information",
                        staticmethod(lambda *args, **kwargs: None))
    monkeypatch.setattr(QMessageBox, "warning",
                        staticmethod(lambda *args, **kwargs: None))


def test_line_balance_uses_confirmed_standard_and_records_baseline():
    from ui.tabs.line_balance_tab import LineBalanceTab

    context = ProjectContext()
    context.record_standard_time(
        "P1", standard_time_s=40, normal_time_s=40, allowance_pct=0,
        rating=1, cycles=4, operator="OP", observation_times=[40, 40, 40, 40],
        change_reason="确认")
    context.record_standard_time(
        "P2", standard_time_s=60, normal_time_s=60, allowance_pct=0,
        rating=1, cycles=4, operator="OP", observation_times=[60, 60, 60, 60],
        change_reason="确认")
    recorded = []

    def _record(phase, bundle):
        recorded.append((phase, bundle))

    tab = LineBalanceTab()
    try:
        tab.set_balance_context(context, _record)
        tab.set_ie_data([
            Process("P1", "装配", cycle_time=10),
            Process("P2", "检验", cycle_time=10),
        ])
        tab.use_standard_check.setChecked(True)
        tab._on_one_click_analyze()
        assert tab.current_result["result"]["current"]["balance_rate"] == 0.8333
        assert [item.cycle_time for item in tab._analysis_processes] == [40.0, 60.0]
        assert tab.ie_processes[0].cycle_time == 10
        tab._record_standard_balance("baseline")
        assert recorded[0][0] == "baseline"
        assert recorded[0][1]["records"][0]["standard_version"] == IE_STANDARD_VERSION
        assert recorded[0][1]["records"][0]["observation_times"] == [40.0, 40.0, 40.0, 40.0]
    finally:
        tab.close()


def test_unchecked_standard_keeps_imported_cycle_time():
    from ui.tabs.line_balance_tab import LineBalanceTab

    tab = LineBalanceTab()
    try:
        tab.set_ie_data([
            Process("P1", "装配", cycle_time=40),
            Process("P2", "检验", cycle_time=60),
        ])
        tab._on_one_click_analyze()
        assert tab.current_result["result"]["current"]["balance_rate"] == 0.8333
        assert tab._last_balance_bundle["records"][0]["source"] == "imported_cycle_time"
        tab._record_standard_balance("baseline")
    finally:
        tab.close()
