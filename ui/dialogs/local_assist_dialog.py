"""评分与异常辅助 — 用户显式打开后，只读已有 SPC / 能力结果和未确认告警。

不新开页面。关闭开关时不生成建议，也不写操作日志。
"""
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
    QPushButton, QVBoxLayout,
)

from ui.font_config import get_ui_font
from ui.theme import colors as theme_colors

_SETTING = "local_assist_enabled"


class LocalAssistDialog(QDialog):
    """本机评分与异常建议。统计判定和告警确认都留在原处。"""

    def __init__(self, analyses=None, alerts=None, parent=None):
        super().__init__(parent)
        self._analyses = dict(analyses or {})
        self._alerts = list(alerts or [])
        self._last = None
        self.setWindowTitle("评分与异常辅助")
        self.resize(760, 520)
        self._setup_ui()

    def _setup_ui(self):
        from config.settings import get_setting

        tc = theme_colors(self)
        self.setStyleSheet(f"QDialog {{ background-color: {tc['bg_body']}; }}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        note = QLabel(
            "默认关闭。打开后只引用当前分析和未确认告警，给出建议；"
            "不改统计判定，也不代替人工确认。不调用外部模型。")
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {tc['text_secondary']};")
        layout.addWidget(note)

        self.enable_box = QCheckBox("启用本机辅助")
        self.enable_box.blockSignals(True)
        self.enable_box.setChecked(bool(get_setting(_SETTING, False)))
        self.enable_box.blockSignals(False)
        self.enable_box.toggled.connect(self._on_toggle)
        layout.addWidget(self.enable_box)

        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText("可选：这次想看什么，例如「看厚度的判异和未确认告警」")
        layout.addWidget(self.note_edit)

        bar = QHBoxLayout()
        self.run_btn = QPushButton("生成建议")
        self.run_btn.setEnabled(self.enable_box.isChecked())
        self.run_btn.clicked.connect(self.run)
        bar.addWidget(self.run_btn)
        bar.addStretch()
        layout.addLayout(bar)

        self.view = QPlainTextEdit()
        self.view.setReadOnly(True)
        self.view.setFont(QFont(get_ui_font(), 10))
        self.view.setStyleSheet(
            f"QPlainTextEdit {{ background: {tc['bg_card']}; color: {tc['text_primary']};"
            f"border: 1px solid {tc['border']}; border-radius: 6px; }}")
        self.view.setPlainText("辅助未启用。统计判定和告警确认保持原样。")
        layout.addWidget(self.view, 1)

    def _on_toggle(self, checked: bool):
        from config.settings import save_config

        save_config({_SETTING: bool(checked)})
        self.run_btn.setEnabled(bool(checked))
        if not checked:
            self.view.setPlainText("辅助未启用。统计判定和告警确认保持原样。")
            self._last = None

    def run(self):
        from core.local_assist import advise

        result = advise(enabled=self.enable_box.isChecked(),
                        analyses=self._analyses, alerts=self._alerts,
                        question=self.note_edit.text())
        self._last = result
        self.view.setPlainText(result.text)
