"""v4.6.0 智能辅助：显式启用、顾问边界、隐私降级与审计追溯。"""
import pandas as pd
import pytest

import core.agent.privacy as privacy
from core.agent.audit import ModelCallAudit
from core.agent.engine import AgentEngine
from core.agent.tools import AgentContext, build_default_registry


class FakeLLM:
    available = True
    provider = "ollama"
    protocol = "ollama"
    model = "fake-qwen"
    api_base = "http://localhost:11434"
    api_key = "must-not-be-audited"

    def __init__(self, text="评分 4 分；需人工确认"):
        self.text = text
        self.calls = 0

    def generate(self, prompt):
        self.calls += 1
        yield self.text


def _context():
    return AgentContext(
        data_frames={"Sheet1": pd.DataFrame({"value": [1.0, 2.0, 3.0]})},
        analyses={2: {
            "analysis_type": "normal_capability",
            "params": {"column": "value", "usl": 10, "lsl": 0},
            "result": {"cpk": 1.25},
            "credential": {"data_fingerprint": "pd-hash-v1:abc"},
        }},
    )


def _engine(llm, audit, enabled=True):
    return AgentEngine(build_default_registry(_context()), llm=llm,
                       context=_context(), audit_sink=audit,
                       assistance_enabled=lambda: enabled)


def test_assistance_is_disabled_by_default(tmp_path):
    engine = _engine(FakeLLM(), ModelCallAudit(tmp_path / "audit.jsonl"), enabled=False)
    with pytest.raises(PermissionError, match="未启用"):
        engine.prepare_assistance("online_scoring")


def test_assistance_requires_analysis(tmp_path):
    engine = AgentEngine(build_default_registry(AgentContext()), llm=FakeLLM(),
                         context=AgentContext(), assistance_enabled=lambda: True)
    with pytest.raises(ValueError, match="请先运行"):
        engine.prepare_assistance("online_scoring")


def test_online_scoring_preserves_decision_and_audits_model(tmp_path):
    audit = ModelCallAudit(tmp_path / "audit.jsonl")
    llm = FakeLLM()
    llm.api_base = "http://user:secret@localhost:11434?api_key=secret"
    engine = _engine(llm, audit)
    question = engine.prepare_assistance("online_scoring")
    reply = engine.respond(question, assistance_kind="online_scoring")

    assert llm.calls == 1
    assert reply.advisory_only is True
    assert reply.human_confirmation_required is True
    assert reply.assistance_kind == "online_scoring"
    assert reply.statistical_decision["credential"]["data_fingerprint"] == "pd-hash-v1:abc"
    assert "不替代统计判定" in reply.text
    assert reply.audit_id

    record = audit.get(reply.audit_id)
    assert record["kind"] == "online_scoring"
    assert record["status"] == "completed"
    assert record["config"]["model"] == "fake-qwen"
    assert record["model_calls"][0]["prompt_sha256"]
    assert "secret" not in record["config"]["api_base"]
    assert "must-not-be-audited" not in str(record)
    assert record["input"]["assistance_source"]["credential"]["data_fingerprint"] == \
        "pd-hash-v1:abc"


def test_anomaly_assistance_uses_same_guardrails(tmp_path):
    engine = _engine(FakeLLM("发现异常簇，请人工复核"), ModelCallAudit(tmp_path / "a.jsonl"))
    question = engine.prepare_assistance("anomaly_assistance")
    reply = engine.respond(question, assistance_kind="anomaly_assistance")
    assert reply.assistance_kind == "anomaly_assistance"
    assert reply.human_confirmation_required is True
    assert "人工复核" in reply.text


def test_assistance_needs_available_model(tmp_path):
    llm = FakeLLM()
    llm.available = False
    engine = _engine(llm, ModelCallAudit(tmp_path / "a.jsonl"))
    question = engine.prepare_assistance("online_scoring")
    reply = engine.respond(question, assistance_kind="online_scoring")
    assert llm.calls == 0
    assert reply.offline is True
    assert "需要可用" in reply.text
    assert not reply.tool_calls


def test_cloud_denial_does_not_fabricate_offline_score(tmp_path, monkeypatch):
    settings = {}
    monkeypatch.setattr(privacy, "_get_setting",
                        lambda key, default=None: settings.get(key, default))
    llm = FakeLLM()
    llm.provider = "deepseek"
    llm.protocol = "openai"
    llm.api_base = "https://api.deepseek.com/v1"
    audit = ModelCallAudit(tmp_path / "a.jsonl")
    engine = _engine(llm, audit)
    question = engine.prepare_assistance("online_scoring")
    reply = engine.respond(question, assistance_kind="online_scoring")

    assert llm.calls == 0
    assert reply.advisory_only is True
    assert not reply.tool_calls
    assert "云调用已在设置中关闭" in reply.text
    assert audit.get(reply.audit_id)["status"] == "blocked"
