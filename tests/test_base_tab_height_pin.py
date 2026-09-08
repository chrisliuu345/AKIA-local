"""W58 — 主窗口共享 QScrollArea 下 tab 高度钉死的回归测试。

复现场景: 分析 tab 出图后 canvas/chart_container/result_stack 被钉高,
切换其他 tab 时高度残留导致所有 tab 被拉长。期望: 切离即释放, 切回即恢复。
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")  # 项目测试惯例

from PySide6.QtWidgets import (
    QApplication, QFrame, QScrollArea, QStackedWidget, QVBoxLayout, QWidget, QPushButton,
)

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
    stack, scroll, tall, plain = _harness()
    stack.setCurrentIndex(1)
    QApplication.processEvents()
    stack.setCurrentIndex(0)
    QApplication.processEvents()
    stack.setCurrentIndex(1)
    QApplication.processEvents()
    assert scroll.verticalScrollBar().maximum() > 200, "切回图表页滚动应恢复"
    assert tall.height() > 900
