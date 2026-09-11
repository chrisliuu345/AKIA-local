"""API Key 快速配置弹窗（v3.8.0 P2 增补）。

在 QAM Harness 中点击"需要密钥但本机未配置"的供应商时弹出，
避免必须绕到「设置 → QAM Harness」才能接入；已有密钥时不触发。
密钥仅由调用方交给 config.settings 加密落盘，本弹窗不落盘、不回显。
"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QVBoxLayout,
)

from core.agent.providers import get_provider
from ui.font_config import get_ui_font
from ui.theme import colors as theme_colors


class ApiKeyDialog(QDialog):
    """供应商 API Key 输入框（密码回显 + 可切换显示）。"""

    def __init__(self, provider_id: str, parent=None):
        super().__init__(parent)
        self.spec = get_provider(provider_id)
        self._key = ""
        self.setWindowTitle(f"配置 {self.spec.label} API Key — QAM Harness")
        self.setMinimumWidth(500)
        self._setup_ui()

    def _setup_ui(self):
        tc = theme_colors(self)
        self.setStyleSheet(f"QDialog {{ background-color: {tc['bg_body']}; }}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        title = QLabel(f"接入 {self.spec.label}")
        title.setFont(QFont(get_ui_font(), 14, QFont.Bold))
        title.setStyleSheet(f"color: {tc['text_primary']};")
        layout.addWidget(title)

        sub = QLabel("未检测到该供应商的 API Key。输入后加密保存在本机，"
                     "下次选择该供应商将直接接入，不再弹出。")
        sub.setWordWrap(True)
        sub.setStyleSheet(f"color: {tc['text_secondary']}; font-size: 10pt;")
        layout.addWidget(sub)

        key_row = QHBoxLayout()
        key_row.setSpacing(6)
        self.key_edit = QLineEdit()
        self.key_edit.setEchoMode(QLineEdit.Password)
        self.key_edit.setPlaceholderText(self.spec.key_hint or "API Key")
        self.key_edit.setMinimumHeight(32)
        self.key_edit.setStyleSheet(
            f"QLineEdit {{ border: 1px solid {tc['border']}; border-radius: 6px;"
            f"padding: 4px 10px; background: {tc['bg_card']};"
            f"color: {tc['text_primary']}; }}"
            f"QLineEdit:focus {{ border-color: {tc['accent_bright']}; }}")
        self.key_edit.returnPressed.connect(self._on_save)
        key_row.addWidget(self.key_edit, 1)

        self.show_check = QCheckBox("显示")
        self.show_check.toggled.connect(
            lambda on: self.key_edit.setEchoMode(
                QLineEdit.Normal if on else QLineEdit.Password))
        key_row.addWidget(self.show_check)
        layout.addLayout(key_row)

        if self.spec.docs_url:
            docs = QLabel(f'<a href="{self.spec.docs_url}" '
                          f'style="color:{tc["accent_bright"]};">获取 API Key</a>')
            docs.setOpenExternalLinks(True)
            docs.setStyleSheet(f"font-size: 9pt; color: {tc['text_muted']};")
            layout.addWidget(docs)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #e74c3c; font-size: 9pt;")
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

        row = QHBoxLayout()
        row.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setMinimumHeight(32)
        cancel_btn.setStyleSheet(
            f"QPushButton {{ background: {tc['bg_card']}; color: {tc['text_secondary']};"
            f"border: 1px solid {tc['border']}; border-radius: 6px; padding: 5px 18px; }}")
        cancel_btn.clicked.connect(self.reject)
        row.addWidget(cancel_btn)

        save_btn = QPushButton("保存并接入")
        save_btn.setMinimumHeight(32)
        save_btn.setDefault(True)
        save_btn.setStyleSheet(
            f"QPushButton {{ background: {tc['accent']}; color: white; border: none;"
            f"border-radius: 6px; padding: 5px 20px; font-weight: bold; }}"
            f"QPushButton:hover {{ background: {tc['accent_bright']}; }}")
        save_btn.clicked.connect(self._on_save)
        row.addWidget(save_btn)
        layout.addLayout(row)
        self.setFocusPolicy(Qt.StrongFocus)
        self.key_edit.setFocus()

    def key(self) -> str:
        """用户确认的密钥（已去首尾空白）；取消/空输入返回空串。"""
        return self._key

    def _on_save(self):
        text = self.key_edit.text().strip()
        if not text:
            self.error_label.setText("请输入 API Key（不能为空）")
            self.error_label.setVisible(True)
            self.key_edit.setFocus()
            return
        self._key = text
        self.accept()
