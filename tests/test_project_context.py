"""test_project_context.py — QualityCharacteristic + ProjectContext 单元测试"""

import pytest
from core.project_context import QualityCharacteristic, ProjectContext


class TestQualityCharacteristic:
    """QualityCharacteristic 数据类测试"""

    def test_default_values(self):
        qc = QualityCharacteristic()
        assert qc.id == ""
        assert qc.name == ""
        assert qc.usl is None
        assert qc.lsl is None

    def test_to_dict(self):
        qc = QualityCharacteristic(
            id="QC-001", name="轴径", process="车削",
            usl=10.02, lsl=9.98, target=10.0, unit="mm",
            data_source="Sheet1:col_a", spc_method="XBar-R",
        )
        d = qc.to_dict()
        assert d["id"] == "QC-001"
        assert d["name"] == "轴径"
        assert d["usl"] == 10.02
        assert d["spc_method"] == "XBar-R"

    def test_from_dict(self):
        d = {
            "id": "QC-002", "name": "孔径", "process": "钻孔",
            "usl": 5.01, "lsl": 4.99, "unit": "mm",
        }
        qc = QualityCharacteristic.from_dict(d)
        assert qc.id == "QC-002"
        assert qc.name == "孔径"
        assert qc.usl == 5.01

    def test_roundtrip(self):
        qc = QualityCharacteristic(id="QC-003", name="硬度", usl=60, lsl=55)
        d = qc.to_dict()
        qc2 = QualityCharacteristic.from_dict(d)
        assert qc2.id == "QC-003"
        assert qc2.usl == 60

    def test_from_dict_ignores_unknown_keys(self):
        d = {"id": "QC-004", "name": "test", "unknown_field": 123}
        qc = QualityCharacteristic.from_dict(d)
        assert qc.id == "QC-004"
        assert not hasattr(qc, "unknown_field")


class TestProjectContext:
    """ProjectContext 项目级上下文测试"""

    def test_default_values(self):
        ctx = ProjectContext()
        assert ctx.project_name == ""
        assert len(ctx.characteristics) == 0
        assert len(ctx.fmea_items) == 0

    def test_add_characteristic(self):
        ctx = ProjectContext()
        qc = QualityCharacteristic(name="轴径")
        ctx.add_characteristic(qc)
        assert len(ctx.characteristics) == 1
        assert ctx.characteristics[0].id == "QC-001"

    def test_add_characteristic_custom_id(self):
        ctx = ProjectContext()
        qc = QualityCharacteristic(id="CUSTOM-01", name="硬度")
        ctx.add_characteristic(qc)
        assert ctx.characteristics[0].id == "CUSTOM-01"

    def test_get_characteristic(self):
        ctx = ProjectContext()
        ctx.add_characteristic(QualityCharacteristic(id="QC-001", name="轴径"))
        ctx.add_characteristic(QualityCharacteristic(id="QC-002", name="孔径"))
        found = ctx.get_characteristic("QC-002")
        assert found is not None
        assert found.name == "孔径"
        assert ctx.get_characteristic("QC-999") is None

    def test_update_characteristic(self):
        ctx = ProjectContext()
        ctx.add_characteristic(QualityCharacteristic(id="QC-001", name="轴径"))
        ctx.update_characteristic("QC-001", name="轴径φ10", usl=10.02)
        qc = ctx.get_characteristic("QC-001")
        assert qc.name == "轴径φ10"
        assert qc.usl == 10.02

    def test_remove_characteristic(self):
        ctx = ProjectContext()
        ctx.add_characteristic(QualityCharacteristic(id="QC-001"))
        ctx.add_characteristic(QualityCharacteristic(id="QC-002"))
        ctx.remove_characteristic("QC-001")
        assert len(ctx.characteristics) == 1
        assert ctx.characteristics[0].id == "QC-002"

    def test_set_fmea_items(self):
        ctx = ProjectContext()
        items = [{"id": "F1", "rpn": 120}, {"id": "F2", "rpn": 80}]
        ctx.set_fmea_items(items)
        assert len(ctx.fmea_items) == 2

    def test_set_control_plan(self):
        ctx = ProjectContext()
        rows = [["OP01", "车削", "轴径", "", "", "5", "每小时", "XBar-R", "隔离"]]
        ctx.set_control_plan(rows)
        assert len(ctx.control_plan_rows) == 1

    def test_get_high_risk_fmea_items(self):
        ctx = ProjectContext()
        ctx.fmea_items = [{"rpn": 200}, {"rpn": 100}, {"rpn": 50}, {"rpn": 30}]
        high = ctx.get_high_risk_fmea_items()
        assert len(high) == 2  # rpn >= 100

    def test_get_high_risk_custom_threshold(self):
        ctx = ProjectContext()
        ctx.fmea_items = [{"rpn": 200}, {"rpn": 100}, {"rpn": 50}]
        high = ctx.get_high_risk_fmea_items(threshold=200)
        assert len(high) == 1

    def test_get_characteristics_for_spc(self):
        ctx = ProjectContext()
        ctx.add_characteristic(QualityCharacteristic(
            id="QC-001", spc_method="XBar-R", data_source="Sheet1:col_a"))
        ctx.add_characteristic(QualityCharacteristic(
            id="QC-002", spc_method="", data_source=""))  # 无 SPC
        spc = ctx.get_characteristics_for_spc()
        assert len(spc) == 1
        assert spc[0].id == "QC-001"

    def test_to_dict(self):
        ctx = ProjectContext(project_name="test")
        ctx.add_characteristic(QualityCharacteristic(id="QC-001", name="轴径"))
        ctx.fmea_items = [{"rpn": 100}]
        d = ctx.to_dict()
        assert d["project_name"] == "test"
        assert len(d["characteristics"]) == 1
        assert d["fmea_items"][0]["rpn"] == 100

    def test_from_dict(self):
        d = {
            "project_name": "test",
            "created_at": "2026-01-01",
            "updated_at": "2026-01-02",
            "characteristics": [{"id": "QC-001", "name": "轴径"}],
            "fmea_items": [{"rpn": 100}],
            "control_plan_rows": [],
            "ppap_report": {},
            "eight_d_reports": [],
            "analysis_snapshots": {},
        }
        ctx = ProjectContext.from_dict(d)
        assert ctx.project_name == "test"
        assert len(ctx.characteristics) == 1
        assert ctx.fmea_items[0]["rpn"] == 100

    def test_roundtrip(self):
        ctx = ProjectContext(project_name="roundtrip_test")
        ctx.add_characteristic(QualityCharacteristic(id="QC-001", name="轴径", usl=10.02))
        ctx.fmea_items = [{"rpn": 150, "cause": "磨损"}]
        ctx.control_plan_rows = [["OP01", "车削"]]
        ctx.analysis_snapshots = {"spc": {"violations": 3}}
        d = ctx.to_dict()
        ctx2 = ProjectContext.from_dict(d)
        assert ctx2.project_name == "roundtrip_test"
        assert ctx2.characteristics[0].usl == 10.02
        assert ctx2.fmea_items[0]["rpn"] == 150
        assert ctx2.analysis_snapshots["spc"]["violations"] == 3

    def test_set_analysis_snapshot(self):
        ctx = ProjectContext()
        ctx.set_analysis_snapshot("spc", {"violations": 5})
        snap = ctx.get_analysis_snapshot("spc")
        assert snap["violations"] == 5
        assert ctx.get_analysis_snapshot("nonexistent") is None
