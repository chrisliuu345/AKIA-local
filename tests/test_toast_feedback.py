"""v4.1.0 B3 — Toast 轻提示接线（分析完成 / 导出 / 批量汇总）。"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")


@pytest.fixture
def window(_qt_application):
    from ui.main_window import MainWindow

    win = MainWindow()
    yield win
    win.close()
    win.deleteLater()


@pytest.fixture
def toast_calls(monkeypatch):
    calls = []

    def _record(parent, message, toast_type="info", duration=3000):
        calls.append({"parent": parent, "message": message,
                      "type": toast_type, "duration": duration})

    monkeypatch.setattr("ui.widgets.toast.Toast.show", staticmethod(_record))
    return calls


class _FakeTab:
    def __init__(self):
        self.current_result = {"analysis_type": "SPC: I-MR", "params": {},
                               "result": {}}


def test_analysis_completion_shows_toast(window, toast_calls, monkeypatch):
    fake = _FakeTab()
    monkeypatch.setattr(window, "_get_tabs", lambda force_load=False: {1: fake})
    window._on_analysis_finished(1)
    assert toast_calls, "分析完成应给出轻提示"
    assert "分析完成" in toast_calls[-1]["message"]
    assert toast_calls[-1]["type"] == "success"


def test_batch_run_suppresses_per_tab_toast(window, toast_calls, monkeypatch):
    fake = _FakeTab()
    monkeypatch.setattr(window, "_get_tabs", lambda force_load=False: {1: fake})
    window._batch_progress = object()          # 模拟批量进行中
    try:
        window._on_analysis_finished(1)
    finally:
        window._batch_progress = None
    assert toast_calls == [], "批量过程中不应逐个 Tab 弹提示"


def test_export_toast_helper(window, toast_calls):
    window._show_toast("已导出：report.docx", "success")
    assert toast_calls[-1]["message"] == "已导出：report.docx"
    assert toast_calls[-1]["type"] == "success"
