"""云调用隐私门测试 — 外发预览 / 授权状态 / 引擎 fail-closed 行为。"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

import core.agent.privacy as privacy
from core.agent.engine import AgentEngine
from core.agent.tools import AgentContext, build_default_registry


@pytest.fixture
def store(monkeypatch):
    """隔离配置存储 — 不触碰真实 user_config.json。"""
    data: dict = {}
    monkeypatch.setattr(privacy, "_get_setting",
                        lambda key, default=None: data.get(key, default))

    def save(values: dict):
        data.update(values)

    monkeypatch.setattr("config.settings.save_config", save)
    return data


class FakeCloudLLM:
    available = True
    provider = "deepseek"
    model = "deepseek-chat"
    api_base = "https://api.deepseek.com/v1"

    def __init__(self):
        self.calls = 0

    def generate(self, prompt):
        self.calls += 1
        yield "云端回答"


@pytest.fixture
def ctx():
    import pandas as pd
    return AgentContext(data_frames={"Sheet1": pd.DataFrame({"a": [1, 2, 3]})})


# ---------- 外发预览 ----------


def test_egress_preview_lists_question_and_tools():
    class Record:
        name = "run_capability"
        summary = "Cpk=1.24" + "x" * 600
        error = ""
        data = {}

    preview = privacy.build_egress_preview(
        "deepseek", "deepseek-chat", "帮我做能力分析",
        tool_calls=[Record()], data_hint="表 Sheet1: a")
    text = preview.as_text()
    assert "DeepSeek" in text and "deepseek-chat" in text
    assert "帮我做能力分析" in text
    assert "run_capability" in text
    assert "约" in text and "字符" in text
    # 单个工具结果截断，避免预览过长
    assert len(preview.tool_summaries[0]) <= privacy.MAX_PREVIEW_CHARS + 1
    assert "原始数据表" in text               # 明确声明不上传的内容
    assert preview.estimated_chars > 0
    assert preview.as_dict()["provider"] == "deepseek"


def test_egress_preview_without_tools_and_strings():
    preview = privacy.build_egress_preview("openai", "gpt-4o-mini", "问题", ["工具结果"])
    assert preview.tool_summaries == ["工具结果"]
    assert "仅问题本身" in preview.as_text() or "工具结果" in preview.as_text()
    empty = privacy.build_egress_preview("openai", "", "")
    assert "（空）" in empty.as_text()


# ---------- 授权状态 ----------


def test_consent_flow_only_once(store):
    assert privacy.needs_consent("deepseek") is True
    privacy.grant_consent("deepseek")
    assert store[privacy.ack_key("deepseek")] is True
    assert privacy.needs_consent("deepseek") is False          # 只拦一次
    privacy.revoke_consent("deepseek")
    assert privacy.needs_consent("deepseek") is True           # 可撤销


def test_local_providers_never_need_consent(store):
    assert privacy.needs_consent("ollama") is False
    assert privacy.needs_consent("custom") is False                    # localhost
    assert privacy.needs_consent("custom", "http://192.168.1.9:8000") is False
    assert privacy.needs_consent("custom", "https://llm.corp.com/v1") is True


def test_cloud_enabled_default_off(store):
    assert privacy.cloud_enabled() is False
    privacy.set_cloud_enabled(True)
    assert privacy.cloud_enabled() is True


def test_consent_status_text(store):
    assert "无需授权" in privacy.consent_status("ollama")
    assert "未授权" in privacy.consent_status("openai")
    privacy.grant_consent("openai")
    assert "已授权" in privacy.consent_status("openai")


# ---------- 引擎行为（fail-closed）----------


def test_engine_blocks_cloud_without_consent(store, ctx):
    llm = FakeCloudLLM()
    engine = AgentEngine(build_default_registry(ctx), llm=llm, context=ctx)
    reply = engine.respond("用当前数据做过程能力分析 USL=4 LSL=2")
    assert llm.calls == 0                       # 绝未调用云 API
    assert reply.offline is True
    assert "云调用已在设置中关闭" in reply.text or "需先授权" in reply.text
    assert reply.tool_calls                     # 已降级到本地工具


def test_engine_allows_after_enable_and_consent(store, ctx):
    privacy.set_cloud_enabled(True)
    privacy.grant_consent("deepseek")
    llm = FakeCloudLLM()
    engine = AgentEngine(build_default_registry(ctx), llm=llm, context=ctx)
    reply = engine.respond("随便问问")
    assert llm.calls == 1 and reply.offline is False
    assert "云端回答" in reply.text


def test_engine_force_offline_for_single_turn(store, ctx):
    privacy.set_cloud_enabled(True)
    privacy.grant_consent("deepseek")
    llm = FakeCloudLLM()
    engine = AgentEngine(build_default_registry(ctx), llm=llm, context=ctx)
    engine.force_offline = True
    reply = engine.respond("用当前数据做过程能力分析 USL=4 LSL=2")
    assert llm.calls == 0
    assert "仅使用本地工具" in reply.text
    assert reply.offline is True


def test_engine_privacy_check_hook(store, ctx):
    """无 UI 的调用方可用 privacy_check 回调控制（返回 False 即拒绝）。"""
    privacy.set_cloud_enabled(True)          # 总开关需打开，回调才有机会决策
    seen = {}

    def deny(provider_id, preview):
        seen["provider"] = provider_id
        seen["preview"] = preview
        return False

    llm = FakeCloudLLM()
    engine = AgentEngine(build_default_registry(ctx), llm=llm, context=ctx,
                         privacy_check=deny)
    reply = engine.respond("测试")
    assert seen["provider"] == "deepseek"
    assert llm.calls == 0 and reply.offline is True
    assert "取消云调用" in reply.text


def test_engine_privacy_state_and_preview(store, ctx):
    llm = FakeCloudLLM()
    engine = AgentEngine(build_default_registry(ctx), llm=llm, context=ctx)
    assert engine.provider_id() == "deepseek"
    assert "未授权" in engine.privacy_state()
    privacy.grant_consent("deepseek")
    assert "已授权" in engine.privacy_state()
    preview = engine.egress_preview("问题内容")
    assert preview.provider == "deepseek" and "问题内容" in preview.question
