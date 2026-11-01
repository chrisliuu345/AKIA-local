"""一键报告模型调用也进入统一本地审计。"""
from core.agent.audit import ModelCallAudit
from core.one_click_analyzer import OneClickAnalyzer


class _LLM:
    available = True
    provider = "ollama"
    protocol = "ollama"
    model = "fake"
    api_base = "http://localhost:11434"

    def generate(self, prompt):
        yield "一键报告"


def test_one_click_synthesis_writes_audit(tmp_path):
    audit = ModelCallAudit(tmp_path / "audit.jsonl")
    analyzer = OneClickAnalyzer(llm_client=_LLM(), audit_sink=audit)
    results = [{"analysis_type": "spc", "success": True, "summary": {"violations": 0}}]
    text = analyzer.synthesize(results, {"global_summary": {"total_sheets": 1, "total_rows": 3}})

    assert text == "一键报告"
    record = audit.records()[0]
    assert record["kind"] == "one_click_report"
    assert record["status"] == "completed"
    assert record["config"]["model"] == "fake"
    assert record["input"]["results"][0]["analysis_type"] == "spc"
    assert record["model_calls"][0]["prompt_sha256"]
