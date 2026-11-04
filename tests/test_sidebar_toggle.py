"""侧栏开关：展开和收起钉在同一底边，宽度动画不是瞬间跳变。"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QAbstractAnimation
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow
from ui.sidebar import SIDEBAR_COLLAPSED_WIDTH, SIDEBAR_EXPANDED_WIDTH

app = QApplication.instance() or QApplication([])


def _toggle_bottom(win):
    button = win.sidebar.collapse_btn
    return button.mapTo(win, button.rect().bottomLeft()).y()


def test_toggle_stays_on_the_same_bottom_edge():
    win = MainWindow()
    win.resize(1200, 800)
    win.show()
    app.processEvents()
    try:
        expanded_y = _toggle_bottom(win)
        assert win.sidebar.width() == SIDEBAR_EXPANDED_WIDTH
        assert abs(win.sidebar.collapse_btn.geometry().bottom() - win.sidebar.height()) <= 1

        win._toggle_sidebar(True, animate=False)
        app.processEvents()
        collapsed_y = _toggle_bottom(win)
        assert win.sidebar.width() == SIDEBAR_COLLAPSED_WIDTH
        assert win.sidebar.collapse_btn.text() == "»"
        assert abs(collapsed_y - expanded_y) <= 1
        assert abs(win.sidebar.collapse_btn.geometry().bottom() - win.sidebar.height()) <= 1

        win._toggle_sidebar(False, animate=False)
        app.processEvents()
        assert win.sidebar.width() == SIDEBAR_EXPANDED_WIDTH
        assert "收起" in win.sidebar.collapse_btn.text()
        assert abs(_toggle_bottom(win) - expanded_y) <= 1
    finally:
        win.close()


def test_sidebar_width_animates():
    win = MainWindow()
    win.resize(1200, 800)
    win.show()
    app.processEvents()
    try:
        win._toggle_sidebar(True, animate=True)
        assert win._sidebar_anim is not None
        assert win._sidebar_anim.state() == QAbstractAnimation.State.Running
        QTest.qWait(40)
        width = win.sidebar.width()
        assert SIDEBAR_COLLAPSED_WIDTH < width < SIDEBAR_EXPANDED_WIDTH
        QTest.qWait(280)
        assert win.sidebar.width() == SIDEBAR_COLLAPSED_WIDTH
    finally:
        win.close()
