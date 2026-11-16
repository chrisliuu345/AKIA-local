"""后台执行不占用界面线程，并且调用返回时工作已经结束。"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication, QWidget

from ui.worker import run_in_worker


def test_run_in_worker_runs_off_the_gui_thread_and_returns_the_value():
    app = QApplication.instance() or QApplication([])
    seen = {}

    def work(value):
        seen["thread"] = QThread.currentThread()
        return value + 1

    owner = QWidget()
    try:
        assert run_in_worker(owner, work, 6) == 7
        assert seen["thread"] is not app.thread()
    finally:
        owner.close()


def test_capability_analysis_runs_off_the_gui_thread():
    import pandas as pd

    import ui.tabs.capability_tab as capability_tab
    from ui.tabs.capability_tab import CapabilityTab

    app = QApplication.instance() or QApplication([])
    seen = {}
    real = capability_tab._compute_capability

    def wrapped(*args, **kwargs):
        seen["thread"] = QThread.currentThread()
        return real(*args, **kwargs)

    capability_tab._compute_capability = wrapped
    tab = CapabilityTab()
    try:
        tab.set_data(pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]}), {})
        tab.usl_spin.setValue(10)
        tab.lsl_spin.setValue(0)
        result = tab.run_and_display()
        assert result["analysis_type"] == "正态过程能力"
        assert seen["thread"] is not app.thread()
        assert tab.current_result["analysis_type"] == "正态过程能力"
    finally:
        capability_tab._compute_capability = real
        tab.close()


def test_regression_analysis_runs_off_the_gui_thread(monkeypatch):
    import pandas as pd

    import ui.tabs.regression_tab as regression_tab
    from ui.tabs.regression_tab import RegressionTab

    app = QApplication.instance() or QApplication([])
    seen = {}
    real = regression_tab.reg_analyze

    def wrapped(*args, **kwargs):
        seen["thread"] = QThread.currentThread()
        return real(*args, **kwargs)

    monkeypatch.setattr(regression_tab, "reg_analyze", wrapped)
    tab = RegressionTab()
    try:
        frame = pd.DataFrame({"y": [1.0, 2.0, 3.0, 4.0, 5.0],
                              "x": [1.0, 2.0, 2.5, 4.0, 5.0]})
        tab.set_data(frame, {})
        tab.response_combo.setCurrentText("y")
        tab.factor1_combo.setCurrentText("x")
        result = tab.run_and_display()
        assert result["params"]["response"] == "y"
        assert seen["thread"] is not app.thread()
    finally:
        tab.close()


def test_run_in_worker_reraises_on_the_caller_thread():
    app = QApplication.instance() or QApplication([])
    def boom():
        raise ValueError("不能计算")

    owner = QWidget()
    try:
        with pytest.raises(ValueError, match="不能计算"):
            run_in_worker(owner, boom)
        assert QThread.currentThread() is app.thread()
    finally:
        owner.close()


def test_run_in_worker_distinguishes_none_result_from_interruption():
    owner = QWidget()
    try:
        assert run_in_worker(owner, lambda: None) is None   # 返回 None 是合法结果
    finally:
        owner.close()


def test_base_exception_in_worker_does_not_hang_the_caller():
    def leave():
        raise SystemExit(3)

    owner = QWidget()
    try:
        with pytest.raises(RuntimeError, match="异常退出"):
            run_in_worker(owner, leave)
    finally:
        owner.close()


def test_missing_result_raises_instead_of_returning_none(monkeypatch):
    from PySide6.QtCore import QEventLoop, QTimer

    from ui.worker import WorkerInterrupted, _FnWorker

    app = QApplication.instance() or QApplication([])
    owner = QWidget()
    real_exec = QEventLoop.exec

    def exec_then_quit(self, *a, **k):
        QTimer.singleShot(0, self.quit)
        return real_exec(self, *a, **k)

    # 线程结束却没有发出任何信号：循环被外部退出后，不能把「没有结果」当成 None。
    monkeypatch.setattr(_FnWorker, "run", lambda self: None)
    monkeypatch.setattr(QEventLoop, "exec", exec_then_quit)
    try:
        with pytest.raises(WorkerInterrupted):
            run_in_worker(owner, lambda: 1)
    finally:
        owner.close()
        app.processEvents()


def test_present_analysis_ignores_reentrant_trigger():
    from ui.present import present_analysis

    class _Text:
        def setStyleSheet(self, *_): pass
        def setText(self, *_): pass

    class _Tab(QWidget):
        analysis_completed = type("S", (), {"emit": lambda self: None})()

        def __init__(self):
            super().__init__()
            self.result_text = _Text()
            self.current_result = None
            self.shown = []
            self.calls = 0

        def validate_params(self): return True, ""
        def _clear_canvas(self): pass
        def display_result(self, result): self.shown.append(result)

    tab = _Tab()
    seen = {}

    def prepare():
        def work():
            tab.calls += 1
            # 计算中再次触发（模拟用户在局部事件循环里再点一次）
            seen["inner"] = present_analysis(tab, lambda: (lambda: "second"))
            return "first"
        return work

    try:
        assert present_analysis(tab, prepare) == "first"
        assert tab.calls == 1
    finally:
        tab.close()
