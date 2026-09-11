"""QAM Harness — 质量工程 AI Agent 核心层（v3.8.0 Phase 1）。

分层约定: 本包为纯逻辑层，**不依赖 Qt**（与 analysis/ 同规则），UI 通过
`ui/agent_bridge.py` 组装 `AgentContext` 后注入。

构成:
  - conversation: 多轮对话与工具调用记录
  - tools:        工具注册表 + 面向本软件能力的工具实现
  - engine:       Agent 主循环（LLM 工具调用 / 离线规则路由两条路径）
"""
from core.agent.conversation import Conversation, Message
from core.agent.engine import AgentEngine, AgentReply, ToolCallRecord
from core.agent.tools import (
    AgentContext, ToolRegistry, ToolResult, ToolSpec, build_default_registry,
)

__all__ = [
    "Conversation", "Message",
    "AgentEngine", "AgentReply", "ToolCallRecord",
    "AgentContext", "ToolRegistry", "ToolResult", "ToolSpec",
    "build_default_registry",
]
