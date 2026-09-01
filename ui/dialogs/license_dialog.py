"""
版本信息对话框 — v3.2.0+ 不再需要许可证
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
)
from PySide6.QtCore import Qt

from config.settings import APP_NAME, APP_VERSION
from core.license import LicenseManager


class LicenseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} 版本信息")
        self.setMinimumSize(400, 300)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # 应用名称和版本
        title = QLabel(f"{APP_NAME}")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #1b5faa; padding: 8px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        version = QLabel(f"版本 {APP_VERSION}")
        version.setStyleSheet("font-size: 16px; color: #666; padding: 4px;")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)

        # 分隔线
        line = QLabel()
        line.setStyleSheet("border-top: 1px solid #ddd; margin: 16px 0;")
        layout.addWidget(line)

        # 版本信息
        info_text = f"""
<b>功能特性:</b>
• 35 个分析模块（SPC/能力/MSA/假设检验/DOE/IE工具）
• AI 智能洞察（Ollama/OpenAI API）
• ESP32 硬件数据采集与监控
• 完整报告输出（PDF/Excel/Word/HTML）

<b>技术栈:</b>
• Python 3.14 + PySide6 (Qt)
• NumPy / SciPy / pandas / matplotlib
• scikit-learn / SHAP

<b>测试:</b>
• 820+ pytest 测试通过
"""
        info_label = QLabel(info_text)
        info_label.setStyleSheet("font-size: 12px; padding: 8px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # 机器ID（用于调试）
        machine_id = LicenseManager.get_machine_id()
        mid_label = QLabel(f"机器ID: {machine_id}")
        mid_label.setStyleSheet("color: #999; font-size: 10px; padding: 4px;")
        mid_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(mid_label)

        # 关闭按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.setMinimumWidth(100)
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
