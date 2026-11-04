"""图表上的普通滚轮滚动页面，Ctrl+滚轮仍留给缩放。"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication, QScrollArea, QVBoxLayout, QWidget

from ui.widgets.chart_wheel import install_chart_wheel_filter

app = QApplication.instance() or QApplication([])
install_chart_wheel_filter(app)


def _wheel(widget, delta_y: int, modifiers=Qt.KeyboardModifier.NoModifier):
    pos = QPointF(widget.width() / 2, widget.height() / 2)
    event = QWheelEvent(
        pos, widget.mapToGlobal(pos.toPoint()),
        QPoint(0, 0), QPoint(0, delta_y),
        Qt.MouseButton.NoButton, modifiers,
        Qt.ScrollPhase.NoScrollPhase, False,
    )
    QApplication.sendEvent(widget, event)
    app.processEvents()


def test_plain_wheel_over_chart_scrolls_page():
    fig, _ax = plt.subplots()
    canvas = FigureCanvasQTAgg(fig)
    canvas.setMinimumHeight(500)
    inner = QWidget()
    inner.setMinimumHeight(1600)
    layout = QVBoxLayout(inner)
    layout.addWidget(canvas)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(inner)
    scroll.resize(480, 240)
    scroll.show()
    app.processEvents()
    before = scroll.verticalScrollBar().value()
    _wheel(canvas, -120)
    after = scroll.verticalScrollBar().value()
    assert after > before
    plt.close(fig)
    scroll.close()


def test_ctrl_wheel_does_not_scroll_page():
    fig, _ax = plt.subplots()
    canvas = FigureCanvasQTAgg(fig)
    canvas.setMinimumHeight(500)
    inner = QWidget()
    inner.setMinimumHeight(1600)
    layout = QVBoxLayout(inner)
    layout.addWidget(canvas)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(inner)
    scroll.resize(480, 240)
    scroll.show()
    app.processEvents()
    before = scroll.verticalScrollBar().value()
    _wheel(canvas, -120, Qt.KeyboardModifier.ControlModifier)
    assert scroll.verticalScrollBar().value() == before
    plt.close(fig)
    scroll.close()


def test_analysis_tabs_drop_the_white_vline():
    from pathlib import Path
    for path in Path("ui/tabs").glob("*.py"):
        assert "QFrame.VLine" not in path.read_text(encoding="utf-8"), path.name
