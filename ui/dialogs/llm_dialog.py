"""AI 分析助手对话框 V2 — 预设问题 + 对话历史 + 增强上下文 + 模型持久化"""

import html

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QWidget, QComboBox, QFileDialog,
)
from PySide6.QtCore import Qt, QThread, Signal, QSettings
from PySide6.QtGui import QFont

from ui.theme import colors as theme_colors

# ── 预设问题模板 ──
PRESET_QUESTIONS = [
    ("SPC判异", "控制图出现超出控制限的点，可能的原因和改善措施？"),
    ("CPK解读", "CPK=0.8 代表什么水平？如何系统性地提升至1.33？"),
    ("GRR判定", "GRR=25% 是否可以接受？如何改进测量系统？"),
    ("控制图选择", "对于需要控制产品外观缺陷率的过程，应选哪种控制图？"),
    ("分布识别", "数据不服从正态分布时，如何进行过程能力分析？"),
    ("DOE建议", "如何用DOE找出影响产品尺寸变异的关键因子？"),
    ("OEE改善", "OEE只有62%，如何从六大损失角度系统改善？"),
    ("线平衡", "装配线平衡率只有72%，如何通过ECRS原则优化？"),
]

HISTORY_MAX = 20


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
                if self.isInterruptionRequested():
                    break
                full += token
                self.token_received.emit(token)
        except Exception as e:
            full = f"错误: {str(e)}"
        self.finished.emit(full)


class LLMDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI 分析助手")
        self.setMinimumSize(700, 560)
        self.resize(720, 600)

        from core.llm_client import LLMClient
        # ── 从 QSettings 恢复上次模型选择 ──
        s = QSettings("QA-Tool", "LLM")
        saved_model = s.value("model", "")
        saved_provider = s.value("provider", "ollama")
        self.llm = LLMClient()
        if saved_model:
            try:
                self.llm.set_model(saved_model, saved_provider)
            except Exception:
                pass

        self.worker = None
        self._history: list = []  # [(role, text), ...]
        self._current_ai_msg = ""

        self._setup_ui()
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
        layout.setSpacing(6)

        # ── 顶部标题栏 ──
        header = QHBoxLayout()
        title = QLabel("AI 分析助手")
        title.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        header.addWidget(title)

        self.llm_status = QLabel("")
        self.llm_status.setFont(QFont("Microsoft YaHei", 9))
        header.addWidget(self.llm_status)
        header.addStretch()

        # 模型选择
        self.model_combo = QComboBox()
        self.model_combo.setMaximumWidth(180)
        from core.llm_client import OLLAMA_MODELS, OPENAI_MODELS
        self.model_combo.addItems(list(OLLAMA_MODELS) + list(OPENAI_MODELS))
        # 恢复上次选择
        s = QSettings("QA-Tool", "LLM")
        saved = s.value("model", "")
        if saved and self.model_combo.findText(saved) >= 0:
            self.model_combo.setCurrentText(saved)
        self.model_combo.currentTextChanged.connect(self._on_model_change)
        header.addWidget(QLabel("模型:"))
        header.addWidget(self.model_combo)

        self.provider_lbl = QLabel(self._provider_label())
        self.provider_lbl.setFont(QFont("Microsoft YaHei", 8))
        self.provider_lbl.setStyleSheet(f"color: {tc['text_muted']};")
        header.addWidget(self.provider_lbl)

        # 操作按钮: 重试 / 导出 / 清空
        retry_btn = QPushButton("重连")
        retry_btn.setFixedSize(40, 24)
        retry_btn.setToolTip("重新检测 Ollama/API 连接")
        retry_btn.clicked.connect(self._retry_connection)
        header.addWidget(retry_btn)

        export_btn = QPushButton("导出")
        export_btn.setFixedSize(40, 24)
        export_btn.setToolTip("导出对话历史为 Markdown")
        export_btn.clicked.connect(self._export_history)
        header.addWidget(export_btn)

        clear_btn = QPushButton("清空")
        clear_btn.setFixedSize(40, 24)
        clear_btn.clicked.connect(self._clear_chat)
        header.addWidget(clear_btn)
        layout.addLayout(header)

        # ── 预设问题模板 ──
        preset_widget = QWidget()
        preset_layout = QHBoxLayout(preset_widget)
        preset_layout.setContentsMargins(0, 0, 0, 0)
        preset_layout.setSpacing(4)
        self._preset_btns = []
        for label, question in PRESET_QUESTIONS:
            btn = QPushButton(label)
            btn.setFont(QFont("Microsoft YaHei", 8))
            btn.setFixedHeight(22)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(question[:60] + "…")
            btn.setStyleSheet(
                f"QPushButton {{ background: {tc['bg_card']}; color: {tc['accent_bright']}; "
                f"border: 1px solid {tc['border_light']}; border-radius: 10px; padding: 2px 8px; }}"
                f"QPushButton:hover {{ background: {tc['bg_hover']}; border-color: {tc['accent']}; }}"
            )
            btn.clicked.connect(lambda _, q=question: self._fill_preset(q))
            preset_layout.addWidget(btn)
            self._preset_btns.append(btn)
        preset_layout.addStretch()
        layout.addWidget(preset_widget)

        # ── 知识库检索行 ──
        kb_row = QHBoxLayout()
        kb_row.setSpacing(6)
        self.kb_input = QLineEdit()
        self.kb_input.setFont(QFont("Microsoft YaHei", 10))
        self.kb_input.setPlaceholderText("搜索知识库：GRR 判定 / AQL 抽样表 / SMED / 8D / 控制图选择 ...")
        self.kb_input.setMinimumHeight(28)
        self.kb_input.setStyleSheet(
            f"QLineEdit {{ border: 1px solid {tc['border_light']}; border-radius: 6px; "
            f"padding: 4px 8px; background: {tc['bg_card']}; }}"
        )
        self.kb_input.installEventFilter(self)
        kb_row.addWidget(self.kb_input, 1)
        kb_btn = QPushButton("检索")
        kb_btn.setFont(QFont("Microsoft YaHei", 10))
        kb_btn.setFixedSize(50, 28)
        kb_btn.setCursor(Qt.PointingHandCursor)
        kb_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {tc['accent_bright']}; "
            f"border: 1px solid {tc['accent']}; border-radius: 6px; }}"
            f"QPushButton:hover {{ background: {tc['bg_hover']}; }}"
        )
        kb_btn.clicked.connect(self._kb_search)
        kb_row.addWidget(kb_btn)
        layout.addLayout(kb_row)

        # ── 对话显示区 ──
        self.chat_view = QTextEdit()
        self.chat_view.setReadOnly(True)
        self.chat_view.setFont(QFont("Microsoft YaHei", 11))
        self.chat_view.setStyleSheet(
            f"QTextEdit {{ background: {tc['bg_card']}; border: 1px solid {tc['border_light']}; "
            f"border-radius: 6px; padding: 8px; }}"
        )
        layout.addWidget(self.chat_view, 1)

        # ── 输入行 ──
        input_row = QHBoxLayout()
        input_row.setSpacing(6)
        self.input_box = QLineEdit()
        self.input_box.setFont(QFont("Microsoft YaHei", 11))
        self.input_box.setPlaceholderText("输入问题，或点击上方模板快速提问…")
        self.input_box.setMinimumHeight(36)
        self.input_box.setStyleSheet(
            f"QLineEdit {{ border: 1px solid {tc['border_light']}; border-radius: 6px; "
            f"padding: 6px 10px; background: {tc['bg_card']}; }}"
        )
        self.input_box.installEventFilter(self)
        input_row.addWidget(self.input_box, 1)

        self.send_btn = QPushButton("发送")
        self.send_btn.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        self.send_btn.setMinimumHeight(36)
        self.send_btn.setMinimumWidth(66)
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.setStyleSheet(
            f"QPushButton {{ background: {tc['accent']}; color: white; border: none; "
            f"border-radius: 6px; padding: 6px 14px; }}"
            f"QPushButton:hover {{ background: {tc['accent_dark']}; }}"
            f"QPushButton:disabled {{ background: {tc['text_muted']}; color: {tc['bg_card']}; }}"
        )
        self.send_btn.clicked.connect(self._send_message)
        input_row.addWidget(self.send_btn)
        layout.addLayout(input_row)

        # ── 初始状态 ──
        self._update_status()
        if not self.llm.available:
            self.append_msg("system",
                "Ollama 服务未连接，已进入离线模式。\n"
                "提问时将从内置知识库（术语/标准/判定表/六西格玛/工程工具）检索作答。\n"
                "也可以直接使用上方检索框按关键词查询知识库。\n\n"
                "完整 AI 问答：安装 Ollama (https://ollama.com) 后运行\n"
                "ollama pull qwen2.5:7b && ollama serve")
        else:
            self.append_msg("system",
                "AI 助手已就绪（124条知识库增强 + 8个预设场景模板）。\n"
                "可以基于当前分析数据提问，或点击上方标签快速开始。")

    # ── 预设问题 ──
    def _fill_preset(self, question: str):
        self.input_box.setText(question)
        self.input_box.setFocus()

    # ── 模型配置持久化 ──
    def _provider_label(self) -> str:
        return "OpenAI" if self.llm.provider == "openai" else "Ollama"

    def _update_status(self):
        tc = theme_colors(self)
        if self.llm.available:
            self.llm_status.setText(" 在线")
            self.llm_status.setStyleSheet("color: #2ca02c; padding: 2px 8px;")
        else:
            self.llm_status.setText(" 离线")
            self.llm_status.setStyleSheet(f"color: {tc['text_muted']}; padding: 2px 8px;")

    def _on_model_change(self, model: str):
        from core.llm_client import OPENAI_MODELS
        if model in OPENAI_MODELS:
            self.llm.set_model(model, "openai")
        else:
            self.llm.set_model(model, "ollama")
        self.provider_lbl.setText(self._provider_label())
        self._update_status()
        # 持久化
        s = QSettings("QA-Tool", "LLM")
        s.setValue("model", model)
        s.setValue("provider", self.llm.provider)

    def _retry_connection(self):
        self.llm.available = self.llm._check_available()
        self._update_status()
        status = "在线" if self.llm.available else "仍离线"
        self.append_msg("system", f"连接检测: {status}")

    def _export_history(self):
        if not self._history:
            self.append_msg("system", "没有对话历史可导出")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出对话历史", "chat_history.md", "Markdown (*.md)"
        )
        if not path:
            return
        lines = ["# QA-Tool AI 分析助手 — 对话记录\n"]
        for role, text in self._history:
            label = {"user": "你", "assistant": "AI", "system": "系统"}.get(role, role)
            lines.append(f"**{label}**: {text}\n")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        self.append_msg("system", f"对话历史已导出到: {path}")

    # ── 发送消息 ──
    def _send_message(self):
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
        self._history.append(("user", text))

        if not self.llm.available:
            self._offline_reply(text)
            return

        # ── 构建增强上下文 ──
        full_prompt = self._build_context_prompt(text)

        self.worker = LLMWorker(self.llm, full_prompt)
        self.worker.token_received.connect(self._on_token)
        self.worker.finished.connect(self._on_finished)
        self._current_ai_msg = ""
        self.worker.start()

    def _build_context_prompt(self, question: str) -> str:
        """构建增强提示词：分析结果 + 数据画像 + 知识库 + 对话历史"""
        parts = []

        # 1. 当前分析结果摘要
        parent = self.parent()
        if parent and hasattr(parent, 'analyses') and parent.analyses:
            from core.context_builder import ContextBuilder
            cb = ContextBuilder()
            analysis_ctx = cb.build_prompt(parent.analyses, question)
            parts.append(analysis_ctx)

        # 2. 数据画像摘要
        if parent and hasattr(parent, 'profile_result') and parent.profile_result:
            prof = parent.profile_result
            keys = list(prof.keys())[:3]  # 最多3个sheet
            lines = ["数据画像:"]
            for k in keys:
                v = prof[k]
                if isinstance(v, dict):
                    lines.append(f"  {k}: {v.get('rows','?')}行×{v.get('cols','?')}列, "
                                f"缺失{v.get('missing_pct','?')}%")
            parts.append("\n".join(lines))

        # 3. 知识库检索
        from core.knowledge_base import get_knowledge_base
        kb = get_knowledge_base()
        if kb.available:
            hits = kb.search(question, top_k=3)
            if hits:
                kb_lines = ["相关知识库条目:"]
                for h in hits:
                    kb_lines.append(f"  [{h.category_label()}] {h.title}: {h.content[:300]}")
                parts.append("\n".join(kb_lines))

        # 4. 对话历史（最近6轮）
        if self._history:
            recent = self._history[-6:]
            hist_lines = ["对话历史:"]
            for role, msg in recent:
                hist_lines.append(f"  {role}: {msg[:200]}")
            parts.append("\n".join(hist_lines))

        # 5. 用户问题
        parts.append(f"\n用户问题: {question}")

        return "\n\n".join(parts)

    def _on_token(self, token: str):
        self._current_ai_msg += token
        # 流式刷新: append新段落, 后续token用cursor删除再重写
        if not hasattr(self, '_streaming_block_added') or not self._streaming_block_added:
            safe = html.escape(self._current_ai_msg).replace("\n", "<br>")
            self.chat_view.append(
                '<p style="margin:4px 0"><b style="color:#2ca02c">AI:</b> ' + safe + "</p>"
            )
            self._streaming_block_added = True
        else:
            cursor = self.chat_view.textCursor()
            cursor.movePosition(cursor.End)
            cursor.movePosition(cursor.StartOfBlock, cursor.KeepAnchor)
            cursor.removeSelectedText()
            safe = html.escape(self._current_ai_msg).replace("\n", "<br>")
            cursor.insertHtml(
                '<p style="margin:4px 0"><b style="color:#2ca02c">AI:</b> ' + safe + "</p>"
            )
        self.chat_view.verticalScrollBar().setValue(
            self.chat_view.verticalScrollBar().maximum()
        )

    def _on_finished(self, full_text: str):
        self._streaming_block_added = False
        self._history.append(("assistant", full_text))
        if len(self._history) > HISTORY_MAX * 2:
            self._history = self._history[-HISTORY_MAX * 2:]
        self.send_btn.setEnabled(True)
        self.send_btn.setText("发送")
        self._current_ai_msg = ""

    def _offline_reply(self, text: str):
        from core.knowledge_base import get_knowledge_base
        kb = get_knowledge_base()
        reply = kb.offline_answer(text) if kb.available else None
        if reply is None:
            reply = ("知识库中未找到完全匹配的内容。\n"
                     "可尝试关键词：CPK / GRR / 控制图 / AQL / 样本量 / 宽放率 / OEE / "
                     "SMED / 8D / FMEA / Weibull / DMAIC ...\n\n"
                     "或安装 Ollama 获得完整 AI 问答：https://ollama.com")
        self.append_msg("assistant", reply)
        self._history.append(("assistant", reply))
        self.send_btn.setEnabled(True)
        self.send_btn.setText("发送")

    # ── 知识库检索 ──
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
            source_tag = h.extra.get("source", "")
            src = f"，来源: {source_tag}" if source_tag else ""
            lines.append(f"\n━━ 【{i}】{h.title}（{h.category_label()}，相关度 {h.score:.2f}{src}）━━")
            lines.append(h.format_full())
        self.append_msg("system", "\n".join(lines))

    # ── 消息输出 ──
    def append_msg(self, role: str, text: str):
        if role == "system":
            prefix, color = "系统", "#8e8ea0"
        elif role == "user":
            prefix, color = "你", "#4da6ff"
        else:
            prefix, color = "AI", "#2ca02c"

        safe = html.escape(text).replace("\n", "<br>")
        self.chat_view.append(
            f"<p style='margin:4px 0'><b style='color:{color}'>{prefix}:</b> {safe}</p>"
        )
        self.chat_view.verticalScrollBar().setValue(
            self.chat_view.verticalScrollBar().maximum()
        )

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            # 先断开信号防止向已销毁控件发消息，再中断线程并掐断连接
            try:
                self.worker.token_received.disconnect(self._on_token)
                self.worker.finished.disconnect(self._on_finished)
            except RuntimeError:
                pass
            self.worker.requestInterruption()
            self.llm.stop()
            if not self.worker.wait(3000):
                self.worker.terminate()
                self.worker.wait(1000)
        super().closeEvent(event)

    def _clear_chat(self):
        self.chat_view.clear()
        self._history.clear()
