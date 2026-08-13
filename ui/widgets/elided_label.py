"""ElidedLabel — 超出宽度自动省略号(…)的 QLabel, 超长时 tooltip 显示全文

用法:
    from ui.widgets.elided_label import ElidedLabel
    lbl = ElidedLabel("很长的文本...")
    lbl.setMaximumWidth(200)
"""

from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics


class ElidedLabel(QLabel):
    """自动省略的文本标签 — 宽度不足时右侧显示 …, tooltip 保持全文"""

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self._full_text = text
        self.setToolTip(text if text else "")

    def setText(self, text: str):
        self._full_text = text
        self.setToolTip(text if text else "")
        self._update_elided()
        super().setText(self._elided)

    def _update_elided(self):
        fm = QFontMetrics(self.font())
        self._elided = fm.elidedText(self._full_text, Qt.ElideRight, max(self.width() - 2, 10))
        # 避免 setText → paintEvent 无限递归: 仅在文本变化时更新
        if self.text() != self._elided:
            super().setText(self._elided)

    def resizeEvent(self, event):
        self._update_elided()
        super().resizeEvent(event)

    def paintEvent(self, event):
        # 确保最新宽度下的省略文本
        fm = QFontMetrics(self.font())
        elided = fm.elidedText(self._full_text, Qt.ElideRight, max(self.width() - 2, 10))
        if self.text() != elided:
            self._elided = elided
            super().setText(elided)
        super().paintEvent(event)
