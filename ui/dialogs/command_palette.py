"""全局命令面板（v4.1.0 B3）— Ctrl+K / Ctrl+P 快速跳转与执行。

条目结构: {"label": 显示名, "category": 分组, "hint": 右侧提示, "kind": ..., "payload": ...}
主窗口负责构建条目与执行；本对话框只负责过滤、键盘导航与选中回传。
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QVBoxLayout,
)

from ui.font_config import get_ui_font
from ui.theme import colors as theme_colors

MAX_VISIBLE = 12


class CommandPaletteDialog(QDialog):
    """居中弹出的命令面板（无边框，输入即筛选）。"""

    triggered = Signal(dict)

    def __init__(self, entries: list[dict[str, Any]], parent=None):
        super().__init__(parent)
        self._entries = list(entries)
        self._visible: list[dict[str, Any]] = []
        self.setWindowTitle("命令面板")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setModal(True)
        self.setMinimumWidth(560)
        self._setup_ui()
        self._apply_filter("")

    # ---------------- UI ----------------

    def _setup_ui(self):
        tc = theme_colors(self)
        self.setStyleSheet(
            f"QDialog {{ background: {tc['bg_card']};"
            f"border: 1px solid {tc['border']}; border-radius: 10px; }}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 10)
        layout.setSpacing(8)

        self.search = QLineEdit()
        self.search.setPlaceholderText("输入以搜索：模块 / 工具 / 操作…")
        self.search.setFont(QFont(get_ui_font(), 12))
        self.search.setMinimumHeight(38)
        self.search.setStyleSheet(
            f"QLineEdit {{ border: 1px solid {tc['border']}; border-radius: 8px;"
            f"padding: 4px 10px; background: {tc['bg_body']};"
            f"color: {tc['text_primary']}; }}"
            f"QLineEdit:focus {{ border-color: {tc['accent_bright']}; }}")
        self.search.textChanged.connect(self._apply_filter)
        layout.addWidget(self.search)

        self.list = QListWidget()
        self.list.setFont(QFont(get_ui_font(), 11))
        self.list.setMinimumHeight(320)
        self.list.setStyleSheet(
            f"QListWidget {{ border: none; background: transparent;"
            f"color: {tc['text_primary']}; outline: none; }}"
            f"QListWidget::item {{ padding: 7px 8px; border-radius: 6px; }}"
            f"QListWidget::item:selected {{ background: {tc['bg_active']}; }}")
        self.list.itemActivated.connect(self._execute_item)
        layout.addWidget(self.list, 1)

        footer = QLabel("↑↓ 选择 · Enter 执行 · Esc 关闭")
        footer.setStyleSheet(f"color: {tc['text_muted']}; font-size: 9pt;")
        layout.addWidget(footer)

    # ---------------- 过滤与执行 ----------------

    def _apply_filter(self, text: str):
        needle = (text or "").strip().lower()
        self._visible = [entry for entry in self._entries
                         if self._matches(entry, needle)][:MAX_VISIBLE]
        self.list.clear()
        for entry in self._visible:
            category = entry.get("category", "")
            hint = entry.get("hint", "")
            label = entry.get("label", "")
            text_line = f"{category} · {label}" if category else label
            if hint:
                text_line = f"{text_line}    {hint}"
            item = QListWidgetItem(text_line)
            item.setData(Qt.UserRole, entry)
            self.list.addItem(item)
        if self.list.count():
            self.list.setCurrentRow(0)

    @staticmethod
    def _matches(entry: dict[str, Any], needle: str) -> bool:
        if not needle:
            return True
        haystack = " ".join(str(entry.get(key, "")) for key in
                            ("label", "category", "hint", "keywords")).lower()
        return all(part in haystack for part in needle.split())

    def _execute_item(self, item: QListWidgetItem):
        entry = item.data(Qt.UserRole)
        if isinstance(entry, dict):
            self.triggered.emit(entry)
            self.accept()

    def execute_current(self) -> bool:
        """执行当前高亮项（供 Enter / 测试使用）。"""
        item = self.list.currentItem()
        if item is None:
            return False
        self._execute_item(item)
        return True

    # ---------------- 键盘 ----------------

    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key_Return, Qt.Key_Enter):
            if self.execute_current():
                return
        elif key == Qt.Key_Escape:
            self.reject()
            return
        elif key == Qt.Key_Down:
            self.list.setCurrentRow(min(self.list.currentRow() + 1,
                                        self.list.count() - 1))
            return
        elif key == Qt.Key_Up:
            self.list.setCurrentRow(max(self.list.currentRow() - 1, 0))
            return
        super().keyPressEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self._center_on_parent()
        self.search.setFocus()

    def _center_on_parent(self):
        parent = self.parentWidget()
        if parent is None:
            return
        geo = parent.frameGeometry()
        self.move(geo.center().x() - self.width() // 2,
                  max(geo.top() + 80, geo.center().y() - self.height() // 3))
