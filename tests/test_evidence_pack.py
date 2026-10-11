"""证据包导出与独立校验测试（v4.3.0 B4-3）。"""

import json
import zipfile

import pandas as pd
import pytest

from core.evidence import make_credential
from core.evidence_ledger import EvidenceLedger
from core.evidence_pack import (
    export_evidence_pack,
    read_evidence_pack,
    verify_evidence_pack,
)
from core.measurement_event import MeasurementEvent
from core.standard_record import StandardRecord, StandardRegistry


def _analyses():
    frame = pd.DataFrame({"x": [1.0, 2.0, 3.0]})
    credential = make_credential("capability@1", {"usl": 10}, df=frame).to_dict()
    return {2: {"analysis_type": "正态过程能力", "params": {"usl": 10},
                "result": {"cpk": 1.3}, "credential": credential}}


def _ledger():
    ledger = EvidenceLedger()
    ledger.append("case_created", actor="tester", object_refs=["case:C1"],
                  payload={"title": "节拍改善"})
    ledger.append("analysis_run", actor="tester", object_refs=["tab:2"],
                  payload={"analysis_type": "正态过程能力"})
    return ledger


def _case():
    return {"schema_version": "1", "case": {"id": "CASE-1", "status": "active",
                                            "title": "节拍改善"}}


class TestExport:
    def test_export_and_verify(self, tmp_path):
        registry = StandardRegistry([StandardRecord(
            record_id="S1", object_type="spec_limit", object_ref="x",
            payload={"usl": 10}, valid_from="2026-10-01T00:00:00+08:00",
            change_reason="初始")])
        result = export_evidence_pack(
            str(tmp_path / "pack"), case=_case(), case_markdown="# 案例",
            analyses=_analyses(), ledger=_ledger(),
            standards=registry.to_dict(),
            measurements=[MeasurementEvent.from_manual(1.0)])
        assert result["path"].endswith(".zip")
        assert result["verify"]["ok"] is True
        assert result["manifest"]["event_count"] == 2
        assert result["manifest"]["credential_count"] == 1
        assert result["manifest"]["includes_raw_data"] is False
        with zipfile.ZipFile(result["path"]) as archive:
            names = set(archive.namelist())
            assert {"manifest.json", "case.json", "case.md", "events.jsonl",
                    "credentials.json", "standards.json",
                    "measurements.jsonl"} <= names
            assert not any(name.startswith("raw/") for name in names)

    def test_read_pack(self, tmp_path):
        result = export_evidence_pack(str(tmp_path / "p.zip"), case=_case(),
                                      analyses=_analyses(), ledger=_ledger())
        payload = read_evidence_pack(result["path"])
        assert payload["manifest"]["case_id"] == "CASE-1"
        assert payload["case.json"]["case"]["title"] == "节拍改善"
        assert "case_created" in payload["events.jsonl"]

    def test_include_raw_data_is_opt_in(self, tmp_path):
        raw = {"工时": pd.DataFrame({"cycle": [31.0, 32.0]})}
        result = export_evidence_pack(
            str(tmp_path / "raw.zip"), case=_case(), analyses={}, ledger=_ledger(),
            raw_data=raw, include_raw_data=True)
        assert result["manifest"]["includes_raw_data"] is True
        with zipfile.ZipFile(result["path"]) as archive:
            assert any(name.startswith("raw/") for name in archive.namelist())

    def test_empty_path_rejected(self):
        with pytest.raises(ValueError, match="路径"):
            export_evidence_pack("")


class TestVerify:
    def _pack(self, tmp_path):
        result = export_evidence_pack(str(tmp_path / "pack.zip"), case=_case(),
                                      case_markdown="# 案例",
                                      analyses=_analyses(), ledger=_ledger())
        return result["path"]

    def test_tampered_file_detected(self, tmp_path):
        path = self._pack(tmp_path)
        with zipfile.ZipFile(path) as archive:
            contents = {name: archive.read(name) for name in archive.namelist()}
        contents["case.json"] = b'{"tampered":true}'
        with zipfile.ZipFile(path, "w") as archive:
            for name, data in contents.items():
                archive.writestr(name, data)
        verify = verify_evidence_pack(path)
        assert verify["ok"] is False
        assert any("哈希不匹配" in problem for problem in verify["problems"])

    def test_extra_file_detected(self, tmp_path):
        path = self._pack(tmp_path)
        with zipfile.ZipFile(path, "a") as archive:
            archive.writestr("extra.txt", "sneaky")
        verify = verify_evidence_pack(path)
        assert verify["ok"] is False
        assert any("未登记文件" in problem for problem in verify["problems"])

    def test_missing_file_detected(self, tmp_path):
        path = self._pack(tmp_path)
        with zipfile.ZipFile(path) as archive:
            contents = {name: archive.read(name) for name in archive.namelist()}
        contents.pop("case.md", None)
        with zipfile.ZipFile(path, "w") as archive:
            for name, data in contents.items():
                archive.writestr(name, data)
        verify = verify_evidence_pack(path)
        assert verify["ok"] is False
        assert any("缺少文件" in problem for problem in verify["problems"])

    def test_broken_ledger_chain_detected(self, tmp_path):
        ledger = _ledger()
        ledger.events[0].payload["title"] = "tampered"
        result = export_evidence_pack(str(tmp_path / "broken.zip"), case=_case(),
                                      analyses={}, ledger=ledger)
        assert result["verify"]["ok"] is False
        assert any("账本" in problem for problem in result["verify"]["problems"])

    def test_missing_pack(self, tmp_path):
        verify = verify_evidence_pack(str(tmp_path / "missing.zip"))
        assert verify["ok"] is False
        assert "不存在" in verify["problems"][0]

    def test_not_a_zip(self, tmp_path):
        target = tmp_path / "bad.zip"
        target.write_text("not a zip", encoding="utf-8")
        verify = verify_evidence_pack(str(target))
        assert verify["ok"] is False

    def test_malformed_manifest_reported_not_crash(self, tmp_path):
        """manifest 结构异常（files 非映射）应返回结构化错误而非抛异常。"""
        target = tmp_path / "bad-manifest.zip"
        with zipfile.ZipFile(target, "w") as archive:
            archive.writestr("manifest.json",
                             json.dumps({"schema_version": "1", "files": ["x"]}))
        verify = verify_evidence_pack(str(target))
        assert verify["ok"] is False
        assert verify["problems"]


def test_manifest_is_valid_json(tmp_path):
    result = export_evidence_pack(str(tmp_path / "m.zip"), case=_case(),
                                  analyses=_analyses(), ledger=_ledger())
    with zipfile.ZipFile(result["path"]) as archive:
        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
    assert manifest["schema_version"] == "1"
    assert all("sha256" in meta for meta in manifest["files"].values())
