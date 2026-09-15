"""v4.1.0 B3 — 批量分析分步执行（进度 / 取消 / 结果收纳）。"""

import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pandas as pd
import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication


class _FakeTab:
    """最小可运行 Tab 替身（避免真实分析开销）。"""

    def __init__(self, name):
        self._name = name
        self.current_result = None
        self.df = pd.DataFrame({"x": [1, 2, 3]})
        self.calls = 0

    def run_and_display(self):
        self.calls += 1
        self.current_result = {"analysis_type": self._name,
                               "params": {}, "result": {}}


def _pump_until(condition, timeout: float = 5.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        QApplication.processEvents()
        if condition():
            return True
        time.sleep(0.01)
    return condition()


@pytest.fixture
def window(_qt_application):
    from ui.main_window import MainWindow

    win = MainWindow()
    win.current_data = {"raw_data": {"Sheet1": pd.DataFrame({"x": [1]})}}
    yield win
    if getattr(win, "_batch_progress", None) is not None:
        win._batch_progress.close()
        win._batch_progress = None
    win.close()
    win.deleteLater()


def test_batch_runs_all_tabs_with_progress(window, monkeypatch):
    tabs = {1: _FakeTab("SPC"), 2: _FakeTab("Capability"), 3: _FakeTab("MSA")}
    monkeypatch.setattr(window, "_get_tabs", lambda force_load=False: tabs)

    window._on_run_all_analyses()
    assert window._batch_progress is not None, "应弹出进度对话框"
    assert _pump_until(lambda: getattr(window, "_batch_progress", None) is None)

    assert all(tab.calls == 1 for tab in tabs.values())
    assert set(window.analyses) == {1, 2, 3}
    assert window._batch_success == 3 and window._batch_failed == 0


def test_batch_cancel_stops_remaining_tabs(window, monkeypatch):
    tabs = {1: _FakeTab("A"), 2: _FakeTab("B"), 3: _FakeTab("C")}
    monkeypatch.setattr(window, "_get_tabs", lambda force_load=False: tabs)

    window._on_run_all_analyses()
    assert _pump_until(lambda: sum(t.calls for t in tabs.values()) >= 1)
    window._cancel_batch_analysis()
    assert _pump_until(lambda: getattr(window, "_batch_progress", None) is None)
    assert sum(tab.calls for tab in tabs.values()) < 3, "取消后不应继续跑完"


def test_batch_failure_is_counted(window, monkeypatch):
    class _Boom(_FakeTab):
        def run_and_display(self):
            self.calls += 1
            raise RuntimeError("boom")

    tabs = {1: _FakeTab("ok"), 2: _Boom("bad")}
    monkeypatch.setattr(window, "_get_tabs", lambda force_load=False: tabs)

    window._on_run_all_analyses()
    assert _pump_until(lambda: getattr(window, "_batch_progress", None) is None)
    assert window._batch_success == 1 and window._batch_failed == 1
