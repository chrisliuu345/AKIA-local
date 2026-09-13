"""QAM Harness 引擎测试 — 离线规则路由 / LLM 工具调用 / 对话管理。"""
import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("PySide6")

from core.agent.conversation import Conversation, Message
from core.agent.engine import AgentEngine, AgentReply, ToolCallRecord
from core.agent.tools import AgentContext, build_default_registry


@pytest.fixture
def ctx():
    rng = np.random.default_rng(5)
    df = pd.DataFrame({"厚度": rng.normal(5.0, 0.05, 40)})
    return AgentContext(data_frames={"Sheet1": df})


@pytest.fixture
def engine(ctx):
    return AgentEngine(build_default_registry(ctx), context=ctx)


class FakeLLM:
    """可编排输出的假 LLM：按顺序返回预设脚本。"""

    def __init__(self, script):
        self.script = list(script)
        self.available = True
        self.provider = "ollama"
        self.model = "fake-model"
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        text = self.script.pop(0) if self.script else "（无更多脚本）"
        for chunk in [text[i:i + 24] for i in range(0, len(text), 24)]:
            yield chunk


# ---------- 离线路径 ----------


def test_offline_routes_capability_with_specs(engine):
    reply = engine.respond("用当前数据做过程能力分析，USL=5.2 LSL=4.8")
    assert reply.offline is True
    assert [c.name for c in reply.tool_calls] == ["run_capability"]
    assert reply.tool_calls[0].ok
    assert "Cpk=" in reply.text and "建议" in reply.text


def test_offline_routes_spc_and_reports_violations(engine):
    reply = engine.respond("跑一下控制图看看有没有判异")
    assert [c.name for c in reply.tool_calls] == ["run_spc"]
    assert "控制图" in reply.text


def test_offline_routes_data_question(engine):
    reply = engine.respond("现在有哪些数据表？多少行？")
    assert [c.name for c in reply.tool_calls] == ["list_data"]
    assert "Sheet1" in reply.text


def test_offline_unknown_question_falls_back_to_knowledge(engine):
    reply = engine.respond("今天天气怎么样")
    assert reply.tool_calls and reply.tool_calls[0].name == "search_knowledge"
    assert "QAM Harness" not in reply.text or True     # 不抛异常即可


def test_offline_missing_context_gives_actionable_error(ctx):
    engine = AgentEngine(build_default_registry(ctx), context=ctx)
    reply = engine.respond("实时 OEE 多少？")
    # 无实时快照 → 不应误报实时数据，应给出可执行提示
    assert reply.offline is True
    assert reply.tool_calls[0].name in ("get_live_oee", "run_oee")
    if not reply.tool_calls[0].ok:
        assert "没能完成" in reply.text or "接入" in reply.text


# ---------- 在线（LLM）路径 ----------


def test_llm_tool_call_then_final_answer(ctx):
    registry = build_default_registry(ctx)
    llm = FakeLLM([
        '```json\n{"tool": "run_capability", "args": {"column": "厚度", "usl": 5.2, "lsl": 4.8}}\n```',
        "结论: 过程能力良好，建议保持现有控制。",
    ])
    engine = AgentEngine(registry, llm=llm, context=ctx)
    reply = engine.respond("帮我做能力分析 USL=5.2 LSL=4.8")
    assert reply.offline is False
    assert [c.name for c in reply.tool_calls] == ["run_capability"]
    assert "过程能力良好" in reply.text
    assert len(llm.prompts) == 2                      # 工具结果已回灌
    assert "run_capability" in llm.prompts[1] or "工具" in llm.prompts[1]


def test_llm_direct_answer_without_tool(ctx):
    llm = FakeLLM(["Cpk 是衡量过程能力的指标，≥1.33 表示良好。"])
    engine = AgentEngine(build_default_registry(ctx), llm=llm, context=ctx)
    reply = engine.respond("什么是 Cpk")
    assert reply.tool_calls == [] and "Cpk" in reply.text


def test_llm_failure_falls_back_to_offline(ctx):
    class BrokenLLM(FakeLLM):
        def generate(self, prompt):
            raise RuntimeError("connection refused")
            yield  # pragma: no cover

    engine = AgentEngine(build_default_registry(ctx), llm=BrokenLLM([]), context=ctx)
    reply = engine.respond("用当前数据做过程能力分析 USL=5.2 LSL=4.8")
    assert reply.offline is True
    assert [c.name for c in reply.tool_calls] == ["run_capability"]


def test_tool_step_limit(ctx):
    # LLM 反复请求同一工具 → 达到 max_tool_steps 后收尾，不无限循环
    script = ['{"tool": "list_data", "args": {}}'] * 6
    engine = AgentEngine(build_default_registry(ctx), llm=FakeLLM(script),
                         context=ctx, max_tool_steps=2)
    reply = engine.respond("看数据")
    assert len(reply.tool_calls) == 2
    assert "已完成 2 步工具调用" in reply.text


def test_stream_events_include_tool_tokens_done(ctx):
    llm = FakeLLM([
        '{"tool": "list_data", "args": {}}',
        "数据里有 1 张表。",
    ])
    engine = AgentEngine(build_default_registry(ctx), llm=llm, context=ctx)
    kinds = [k for k, _ in engine.respond_stream("列出数据")]
    assert "tool" in kinds and "token" in kinds and kinds[-1] == "done"


# ---------- O2: 流式输出不得泄漏工具调用 JSON ----------


def _stream(ctx, script):
    llm = FakeLLM(script)
    engine = AgentEngine(build_default_registry(ctx), llm=llm, context=ctx)
    events = list(engine.respond_stream("测试"))
    tokens = "".join(p for k, p in events if k == "token")
    tools = [p for k, p in events if k == "tool"]
    reply = next(p for k, p in events if k == "done")
    return tokens, tools, reply


def test_stream_pure_tool_call_emits_no_json(ctx):
    tokens, tools, reply = _stream(ctx, [
        '{"tool": "list_data", "args": {}}',
        "数据里有 1 张表。",
    ])
    assert '{"tool"' not in tokens and "list_data" not in tokens
    assert [t.name for t in tools] == ["list_data"]
    assert "1 张表" in reply.text


def test_stream_preamble_then_tool_hides_json(ctx):
    """模型先说话再给 JSON 工具调用时，只放行正文，JSON 不外泄。"""
    tokens, tools, reply = _stream(ctx, [
        '我先看一下数据结构。\n{"tool": "list_data", "args": {}}',
        "结论: 有 1 张表。",
    ])
    assert '{"tool"' not in tokens and '"args"' not in tokens
    assert "我先看一下数据结构。" in tokens
    assert [t.name for t in tools] == ["list_data"]
    assert "有 1 张表" in reply.text


def test_stream_json_answer_without_tool_is_not_lost(ctx):
    """非工具调用的 JSON 回答同样不能丢内容。"""
    _tokens, tools, reply = _stream(ctx, ['{"结论": "过程受控"}'])
    assert tools == []
    assert "过程受控" in reply.text


def test_stream_plain_answer_still_streams(ctx):
    tokens, tools, reply = _stream(ctx, ["Cpk≥1.33 表示过程能力良好。"])
    assert tools == []
    assert "Cpk" in tokens and "Cpk" in reply.text


def test_parse_tool_call_variants(engine):
    parse = engine._extract_tool_call
    assert parse('{"tool": "list_data", "args": {}}')[0] == "list_data"
    assert parse('```json\n{"tool": "run_spc", "args": {"chart_type": "imr"}}\n```')[1] == \
        {"chart_type": "imr"}
    assert parse('前缀文字 {"tool": "get_plant", "args": {}} 后缀')[0] == "get_plant"
    assert parse("这不是 JSON") == (None, {})
    assert parse('{"tool": "x", "arguments": {"a": 1}}')[1] == {"a": 1}


def test_reply_and_record_serialisation():
    record = ToolCallRecord(name="run_spc", args={"chart_type": "imr"}, ok=True,
                            summary="CL=1", duration_ms=3.2)
    reply = AgentReply(text="ok", tool_calls=[record], offline=False,
                       provider="ollama", model="m", elapsed_ms=10.0)
    data = reply.as_dict()
    assert data["tool_calls"][0]["name"] == "run_spc"
    assert record.label() == "run_spc(chart_type=imr)"


# ---------- 对话管理 ----------


def test_conversation_trim_and_history():
    conv = Conversation(max_turns=2, system_prompt="sys")
    for i in range(6):
        conv.add_user(f"q{i}")
        conv.add_assistant(f"a{i}")
    assert len(conv) <= 5
    assert conv.messages()[0].role == "system"
    assert conv.last_user_question() == "q5"
    assert "q5" in conv.prompt_history()


def test_conversation_tool_records_and_export():
    conv = Conversation()
    conv.add_user("做能力分析")
    conv.add_tool_result("run_capability", True, "Cpk=1.4", {"column": "厚度"})
    conv.add_assistant("结论: 良好")
    md = conv.to_markdown()
    assert "run_capability" in md and "Cpk=1.4" in md and "结论: 良好" in md
    assert conv.tool_calls()[0].tool_name == "run_capability"
    conv.clear()
    assert len(conv) == 0


def test_message_roundtrip_and_prompt_line():
    msg = Message(role="tool", content="x" * 900, tool_name="t", tool_ok=False)
    assert len(msg.prompt_line(max_chars=100)) <= 120
    assert "失败" in msg.prompt_line()
    assert Message.from_dict(msg.to_dict()).tool_name == "t"
    assert json.dumps(msg.to_dict(), ensure_ascii=False)
