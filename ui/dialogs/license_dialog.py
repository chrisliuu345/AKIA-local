"""
许可证激活对话框
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTextEdit,
    QPushButton, QHBoxLayout, QMessageBox
)
from PySide6.QtCore import Qt

from core.license import license_manager, LicenseStatus


class LicenseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("QA-Tool 许可证激活")
        self.setMinimumSize(500, 400)
        self._setup_ui()
        self._refresh_status()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        self.status_label = QLabel("状态: 检查中...")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 14px; padding: 8px;")
        layout.addWidget(self.status_label)

        machine_id = license_manager.get_machine_id()
        mid_label = QLabel(f"本机机器指纹: {machine_id}")
        mid_label.setStyleSheet("color: #666; font-size: 12px; padding: 4px;")
        mid_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(mid_label)

        input_label = QLabel("请粘贴许可证文本:")
        input_label.setStyleSheet("padding-top: 12px;")
        layout.addWidget(input_label)

        self.license_input = QTextEdit()
        self.license_input.setPlaceholderText("在此粘贴 JSON 格式的许可证...")
        self.license_input.setStyleSheet("font-family: Consolas, monospace; font-size: 12px;")
        layout.addWidget(self.license_input)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.activate_btn = QPushButton("激活")
        self.activate_btn.setMinimumWidth(100)
        self.activate_btn.clicked.connect(self._on_activate)
        btn_layout.addWidget(self.activate_btn)

        self.close_btn = QPushButton("关闭")
        self.close_btn.setMinimumWidth(100)
        self.close_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.close_btn)

        layout.addLayout(btn_layout)

    def _on_activate(self):
        license_text = self.license_input.toPlainText().strip()
        if not license_text:
            QMessageBox.warning(self, "提示", "请输入许可证文本")
            return

        success, message = license_manager.activate(license_text)

        if success:
            QMessageBox.information(self, "成功", message)
            self._refresh_status()
            self.accept()
        else:
            QMessageBox.critical(self, "失败", message)

    def _refresh_status(self):
        status = license_manager.verify()
        info = license_manager.get_license_info()

        status_map = {
            LicenseStatus.VALID: ("已激活", "color: green;"),
            LicenseStatus.EXPIRED: ("已过期", "color: orange;"),
            LicenseStatus.INVALID: ("未激活", "color: red;"),
            LicenseStatus.TAMPERED: ("已篡改", "color: red;"),
            LicenseStatus.WRONG_MACHINE: ("机器不匹配", "color: red;"),
        }

        status_text, style = status_map.get(status, ("未知", "color: gray;"))
        extra = ""
        if status == LicenseStatus.VALID:
            if info.get('expires_at'):
                extra = f" | 到期: {info['expires_at']}"
            if info.get('licensee'):
                extra += f" | 被许可方: {info['licensee']}"

        self.status_label.setText(f"状态: {status_text}{extra}")
        self.status_label.setStyleSheet(f"font-weight: bold; font-size: 14px; padding: 8px; {style}")
