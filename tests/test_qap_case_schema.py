"""test_qap_case_schema.py — P0 `.qap` 1.7 案例段读写与向后兼容测试"""

import json
import os
import tempfile
import zipfile

import pandas as pd

from core.improvement_case import CASE_SCHEMA_VERSION, ImprovementCase
from core.project_manager import VERSION, ProjectManager


def _sample_cases():
    first = ImprovementCase(id="CASE-001", title="节拍改善",
                            baseline_refs=["sheet:工时"])
    first.add_step("baseline", ref="sheet:工时")
    second = ImprovementCase(id="CASE-002", title="换型改善")
    return [first.to_dict(), second.to_dict()]


class TestQapCaseRoundtrip:
    def test_save_load_with_cases(self):
        raw = {"Sheet1": pd.DataFrame({"A": [1, 2, 3]})}
        with tempfile.NamedTemporaryFile(suffix=".qap", delete=False) as handle:
            path = handle.name
        try:
            ProjectManager.save_project(path, raw, {}, {}, cases=_sample_cases())
            project = ProjectManager.load_project(path)

            assert project["manifest"]["version"] == VERSION == "1.7"
            assert project["manifest"]["case_count"] == 2
            assert project["manifest"]["has_cases"] is True
            assert [case["id"] for case in project["cases"]] == ["CASE-001", "CASE-002"]
            assert project["cases"][0]["steps"][0]["phase"] == "baseline"

            with zipfile.ZipFile(path, "r") as zf:
                payload = json.loads(zf.read("cases.json").decode("utf-8"))
            assert payload["schema_version"] == CASE_SCHEMA_VERSION
            assert len(payload["cases"]) == 2
        finally:
            os.unlink(path)

    def test_save_without_cases_keeps_schema(self):
        raw = {"Sheet1": pd.DataFrame({"A": [1]})}
        with tempfile.NamedTemporaryFile(suffix=".qap", delete=False) as handle:
            path = handle.name
        try:
            ProjectManager.save_project(path, raw, {}, {})
            project = ProjectManager.load_project(path)
            assert project["cases"] == []
            assert project["manifest"]["case_count"] == 0
            assert project["manifest"]["has_cases"] is False
            with zipfile.ZipFile(path, "r") as zf:
                assert "cases.json" not in zf.namelist()
        finally:
            os.unlink(path)

    def test_backward_compat_without_cases_json(self):
        """旧 1.6 文件（无 cases.json）可正常加载，cases 为空列表。"""
        with tempfile.NamedTemporaryFile(suffix=".qap", delete=False) as handle:
            path = handle.name
        try:
            with zipfile.ZipFile(path, "w") as zf:
                zf.writestr("manifest.json", '{"version": "1.6"}')
                zf.writestr("data/test.csv", "a,b\n1,2")
                zf.writestr("analyses.json", "{}")
            project = ProjectManager.load_project(path)
            assert project["manifest"]["version"] == "1.6"
            assert project["cases"] == []
        finally:
            os.unlink(path)

    def test_old_positional_signature_still_works(self):
        raw = {"Sheet1": pd.DataFrame({"A": [1]})}
        with tempfile.NamedTemporaryFile(suffix=".qap", delete=False) as handle:
            path = handle.name
        try:
            ProjectManager.save_project(path, raw, {}, {})
            assert ProjectManager.load_project(path)["cases"] == []
        finally:
            os.unlink(path)
