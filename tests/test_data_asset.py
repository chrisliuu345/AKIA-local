"""`.qda` 本地数据资产：统一领域段、完整迁移与防篡改回归。"""
import json
import zipfile

import pandas as pd

from core.data_asset import (
    DATA_ASSET_KIND, DATA_ASSET_SCHEMA_VERSION, export_data_asset,
    load_data_asset, migrate_project_to_asset, verify_data_asset,
)
from core.evidence_ledger import EvidenceLedger
from core.measurement_event import MeasurementEvent
from core.project_context import ProjectContext, QualityCharacteristic
from core.project_manager import ProjectManager


def _context():
    context = ProjectContext(project_name="本地资产")
    context.add_characteristic(QualityCharacteristic(
        id="QC-001", name="直径", usl=10.4, lsl=9.6, unit="mm"))
    context.record_standard_time(
        "OP10", standard_time_s=12.0, normal_time_s=10.0,
        allowance_pct=0.2, change_reason="已知标准工时")
    return context


def test_asset_roundtrip_preserves_domain_assets(tmp_path):
    context = _context()
    ledger = EvidenceLedger()
    ledger.append("analysis_run", object_refs=["tab:2"], payload={"cpk": 1.25})
    measurement = MeasurementEvent.from_manual(10.1, characteristic_id="QC-001")
    target = tmp_path / "资产.qda"
    exported = export_data_asset(
        target,
        raw_data={"中文/表:A": pd.DataFrame({"直径": [10.0, 10.1]})},
        analyses={2: {"analysis_type": "normal_capability", "params": {}, "result": {}}},
        chart_bytes={"能力图": b"png"},
        project_context=context,
        standards=context.standards,
        evidence_events=ledger,
        measurements=[measurement],
        sampling={"lots": [{"lot_id": "LOT-1", "decision": "accept"}]},
        gauge_studies={"studies": []}, benefits={"records": []}, skills={"entries": []},
    )

    assert exported["verify"]["ok"] is True
    assert exported["manifest"]["kind"] == DATA_ASSET_KIND
    assert exported["manifest"]["schema_version"] == DATA_ASSET_SCHEMA_VERSION
    assert exported["manifest"]["asset_counts"] == {
        "characteristics": 1, "lots": 1, "standard_times": 1}

    loaded = load_data_asset(target)
    assert list(loaded["raw_data"]) == ["中文/表:A"]
    assert loaded["raw_data"]["中文/表:A"]["直径"].tolist() == [10.0, 10.1]
    assert loaded["chart_bytes"] == {"能力图": b"png"}
    assert loaded["project_context"]["project_name"] == "本地资产"
    assert loaded["assets"]["characteristics"][0]["id"] == "QC-001"
    assert loaded["assets"]["lots"][0]["lot_id"] == "LOT-1"
    assert loaded["assets"]["standard_times"][0]["payload"]["standard_time_s"] == 12.0
    assert len(loaded["evidence_events"]) == 1
    assert loaded["measurements"][0]["characteristic_id"] == "QC-001"
    assert loaded["sampling"]["lots"][0]["decision"] == "accept"


def test_project_migration_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(ProjectManager, "add_recent", lambda *args: None)
    context = _context()
    project_path = tmp_path / "old.qap"
    ProjectManager.save_project(
        str(project_path), {"Sheet1": pd.DataFrame({"x": [1, 2]})}, {}, {},
        project_context=context.to_dict(), standards=context.standards,
        measurements=[MeasurementEvent.from_manual(2.0)],
        sampling={"lots": [{"lot_id": "L2"}]})

    result = migrate_project_to_asset(project_path, tmp_path / "new.qda")
    assert result["verify"]["ok"] is True
    loaded = load_data_asset(result["path"])
    assert loaded["raw_data"]["Sheet1"]["x"].tolist() == [1, 2]
    assert loaded["assets"]["standard_times"]
    assert loaded["assets"]["lots"][0]["lot_id"] == "L2"
    assert loaded["measurements"]


def test_asset_rejects_tampering_and_unknown_schema(tmp_path):
    target = tmp_path / "asset.qda"
    export_data_asset(target, raw_data={"S": pd.DataFrame({"x": [1]})})
    with zipfile.ZipFile(target, "a") as archive:
        archive.writestr("unexpected.txt", b"tampered")
    verification = verify_data_asset(target)
    assert verification["ok"] is False
    assert "不一致" in verification["problems"][0]

    bad = tmp_path / "bad.qda"
    with zipfile.ZipFile(bad, "w") as archive:
        archive.writestr("manifest.json", json.dumps({
            "schema_version": "2.0", "kind": DATA_ASSET_KIND, "files": {}}))
    assert verify_data_asset(bad)["ok"] is False

    malformed = tmp_path / "malformed.qda"
    with zipfile.ZipFile(malformed, "w") as archive:
        archive.writestr("manifest.json", json.dumps({
            "schema_version": "1.0", "kind": DATA_ASSET_KIND,
            "files": {"data.txt": "not-metadata"}}))
        archive.writestr("data.txt", b"x")
    verification = verify_data_asset(malformed)
    assert verification["ok"] is False
    assert "元数据无效" in verification["problems"][0]


def test_asset_manifest_tracks_all_file_hashes(tmp_path):
    target = tmp_path / "asset.qda"
    exported = export_data_asset(target, raw_data={"S": pd.DataFrame({"x": [1]})})
    with zipfile.ZipFile(target) as archive:
        assert set(archive.namelist()) - {"manifest.json"} == set(
            exported["manifest"]["files"])
        for name, metadata in exported["manifest"]["files"].items():
            assert len(archive.read(name)) == metadata["size"]
