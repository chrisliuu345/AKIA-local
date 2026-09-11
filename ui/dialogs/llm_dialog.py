"""QAM Harness 对话界面（v3.8.0 Phase 1）。

在原「AI 分析助手」对话框基础上升级:
  - 接入 AgentEngine：可调用软件内 16 个工具（SPC/能力/MSA/假设检验/OEE/成本/
    告警/五链/产线/实时/知识库/指标解读），离线时走规则路由同样能出结论
  - 可读性: 聊天气泡（左右分栏）、Markdown 轻渲染、工具调用卡片（含参数/耗时/
    状态）、上下文条（数据表/分析数/告警数/工具数）、等宽代码块
  - 保留原能力: Ollama/OpenAI 兼容模型选择与持久化、知识库检索、导出、清空
"""
from __future__ import annotations

import html
import re

from PySide6.QtCore import QEvent, QSettings, Qt, QThread, Signal
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QTextEdit, QVBoxLayout, QWidget,
)

from ui.font_config import get_ui_font
from ui.theme import colors as theme_colors

PRESET_QUESTIONS = [
    ("数据概况", "当前导入了哪些数据？用一句话总结表、行数与可用数值列。"),
    ("能力分析", "用当前数据做过程能力分析，给出 Cpk、PPM 与改善建议。"),
    ("控制图判异", "对当前数据跑 I-MR 控制图，说明判异点与可能的特殊原因。"),
    ("测量系统", "评估当前测量系统（Gage R&R），%GRR 与 ndc 是否可接受？"),
    ("实时 OEE", "实时 OEE 现在是多少？主要损失在哪一环？"),
    ("成本损失", "当前成本损失是多少？按损失从大到小说明来源。"),
    ("告警处置", "有哪些未确认告警？建议的处置顺序是什么？"),
    ("五链状态", "五链（FMEA → 控制计划 → PPAP → 8D）现在是什么状态？"),
]


class AgentWorker(QThread):
    """后台执行 Agent 事件流 — 通过信号回主线程渲染。"""

    tool_called = Signal(object)
    token_received = Signal(str)
    replied = Signal(object)
    failed = Signal(str)

    def __init__(self, engine, question: str):
        super().__init__()
        self.engine = engine
        self.question = question

    def run(self):
        try:
            for kind, payload in self.engine.respond_stream(self.question):
                if self.isInterruptionRequested():
                    return
                if kind == "tool":
                    self.tool_called.emit(payload)
                elif kind == "token":
                    self.token_received.emit(payload)
                elif kind == "done":
                    self.replied.emit(payload)
        except Exception as e:                      # 兜底: 不让异常冒到 Qt 事件循环
            self.failed.emit(f"{type(e).__name__}: {e}")


def md_to_html(text: str) -> str:
    """轻量 Markdown → Qt 富文本（标题/加粗/行内代码/代码块/列表）。"""
    text = text or ""
    blocks = re.split(r"```", text)
    out: list[str] = []
    for idx, block in enumerate(blocks):
        if idx % 2 == 1:                            # 代码块
            out.append("<pre style='background:#14141e;color:#c8ccd6;"
                       "padding:8px 10px;border-left:3px solid #1b5faa;'>"
                       + html.escape(block.strip()) + "</pre>")
            continue
        safe = html.escape(block)
        safe = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", safe)
        safe = re.sub(r"`([^`]+)`",
                      r"<code style='background:#35354a;color:#e0a040;'>\1</code>", safe)
        lines = []
        for line in safe.split("\n"):
            stripped = line.strip()
            if stripped.startswith("### "):
                lines.append(f"<div style='color:#4da6ff;font-weight:bold;'>"
                             f"{stripped[4:]}</div>")
            elif stripped.startswith(("- ", "* ")):
                lines.append("&nbsp;&nbsp;• " + stripped[2:])
            elif re.match(r"^\d+\.\s", stripped):
                lines.append("&nbsp;&nbsp;" + stripped)
            else:
                lines.append(line)
        out.append("<br>".join(lines))
    return "".join(out)


class QAMHarnessDialog(QDialog):
    """QAM Harness 对话窗口 — Agent 工具调用 + 知识库 + 模型管理。"""

    def __init__(self, parent=None, engine=None):
        super().__init__(parent)
        self.setWindowTitle("QAM Harness — 质量工程 AI Agent")
        # 独立顶层窗口：可自由移动/最大化/全屏，不随主窗口模态锁定
        self.setWindowFlags(Qt.Window | Qt.WindowMinimizeButtonHint
                            | Qt.WindowMaximizeButtonHint
                            | Qt.WindowCloseButtonHint)
        self.setWindowModality(Qt.NonModal)
        self.setSizeGripEnabled(True)
        self.setMinimumSize(860, 560)
        self._apply_initial_geometry(parent)

        from core.llm_client import LLMClient
        from ui.agent_bridge import build_engine

        # 已注入 engine（测试/内嵌用法）时沿用它自带的 LLM，避免被覆盖
        self.llm = getattr(engine, "llm", None) if engine is not None else None
        if self.llm is None:
            self.llm = LLMClient.from_config()
            saved_model = QSettings("QA-Tool", "LLM").value("model", "")
            if saved_model:
                try:
                    self.llm.set_model(saved_model, self.llm.provider)
                except Exception:
                    pass
        if engine is None:
            engine, self.agent_context = build_engine(parent, llm=self.llm)
        else:
            self.agent_context = getattr(engine, "context", None)
            if getattr(engine, "llm", None) is None:
                engine.set_llm(self.llm)
        self.engine = engine
        self._last_provider_id = self.llm.provider

        self.worker: AgentWorker | None = None
        self._history: list[tuple[str, str]] = []
        self._current_ai_msg = ""
        self._streaming_started = False
        self._stream_anchor: int | None = None

        self._setup_ui()
        self.input_box.installEventFilter(self)
        self._refresh_context_bar()
        self._greet()

    def _apply_initial_geometry(self, parent):
        """按可用屏幕确定初始尺寸，并居中于父窗口后夹取到屏幕内，避免遮挡。"""
        screen = QApplication.primaryScreen()
        if screen is None:
            self.resize(1000, 720)
            return
        avail = screen.availableGeometry()
        width = max(900, min(1180, int(avail.width() * 0.82)))
        height = max(620, min(880, int(avail.height() * 0.86)))
        self.resize(width, height)
        if parent is not None and parent.isVisible():
            center = parent.frameGeometry().center()
            x = max(avail.left(), min(center.x() - width // 2,
                                      avail.right() - width))
            y = max(avail.top(), min(center.y() - height // 2,
                                     avail.bottom() - height))
            self.move(x, y)

    # ------------------------------------------------------------ UI
    def _setup_ui(self):
        tc = theme_colors(self)
        self.setStyleSheet(f"QDialog {{ background-color: {tc['bg_body']}; }}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        # ---- 标题行 ----
        header = QHBoxLayout()
        header.setSpacing(8)
        title_box = QVBoxLayout()
        title_box.setSpacing(0)
        title = QLabel("QAM Harness")
        title.setFont(QFont(get_ui_font(), 17, QFont.Bold))
        title.setStyleSheet(f"color: {tc['text_primary']};")
        subtitle = QLabel("质量工程 AI Agent · 本地工具调用 + 知识库（数据不出本机）")
        subtitle.setFont(QFont(get_ui_font(), 9))
        subtitle.setStyleSheet(f"color: {tc['text_muted']};")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)

        self.llm_status = QLabel("")
        self.llm_status.setFont(QFont(get_ui_font(), 9, QFont.Bold))
        header.addWidget(self.llm_status)
        header.addStretch()

        for text, tip, slot, width in (
                ("重连", "重新检测模型服务", self._retry_connection, 54),
                ("导出", "导出对话为 Markdown", self._export_history, 54),
                ("清空", "清空对话", self._clear_chat, 54)):
            btn = QPushButton(text)
            btn.setFixedSize(width, 26)
            btn.setToolTip(tip)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(
                f"QPushButton {{ background: {tc['bg_card']}; color: {tc['text_secondary']};"
                f"border: 1px solid {tc['border']}; border-radius: 6px; }}"
                f"QPushButton:hover {{ background: {tc['bg_hover']}; color: {tc['text_primary']}; }}")
            btn.clicked.connect(slot)
            header.addWidget(btn)
        layout.addLayout(header)

        # ---- 供应商 / 模型名称（完全自定义，无下拉选择）----
        model_row = QHBoxLayout()
        model_row.setSpacing(8)
        model_row.addWidget(QLabel("供应商:"))
        self.provider_combo = QComboBox()
        self.provider_combo.setMinimumWidth(150)
        self._populate_providers()
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        self.provider_combo.activated.connect(self._on_provider_activated)
        model_row.addWidget(self.provider_combo)
        model_row.addWidget(QLabel("模型名称:"))
        self.model_edit = QLineEdit()
        self.model_edit.setMinimumWidth(220)
        self.model_edit.setPlaceholderText(
            "完全自定义，如 qwen2.5:7b / gpt-4o-mini / deepseek-chat")
        self.model_edit.setToolTip("直接输入任意模型名；回车或失去焦点生效")
        self.model_edit.returnPressed.connect(self._apply_model_name)
        self.model_edit.editingFinished.connect(self._apply_model_name)
        model_row.addWidget(self.model_edit, 1)
        layout.addLayout(model_row)
        self._sync_model_edit()

        # ---- 上下文 / 工具条 ----
        self.context_label = QLabel("")
        self.context_label.setFont(QFont(get_ui_font(), 9))
        self.context_label.setStyleSheet(
            f"color: {tc['text_secondary']}; background: {tc['bg_card']};"
            f"border: 1px solid {tc['border_light']}; border-radius: 6px; padding: 5px 10px;")
        self.context_label.setWordWrap(True)
        layout.addWidget(self.context_label)

        # ---- 预设问题 ----
        preset_widget = QWidget()
        preset_layout = QHBoxLayout(preset_widget)
        preset_layout.setContentsMargins(0, 0, 0, 0)
        preset_layout.setSpacing(4)
        for label, question in PRESET_QUESTIONS:
            btn = QPushButton(label)
            btn.setFont(QFont(get_ui_font(), 9))
            btn.setFixedHeight(24)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(question)
            btn.setStyleSheet(
                f"QPushButton {{ background: {tc['bg_card']}; color: {tc['accent_bright']};"
                f"border: 1px solid {tc['border_light']}; border-radius: 11px; padding: 2px 10px; }}"
                f"QPushButton:hover {{ background: {tc['bg_hover']};"
                f"border-color: {tc['accent']}; }}")
            btn.clicked.connect(lambda _, q=question: self._fill_preset(q))
            preset_layout.addWidget(btn)
        preset_layout.addStretch()
        layout.addWidget(preset_widget)

        # ---- 对话区 ----
        self.chat_view = QTextEdit()
        self.chat_view.setReadOnly(True)
        self.chat_view.setFont(QFont(get_ui_font(), 11))
        self.chat_view.setStyleSheet(
            f"QTextEdit {{ background: {tc['bg_body']}; border: 1px solid {tc['border_light']};"
            f"border-radius: 8px; padding: 10px 12px; line-height: 150%; }}")
        layout.addWidget(self.chat_view, 1)

        # ---- 输入区 ----
        input_row = QHBoxLayout()
        input_row.setSpacing(8)
        self.input_box = QLineEdit()
        self.input_box.setFont(QFont(get_ui_font(), 11))
        self.input_box.setPlaceholderText(
            "输入问题（Enter 发送）— 例: 用当前数据做能力分析 / 最近告警怎么处置")
        self.input_box.setMinimumHeight(38)
        self.input_box.setStyleSheet(
            f"QLineEdit {{ border: 1px solid {tc['border']}; border-radius: 8px;"
            f"padding: 6px 12px; background: {tc['bg_card']}; }}"
            f"QLineEdit:focus {{ border-color: {tc['accent_bright']}; }}")
        self.input_box.installEventFilter(self)
        input_row.addWidget(self.input_box, 1)

        self.send_btn = QPushButton("发送")
        self.send_btn.setFont(QFont(get_ui_font(), 11, QFont.Bold))
        self.send_btn.setMinimumHeight(38)
        self.send_btn.setMinimumWidth(80)
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.setStyleSheet(
            f"QPushButton {{ background: {tc['accent']}; color: white; border: none;"
            f"border-radius: 8px; padding: 6px 18px; }}"
            f"QPushButton:hover {{ background: {tc['accent_bright']}; }}"
            f"QPushButton:disabled {{ background: {tc['text_muted']}; }}")
        self.send_btn.clicked.connect(self._send_message)
        input_row.addWidget(self.send_btn)
        layout.addLayout(input_row)

        # ---- 知识库检索（保留原快捷入口）----
        kb_row = QHBoxLayout()
        kb_row.setSpacing(6)
        self.kb_input = QLineEdit()
        self.kb_input.setFont(QFont(get_ui_font(), 10))
        self.kb_input.setPlaceholderText(
            "知识库直查（Enter）：GRR 判定 / AQL 抽样表 / SMED / 8D / 控制图选择 …")
        self.kb_input.setMinimumHeight(30)
        self.kb_input.setStyleSheet(
            f"QLineEdit {{ border: 1px solid {tc['border_light']}; border-radius: 6px;"
            f"padding: 4px 10px; background: {tc['bg_card']}; }}")
        self.kb_input.installEventFilter(self)
        kb_row.addWidget(self.kb_input, 1)
        kb_btn = QPushButton("检索")
        kb_btn.setFixedSize(56, 30)
        kb_btn.setCursor(Qt.PointingHandCursor)
        kb_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {tc['accent_bright']};"
            f"border: 1px solid {tc['accent']}; border-radius: 6px; }}"
            f"QPushButton:hover {{ background: {tc['bg_hover']}; }}")
        kb_btn.clicked.connect(self._kb_search)
        kb_row.addWidget(kb_btn)
        layout.addLayout(kb_row)

        self._update_status()

    # ------------------------------------------------------------ 事件
    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if obj is self.input_box:
                self._send_message()
                return True
            if obj is self.kb_input:
                self._kb_search()
                return True
        return super().eventFilter(obj, event)

    # ------------------------------------------------------------ 模型管理
    def _populate_providers(self):
        from core.agent.providers import PROVIDERS, requires_key
        from config.settings import get_secret

        self.provider_combo.clear()
        for pid, spec in PROVIDERS.items():
            configured = (not requires_key(pid)) or bool(get_secret(f"llm_{pid}_api_key", ""))
            label = spec.label if configured else f"{spec.label}（未配置密钥）"
            self.provider_combo.addItem(label, pid)
        idx = self.provider_combo.findData(self.llm.provider)
        if idx >= 0:
            self.provider_combo.setCurrentIndex(idx)

    def _on_provider_changed(self, *_):
        pid = str(self.provider_combo.currentData() or "ollama")
        if pid == self.llm.provider:
            self._sync_model_edit()
            self._update_status()
            self._refresh_context_bar()
            return
        self._activate_provider(pid)

    def _on_provider_activated(self, index: int):
        """用户点击下拉项时触发。

        QComboBox 重复选择同一项不会发出 currentIndexChanged，
        因此"点击当前未配置密钥的供应商"需要走 activated 补弹输入框。
        """
        pid = str(self.provider_combo.itemData(index) or "")
        from core.agent.providers import requires_key

        if not pid or pid != self.provider_combo.currentData():
            return                          # 切换路径由 _on_provider_changed 处理
        if not requires_key(pid) or self._stored_key(pid):
            return                          # 已有密钥 → 不弹窗
        if self._activate_provider(pid):
            self.append_msg("system", f"已接入 {self._provider_label()}。")

    def _activate_provider(self, pid: str) -> bool:
        """切换到 pid；云供应商缺密钥时先弹输入框（取消则回退选择）。"""
        from core.agent.providers import get_provider, requires_key

        spec = get_provider(pid)
        key = self._stored_key(pid)
        if requires_key(pid) and not key:
            key = self._prompt_api_key(spec)
            if key is None:
                self._restore_provider_selection()
                return False
        try:
            from config.settings import get_setting
            model = (get_setting(f"llm_{pid}_model", "") or spec.default_model())
            base = get_setting(f"llm_{pid}_api_base", "")
            self.llm = type(self.llm)(model=model, provider=pid, api_key=key,
                                      api_base=base)
            self.engine.set_llm(self.llm)
            self._last_provider_id = pid
            self._mark_provider_configured(pid)
        except Exception as e:
            self.append_msg("system", f"切换供应商失败: {e}")
            self._restore_provider_selection()
            return False
        self._sync_model_edit()
        self._update_status()
        self._refresh_context_bar()
        return True

    @staticmethod
    def _stored_key(pid: str) -> str:
        from config.settings import get_secret

        return get_secret(f"llm_{pid}_api_key", "")

    def _prompt_api_key(self, spec) -> str | None:
        """弹出密钥输入框并加密落盘；取消/空输入返回 None。"""
        from ui.dialogs.api_key_dialog import ApiKeyDialog

        dlg = ApiKeyDialog(spec.id, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            self.append_msg("system", f"已取消接入 {spec.label}（未保存 API Key）")
            return None
        key = dlg.key().strip()
        if not key:
            return None
        from config.settings import save_config

        save_config({f"llm_{spec.id}_api_key": key})
        return key

    def _mark_provider_configured(self, pid: str):
        """密钥配置成功后去掉下拉项的"（未配置密钥）"标注。"""
        from core.agent.providers import get_provider

        idx = self.provider_combo.findData(pid)
        if idx < 0:
            return
        label = get_provider(pid).label
        if self.provider_combo.itemText(idx) != label:
            blocked = self.provider_combo.blockSignals(True)
            self.provider_combo.setItemText(idx, label)
            self.provider_combo.blockSignals(blocked)

    def _restore_provider_selection(self):
        target = getattr(self, "_last_provider_id", None) or self.llm.provider
        idx = self.provider_combo.findData(target)
        if idx >= 0 and idx != self.provider_combo.currentIndex():
            self.provider_combo.blockSignals(True)
            self.provider_combo.setCurrentIndex(idx)
            self.provider_combo.blockSignals(False)
        self._update_status()
        self._refresh_context_bar()

    def _provider_label(self) -> str:
        spec = getattr(self.llm, "spec", None)
        return getattr(spec, "label", None) or getattr(self.llm, "provider", "本地")

    def _sync_model_edit(self):
        """供应商切换/初始化时同步模型名：记住的同供应商输入 > 配置 > 当前/默认。"""
        from config.settings import get_setting
        from core.agent.providers import get_provider

        pid = self.llm.provider
        settings = QSettings("QA-Tool", "LLM")
        saved_model = str(settings.value("model", "") or "")
        saved_provider = str(settings.value("provider", "") or "")
        name = saved_model if saved_model and saved_provider == pid else ""
        if not name:
            name = str(get_setting(f"llm_{pid}_model", "") or "")
        if not name:
            name = getattr(self.llm, "model", "") or get_provider(pid).default_model()
        self.model_edit.setText(str(name or ""))

    def _apply_model_name(self):
        """完全自定义模型名：回车/失焦即生效并持久化 QSettings。"""
        name = self.model_edit.text().strip()
        if not name:
            self._sync_model_edit()
            return
        if name == getattr(self.llm, "model", ""):
            return
        try:
            self.llm.set_model(name, self.llm.provider)
        except Exception:
            pass
        settings = QSettings("QA-Tool", "LLM")
        settings.setValue("model", name)
        settings.setValue("provider", self.llm.provider)
        self._update_status()

    def _retry_connection(self):
        self.llm.available = self.llm._check_available()
        self._update_status()
        self.append_msg("system", "连接检测: " + ("在线" if self.llm.available else "仍离线（工具模式可用）"))

    def _update_status(self):
        tc = theme_colors(self)
        if self.llm.available:
            self.llm_status.setText(f"● 在线 · {self._provider_label()}")
            self.llm_status.setStyleSheet("color: #27ae60; padding: 2px 6px;")
        else:
            self.llm_status.setText("● 离线 · 工具模式")
            self.llm_status.setStyleSheet(f"color: {tc['text_muted']}; padding: 2px 6px;")
        self._update_privacy_hint()
        self._refresh_context_bar()

    def _update_privacy_hint(self):
        """未配置密钥 / 未授权云调用 → 在状态栏给出可执行提示。"""
        from core.agent.privacy import consent_status
        from core.agent.providers import requires_key
        from config.settings import get_secret

        pid = self.llm.provider
        self.privacy_note = ""
        if requires_key(pid) and not get_secret(f"llm_{pid}_api_key", ""):
            self.privacy_note = f"{self._provider_label()} 未配置密钥（设置 → QAM Harness）"
        else:
            state = consent_status(pid, getattr(self.llm, "api_base", ""))
            if state.startswith("未授权"):
                self.privacy_note = "首次云调用会弹出隐私确认"

    def _refresh_context_bar(self):
        ctx = self.agent_context
        summary = ctx.summary() if ctx is not None else "无上下文"
        tools = self.engine.tool_count()
        model_state = (self.engine.provider_label() if self.engine.llm_available
                       else "离线工具模式")
        note = f"　|　{self.privacy_note}" if getattr(self, "privacy_note", "") else ""
        self.context_label.setText(
            f"上下文: {summary}　|　可用工具 {tools} 个"
            f"（SPC/能力/MSA/检验/DOE/回归/可靠性/时序/IE/成本/实时/五链/知识库）"
            f"　|　{model_state}{note}")

    # ------------------------------------------------------------ 渲染
    @staticmethod
    def _bubble(inner_html: str, role: str, tc: dict) -> str:
        """左右分栏气泡 — 用户靠右（蓝），助手靠左（卡片色）。"""
        if role == "user":
            bg, border = "#1f3550", "#2c5f92"
            spacer = "<td width='16%'></td>"
            cells = f"{spacer}<td style='background:{bg};border:1px solid {border};" \
                    f"border-radius:10px;padding:9px 12px;color:{tc['text_primary']};'>" \
                    f"{inner_html}</td>"
        else:
            bg, border = tc["bg_card"], tc["border_light"]
            spacer = "<td width='16%'></td>"
            cells = f"<td style='background:{bg};border:1px solid {border};" \
                    f"border-radius:10px;padding:9px 12px;color:{tc['text_primary']};'>" \
                    f"{inner_html}</td>{spacer}"
        return (f"<table width='100%' cellspacing='0' cellpadding='0' "
                f"style='margin:6px 0'><tr>{cells}</tr></table>")

    def append_msg(self, role: str, text: str, markdown: bool = True):
        tc = theme_colors(self)
        if role == "system":
            body = (f"<span style='color:{tc['text_muted']};font-size:10pt;'>"
                    f"ⓘ {html.escape(text)}</span>")
            self.chat_view.append(
                f"<div style='margin:4px 0;color:{tc['text_muted']};'>{body}</div>")
        else:
            body = md_to_html(text) if markdown else html.escape(text).replace("\n", "<br>")
            self.chat_view.append(self._bubble(body, role, tc))
        self._scroll_bottom()

    def _append_tool_card(self, record):
        tc = theme_colors(self)
        ok = getattr(record, "ok", False)
        color = "#27ae60" if ok else "#e74c3c"
        bg = "#1c2b22" if ok else "#2b1f1f"
        state = "成功" if ok else "失败"
        args = ", ".join(f"{k}={v}" for k, v in (getattr(record, "args", {}) or {}).items())
        summary = getattr(record, "summary", "") or getattr(record, "error", "")
        summary_html = html.escape(summary[:600]).replace("\n", "<br>")
        ms = getattr(record, "duration_ms", 0.0)
        card = (
            f"<table width='100%' cellspacing='0' cellpadding='0' style='margin:6px 0'><tr>"
            f"<td width='16%'></td>"
            f"<td style='background:{bg};border-left:3px solid {color};"
            f"border-radius:6px;padding:8px 12px;'>"
            f"<span style='color:{color};font-weight:bold;'>🔧 {html.escape(record.name)}</span>"
            f"<span style='color:{tc['text_muted']};font-size:9pt;'>"
            f"　{args}　·　{state}　·　{ms:.0f} ms</span><br>"
            f"<span style='color:{tc['text_secondary']};font-size:10pt;'>{summary_html}</span>"
            f"</td><td width='16%'></td></tr></table>")
        self.chat_view.append(card)
        self._scroll_bottom()

    def _scroll_bottom(self):
        bar = self.chat_view.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _greet(self):
        ctx = self.agent_context
        lines = []
        if self.llm.available:
            lines.append(f"QAM Harness 已就绪（{self._provider_label()}）。"
                         "可直接提问，我会自动调用软件内工具取数分析。")
        else:
            lines.append("未检测到 Ollama/云 API，已进入**离线工具模式**："
                         "仍可调用本机分析引擎（SPC/能力/MSA/OEE/成本/告警/五链/知识库），"
                         "结论附带判定阈值与改善建议。")
            lines.append("需要自然语言长文解读时，可安装 Ollama（`ollama serve`）后点「重连」。")
        if ctx is not None and not ctx.data_frames:
            lines.append("提示: 先「文件 → 导入数据文件」再提问，我就能对真实数据做分析。")
        lines.append("试试上方标签，或直接问: “用当前数据做过程能力分析”。")
        self.append_msg("assistant", "\n\n".join(lines))

    # ------------------------------------------------------------ 发送
    def _fill_preset(self, question: str):
        self.input_box.setText(question)
        self.input_box.setFocus()

    def _send_message(self):
        if self.worker is not None and self.worker.isRunning():
            self.append_msg("system", "正在生成回复，请稍候…")
            return
        text = self.input_box.text().strip()
        if not text:
            return

        # ---- 隐私门（主线程弹窗；阻止后自动降级本地工具模式）----
        from core.agent.privacy import (
            cloud_enabled, grant_consent, is_cloud_endpoint, needs_consent,
            set_cloud_enabled,
        )
        pid = self.engine.provider_id()
        cloud = is_cloud_endpoint(pid, self.engine.api_base())
        if self.engine.llm_available and cloud and (
                needs_consent(pid, self.engine.api_base()) or not cloud_enabled()):
            from ui.dialogs.privacy_dialog import CloudPrivacyDialog
            dlg = CloudPrivacyDialog(self, self.engine.egress_preview(text),
                                     self._provider_label())
            dlg.exec()
            if dlg.consent:
                grant_consent(pid)
                set_cloud_enabled(True)
            elif dlg.use_local_only:
                self.engine.force_offline = True
                self.append_msg("system", "本次仅使用本地工具（不调用云 API）")
            else:
                return

        self.input_box.clear()
        self.send_btn.setEnabled(False)
        self.send_btn.setText("…")
        self.append_msg("user", text, markdown=False)
        self._history.append(("user", text))
        self._current_ai_msg = ""
        self._streaming_started = False
        self._stream_anchor = None

        self.worker = AgentWorker(self.engine, text)
        self.worker.tool_called.connect(self._on_tool)
        self.worker.token_received.connect(self._on_token)
        self.worker.replied.connect(self._on_replied)
        self.worker.failed.connect(self._on_failed)
        self.worker.start()

    def _on_tool(self, record):
        # 工具卡片到达时结束当前流式气泡，避免后续 token 更新覆盖卡片
        if self._streaming_started:
            self._streaming_started = False
            self._stream_anchor = None
        self._append_tool_card(record)

    def _on_token(self, token: str):
        self._current_ai_msg += token
        tc = theme_colors(self)
        body = md_to_html(self._current_ai_msg)
        block = self._bubble(body, "assistant", tc)
        if not self._streaming_started:
            # 记录气泡起点锚点（append 之前），后续 token 用整段替换
            cursor = self.chat_view.textCursor()
            cursor.movePosition(QTextCursor.End)
            self._stream_anchor = cursor.position()
            self.chat_view.append(block)
            self._streaming_started = True
        else:
            cursor = QTextCursor(self.chat_view.document())
            cursor.setPosition(self._stream_anchor or 0)
            cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
            cursor.removeSelectedText()
            cursor.insertHtml(block)
        self._scroll_bottom()

    def _on_replied(self, reply):
        if not self._streaming_started and getattr(reply, "text", ""):
            self.append_msg("assistant", reply.text)
        self._history.append(("assistant", getattr(reply, "text", "")))
        self._streaming_started = False
        self._stream_anchor = None
        self._current_ai_msg = ""
        self.send_btn.setEnabled(True)
        self.send_btn.setText("发送")
        mode = "离线工具模式" if getattr(reply, "offline", True) else getattr(reply, "provider", "")
        tools = len(getattr(reply, "tool_calls", []) or [])
        self.append_msg("system",
                        f"完成（{mode}）· 工具调用 {tools} 次 · "
                        f"{getattr(reply, 'elapsed_ms', 0) / 1000:.1f}s")
        self._refresh_context_bar()
        self.engine.force_offline = False      # 仅对当次生效（此时工作线程已结束）

    def _on_failed(self, message: str):
        self._streaming_started = False
        self._stream_anchor = None
        self._current_ai_msg = ""
        self.append_msg("system", f"执行失败: {message}")
        self.send_btn.setEnabled(True)
        self.send_btn.setText("发送")
        self.engine.force_offline = False

    # ------------------------------------------------------------ 知识库 / 导出
    def _kb_search(self):
        query = self.kb_input.text().strip()
        if not query:
            return
        result = self.engine.registry.call("search_knowledge", {"query": query, "top_k": 5},
                                           self.agent_context)
        if not result.ok:
            self.append_msg("system", result.error or "知识库不可用")
            return
        self.append_msg("assistant", f"**知识库检索「{query}」**\n\n{result.text}")

    def _export_history(self):
        if not len(self.engine.conversation):
            self.append_msg("system", "没有对话历史可导出")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出对话历史", "qam_harness_chat.md", "Markdown (*.md)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.engine.conversation.to_markdown())
        except OSError as e:
            QMessageBox.warning(self, "导出失败", str(e))
            return
        self.append_msg("system", f"对话已导出: {path}")

    def _clear_chat(self):
        self.chat_view.clear()
        self._history.clear()
        try:
            self.engine.conversation.clear()
        except Exception:
            pass
        self._current_ai_msg = ""
        self._streaming_started = False
        self._stream_anchor = None
        self._greet()

    # ------------------------------------------------------------ 关闭
    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            # 逐个断开信号 — 对 worker 形态变化（测试替身/未来重构）保持健壮
            for signal_name, slot in (("tool_called", self._on_tool),
                                      ("token_received", self._on_token),
                                      ("replied", self._on_replied),
                                      ("failed", self._on_failed)):
                signal = getattr(self.worker, signal_name, None)
                if signal is None:
                    continue
                try:
                    signal.disconnect(slot)
                except (RuntimeError, TypeError, AttributeError):
                    pass
            request_stop = getattr(self.worker, "requestInterruption", None)
            if callable(request_stop):
                request_stop()
            try:
                self.llm.stop()
            except Exception:
                pass
            wait = getattr(self.worker, "wait", None)
            if callable(wait) and not wait(1500):
                terminate = getattr(self.worker, "terminate", None)
                if callable(terminate):
                    terminate()
        super().closeEvent(event)


# 兼容旧引用（v3.8.0 起界面名称统一为 QAM Harness）
LLMDialog = QAMHarnessDialog
