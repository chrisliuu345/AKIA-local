"""test_qap_roundtrip.py — .qap save/load 含 context.json 完整闭环测试"""

import os
import tempfile
import pytest
import pandas as pd

from core.project_manager import ProjectManager
from core.project_context import ProjectContext, QualityCharacteristic


@pytest.fixture
def sample_project():
    """创建包含完整数据的项目"""
    ctx = ProjectContext(project_name="test_project")
    qc = QualityCharacteristic(
        id="QC-001", name="轴径φ10±0.02", process="车削",
        usl=10.02, lsl=9.98, target=10.0, unit="mm",
        data_source="Sheet1:轴径", spc_method="XBar-R",
    )
    ctx.add_characteristic(qc)
    ctx.fmea_items = [
        {"id": "F1", "function": "车削", "failure_mode": "尺寸超差", "rpn": 120},
        {"id": "F2", "function": "钻孔", "failure_mode": "孔径偏大", "rpn": 80},
    ]
    ctx.control_plan_rows = [
        ["OP01", "车削", "轴径", "10±0.02", "千分尺", "5", "每小时", "XBar-R", "隔离"],
    ]
    ctx.ppap_report = {"part_no": "P-001", "level": 3}
    ctx.eight_d_reports = [{"title": "8D-001", "d1_team": "质量组"}]
    ctx.analysis_snapshots = {"spc": {"violations": 3}, "capability": {"cpk": 1.45}}

    raw = {
        "Sheet1": pd.DataFrame({"轴径": [10.01, 9.99, 10.00, 10.02, 9.98]}),
        "Sheet2": pd.DataFrame({"孔径": [5.005, 4.995, 5.000]}),
    }
    analyses = {
        1: {"analysis_type": "XBar-R", "params": {}, "result": {"violations": 3}},
        2: {"analysis_type": "Capability", "params": {}, "result": {"cpk": 1.45}},
    }
    charts = {"chart1": b"fake_png_data"}
    return raw, analyses, charts, ctx


class TestQapRoundtrip:
    """`.qap` save/load 含 context.json 完整闭环"""

    def test_save_load_with_context(self, sample_project):
        raw, analyses, charts, ctx = sample_project
        with tempfile.NamedTemporaryFile(suffix=".qap", delete=False) as f:
            path = f.name
        try:
            ProjectManager.save_project(
                path, raw, analyses, charts, "",
                project_context=ctx.to_dict(),
            )
            project = ProjectManager.load_project(path)

            # 验证 context.json 完整还原
            loaded_ctx = project.get("project_context")
            assert loaded_ctx is not None
            assert loaded_ctx["project_name"] == "test_project"
            assert len(loaded_ctx["characteristics"]) == 1
            assert loaded_ctx["characteristics"][0]["id"] == "QC-001"
            assert loaded_ctx["fmea_items"][0]["rpn"] == 120
            assert len(loaded_ctx["control_plan_rows"]) == 1
            assert loaded_ctx["ppap_report"]["part_no"] == "P-001"
            assert len(loaded_ctx["eight_d_reports"]) == 1
            assert loaded_ctx["analysis_snapshots"]["spc"]["violations"] == 3
        finally:
            os.unlink(path)

    def test_save_load_without_context(self):
        """不传 project_context 时正常工作"""
        raw = {"Sheet1": pd.DataFrame({"A": [1, 2, 3]})}
        with tempfile.NamedTemporaryFile(suffix=".qap", delete=False) as f:
            path = f.name
        try:
            ProjectManager.save_project(path, raw, {}, {}, "")
            project = ProjectManager.load_project(path)
            assert project.get("project_context") is None
        finally:
            os.unlink(path)

    def test_backward_compat_no_context_json(self):
        """旧 .qap (无 context.json) 向后兼容"""
        import zipfile
        with tempfile.NamedTemporaryFile(suffix=".qap", delete=False) as f:
            path = f.name
        try:
            with zipfile.ZipFile(path, "w") as zf:
                zf.writestr("manifest.json", '{"version": "1.0"}')
                zf.writestr("data/test.csv", "a,b\n1,2")
                zf.writestr("analyses.json", "{}")
            project = ProjectManager.load_project(path)
            assert project.get("project_context") is None
            assert "Sheet1" in project["raw_data"] or "test" in project["raw_data"]
        finally:
            os.unlink(path)

    def test_context_roundtrip_preserves_types(self):
        """序列化/反序列化保持数据类型"""
        ctx = ProjectContext(project_name="type_test")
        qc = QualityCharacteristic(
            id="QC-001", name="test", usl=10.5, lsl=9.5, target=10.0,
        )
        ctx.add_characteristic(qc)
        ctx.fmea_items = [{"rpn": 150, "severity": 8}]

        with tempfile.NamedTemporaryFile(suffix=".qap", delete=False) as f:
            path = f.name
        try:
            ProjectManager.save_project(
                path, {"S": pd.DataFrame({"A": [1]})}, {}, {},
                project_context=ctx.to_dict(),
            )
            project = ProjectManager.load_project(path)
            loaded = ProjectContext.from_dict(project["project_context"])
            assert loaded.characteristics[0].usl == 10.5
            assert isinstance(loaded.fmea_items[0]["rpn"], int)
        finally:
            os.unlink(path)

    def test_manifest_has_context_flag(self):
        """manifest 中 has_context 标记正确"""
        ctx = ProjectContext(project_name="flag_test")
        raw = {"S": pd.DataFrame({"A": [1]})}
        with tempfile.NamedTemporaryFile(suffix=".qap", delete=False) as f:
            path = f.name
        try:
            ProjectManager.save_project(
                path, raw, {}, {}, "",
                project_context=ctx.to_dict(),
            )
            project = ProjectManager.load_project(path)
            assert project["manifest"].get("has_context") is True
        finally:
            os.unlink(path)

    def test_manifest_no_context_flag(self):
        """无 context 时 has_context 为 False"""
        raw = {"S": pd.DataFrame({"A": [1]})}
        with tempfile.NamedTemporaryFile(suffix=".qap", delete=False) as f:
            path = f.name
        try:
            ProjectManager.save_project(path, raw, {}, {}, "")
            project = ProjectManager.load_project(path)
            assert project["manifest"].get("has_context") is False
        finally:
            os.unlink(path)
