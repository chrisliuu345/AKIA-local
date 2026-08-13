"""Dashboard 卡片布局设置对话框 — 显隐勾选 + 上移/下移排序 + 恢复默认 (v2.4 F2)"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QDialogButtonBox,
)
from PySide6.QtCore import Qt, QSettings

from core.i18n import i18n
from ui.theme import BUTTON_SECONDARY


class LayoutDialog(QDialog):
    """卡片显隐与排序 — 勾选=显示, 顺序=卡片顺序; 确定后写入 QSettings"""

    def __init__(self, parent=None, items: list = None, settings: QSettings = None):
        super().__init__(parent)
        self.setWindowTitle(i18n.tr("dashboard.layout"))
        self.setMinimumSize(360, 420)
        self._items = list(items or [])
        self._settings = settings or QSettings("QA-Tool", "Dashboard")

        layout = QVBoxLayout(self)
        hint = QLabel(i18n.tr("dashboard.layout_hint"))
        hint.setStyleSheet("color: #a0a3ae;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.list = QListWidget()
        saved_order = self._settings.value("order", [])
        hidden_raw = self._settings.value("hidden", [])
        if not isinstance(saved_order, (list, tuple)):
            saved_order = []
        hidden = set(hidden_raw) if isinstance(hidden_raw, (list, tuple)) else set()
        # 已有顺序优先, 新出现的分析类型排在末尾
        ordered = [it for it in saved_order if it in self._items]
        rest = [it for it in self._items if it not in ordered]
        for it in ordered + rest:
            item = QListWidgetItem(it)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked if it in hidden else Qt.Checked)
            self.list.addItem(item)
        layout.addWidget(self.list, 1)

        # 排序按钮
        btn_row = QHBoxLayout()
        up_btn = QPushButton("↑ " + i18n.tr("dashboard.layout_up"))
        up_btn.setStyleSheet(BUTTON_SECONDARY)
        up_btn.clicked.connect(self._move_up)
        btn_row.addWidget(up_btn)
        down_btn = QPushButton("↓ " + i18n.tr("dashboard.layout_down"))
        down_btn.setStyleSheet(BUTTON_SECONDARY)
        down_btn.clicked.connect(self._move_down)
        btn_row.addWidget(down_btn)
        reset_btn = QPushButton(i18n.tr("dashboard.layout_reset"))
        reset_btn.setStyleSheet(BUTTON_SECONDARY)
        reset_btn.clicked.connect(self._reset)
        btn_row.addWidget(reset_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._save_and_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _move_up(self):
        row = self.list.currentRow()
        if row <= 0:
            return
        item = self.list.takeItem(row)
        self.list.insertItem(row - 1, item)
        self.list.setCurrentRow(row - 1)

    def _move_down(self):
        row = self.list.currentRow()
        if row < 0 or row >= self.list.count() - 1:
            return
        item = self.list.takeItem(row)
        self.list.insertItem(row + 1, item)
        self.list.setCurrentRow(row + 1)

    def _reset(self):
        # 全部显示, 按字母/字典序恢复
        texts = sorted(self.list.item(i).text() for i in range(self.list.count()))
        self.list.clear()
        for t in texts:
            item = QListWidgetItem(t)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.list.addItem(item)

    def _save_and_accept(self):
        if self.list.count() == 0:
            self.accept()  # 空列表不写盘, 防止覆盖已保存布局
            return
        order = []
        hidden = []
        for i in range(self.list.count()):
            item = self.list.item(i)
            order.append(item.text())
            if item.checkState() == Qt.Unchecked:
                hidden.append(item.text())
        self._settings.setValue("order", order)
        self._settings.setValue("hidden", hidden)
        self.accept()
