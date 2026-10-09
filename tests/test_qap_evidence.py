"""`.qap` 1.9 标准段/证据段读写与旧版兼容测试（v4.3.0 B0-4）。"""

import json
import os
import tempfile
import zipfile

import pandas as pd
import pytest

from core.evidence_ledger import EvidenceLedger
from core.measurement_event import MeasurementEvent
from core.measurement_store import MeasurementStore
from core.project_manager import ProjectManager
from core.standard_record import StandardRecord, StandardRegistry

T1 = "2026-10-01T00:00:00+08:00"


def _registry():
    registry = StandardRegistry()
    registry.append(StandardRecord(
        record_id="S1", object_type="spec_limit", object_ref="QC-001",
        payload={"usl": 10.1, "lsl": 9.9}, valid_from=T1,
        change_reason="初始版本", changed_by="tester"))
    return registry


def _ledger():
    ledger = EvidenceLedger()
    ledger.append("case_created", actor="tester", object_refs=["case:C1"],
                  payload={"title": "节拍改善"})
    ledger.append("standard_changed", actor="tester", object_refs=["QC-001"],
                  payload={"record_id": "S1"})
    return ledger


def _measurement_store():
    return MeasurementStore([
        MeasurementEvent.from_manual(1.0, characteristic_id="QC-001"),
        MeasurementEvent.from_manual(2.0, characteristic_id="QC-001"),
    ])


class TestQapEvidenceSections:
    def test_roundtrip_standards_and_evidence(self):
        raw = {"Sheet1": pd.DataFrame({"x": [1.0, 2.0]})}
        with tempfile.NamedTemporaryFile(suffix=".qap", delete=False) as handle:
            path = handle.name
        try:
            ProjectManager.save_project(
                path, raw, {}, {},
                standards=_registry(), evidence_events=_ledger())
            project = ProjectManager.load_project(path)

            manifest = project["manifest"]
            assert manifest["version"] == "1.9"
            assert manifest["has_standards"] is True
            assert manifest["standard_count"] == 1
            assert manifest["has_evidence"] is True
            assert manifest["evidence_event_count"] == 2

            restored = StandardRegistry.from_dict(project["standards"])
            assert restored.current("QC-001").payload["usl"] == 10.1

            ledger = EvidenceLedger.from_events(project["evidence_events"])
            assert ledger.verify()["ok"] is True
            assert ledger.events_for("case:C1")[0].seq == 1

            with zipfile.ZipFile(path, "r") as zf:
                names = zf.namelist()
                assert "standards.json" in names
                assert "evidence/events.jsonl" in names
                payload = json.loads(zf.read("standards.json").decode("utf-8"))
                assert payload["records"][0]["record_id"] == "S1"
        finally:
            os.unlink(path)

    def test_save_without_sections_keeps_19_layout(self):
        raw = {"Sheet1": pd.DataFrame({"x": [1]})}
        with tempfile.NamedTemporaryFile(suffix=".qap", delete=False) as handle:
            path = handle.name
        try:
            ProjectManager.save_project(path, raw, {}, {})
            project = ProjectManager.load_project(path)
            assert project["manifest"]["has_standards"] is False
            assert project["manifest"]["has_evidence"] is False
            assert project["standards"] is None
            assert project["evidence_events"] == []
            with zipfile.ZipFile(path, "r") as zf:
                assert "standards.json" not in zf.namelist()
                assert "evidence/events.jsonl" not in zf.namelist()
        finally:
            os.unlink(path)

    def test_accepts_plain_dict_and_list(self):
        raw = {"Sheet1": pd.DataFrame({"x": [1]})}
        events = [event.to_dict() for event in _ledger().events]
        with tempfile.NamedTemporaryFile(suffix=".qap", delete=False) as handle:
            path = handle.name
        try:
            ProjectManager.save_project(path, raw, {}, {},
                                        standards=_registry().to_dict(),
                                        evidence_events=events)
            project = ProjectManager.load_project(path)
            assert len(project["evidence_events"]) == 2
            assert project["standards"]["records"][0]["record_id"] == "S1"
        finally:
            os.unlink(path)

    def test_rejects_bad_types(self):
        raw = {"Sheet1": pd.DataFrame({"x": [1]})}
        with tempfile.NamedTemporaryFile(suffix=".qap", delete=False) as handle:
            path = handle.name
        try:
            with pytest.raises(TypeError, match="standards"):
                ProjectManager.save_project(path, raw, {}, {}, standards="bad")
            with pytest.raises(TypeError, match="evidence_events"):
                ProjectManager.save_project(path, raw, {}, {}, evidence_events="bad")
        finally:
            os.unlink(path)

    def test_measurements_roundtrip(self):
        raw = {"Sheet1": pd.DataFrame({"x": [1.0]})}
        store = _measurement_store()
        with tempfile.NamedTemporaryFile(suffix=".qap", delete=False) as handle:
            path = handle.name
        try:
            ProjectManager.save_project(path, raw, {}, {}, measurements=store)
            project = ProjectManager.load_project(path)
            assert project["manifest"]["has_measurements"] is True
            assert project["manifest"]["measurement_count"] == 2
            restored = MeasurementStore(project["measurements"])
            assert [e.event_id for e in restored] == [e.event_id for e in store]
            with zipfile.ZipFile(path, "r") as zf:
                assert "measurements.jsonl" in zf.namelist()
        finally:
            os.unlink(path)

    def test_rejects_bad_measurements_type(self):
        raw = {"Sheet1": pd.DataFrame({"x": [1]})}
        with tempfile.NamedTemporaryFile(suffix=".qap", delete=False) as handle:
            path = handle.name
        try:
            with pytest.raises(TypeError, match="measurements"):
                ProjectManager.save_project(path, raw, {}, {}, measurements="bad")
        finally:
            os.unlink(path)


class TestLegacyCompatibility:
    def test_legacy_18_file_has_empty_new_sections(self):
        with tempfile.NamedTemporaryFile(suffix=".qap", delete=False) as handle:
            path = handle.name
        try:
            with zipfile.ZipFile(path, "w") as zf:
                zf.writestr("manifest.json", json.dumps({"version": "1.8"}))
                zf.writestr("data/Sheet1.csv", "x\n1\n")
                zf.writestr("analyses.json", "{}")
                zf.writestr("cases.json", json.dumps(
                    {"schema_version": "0", "cases": [
                        {"schema_version": "0", "id": "CASE-OLD", "title": "旧案例"}]}))
            project = ProjectManager.load_project(path)
            assert project["manifest"]["version"] == "1.8"
            assert project["standards"] is None
            assert project["evidence_events"] == []
            assert project["cases"][0]["id"] == "CASE-OLD"
        finally:
            os.unlink(path)

    def test_truncated_evidence_tail_recovered(self):
        raw = {"Sheet1": pd.DataFrame({"x": [1]})}
        with tempfile.NamedTemporaryFile(suffix=".qap", delete=False) as handle:
            path = handle.name
        try:
            ProjectManager.save_project(path, raw, {}, {}, evidence_events=_ledger())
            with zipfile.ZipFile(path, "r") as zf:
                names = zf.namelist()
                contents = {name: zf.read(name) for name in names}
            contents["evidence/events.jsonl"] += b'{"seq":3,"type":"case_'
            with zipfile.ZipFile(path, "w") as zf:
                for name, data in contents.items():
                    zf.writestr(name, data)
            project = ProjectManager.load_project(path)
            assert project["evidence_recovered"] is True
            assert project["evidence_errors"] == []
            assert len(project["evidence_events"]) == 2
            assert EvidenceLedger.from_events(project["evidence_events"]).verify()["ok"] is True
        finally:
            os.unlink(path)

    def test_malformed_evidence_line_is_reported_not_crash(self):
        raw = {"Sheet1": pd.DataFrame({"x": [1]})}
        with tempfile.NamedTemporaryFile(suffix=".qap", delete=False) as handle:
            path = handle.name
        try:
            ProjectManager.save_project(path, raw, {}, {}, evidence_events=_ledger())
            with zipfile.ZipFile(path, "r") as zf:
                contents = {name: zf.read(name) for name in zf.namelist()}
            lines = contents["evidence/events.jsonl"].decode("utf-8").splitlines()
            lines.insert(1, "{bad-json")
            contents["evidence/events.jsonl"] = ("\n".join(lines) + "\n").encode("utf-8")
            with zipfile.ZipFile(path, "w") as zf:
                for name, data in contents.items():
                    zf.writestr(name, data)
            project = ProjectManager.load_project(path)
            assert project["evidence_errors"]
            assert len(project["evidence_events"]) == 2
        finally:
            os.unlink(path)

    def test_truncated_measurements_tail_recovered(self):
        raw = {"Sheet1": pd.DataFrame({"x": [1]})}
        with tempfile.NamedTemporaryFile(suffix=".qap", delete=False) as handle:
            path = handle.name
        try:
            ProjectManager.save_project(path, raw, {}, {},
                                        measurements=_measurement_store())
            with zipfile.ZipFile(path, "r") as zf:
                contents = {name: zf.read(name) for name in zf.namelist()}
            contents["measurements.jsonl"] += b'{"schema_version":"1","event_id":"MEV-'
            with zipfile.ZipFile(path, "w") as zf:
                for name, data in contents.items():
                    zf.writestr(name, data)
            project = ProjectManager.load_project(path)
            assert project["measurement_recovered"] is True
            assert project["measurement_errors"] == []
            assert len(project["measurements"]) == 2
        finally:
            os.unlink(path)
