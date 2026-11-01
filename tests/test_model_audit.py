"""模型调用本地审计的持久化、轮转与导出回归。"""
import json

from core.agent.audit import MODEL_AUDIT_SCHEMA_VERSION, ModelCallAudit, prompt_digest


def test_audit_roundtrip_rotation_and_export(tmp_path):
    path = tmp_path / "calls.jsonl"
    audit = ModelCallAudit(path, max_records=2)
    for index in range(3):
        audit.record({"kind": "chat", "status": "completed",
                      "input": {"question": f"q{index}"},
                      "result": {"value": float("nan") if index == 0 else index}})

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[-1])["input"]["question"] == "q2"
    assert audit.records()[0]["input"]["question"] == "q2"
    assert audit.records()[1]["result"]["value"] == 1
    assert audit.get(audit.records()[0]["record_id"]) is not None

    exported = audit.export(tmp_path / "audit.json")
    payload = json.loads(exported.read_text(encoding="utf-8"))
    assert payload["schema_version"] == MODEL_AUDIT_SCHEMA_VERSION
    assert payload["record_count"] == 2


def test_audit_skips_damaged_lines_and_reopens(tmp_path):
    path = tmp_path / "calls.jsonl"
    path.write_text('{bad json}\n{"record_id":"ok","kind":"chat"}\n', encoding="utf-8")
    audit = ModelCallAudit(path)
    assert [item["record_id"] for item in audit.records()] == ["ok"]
    assert audit._errors

    audit.record({"kind": "chat", "input": {"question": "new"}})
    reopened = ModelCallAudit(path)
    assert len(reopened.records()) == 2


def test_prompt_digest_is_stable():
    assert prompt_digest("abc") == prompt_digest("abc")
    assert prompt_digest("abc") != prompt_digest("abd")
