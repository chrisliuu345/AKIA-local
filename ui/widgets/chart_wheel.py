"""普通滚轮把页面卷走；Ctrl / Shift 仍留给图表缩放。"""

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QApplication, QScrollArea

_installed = False


def _is_chart_canvas(obj) -> bool:
    return type(obj).__name__ in ("FigureCanvasQTAgg", "FigureCanvasQT")


def _forward_page_scroll(origin, event) -> None:
    parent = origin.parentWidget()
    while parent is not None:
        if isinstance(parent, QScrollArea):
            bar = parent.verticalScrollBar()
            if bar.maximum() > bar.minimum():
                event.ignore()
                parent.wheelEvent(event)
                return
        parent = parent.parentWidget()
    event.ignore()


class _ChartWheelFilter(QObject):
    def eventFilter(self, obj, event):
        if event.type() != QEvent.Type.Wheel or not _is_chart_canvas(obj):
            return False
        modifiers = event.modifiers()
        if modifiers & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier):
            return False
        _forward_page_scroll(obj, event)
        return True


def install_chart_wheel_filter(app=None) -> None:
    """每个进程只装一次。普通滚轮不进 matplotlib，改滚外层页面。"""
    global _installed
    app = app or QApplication.instance()
    if app is None or _installed:
        return
    app.installEventFilter(_ChartWheelFilter(app))
    _installed = True
