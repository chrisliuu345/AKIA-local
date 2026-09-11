"""云 API 隐私确认弹窗（v3.8.0 P2）—— 首次调用某云供应商时拦截。

三个出口:
  - 同意并继续 : 记录授权（按供应商记忆，只拦一次）
  - 仅用本地工具: 本次不调用云 API，降级到离线工具模式
  - 取消      : 放弃本次提问
"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout,
)

from ui.font_config import get_ui_font
from ui.theme import colors as theme_colors


class CloudPrivacyDialog(QDialog):
    def __init__(self, parent=None, preview=None, provider_label: str = ""):
        super().__init__(parent)
        self.preview = preview
        self.consent = False            # 同意云调用
        self.use_local_only = False     # 仅本次使用本地工具
        self.setWindowTitle("云 API 隐私确认 — QAM Harness")
        self.setMinimumSize(620, 460)
        self._setup_ui(provider_label)

    def _setup_ui(self, provider_label: str):
        tc = theme_colors(self)
        self.setStyleSheet(f"QDialog {{ background-color: {tc['bg_body']}; }}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        title = QLabel("即将调用云 API，请确认外发内容")
        title.setFont(QFont(get_ui_font(), 14, QFont.Bold))
        title.setStyleSheet(f"color: {tc['text_primary']};")
        layout.addWidget(title)

        sub = QLabel(
            f"供应商: {provider_label or getattr(self.preview, 'provider_label', '')}"
            "　·　目的是把本机分析结果交给大模型做自然语言解读。"
            "本操作按供应商只需确认一次，可随时在「设置 → QAM Harness」撤销。")
        sub.setWordWrap(True)
        sub.setStyleSheet(f"color: {tc['text_secondary']}; font-size: 10pt;")
        layout.addWidget(sub)

        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setFont(QFont(get_ui_font(), 10))
        self.detail.setStyleSheet(
            f"QTextEdit {{ background: {tc['bg_card']}; color: {tc['text_primary']};"
            f"border: 1px solid {tc['border_light']}; border-radius: 8px; padding: 10px; }}")
        text = self.preview.as_text() if self.preview is not None else "（无预览内容）"
        self.detail.setPlainText(text)
        layout.addWidget(self.detail, 1)

        note = QLabel("不会发送: 原始数据表、文件路径、API Key、告警历史全量内容。\n"
                      "敏感工艺参数建议改用本地 Ollama 或内网 OpenAI 兼容端点"
                      "（自定义端点 + 私网地址不会触发本确认）。")
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {tc['text_muted']}; font-size: 9pt;")
        layout.addWidget(note)

        row = QHBoxLayout()
        row.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setMinimumHeight(34)
        cancel_btn.setStyleSheet(
            f"QPushButton {{ background: {tc['bg_card']}; color: {tc['text_secondary']};"
            f"border: 1px solid {tc['border']}; border-radius: 6px; padding: 6px 18px; }}")
        cancel_btn.clicked.connect(self.reject)
        row.addWidget(cancel_btn)

        local_btn = QPushButton("仅用本地工具")
        local_btn.setMinimumHeight(34)
        local_btn.setToolTip("本次不调用云 API，改用本机分析引擎（SPC/能力/MSA/OEE/成本/告警…）")
        local_btn.setStyleSheet(
            f"QPushButton {{ background: {tc['bg_card']}; color: {tc['accent_bright']};"
            f"border: 1px solid {tc['accent']}; border-radius: 6px; padding: 6px 18px; }}")
        local_btn.clicked.connect(self._choose_local)
        row.addWidget(local_btn)

        ok_btn = QPushButton("同意并继续")
        ok_btn.setMinimumHeight(34)
        ok_btn.setDefault(True)
        ok_btn.setStyleSheet(
            f"QPushButton {{ background: {tc['accent']}; color: white; border: none;"
            f"border-radius: 6px; padding: 6px 20px; font-weight: bold; }}"
            f"QPushButton:hover {{ background: {tc['accent_bright']}; }}")
        ok_btn.clicked.connect(self._choose_cloud)
        row.addWidget(ok_btn)
        layout.addLayout(row)
        self.setFocusPolicy(Qt.StrongFocus)

    def _choose_cloud(self):
        self.consent = True
        self.use_local_only = False
        self.accept()

    def _choose_local(self):
        self.use_local_only = True
        self.consent = False
        self.accept()
