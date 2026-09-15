"""v4.1.0 B3 — 统一空状态（无数据遮罩 / 导入按钮 / 有数据隐藏）。"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pandas as pd
import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QLabel, QPushButton


@pytest.fixture
def window(_qt_application):
    from ui.main_window import MainWindow

    win = MainWindow()
    win.resize(1200, 800)
    win.show()
    QApplication.processEvents()
    yield win
    win.close()
    win.deleteLater()


def test_empty_state_shown_for_tab_without_data(window):
    tab = window._lazy_load_tab(1)          # SPC
    window._switch_tab(1)
    QApplication.processEvents()
    assert tab._empty_overlay is not None
    assert tab._empty_overlay.isVisible()
    texts = [label.text() for label in tab._empty_overlay.findChildren(QLabel)]
    assert any("导入数据" in text for text in texts)


def test_empty_state_hidden_after_data_loaded(window):
    tab = window._lazy_load_tab(1)
    window._switch_tab(1)
    QApplication.processEvents()
    assert tab._empty_overlay.isVisible()

    tab.set_data(pd.DataFrame({"x": [1, 2, 3]}), {})
    window._update_tab_empty_state(1)       # 导入流程在 set_data 后统一刷新
    assert not tab._empty_overlay.isVisible()

    window._switch_tab(2)
    window._switch_tab(1)
    QApplication.processEvents()
    assert not tab._empty_overlay.isVisible()


def test_empty_state_import_button_emits_signal(window):
    tab = window._lazy_load_tab(1)
    window._switch_tab(1)
    QApplication.processEvents()
    calls = []
    try:                                   # 断开主窗口的真实导入动作，避免弹文件对话框
        tab.import_data_requested.disconnect()
    except (RuntimeError, TypeError):
        pass
    tab.import_data_requested.connect(lambda: calls.append(1))
    buttons = tab._empty_overlay.findChildren(QPushButton)
    assert buttons, "空状态应包含导入按钮"
    buttons[0].click()
    QApplication.processEvents()
    assert calls == [1]


def test_empty_state_skips_dashboard_tabs(window):
    window._switch_tab(27)                  # Dashboard — 不套空状态遮罩
    QApplication.processEvents()
    tab = window.stack.widget(27)
    overlay = getattr(tab, "_empty_overlay", None)
    assert overlay is None or not overlay.isVisible()
