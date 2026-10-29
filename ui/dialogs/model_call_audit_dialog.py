"""模型调用审计 — 只读查看本机操作日志中的 model_call 记录。

调度本身在 core.agent 完成；这里只给已有菜单一个查看入口，不新开页面。
"""
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout,
)

from core.audit import MODEL_CALL_ACTION, read_log
from ui.font_config import get_ui_font
from ui.theme import colors as theme_colors


class ModelCallAuditDialog(QDialog):
    """本机模型调用记录。关闭或刷新都不会改日志。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("模型调用审计")
        self.resize(780, 480)
        self._setup_ui()
        self.reload()

    def _setup_ui(self):
        tc = theme_colors(self)
        self.setStyleSheet(f"QDialog {{ background-color: {tc['bg_body']}; }}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        note = QLabel("记录保存在本机操作日志，不上传。每条包含输入、模型、配置和结果。")
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {tc['text_secondary']};")
        layout.addWidget(note)

        bar = QHBoxLayout()
        self.count_label = QLabel("")
        self.count_label.setStyleSheet(f"color: {tc['text_muted']};")
        bar.addWidget(self.count_label)
        bar.addStretch()
        refresh = QPushButton("刷新")
        refresh.clicked.connect(self.reload)
        bar.addWidget(refresh)
        layout.addLayout(bar)

        self.view = QPlainTextEdit()
        self.view.setReadOnly(True)
        self.view.setFont(QFont(get_ui_font(), 10))
        self.view.setStyleSheet(
            f"QPlainTextEdit {{ background: {tc['bg_card']}; color: {tc['text_primary']};"
            f"border: 1px solid {tc['border']}; border-radius: 6px; }}")
        layout.addWidget(self.view, 1)

    def reload(self):
        lines = read_log(limit=200, action=MODEL_CALL_ACTION)
        self.count_label.setText(f"{len(lines)} 条（本机）")
        if not lines:
            self.view.setPlainText("尚无模型调用记录。")
            return
        self.view.setPlainText("\n".join(lines))
