"""QAM Harness 对话管理 — 多轮上下文 + 工具调用记录（纯 stdlib，无 Qt）。

职责:
  - 保存 user / assistant / tool / system 消息，按轮数裁剪避免 prompt 膨胀
  - 为 LLM 生成"对话历史"文本片段
  - 导出 Markdown 对话记录（UI「导出」按钮复用）
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field

ROLE_LABELS = {
    "system": "系统",
    "user": "用户",
    "assistant": "QAM Harness",
    "tool": "工具",
}


@dataclass
class Message:
    role: str                      # system / user / assistant / tool
    content: str
    tool_name: str = ""
    tool_args: dict = field(default_factory=dict)
    tool_ok: bool = True
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Message:
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in data.items() if k in known})

    def prompt_line(self, max_chars: int = 600) -> str:
        text = (self.content or "").strip().replace("\n", " ")
        if len(text) > max_chars:
            text = text[:max_chars] + "…"
        if self.role == "tool":
            state = "成功" if self.tool_ok else "失败"
            return f"[工具执行·{state}] {self.tool_name}: {text}"
        return f"{ROLE_LABELS.get(self.role, self.role)}: {text}"


class Conversation:
    """对话历史 — 默认保留最近 max_turns 轮（1 轮 = 用户 + 助手）。"""

    def __init__(self, max_turns: int = 12, system_prompt: str = ""):
        self.max_turns = max(1, int(max_turns))
        self._messages: list[Message] = []
        if system_prompt:
            self._messages.append(Message("system", system_prompt))

    # ---------- 写入 ----------
    def add(self, role: str, content: str, **kwargs) -> Message:
        msg = Message(role=role, content=content, **kwargs)
        self._messages.append(msg)
        self._trim()
        return msg

    def add_user(self, text: str) -> Message:
        return self.add("user", text)

    def add_assistant(self, text: str) -> Message:
        return self.add("assistant", text)

    def add_tool_result(self, name: str, ok: bool, content: str,
                        args: dict | None = None) -> Message:
        return self.add("tool", content, tool_name=name, tool_ok=ok,
                        tool_args=dict(args or {}))

    def set_system_prompt(self, text: str) -> None:
        if self._messages and self._messages[0].role == "system":
            self._messages[0] = Message("system", text)
        else:
            self._messages.insert(0, Message("system", text))

    def clear(self) -> None:
        system = self._messages[:1] if (self._messages
                                        and self._messages[0].role == "system") else []
        self._messages = list(system)

    def _trim(self) -> None:
        limit = self.max_turns * 2 + 1        # +1 为系统提示
        if len(self._messages) > limit:
            head = self._messages[:1] if self._messages[0].role == "system" else []
            self._messages = head + self._messages[-(limit - len(head)):]

    # ---------- 读取 ----------
    def messages(self) -> list[Message]:
        return list(self._messages)

    def history(self, limit: int | None = None) -> list[Message]:
        items = [m for m in self._messages if m.role != "system"]
        return items[-limit:] if limit else items

    def tool_calls(self, limit: int | None = None) -> list[Message]:
        items = [m for m in self._messages if m.role == "tool"]
        return items[-limit:] if limit else items

    def last_user_question(self) -> str:
        for msg in reversed(self._messages):
            if msg.role == "user":
                return msg.content
        return ""

    def prompt_history(self, limit: int = 6, max_chars: int = 500) -> str:
        recent = [m for m in self.history() if m.role in ("user", "assistant")][-limit:]
        return "\n".join(m.prompt_line(max_chars) for m in recent)

    def __len__(self) -> int:
        return len([m for m in self._messages if m.role != "system"])

    # ---------- 导出 ----------
    def to_markdown(self, title: str = "QAM Harness 对话记录") -> str:
        lines = [f"# {title}", ""]
        for msg in self._messages:
            if msg.role == "system":
                continue
            if msg.role == "tool":
                state = "成功" if msg.tool_ok else "失败"
                args = ", ".join(f"{k}={v}" for k, v in (msg.tool_args or {}).items())
                lines.append(f"> 🔧 工具 `{msg.tool_name}`（{state}）"
                             + (f" 参数: {args}" if args else ""))
                lines.append("")
                lines.append("```")
                lines.append(msg.content.strip())
                lines.append("```")
                lines.append("")
                continue
            label = ROLE_LABELS.get(msg.role, msg.role)
            when = time.strftime("%H:%M:%S", time.localtime(msg.ts))
            lines.append(f"**{label}**（{when}）")
            lines.append("")
            lines.append(msg.content.strip())
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"
