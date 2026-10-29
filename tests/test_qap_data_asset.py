"""`.qap` 本地数据资产段：缺段仍可打开，写入后能按版本读回。"""

import json
import zipfile

import pandas as pd

from core import project_manager as pm
from core.data_asset import DATA_ASSET_FORMAT_VERSION, DATA_ASSET_MEMBER
from core.project_manager import ProjectManager


def _raw():
    return {"Sheet1": pd.DataFrame({"x": [1, 2]})}


def _write_legacy(path, version: str = "1.9") -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("manifest.json", json.dumps({"version": version}))
        archive.writestr("data/Sheet1.csv", "x\n1\n2\n")
        archive.writestr("analyses.json", json.dumps({
            "1": {"analysis_type": "spc", "params": {"k": 1}, "result": {"n": 2}},
        }))


class TestDataAssetSection:
    def test_missing_section_still_loads(self, tmp_path):
        path = tmp_path / "legacy.qap"
        _write_legacy(path, "1.6")
        loaded = ProjectManager.load_project(str(path))
        assert loaded["manifest"]["version"] == "1.6"
        assert loaded["data_asset"] is None
        assert loaded["raw_data"]["Sheet1"]["x"].tolist() == [1, 2]
        assert loaded["analyses"][1]["params"] == {"k": 1}
        assert loaded["sampling"] is None

    def test_section_round_trips(self, tmp_path):
        path = tmp_path / "asset.qap"
        asset = {
            "format_version": DATA_ASSET_FORMAT_VERSION,
            "characteristics": [{"id": "kept"}],
            "batches": [],
            "standard_times": [],
            "note": "keep-me",
        }
        ProjectManager.save_project(str(path), _raw(), {}, {}, data_asset=asset)
        loaded = ProjectManager.load_project(str(path))
        assert loaded["data_asset"]["characteristics"] == [{"id": "kept"}]
        assert loaded["data_asset"]["batches"] == []
        assert loaded["data_asset"]["standard_times"] == []
        assert loaded["data_asset"]["note"] == "keep-me"
        assert loaded["manifest"]["has_data_asset"] is True
        with zipfile.ZipFile(path, "r") as archive:
            member = json.loads(archive.read(DATA_ASSET_MEMBER).decode("utf-8"))
        assert member["format_version"] == DATA_ASSET_FORMAT_VERSION
        assert member["note"] == "keep-me"

    def test_version_field_present(self, tmp_path):
        path = tmp_path / "plain.qap"
        ProjectManager.save_project(str(path), _raw(), {}, {})
        loaded = ProjectManager.load_project(str(path))
        assert loaded["data_asset"]["format_version"] == DATA_ASSET_FORMAT_VERSION
        assert loaded["manifest"]["data_asset_format_version"] == DATA_ASSET_FORMAT_VERSION
        with zipfile.ZipFile(path, "r") as archive:
            member = json.loads(archive.read(DATA_ASSET_MEMBER).decode("utf-8"))
        assert "format_version" in member
        assert member["format_version"] == DATA_ASSET_FORMAT_VERSION

    def test_old_project_round_trip_keeps_existing_data(self, tmp_path):
        source = tmp_path / "old.qap"
        _write_legacy(source)
        loaded = ProjectManager.load_project(str(source))
        assert loaded["data_asset"] is None
        dest = tmp_path / "resaved.qap"
        ProjectManager.save_project(
            str(dest), loaded["raw_data"], loaded["analyses"], {})
        again = ProjectManager.load_project(str(dest))
        assert again["raw_data"]["Sheet1"]["x"].tolist() == [1, 2]
        assert again["analyses"][1]["analysis_type"] == "spc"
        assert again["data_asset"]["format_version"] == DATA_ASSET_FORMAT_VERSION
        assert again["data_asset"]["characteristics"] == []
        assert again["data_asset"]["batches"] == []
        assert again["data_asset"]["standard_times"] == []

    def test_save_does_not_copy_characteristics_batches_or_standard_times(self, tmp_path):
        path = tmp_path / "sources.qap"
        ProjectManager.save_project(
            str(path), _raw(), {}, {},
            project_context={"project_name": "p", "characteristics": [{"id": "QC-1"}]},
            sampling={"schema_version": "1", "lots": [{"lot_id": "L1"}], "states": []},
            standards={"records": [{
                "object_type": "standard_time", "object_ref": "OP10",
            }]},
        )
        loaded = ProjectManager.load_project(str(path))
        assert loaded["project_context"]["characteristics"][0]["id"] == "QC-1"
        assert loaded["sampling"]["lots"][0]["lot_id"] == "L1"
        assert loaded["standards"]["records"][0]["object_ref"] == "OP10"
        assert loaded["data_asset"]["characteristics"] == []
        assert loaded["data_asset"]["batches"] == []
        assert loaded["data_asset"]["standard_times"] == []

    def test_other_format_version_round_trips_unchanged(self, tmp_path):
        path = tmp_path / "future.qap"
        asset = {"format_version": "2", "characteristics": {"migrated": True}}
        ProjectManager.save_project(str(path), _raw(), {}, {}, data_asset=asset)
        loaded = ProjectManager.load_project(str(path))
        assert loaded["data_asset"]["format_version"] == "2"
        assert loaded["data_asset"]["characteristics"] == {"migrated": True}
        assert loaded["manifest"]["data_asset_format_version"] == "2"

    def test_shared_save_forwards_data_asset(self, tmp_path, monkeypatch):
        monkeypatch.setattr(pm, "SHARED_DIR", str(tmp_path / "shared"))
        asset = {
            "format_version": DATA_ASSET_FORMAT_VERSION,
            "characteristics": [],
            "batches": [{"lot_id": "kept-batch"}],
            "standard_times": [],
        }
        pm.SharedProjectManager.save_shared(
            "s.qap", _raw(), {}, {}, "公共", "", data_asset=asset)
        loaded = pm.SharedProjectManager.load_shared(
            str(tmp_path / "shared" / "公共" / "s.qap"))
        assert loaded["data_asset"]["format_version"] == DATA_ASSET_FORMAT_VERSION
        assert loaded["data_asset"]["batches"] == [{"lot_id": "kept-batch"}]
        assert loaded["data_asset"]["characteristics"] == []
        assert loaded["data_asset"]["standard_times"] == []
