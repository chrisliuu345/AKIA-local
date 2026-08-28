"""Toast 通知 — 右下角非阻塞滑入通知, 3s 自动消失

用法:
    from ui.widgets.toast import Toast
from ui.font_config import get_ui_font
    Toast.show(self, "分析完成", type="success")
    Toast.show(self, "导出失败: 文件被占用", type="error", duration=5000)
"""

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer, QPoint
from PySide6.QtGui import QFont


_TOAST_COLORS = {
    "success": ("#27ae60", "#1a1a22"),
    "error":   ("#e74c3c", "#1a1a22"),
    "info":    ("#4da6ff", "#1a1a22"),
    "warning": ("#ffa726", "#1a1a22"),
}


class Toast(QFrame):
    """单条通知 — 自动滑入 + 淡出"""

    _active_toasts: list = []  # 类变量跟踪所有活跃 toast

    def __init__(self, parent, message: str, toast_type: str = "info",
                 duration: int = 3000):
        super().__init__(parent)
        self._duration = duration
        border_color, bg_color = _TOAST_COLORS.get(
            toast_type, _TOAST_COLORS["info"])

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.SubWindow)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setStyleSheet(
            f"QFrame {{"
            f"background-color: {bg_color};"
            f"border: 1px solid {border_color};"
            f"border-radius: 6px;"
            f"}}"
        )
        self.setMinimumHeight(40)  # v2.3.1: 换行后允许增高, 不再硬裁切
        self.setMinimumWidth(200)
        self.setMaximumWidth(480)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 6, 16, 6)
        label = QLabel(message)
        label.setFont(QFont(get_ui_font(), 10))
        label.setStyleSheet(f"color: #e1e2e6; background: transparent;")
        label.setWordWrap(True)
        layout.addWidget(label)

        self.adjustSize()
        self._slide_in()

    def _slide_in(self):
        parent = self.parent()
        if parent is None:
            self.hide()
            return
        pw, ph = parent.width(), parent.height()
        x = pw - self.width() - 20
        y_offset = sum(t.height() + 8 for t in Toast._active_toasts)
        y = ph - self.height() - 20 - y_offset
        self.move(x, y + 60)
        self.show()

        anim = QPropertyAnimation(self, b"pos")
        anim.setDuration(300)
        anim.setStartValue(QPoint(x, y + 40))
        anim.setEndValue(QPoint(x, y))
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start()
        self._anim = anim

        Toast._active_toasts.append(self)
        QTimer.singleShot(self._duration, self._fade_out)

    def _fade_out(self):
        self._anim = QPropertyAnimation(self, b"windowOpacity")
        self._anim.setDuration(300)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.setEasingCurve(QEasingCurve.InCubic)
        self._anim.finished.connect(self._cleanup)
        self._anim.start()

    def _cleanup(self):
        if self in Toast._active_toasts:
            Toast._active_toasts.remove(self)
        self.setParent(None)
        self.deleteLater()

    @classmethod
    def show(cls, parent, message: str, toast_type: str = "info",
             duration: int = 3000):
        """静态方法: 在 parent 右下角显示一条 toast, duration 毫秒后自动消失"""
        if parent is None:
            return
        cls(parent, message, toast_type, duration)
