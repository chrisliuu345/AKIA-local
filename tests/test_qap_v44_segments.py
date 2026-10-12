"""`.qap` 2.0 抽样/量具/收益/技能段与旧版本兼容测试（v4.4.0 B0）。"""

import json
import zipfile

import pandas as pd
import pytest

from core import project_manager as pm
from core.benefit_ledger import BenefitLedger, BenefitRecord
from core.gauge_study import GaugeStudyPolicy
from core.sampling_plan import LotRecord
from core.skill_matrix import SkillMatrix


def _raw():
    return {"S": pd.DataFrame({"x": [1.0, 2.0]})}


class TestV44Segments:
    def test_roundtrip_four_segments(self, tmp_path):
        path = str(tmp_path / "v44.qap")
        sampling = {
            "schema_version": "1",
            "lots": [LotRecord(lot_id="L1", qty=100, inspected=20,
                               defects=1, decision="accept").to_dict()],
            "states": [],
        }
        gauge = {"schema_version": "1",
                 "studies": [GaugeStudyPolicy(gauge_id="g1").to_dict()]}
        benefits = BenefitLedger([
            BenefitRecord(case_id="CASE-1", month="2026-10",
                          basis={"quantity": 1, "unit_cost": 1})]).to_dict()
        skills = SkillMatrix(entries=[
            {"operator": "张三", "process_id": "OP10", "level": 3}])
        pm.ProjectManager.save_project(
            path, _raw(), {}, {}, sampling=sampling, gauge_studies=gauge,
            benefits=benefits, skills=skills)
        loaded = pm.ProjectManager.load_project(path)
        manifest = loaded["manifest"]
        assert manifest["version"] == "2.0"
        assert manifest["has_sampling"] is True
        assert manifest["sampling_lot_count"] == 1
        assert manifest["has_gauge_studies"] is True
        assert manifest["gauge_study_count"] == 1
        assert manifest["has_benefits"] is True
        assert manifest["benefit_count"] == 1
        assert manifest["has_skills"] is True
        assert manifest["skill_entry_count"] == 1
        assert loaded["sampling"]["lots"][0]["lot_id"] == "L1"
        assert loaded["gauge_studies"]["studies"][0]["gauge_id"] == "g1"
        assert loaded["benefits"]["records"][0]["case_id"] == "CASE-1"
        assert loaded["skills"]["entries"][0]["operator"] == "张三"

    def test_segments_absent_by_default(self, tmp_path):
        path = str(tmp_path / "plain.qap")
        pm.ProjectManager.save_project(path, _raw(), {}, {})
        loaded = pm.ProjectManager.load_project(path)
        assert loaded["sampling"] is None
        assert loaded["gauge_studies"] is None
        assert loaded["benefits"] is None
        assert loaded["skills"] is None
        assert loaded["manifest"]["has_sampling"] is False

    @pytest.mark.parametrize("version", ["1.6", "1.7", "1.8", "1.9"])
    def test_old_versions_read_compatible(self, tmp_path, version):
        path = str(tmp_path / f"old_{version}.qap")
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("manifest.json",
                             json.dumps({"version": version}))
            archive.writestr("data/S.csv", "x\n1\n")
        loaded = pm.ProjectManager.load_project(path)
        assert loaded["manifest"]["version"] == version
        assert loaded["sampling"] is None
        assert loaded["gauge_studies"] is None
        assert loaded["benefits"] is None
        assert loaded["skills"] is None

    def test_segment_payload_type_validation(self, tmp_path):
        path = str(tmp_path / "bad.qap")
        with pytest.raises(TypeError, match="sampling"):
            pm.ProjectManager.save_project(path, _raw(), {}, {},
                                           sampling=["not-a-dict"])

    def test_shared_save_forwards_new_segments(self, tmp_path, monkeypatch):
        monkeypatch.setattr(pm, "SHARED_DIR", str(tmp_path / "shared"))
        skills = {"schema_version": "1", "entries": [
            {"operator": "李四", "process_id": "OP20", "level": 4,
             "updated_at": ""}]}
        pm.SharedProjectManager.save_shared(
            "s.qap", _raw(), {}, {}, "公共", "", skills=skills)
        loaded = pm.SharedProjectManager.load_shared(
            str(tmp_path / "shared" / "公共" / "s.qap"))
        assert loaded["manifest"]["has_skills"] is True
        assert loaded["skills"]["entries"][0]["operator"] == "李四"
