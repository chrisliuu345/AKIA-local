"""
登录对话框 — 用户名/密码认证 + 首次运行自动创建 admin
认证加固：登录锁定提示 + must_change_password 强制改密 + W11 默认凭据提示控制
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from core.auth import AuthManager, User
from core.password_policy import validate_password
from ui.theme import colors as theme_colors


class ForceChangePasswordDialog(QDialog):
    """强制修改密码对话框（must_change_password 场景）"""

    def __init__(self, auth: AuthManager, username: str, parent=None, user: User = None):
        super().__init__(parent)
        self.auth = auth
        self.username = username
        self._caller = user
        self._setup_ui()

    def _setup_ui(self):
        tc = theme_colors()
        self.setWindowTitle("强制修改密码")
        self.setFixedSize(360, 220)
        self.setStyleSheet(f"background-color: {tc['bg_body']};")

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(36, 24, 36, 20)

        hint = QLabel("⚠ 首次登录或密码已被重置，请修改密码后继续。")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {tc['accent_bright']}; font-size: 12px;")
        layout.addWidget(hint)

        self.new_pwd = QLineEdit()
        self.new_pwd.setPlaceholderText("新密码（至少8位，含字母和数字）")
        self.new_pwd.setEchoMode(QLineEdit.Password)
        self.new_pwd.setMinimumHeight(32)
        self.new_pwd.setStyleSheet(
            f"QLineEdit {{ background: {tc['bg_card']}; color: {tc['text_primary']};"
            f"border: 1px solid {tc['border']}; border-radius: 6px; padding: 6px 12px; }}"
        )
        layout.addWidget(self.new_pwd)

        self.confirm_pwd = QLineEdit()
        self.confirm_pwd.setPlaceholderText("确认新密码")
        self.confirm_pwd.setEchoMode(QLineEdit.Password)
        self.confirm_pwd.setMinimumHeight(32)
        self.confirm_pwd.setStyleSheet(self.new_pwd.styleSheet())
        self.confirm_pwd.returnPressed.connect(self._on_confirm)
        layout.addWidget(self.confirm_pwd)

        btn = QPushButton("确认修改")
        btn.setMinimumHeight(36)
        btn.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        btn.setStyleSheet(
            f"QPushButton {{ background-color: {tc['accent']}; color: #fff;"
            f"border: none; border-radius: 8px; }}"
            f"QPushButton:hover {{ background-color: {tc['accent_bright']}; }}"
        )
        btn.clicked.connect(self._on_confirm)
        layout.addWidget(btn)

    def _on_confirm(self):
        new_pwd = self.new_pwd.text()
        confirm = self.confirm_pwd.text()
        if not new_pwd:
            QMessageBox.warning(self, "提示", "请输入新密码")
            return
        if new_pwd != confirm:
            QMessageBox.warning(self, "提示", "两次输入的密码不一致")
            return
        ok, reason = validate_password(new_pwd)
        if not ok:
            QMessageBox.warning(self, "密码不符合要求", reason)
            return
        if self.auth.force_change_password(self.username, new_pwd, caller=self._caller):
            self.accept()
        else:
            QMessageBox.warning(self, "修改失败", "密码修改失败，请重试")


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

        # W11: 仅当 admin 仍使用默认密码（must_change_password=True）时显示提示
        hint_text = self._get_default_hint()
        if hint_text:
            hint = QLabel(hint_text)
            hint.setAlignment(Qt.AlignCenter)
            hint.setStyleSheet(f"color: {tc['text_muted']}; font-size: 11px;")
            layout.addWidget(hint)

    def _get_default_hint(self) -> str:
        """W11: 仅在 admin 未改密时显示默认凭据提示"""
        try:
            users = self.auth._load_users()
            admin = next((u for u in users if u["username"] == "admin"), None)
            if admin and admin.get("must_change_password", False):
                return "默认账户: admin / admin（首次登录需修改密码）"
        except Exception:
            pass
        return ""

    def _on_login(self):
        username = self.user_edit.text().strip()
        password = self.pass_edit.text()
        if not username:
            QMessageBox.warning(self, "提示", "请输入用户名")
            return

        user = self.auth.authenticate(username, password)
        if user:
            if user.must_change_password:
                dlg = ForceChangePasswordDialog(self.auth, username, self, user=user)
                if dlg.exec() == QDialog.Accepted:
                    user.must_change_password = False
                    self.user = user
                    self.accept()
                else:
                    # P2-2: 取消强制改密 → 提示并停留在登录页
                    QMessageBox.warning(self, "需要修改密码", "请修改初始密码后才能登录")
                return
            self.user = user
            self.accept()
        else:
            if self.auth.is_account_locked(username):
                QMessageBox.warning(self, "账户已锁定", "连续登录失败次数过多，账户已锁定。\n请联系管理员解锁。")
            else:
                QMessageBox.warning(self, "登录失败", "用户名或密码错误")
