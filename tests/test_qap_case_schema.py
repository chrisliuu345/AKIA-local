"""test_qap_case_schema.py — `.qap` 案例段读写与向后兼容测试（1.8 起含凭证段）"""

import json
import os
import tempfile
import zipfile

import pandas as pd

from core.improvement_case import CASE_SCHEMA_VERSION, ImprovementCase
from core.evidence import make_credential
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

            assert project["manifest"]["version"] == VERSION == "2.0"
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


class TestQapCredentialSection:
    """1.8 起 analyses 条目携带判定凭证；1.7 及更早文件只读兼容。"""

    @staticmethod
    def _analyses_with_credential() -> dict:
        frame = pd.DataFrame({"x": [1.0, 2.0, 3.0]})
        credential = make_credential(rule_version="spc.imr",
                                     params={"subgroup": 5}, df=frame).to_dict()
        return {1: {"analysis_type": "spc.imr", "params": {"subgroup": 5},
                    "result": {"chart_type": "I-MR"}, "credential": credential}}

    def test_credential_roundtrip(self):
        raw = {"Sheet1": pd.DataFrame({"x": [1.0, 2.0, 3.0]})}
        with tempfile.NamedTemporaryFile(suffix=".qap", delete=False) as handle:
            path = handle.name
        try:
            ProjectManager.save_project(path, raw, self._analyses_with_credential(), {})
            project = ProjectManager.load_project(path)
            assert project["manifest"]["credential_count"] == 1
            credential = project["analyses"][1]["credential"]
            assert credential["rule_version"] == "spc.imr"
            assert credential["params"] == {"subgroup": 5}
            assert credential["data_fingerprint"].startswith("pd-hash-v1:")
            assert credential["app_version"]
        finally:
            os.unlink(path)

    def test_project_without_credential_still_saves(self):
        raw = {"Sheet1": pd.DataFrame({"x": [1]})}
        analyses = {1: {"analysis_type": "spc.imr", "params": {}, "result": {}}}
        with tempfile.NamedTemporaryFile(suffix=".qap", delete=False) as handle:
            path = handle.name
        try:
            ProjectManager.save_project(path, raw, analyses, {})
            project = ProjectManager.load_project(path)
            assert project["manifest"]["credential_count"] == 0
            assert "credential" not in project["analyses"][1]
        finally:
            os.unlink(path)

    def test_legacy_1_7_file_without_credential_reads(self):
        """手工构造 1.7 布局（analyses.json 无 credential 字段）应可读。"""
        import io

        from core.project_manager import _sanitize_for_json

        with tempfile.NamedTemporaryFile(suffix=".qap", delete=False) as handle:
            path = handle.name
        try:
            with zipfile.ZipFile(path, "w") as zf:
                zf.writestr("manifest.json", json.dumps({"version": "1.7"}))
                buf = io.StringIO()
                pd.DataFrame({"x": [1, 2]}).to_csv(buf, index=False)
                zf.writestr("data/Sheet1.csv", buf.getvalue())
                zf.writestr("analyses.json", json.dumps({
                    "1": {"analysis_type": "spc.imr", "params": {"k": 1},
                          "result": {"chart_type": "I-MR"}}}))
            project = ProjectManager.load_project(path)
            assert project["manifest"]["version"] == "1.7"
            assert project["analyses"][1]["params"] == {"k": 1}
            assert "credential" not in project["analyses"][1]
            assert ProjectManager.save_project  # 仍可另存为 1.8
            assert _sanitize_for_json({"a": 1}) == {"a": 1}
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
