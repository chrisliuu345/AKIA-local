"""
登录对话框 — 用户名/密码认证 + 首次运行自动创建 admin
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from core.auth import AuthManager, User
from ui.theme import colors as theme_colors


class LoginDialog(QDialog):
    def __init__(self, auth: AuthManager, parent=None):
        super().__init__(parent)
        self.auth = auth
        self.user: User = None
        self._setup_ui()

    def _setup_ui(self):
        tc = theme_colors()
        self.setWindowTitle("QA-Tool — 登录")
        self.setFixedSize(380, 240)
        self.setStyleSheet(f"background-color: {tc['bg_body']};")

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(40, 30, 40, 20)

        title = QLabel("🔐 QA-Tool")
        title.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {tc['accent_bright']};")
        layout.addWidget(title)

        self.user_edit = QLineEdit()
        self.user_edit.setPlaceholderText("用户名")
        self.user_edit.setMinimumHeight(34)
        self.user_edit.setStyleSheet(
            f"QLineEdit {{ background: {tc['bg_card']}; color: {tc['text_primary']};"
            f"border: 1px solid {tc['border']}; border-radius: 6px; padding: 6px 12px; }}"
        )
        layout.addWidget(self.user_edit)

        self.pass_edit = QLineEdit()
        self.pass_edit.setPlaceholderText("密码")
        self.pass_edit.setEchoMode(QLineEdit.Password)
        self.pass_edit.setMinimumHeight(34)
        self.pass_edit.setStyleSheet(self.user_edit.styleSheet())
        self.pass_edit.returnPressed.connect(self._on_login)
        layout.addWidget(self.pass_edit)

        self.login_btn = QPushButton("登 录")
        self.login_btn.setMinimumHeight(40)
        self.login_btn.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.setStyleSheet(
            f"QPushButton {{ background-color: {tc['accent']}; color: #fff;"
            f"border: none; border-radius: 8px; }}"
            f"QPushButton:hover {{ background-color: {tc['accent_bright']}; }}"
        )
        self.login_btn.clicked.connect(self._on_login)
        layout.addWidget(self.login_btn)

        hint = QLabel("默认账户: admin / admin")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet(f"color: {tc['text_muted']}; font-size: 11px;")
        layout.addWidget(hint)

    def _on_login(self):
        username = self.user_edit.text().strip()
        password = self.pass_edit.text()
        if not username:
            QMessageBox.warning(self, "提示", "请输入用户名")
            return

        user = self.auth.authenticate(username, password)
        if user:
            self.user = user
            self.accept()
        else:
            QMessageBox.warning(self, "登录失败", "用户名或密码错误")
