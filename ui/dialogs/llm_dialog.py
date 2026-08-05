"""AI 分析助手对话框 — 自然语言交互式问答 + 知识库检索"""

import html

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QSplitter, QWidget, QComboBox,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont

from ui.theme import colors as theme_colors


class LLMWorker(QThread):
    token_received = Signal(str)
    finished = Signal(str)

    def __init__(self, client, prompt):
        super().__init__()
        self.client = client
        self.prompt = prompt

    def run(self):
        full = ""
        try:
            for token in self.client.generate(self.prompt):
                full += token
                self.token_received.emit(token)
        except Exception as e:
            full = f"错误: {str(e)}"
        self.finished.emit(full)


class LLMDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI 分析助手")
        self.setMinimumSize(640, 500)
        self.resize(680, 560)

        from core.llm_client import LLMClient
        self.llm = LLMClient()
        self.worker = None

        self._setup_ui()
        # 安装事件过滤器以捕获回车键（QDialog 默认会拦截 Enter）
        self.input_box.installEventFilter(self)

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                if obj == self.input_box:
                    self._send_message()
                    return True
                elif obj == self.kb_input:
                    self._kb_search()
                    return True
        return super().eventFilter(obj, event)

    def _setup_ui(self):
        tc = theme_colors(self)
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("AI 分析助手")
        title.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        header.addWidget(title)
        status = "在线" if hasattr(self, 'llm') and self.llm.available else ""
        self.llm_status = QLabel("" if not status else f" {status}")
        self.llm_status.setFont(QFont("Microsoft YaHei", 9))
        self.llm_status.setStyleSheet(
            f"color: {'#2ca02c' if status == '在线' else tc['text_muted']}; "
            "padding: 2px 8px; border-radius: 4px;"
        )
        header.addWidget(self.llm_status)
        header.addStretch()
        # 模型选择
        self.model_combo = QComboBox(); self.model_combo.setMaximumWidth(200)
        from core.llm_client import OLLAMA_MODELS, OPENAI_MODELS
        self.model_combo.addItems(OLLAMA_MODELS)
        self.model_combo.currentTextChanged.connect(self._on_model_change)
        header.addWidget(QLabel("模型:")); header.addWidget(self.model_combo)
        self.provider_lbl = QLabel("Ollama"); self.provider_lbl.setFont(QFont("Microsoft YaHei", 8))
        self.provider_lbl.setStyleSheet(f"color: {tc['text_muted']};")
        header.addWidget(self.provider_lbl)
        clear_btn = QPushButton("清空")
        clear_btn.setFixedSize(50, 24)
        clear_btn.clicked.connect(self._clear_chat)
        header.addWidget(clear_btn)
        layout.addLayout(header)

        kb_row = QHBoxLayout()
        kb_row.setSpacing(6)
        self.kb_input = QLineEdit()
        self.kb_input.setFont(QFont("Microsoft YaHei", 10))
        self.kb_input.setPlaceholderText("搜索知识库：GRR 判定 / AQL 抽样表 / 宽放率 / 控制图常数 ...")
        self.kb_input.setMinimumHeight(30)
        self.kb_input.setStyleSheet(
            f"QLineEdit {{ border: 1px solid {tc['border_light']}; border-radius: 6px; "
            f"padding: 4px 10px; background: {tc['bg_card']}; }}"
        )
        self.kb_input.installEventFilter(self)
        kb_row.addWidget(self.kb_input, 1)

        kb_btn = QPushButton("检索")
        kb_btn.setFont(QFont("Microsoft YaHei", 10))
        kb_btn.setFixedSize(56, 30)
        kb_btn.setCursor(Qt.PointingHandCursor)
        kb_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {tc['accent_bright']}; "
            f"border: 1px solid {tc['accent']}; border-radius: 6px; }}"
            f"QPushButton:hover {{ background: {tc['bg_hover']}; }}"
        )
        kb_btn.clicked.connect(self._kb_search)
        kb_row.addWidget(kb_btn)
        layout.addLayout(kb_row)

        self.chat_view = QTextEdit()
        self.chat_view.setReadOnly(True)
        self.chat_view.setFont(QFont("Microsoft YaHei", 11))
        self.chat_view.setStyleSheet(
            f"QTextEdit {{ background: {tc['bg_card']}; border: 1px solid {tc['border_light']}; "
            f"border-radius: 6px; padding: 8px; }}"
        )
        layout.addWidget(self.chat_view, 1)

        input_row = QHBoxLayout()
        input_row.setSpacing(6)
        self.input_box = QLineEdit()
        self.input_box.setFont(QFont("Microsoft YaHei", 11))
        self.input_box.setPlaceholderText("输入问题，例如：CPK=0.8 代表什么？如何改进？")
        self.input_box.setMinimumHeight(38)
        self.input_box.setStyleSheet(
            f"QLineEdit {{ border: 1px solid {tc['border_light']}; border-radius: 6px; "
            f"padding: 6px 10px; background: {tc['bg_card']}; }}"
        )
        self.input_box.installEventFilter(self)
        input_row.addWidget(self.input_box, 1)

        self.send_btn = QPushButton("发送")
        self.send_btn.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        self.send_btn.setMinimumHeight(38)
        self.send_btn.setMinimumWidth(70)
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.setStyleSheet(
            f"QPushButton {{ background: {tc['accent']}; color: white; border: none; "
            f"border-radius: 6px; padding: 6px 16px; }}"
            f"QPushButton:hover {{ background: {tc['accent_dark']}; }}"
            f"QPushButton:disabled {{ background: {tc['text_muted']}; color: {tc['bg_card']}; }}"
        )
        self.send_btn.clicked.connect(self._send_message)
        input_row.addWidget(self.send_btn)
        layout.addLayout(input_row)

        if not self.llm.available:
            self.llm_status.setText(" 离线")
            self.llm_status.setStyleSheet(f"color: {tc['text_muted']}; padding: 2px 8px;")
            self.append_msg("system",
                "Ollama 服务未连接，已进入离线模式。\n"
                "提问时将从内置知识库（标准/术语/判定表/六西格玛）检索作答。\n"
                "也可以直接使用上方检索框按关键词查询知识库。\n\n"
                "完整 AI 问答：安装 Ollama (https://ollama.com) 后运行 "
                "ollama pull qwen2.5:7b && ollama serve")
        else:
            self.llm_status.setText(" 在线")
            self.llm_status.setStyleSheet("color: #2ca02c; padding: 2px 8px;")
            self.append_msg("system", "AI 助手已就绪（已接入知识库增强）。可以基于当前分析数据提问，例如：\n"
                           "• 这个 CPK 结果是否满足要求？\n• 如何改进过程能力？\n"
                           "• GRR 25% 可以接受吗？")

    def _send_message(self):
        # 线程保护：正在等待 AI 回复时不允许发送新消息
        if self.worker and self.worker.isRunning():
            self.append_msg("system", "AI 正在生成回复，请稍候...")
            return
        text = self.input_box.text().strip()
        if not text:
            return
        self.input_box.clear()
        self.send_btn.setEnabled(False)
        self.send_btn.setText("...")
        self.append_msg("user", text)

        if not self.llm.available:
            self._offline_reply(text)
            return

        from core.context_builder import ContextBuilder
        cb = ContextBuilder()

        if hasattr(self.parent(), 'analyses'):
            full_prompt = cb.build_prompt(self.parent().analyses, text)
        else:
            full_prompt = text

        from core.knowledge_base import get_knowledge_base
        full_prompt = get_knowledge_base().enrich_prompt(full_prompt, text)

        self.worker = LLMWorker(self.llm, full_prompt)
        self.worker.token_received.connect(self._on_token)
        self.worker.finished.connect(self._on_finished)
        self._current_ai_msg = ""
        self.worker.start()

    def _on_token(self, token: str):
        self._current_ai_msg += token

    def _on_finished(self, full_text: str):
        self.append_msg("assistant", full_text)
        self.send_btn.setEnabled(True)
        self.send_btn.setText("发送")
        self._current_ai_msg = ""

    def _offline_reply(self, text: str):
        from core.knowledge_base import get_knowledge_base
        reply = get_knowledge_base().offline_answer(text)
        if reply is None:
            reply = ("知识库中未找到完全匹配的内容。\n"
                     "可尝试关键词：CPK / GRR / 控制图 / AQL / 样本量 / 宽放率 / OEE / DMAIC ...\n\n"
                     "或安装 Ollama 获得完整 AI 问答：https://ollama.com")
        self.append_msg("assistant", reply)
        self.send_btn.setEnabled(True)
        self.send_btn.setText("发送")

    def _on_model_change(self, model: str):
        from core.llm_client import OPENAI_MODELS
        if model in OPENAI_MODELS:
            self.llm.set_model(model, "openai"); self.provider_lbl.setText("OpenAI")
        else:
            self.llm.set_model(model, "ollama"); self.provider_lbl.setText("Ollama")
        status = "在线" if self.llm.available else "离线"
        self.llm_status.setText(f" {status}")

    def _kb_search(self):
        query = self.kb_input.text().strip()
        if not query:
            return
        from core.knowledge_base import get_knowledge_base
        kb = get_knowledge_base()
        if not kb.available:
            self.append_msg("system", "知识库不可用（config/knowledge 目录缺失）")
            return
        hits = kb.search(query, top_k=5)
        if not hits:
            self.append_msg("system", f"知识库中未找到与「{query}」相关的内容")
            return
        lines = [f"知识库检索「{query}」— {len(hits)} 条结果："]
        for i, h in enumerate(hits, 1):
            lines.append(f"\n━━ 【{i}】{h.title}（{h.category_label()}，相关度 {h.score:.2f}）━━")
            lines.append(h.format_full())
        self.append_msg("system", "\n".join(lines))

    def append_msg(self, role: str, text: str):
        if role == "system":
            prefix = "系统"
            color = "#8e8ea0"
        elif role == "user":
            prefix = "你"
            color = "#4da6ff"
        else:
            prefix = "AI"
            color = "#2ca02c"

        safe = html.escape(text).replace("\n", "<br>")
        self.chat_view.append(
            f"<p style='margin:4px 0'><b style='color:{color}'>{prefix}:</b> {safe}</p>"
        )
        self.chat_view.verticalScrollBar().setValue(
            self.chat_view.verticalScrollBar().maximum()
        )

    def _clear_chat(self):
        self.chat_view.clear()
