"""
设置对话框
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QSpinBox,
    QDoubleSpinBox, QDialogButtonBox, QGroupBox, QCheckBox, QTabWidget, QWidget,
    QLineEdit, QLabel, QPushButton, QHBoxLayout, QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from config.settings import (
    FONT_FAMILY, CHART_DPI, MSA_GRR_ACCEPTABLE, MSA_NDC_THRESHOLD, get_setting,
)
from ui.theme import colors as theme_colors
from core.auth import _DEPARTMENTS, _TEAMS


class SettingsDialog(QDialog):
    def __init__(self, parent=None, user=None, account_only=False):
        super().__init__(parent)
        self._user = user
        self._account_only = account_only
        self.setWindowTitle("账户设置" if account_only else "系统设置")
        self.setMinimumSize(520, 430)
        self._setup_ui()

    def _setup_ui(self):
        tc = theme_colors()
        self.setStyleSheet(f"background-color: {tc['bg_body']}; color: {tc['text_primary']};")
        layout = QVBoxLayout(self)

        tabs = QTabWidget()

        if self._account_only:
            if self._user:
                self._add_account_tab(tabs, tc)
            layout.addWidget(tabs)
            buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            buttons.accepted.connect(self.accept)
            buttons.rejected.connect(self.reject)
            layout.addWidget(buttons)
            return

        general_tab = QWidget()
        general_layout = QFormLayout(general_tab)

        self.font_combo = QComboBox()
        self.font_combo.addItems(FONT_FAMILY)
        saved_font = get_setting("font_family", FONT_FAMILY[0])
        if saved_font in [self.font_combo.itemText(i) for i in range(self.font_combo.count())]:
            self.font_combo.setCurrentText(saved_font)
        general_layout.addRow("默认字体:", self.font_combo)

        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 300)
        self.dpi_spin.setValue(get_setting("chart_dpi", CHART_DPI))
        general_layout.addRow("图表DPI:", self.dpi_spin)

        self.animations_check = QCheckBox("界面动画效果 (淡入/数字滚动)")
        self.animations_check.setChecked(get_setting("animations_enabled", True))
        general_layout.addRow("动画:", self.animations_check)

        tabs.addTab(general_tab, "通用")

        rules_tab = QWidget()
        rules_layout = QFormLayout(rules_tab)

        self.nelson_check = QCheckBox("启用Nelson判异规则")
        self.nelson_check.setChecked(get_setting("nelson_rules_enabled", True))
        rules_layout.addRow(self.nelson_check)

        tabs.addTab(rules_tab, "判异规则")

        msa_tab = QWidget()
        msa_layout = QFormLayout(msa_tab)

        self.grr_accept = QDoubleSpinBox()
        self.grr_accept.setRange(0, 0.5)
        self.grr_accept.setValue(get_setting("msa_grr_acceptable", MSA_GRR_ACCEPTABLE))
        self.grr_accept.setSingleStep(0.01)
        msa_layout.addRow("%GRR 可接受阈值:", self.grr_accept)

        self.ndc_spin = QSpinBox()
        self.ndc_spin.setRange(1, 10)
        self.ndc_spin.setValue(get_setting("msa_ndc_threshold", MSA_NDC_THRESHOLD))
        msa_layout.addRow("NDC 阈值:", self.ndc_spin)

        tabs.addTab(msa_tab, "MSA")

        # ── 告警标签页 (E3) ──
        alert_tab = QWidget()
        alert_layout = QFormLayout(alert_tab)

        self.alert_min_spin = QSpinBox()
        self.alert_min_spin.setRange(0, 100)
        self.alert_min_spin.setValue(get_setting("alert_min_violations", 1))
        self.alert_min_spin.setToolTip("判异点数达到该阈值才触发告警")
        alert_layout.addRow("最小判异点数:", self.alert_min_spin)

        self.alert_popup_check = QCheckBox("弹窗告警")
        self.alert_popup_check.setChecked(get_setting("alert_popup_enabled", True))
        alert_layout.addRow(self.alert_popup_check)

        self.alert_sound_check = QCheckBox("声音提醒")
        self.alert_sound_check.setChecked(get_setting("alert_sound_enabled", True))
        alert_layout.addRow(self.alert_sound_check)

        self.alert_log_check = QCheckBox("告警日志")
        self.alert_log_check.setChecked(get_setting("alert_log_enabled", True))
        alert_layout.addRow(self.alert_log_check)

        tabs.addTab(alert_tab, "告警")

        # ── 账户标签页 ──
        if self._user:
            self._add_account_tab(tabs, tc)

        layout.addWidget(tabs)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _add_account_tab(self, tabs, tc):
        """构建账户标签页 (账户信息 + 修改密码)"""
        account_tab = QWidget()
        account_layout = QVBoxLayout(account_tab)
        account_layout.setSpacing(10)

        info_group = QGroupBox("账户信息")
        info_form = QFormLayout(info_group)

        self.acc_username = QLabel(self._user.username)
        self.acc_username.setStyleSheet(f"color: {tc['accent_bright']}; font-weight: bold;")
        info_form.addRow("用户名:", self.acc_username)

        role_labels = {"admin": "管理员", "dept_admin": "部门管理员", "analyst": "分析师", "readonly": "只读"}
        self.acc_role = QLabel(role_labels.get(self._user.role, self._user.role))
        info_form.addRow("角色:", self.acc_role)

        self.dept_combo = QComboBox()
        self.dept_combo.setEditable(True)
        self.dept_combo.addItems(_DEPARTMENTS)
        if self._user.department:
            idx = self.dept_combo.findText(self._user.department)
            if idx >= 0:
                self.dept_combo.setCurrentIndex(idx)
            else:
                self.dept_combo.setCurrentText(self._user.department)
        self.dept_combo.setMinimumHeight(28)
        info_form.addRow("部门:", self.dept_combo)

        self.team_combo = QComboBox()
        self.team_combo.setEditable(True)
        self.team_combo.addItems(_TEAMS)
        if self._user.team:
            idx = self.team_combo.findText(self._user.team)
            if idx >= 0:
                self.team_combo.setCurrentIndex(idx)
            else:
                self.team_combo.setCurrentText(self._user.team)
        self.team_combo.setMinimumHeight(28)
        info_form.addRow("班组:", self.team_combo)

        self.display_edit = QLineEdit()
        self.display_edit.setText(self._user.display_name or self._user.username)
        self.display_edit.setMinimumHeight(28)
        info_form.addRow("显示名称:", self.display_edit)

        account_layout.addWidget(info_group)

        pwd_group = QGroupBox("修改密码")
        pwd_form = QFormLayout(pwd_group)
        self.old_pwd = QLineEdit()
        self.old_pwd.setEchoMode(QLineEdit.Password)
        self.old_pwd.setMinimumHeight(28)
        pwd_form.addRow("旧密码:", self.old_pwd)
        self.new_pwd = QLineEdit()
        self.new_pwd.setEchoMode(QLineEdit.Password)
        self.new_pwd.setMinimumHeight(28)
        pwd_form.addRow("新密码:", self.new_pwd)
        self.confirm_pwd = QLineEdit()
        self.confirm_pwd.setEchoMode(QLineEdit.Password)
        self.confirm_pwd.setMinimumHeight(28)
        pwd_form.addRow("确认密码:", self.confirm_pwd)

        pwd_btn_row = QHBoxLayout()
        self.pwd_status = QLabel("")
        self.pwd_status.setStyleSheet(f"color: {tc['text_muted']};")
        pwd_btn_row.addWidget(self.pwd_status, 1)
        change_btn = QPushButton("修改密码")
        change_btn.setMinimumHeight(32)
        change_btn.clicked.connect(self._on_change_password)
        pwd_btn_row.addWidget(change_btn)
        pwd_form.addRow("", pwd_btn_row)

        account_layout.addWidget(pwd_group)
        account_layout.addStretch()

        tabs.addTab(account_tab, "账户")

    def _on_change_password(self):
        old = self.old_pwd.text()
        new = self.new_pwd.text()
        confirm = self.confirm_pwd.text()
        if not old or not new:
            self.pwd_status.setText("请填写旧密码和新密码")
            self.pwd_status.setStyleSheet("color: #e74c3c;")
            return
        if new != confirm:
            self.pwd_status.setText("两次输入的新密码不一致")
            self.pwd_status.setStyleSheet("color: #e74c3c;")
            return
        from core.password_policy import validate_password
        ok, reason = validate_password(new)
        if not ok:
            self.pwd_status.setText(reason)
            self.pwd_status.setStyleSheet("color: #e74c3c;")
            return
        from core.auth import AuthManager
        auth = AuthManager()
        if auth.change_password(self._user.username, old, new):
            self.pwd_status.setText("密码已修改！")
            self.pwd_status.setStyleSheet("color: #27ae60;")
            self.old_pwd.clear()
            self.new_pwd.clear()
            self.confirm_pwd.clear()
        else:
            self.pwd_status.setText("旧密码错误")
            self.pwd_status.setStyleSheet("color: #e74c3c;")

    def get_account_values(self) -> dict:
        """返回账户设置值（供 main_window 更新用户信息）"""
        if not hasattr(self, 'dept_combo'):
            return {}
        return {
            "department": self.dept_combo.currentText(),
            "team": self.team_combo.currentText(),
            "display_name": self.display_edit.text().strip(),
        }

    def get_values(self) -> dict:
        """返回所有用户设置值"""
        return {
            "font_family": self.font_combo.currentText(),
            "chart_dpi": self.dpi_spin.value(),
            "animations_enabled": self.animations_check.isChecked(),
            "nelson_rules_enabled": self.nelson_check.isChecked(),
            "msa_grr_acceptable": self.grr_accept.value(),
            "msa_ndc_threshold": self.ndc_spin.value(),
            "alert_min_violations": self.alert_min_spin.value(),
            "alert_popup_enabled": self.alert_popup_check.isChecked(),
            "alert_sound_enabled": self.alert_sound_check.isChecked(),
            "alert_log_enabled": self.alert_log_check.isChecked(),
        }
