"""
用户管理对话框 — 管理员创建/编辑/删除用户
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QComboBox, QLineEdit, QFormLayout, QGroupBox, QInputDialog,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from core.auth import AuthManager, _DEPARTMENTS, _TEAMS
from ui.theme import colors as theme_colors, BUTTON_PRIMARY, BUTTON_SECONDARY, BUTTON_TOGGLE

ROLE_LABELS = {
    "admin": "管理员", "dept_admin": "部门管理员",
    "analyst": "分析师", "readonly": "只读",
}


class UserManagementDialog(QDialog):
    def __init__(self, current_user, parent=None):
        super().__init__(parent)
        self.auth = AuthManager()
        self.current_user = current_user
        self._setup_ui()
        self._refresh()

    def _setup_ui(self):
        tc = theme_colors()
        self.setWindowTitle("用户管理")
        self.setMinimumSize(700, 450)
        self.setStyleSheet(f"background-color: {tc['bg_body']}; color: {tc['text_primary']};")

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("用户管理")
        title.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        header.addWidget(title)
        header.addStretch()
        btn_add = QPushButton("+ 添加用户")
        btn_add.setStyleSheet(BUTTON_PRIMARY)
        btn_add.clicked.connect(self._on_add_user)
        header.addWidget(btn_add)
        layout.addLayout(header)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["用户名", "角色", "部门", "班组", "创建时间", "操作"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        self.table.setColumnWidth(5, 120)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(
            f"QTableWidget {{ background: {tc['bg_card']}; border: 1px solid {tc['border_light']}; }}"
        )
        layout.addWidget(self.table, 1)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet(BUTTON_SECONDARY)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _refresh(self):
        dept = self.current_user.department if self.current_user.role == "dept_admin" else ""
        users = self.auth.list_users(department=dept)
        self.table.setRowCount(len(users))
        for i, u in enumerate(users):
            self.table.setItem(i, 0, QTableWidgetItem(u.username))
            self.table.setItem(i, 1, QTableWidgetItem(ROLE_LABELS.get(u.role, u.role)))
            self.table.setItem(i, 2, QTableWidgetItem(u.department or "-"))
            self.table.setItem(i, 3, QTableWidgetItem(u.team or "-"))
            self.table.setItem(i, 4, QTableWidgetItem(u.created_at[:10] if u.created_at else ""))

            btn_widget = QPushButton("编辑/删除")
            btn_widget.setStyleSheet(BUTTON_TOGGLE)
            btn_widget.clicked.connect(lambda checked, uname=u.username: self._on_edit_user(uname))
            self.table.setCellWidget(i, 5, btn_widget)

    def _on_add_user(self):
        dialog = _UserEditDialog(self, new_mode=True, current_user=self.current_user)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            result = self.auth.create_user(
                username=data["username"], password=data["password"],
                role=data["role"], department=data["department"],
                team=data["team"], display_name=data["display_name"],
            )
            if result:
                self._refresh()
            else:
                QMessageBox.warning(self, "添加失败", "用户名已存在或无效")

    def _on_edit_user(self, username: str):
        users = self.auth.list_users()
        target = next((u for u in users if u.username == username), None)
        if not target:
            return
        dialog = _UserEditDialog(self, new_mode=False, current_user=self.current_user, target_user=target)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            if data.get("delete"):
                self.auth.delete_user(username)
            elif data.get("reset_password"):
                self.auth.reset_password(username, data.get("new_password", "123456"))
                QMessageBox.information(self, "密码已重置", f"用户 {username} 的密码已重置")
            else:
                self.auth.update_user(username, role=data.get("role"),
                                      department=data.get("department"),
                                      team=data.get("team"),
                                      display_name=data.get("display_name"))
            self._refresh()


class _UserEditDialog(QDialog):
    def __init__(self, parent, new_mode=False, current_user=None, target_user=None):
        super().__init__(parent)
        self._new_mode = new_mode
        self._current_user = current_user
        self._target = target_user
        self._delete = False
        self._reset_pwd = False
        self._setup_ui()

    def _setup_ui(self):
        tc = theme_colors()
        title = "添加用户" if self._new_mode else f"编辑用户: {self._target.username}"
        self.setWindowTitle(title)
        self.setFixedSize(380, 350 if self._new_mode else 300)
        self.setStyleSheet(f"background-color: {tc['bg_body']}; color: {tc['text_primary']};")

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.user_edit = QLineEdit()
        self.user_edit.setMinimumHeight(28)
        if not self._new_mode:
            self.user_edit.setText(self._target.username)
            self.user_edit.setReadOnly(True)
        form.addRow("用户名:", self.user_edit)

        if self._new_mode:
            self.pwd_edit = QLineEdit()
            self.pwd_edit.setEchoMode(QLineEdit.Password)
            self.pwd_edit.setMinimumHeight(28)
            self.pwd_edit.setText("123456")
            form.addRow("密码:", self.pwd_edit)

        self.role_combo = QComboBox()
        available_roles = ["analyst", "readonly"]
        if self._current_user.role == "admin":
            available_roles = ["admin", "dept_admin", "analyst", "readonly"]
        elif self._current_user.role == "dept_admin":
            available_roles = ["analyst", "readonly"]
        self.role_combo.addItems([ROLE_LABELS.get(r, r) for r in available_roles])
        self._role_keys = available_roles
        if not self._new_mode:
            idx = self._role_keys.index(self._target.role) if self._target.role in self._role_keys else 0
            self.role_combo.setCurrentIndex(idx)
        form.addRow("角色:", self.role_combo)

        self.dept_combo = QComboBox()
        self.dept_combo.setEditable(True)
        self.dept_combo.addItems(_DEPARTMENTS)
        if not self._new_mode and self._target.department:
            self.dept_combo.setCurrentText(self._target.department)
        form.addRow("部门:", self.dept_combo)

        self.team_combo = QComboBox()
        self.team_combo.setEditable(True)
        self.team_combo.addItems(_TEAMS)
        if not self._new_mode and self._target.team:
            self.team_combo.setCurrentText(self._target.team)
        form.addRow("班组:", self.team_combo)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        if not self._new_mode and self._current_user.role in ("admin", "dept_admin"):
            reset_btn = QPushButton("重置密码")
            reset_btn.setStyleSheet(BUTTON_TOGGLE)
            reset_btn.clicked.connect(self._on_reset_password)
            btn_row.addWidget(reset_btn)
            if self._target.username != "admin":
                del_btn = QPushButton("删除用户")
                del_btn.setStyleSheet("QPushButton { color: #e74c3c; }")
                del_btn.clicked.connect(self._on_delete)
                btn_row.addWidget(del_btn)
        btn_row.addStretch()
        ok_btn = QPushButton("保存" if not self._new_mode else "添加")
        ok_btn.setStyleSheet(BUTTON_PRIMARY)
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def _on_delete(self):
        reply = QMessageBox.question(self, "确认删除", f"确定要删除用户 {self._target.username} 吗？")
        if reply == QMessageBox.Yes:
            self._delete = True
            self.accept()

    def _on_reset_password(self):
        text, ok = QInputDialog.getText(self, "重置密码", "新密码:", QLineEdit.Password, "123456")
        if ok and text:
            self._reset_pwd = True
            self._new_password = text

    def get_data(self) -> dict:
        role_key = self._role_keys[self.role_combo.currentIndex()] if self._role_keys else "analyst"
        return {
            "username": self.user_edit.text().strip(),
            "password": self.pwd_edit.text() if hasattr(self, 'pwd_edit') else "",
            "role": role_key,
            "department": self.dept_combo.currentText(),
            "team": self.team_combo.currentText(),
            "display_name": self.user_edit.text().strip(),
            "delete": self._delete,
            "reset_password": self._reset_pwd,
            "new_password": getattr(self, '_new_password', ''),
        }
