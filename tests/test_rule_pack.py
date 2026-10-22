"""Versioned declarative rule-pack contract and CLI tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from core.rule_pack import Rule, RulePack

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / "config" / "rule-packs" / "example-quality.json"


def _simple_pack() -> RulePack:
    return RulePack(
        id="test.rules",
        name="Test Rules",
        version="1.2.0",
        rules=[
            Rule(
                id="judgement.cpk",
                category="judgement",
                type="threshold",
                metric="cpk",
                operator=">=",
                value=1.33,
                message="Cpk too low",
            ),
            Rule(
                id="judgement.band",
                category="judgement",
                type="threshold",
                metric="bias",
                operator="between",
                value=[-0.1, 0.1],
                severity="warning",
                message="Bias outside band",
            ),
            Rule(
                id="quality.status",
                category="quality",
                type="categorical",
                metric="status",
                operator="in",
                value=["accepted", "conditional"],
                message="Status not accepted",
            ),
            Rule(
                id="sampling.config",
                category="sampling",
                type="configuration",
                settings={"aql": 2.5, "level": "II"},
                message="Sampling configuration",
            ),
        ],
    )


def test_rule_pack_roundtrip_and_fingerprint(tmp_path):
    pack = _simple_pack()
    assert pack.fingerprint.startswith("rulepack-hash-v1:")
    target = pack.save(tmp_path / "rules.json")
    loaded = RulePack.load(target)
    assert loaded.to_dict() == pack.to_dict()
    assert loaded.fingerprint == pack.fingerprint

    data = json.loads(target.read_text(encoding="utf-8"))
    data["version"] = "9.9.9"
    with pytest.raises(ValueError, match="fingerprint"):
        RulePack.from_dict(data)


def test_rule_pack_rejects_unknown_and_duplicate_rules():
    with pytest.raises(ValueError, match="未知字段"):
        Rule.from_dict({
            "id": "bad.rule", "category": "judgement",
            "type": "threshold", "metric": "x", "operator": ">",
            "value": 1, "script": "os.system('no')",
        })
    with pytest.raises(ValueError, match="唯一"):
        RulePack(
            id="duplicate.rules", name="Duplicate", version="1",
            rules=[
                Rule(id="same.rule", category="judgement", type="threshold",
                     metric="x", operator=">", value=1),
                Rule(id="same.rule", category="quality", type="threshold",
                     metric="y", operator="<", value=2),
            ],
        )
    with pytest.raises(ValueError, match="运算符"):
        Rule(id="bad.operator", category="judgement", type="threshold",
             metric="x", operator="=~", value=1)
    with pytest.raises(ValueError, match="有限数值"):
        Rule(id="huge.rule", category="judgement", type="threshold",
             metric="x", operator=">", value=10 ** 400)


def test_rule_pack_evaluation_and_missing_metrics():
    result = _simple_pack().evaluate({
        "cpk": 1.5, "bias": 0.2, "status": "rejected",
    })
    assert result["ok"] is False
    assert result["passed"] == 1
    assert result["failed"] == 2
    assert result["errors"] == 1
    assert result["warnings"] == 1
    assert result["skipped"] == 0
    by_id = {item["rule_id"]: item for item in result["results"]}
    assert by_id["judgement.cpk"]["status"] == "pass"
    assert by_id["judgement.band"]["status"] == "fail"
    assert by_id["quality.status"]["status"] == "fail"
    assert by_id["sampling.config"]["status"] == "configured"

    warning_only = _simple_pack().evaluate({
        "cpk": 1.5, "bias": 0.2, "status": "accepted",
    })
    assert warning_only["ok"] is True
    assert warning_only["warnings"] == 1

    missing = _simple_pack().evaluate({"cpk": 1.5})
    assert missing["ok"] is True
    assert "bias" in missing["missing_metrics"]
    assert "status" in missing["missing_metrics"]

    blocked = _simple_pack().evaluate({"cpk": 0.8})
    assert blocked["ok"] is False
    assert blocked["errors"] == 1


def test_example_pack_and_cli(tmp_path):
    pack = RulePack.load(EXAMPLE)
    assert pack.id == "example.quality"
    assert len(pack.rules) == 3

    validate = subprocess.run(
        [sys.executable, "-m", "akia_sdk", "rules-validate",
         "--pack", str(EXAMPLE)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert validate.returncode == 0, validate.stderr
    payload = json.loads(validate.stdout)
    assert payload["kind"] == "rule_pack"
    assert payload["rule_count"] == 3

    metrics_path = tmp_path / "metrics.json"
    metrics_path.write_text(
        json.dumps({"cpk": 1.4, "grr_pct": 8.0}), encoding="utf-8")
    evaluate = subprocess.run(
        [sys.executable, "-m", "akia_sdk", "rules-evaluate",
         "--pack", str(EXAMPLE), "--metrics-file", str(metrics_path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert evaluate.returncode == 0, evaluate.stderr
    result = json.loads(evaluate.stdout)
    assert result["ok"] is True
    assert result["passed"] == 2
    assert result["results"][0]["status"] == "configured"

    failed = subprocess.run(
        [sys.executable, "-m", "akia_sdk", "rules-evaluate",
         "--pack", str(EXAMPLE), "--metrics", '{"cpk":0.9}'],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert failed.returncode == 1
    assert json.loads(failed.stdout)["ok"] is False
