"""W58 — 主窗口共享 QScrollArea 下 tab 高度钉死的回归测试。

复现场景: 分析 tab 出图后 canvas/chart_container/result_stack 被钉高,
切换其他 tab 时高度残留导致所有 tab 被拉长。期望: 切离即释放, 切回即恢复。
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")  # 项目测试惯例

import time

from PySide6.QtWidgets import (
    QApplication, QFrame, QScrollArea, QStackedWidget, QVBoxLayout, QWidget,
    QPushButton,
)
from PySide6.QtCore import QSize

from ui.tabs.base_tab import BaseAnalysisTab


class _TallPage(BaseAnalysisTab):
    """最小复刻图表 tab — 复用基类 _pin/_sync/_release 逻辑"""

    def __init__(self):
        super().__init__()
        self.chart_container = QWidget()
        self.chart_layout = QVBoxLayout(self.chart_container)
        self.chart_layout.setContentsMargins(0, 0, 0, 0)
        self.chart_container.setMinimumHeight(300)
        self.result_stack = QStackedWidget()
        self.result_stack.addWidget(self.chart_container)
        self.canvas = QWidget()
        self.chart_layout.addWidget(self.canvas)
        root = QVBoxLayout(self)
        root.addWidget(self.result_stack)
        root.addWidget(QPushButton("btn"))
        root.addStretch()


class _FakeFigure:
    def get_size_inches(self):
        return (10, 8)

    def get_dpi(self):
        return 120


def _harness():
    stack = QStackedWidget()
    plain = QWidget()
    pl = QVBoxLayout(plain)
    pl.addWidget(QPushButton("b"))
    pl.addStretch()
    tall = _TallPage()
    tall.current_figure = _FakeFigure()
    stack.addWidget(plain)
    stack.addWidget(tall)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(stack)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.resize(400, 600)
    scroll.show()
    QApplication.processEvents()
    return stack, scroll, tall, plain


def test_hidden_pinned_tab_stretches_others():
    stack, scroll, tall, plain = _harness()
    stack.setCurrentIndex(1)
    QApplication.processEvents()
    assert scroll.verticalScrollBar().maximum() > 200, "图表页应可滚动浏览全图"
    assert tall.height() > 900

    stack.setCurrentIndex(0)
    QApplication.processEvents()
    assert scroll.verticalScrollBar().maximum() == 0, "普通页不应继承图表页滚动范围"
    assert plain.height() <= 650, "普通页不应被拉伸"
    assert tall.height() > 900


def test_return_to_chart_restores_height():
    stack, scroll, tall, _plain = _harness()
    stack.setCurrentIndex(1)
    QApplication.processEvents()
    stack.setCurrentIndex(0)
    QApplication.processEvents()
    stack.setCurrentIndex(1)
    QApplication.processEvents()
    assert scroll.verticalScrollBar().maximum() > 200, "切回图表页滚动应恢复"
    assert tall.height() > 900


# ---------- W58 复发（2026-09-13）：共享滚动区随当前页重置 ----------


class _BigHintWidget(QWidget):
    """模拟分析后的参数面板/数据表：隐藏时仍有大 sizeHint。"""

    def sizeHint(self):
        return QSize(400, 1500)

    def minimumSizeHint(self):
        return QSize(400, 1500)


def test_current_page_stack_ignores_hidden_page_hints():
    from ui.main_window import _CurrentPageStack

    stack = _CurrentPageStack()
    tall = QWidget()
    QVBoxLayout(tall).addWidget(_BigHintWidget())
    plain = QWidget()
    QVBoxLayout(plain).addWidget(QPushButton("b"))
    stack.addWidget(tall)
    stack.addWidget(plain)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(stack)
    scroll.resize(400, 600)
    scroll.show()
    QApplication.processEvents()

    stack.setCurrentIndex(0)
    QApplication.processEvents()
    assert stack.minimumSizeHint().height() > 500

    stack.setCurrentIndex(1)                 # 隐藏页的大 hint 不再影响当前布局
    QApplication.processEvents()
    assert stack.minimumSizeHint().height() < 200


def _pump(ms: int = 350):
    deadline = time.time() + ms / 1000.0
    while time.time() < deadline:
        QApplication.processEvents()
        time.sleep(0.01)


def test_main_window_resets_scroll_range_on_tab_switch():
    """真实主窗口：长分析页 → 切换 → 滚动区回落并置顶；切回可恢复。"""
    from ui.main_window import MainWindow

    win = MainWindow()
    win.resize(1300, 880)
    win.show()
    QApplication.processEvents()
    scroll = win.findChild(QScrollArea)

    tall = win._lazy_load_tab(1)             # SPC
    tall.result_stack.setMinimumHeight(1400)
    tall.chart_container.setMinimumHeight(1400)
    tall._last_page_height = 1600            # 模拟分析完成时记录的高度
    win._switch_tab(1)
    _pump()
    assert scroll.verticalScrollBar().maximum() > 200, "长页应可滚动"

    win._switch_tab(2)                       # 切到过程能力
    _pump()
    assert scroll.verticalScrollBar().maximum() < 100, "不应继承上一页的滚动长度"
    assert scroll.verticalScrollBar().value() == 0, "切换后应回到顶部"

    win._switch_tab(1)                       # 切回长页
    _pump()
    assert scroll.verticalScrollBar().maximum() > 200, "切回长页应恢复滚动范围"

    win.close()
    win.deleteLater()
