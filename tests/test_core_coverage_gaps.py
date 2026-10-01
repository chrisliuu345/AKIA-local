"""核心模块覆盖补口（v4.2.0 P3-4）

覆盖此前无直接测试引用的模块:
core/excel_utils.py · core/session_manager.py · core/audit.py · output/base_report_engine.py
"""

import re

import pandas as pd
import pytest

from core import audit as audit_module
from core.excel_utils import open_excel_auto, read_excel_auto
from core.session_manager import SessionManager
from output.base_report_engine import BaseReportEngine


@pytest.fixture
def excel_file(tmp_path):
    path = tmp_path / "sample.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame({"x": [1, 2, 3], "y": [4.0, 5.0, 6.0]}).to_excel(
            writer, sheet_name="Sheet1", index=False)
        pd.DataFrame({"z": [7, 8]}).to_excel(writer, sheet_name="Extra", index=False)
    return path


class TestExcelUtils:
    def test_read_xlsx_returns_dataframe(self, excel_file):
        frame = read_excel_auto(str(excel_file))
        assert list(frame.columns) == ["x", "y"]
        assert frame["x"].tolist() == [1, 2, 3]

    def test_read_all_sheets_returns_mapping(self, excel_file):
        sheets = read_excel_auto(str(excel_file), sheet_name=None)
        assert set(sheets) == {"Sheet1", "Extra"}
        assert list(sheets["Extra"].columns) == ["z"]

    def test_open_excel_auto_lists_sheets(self, excel_file):
        workbook = open_excel_auto(str(excel_file))
        assert workbook.sheet_names == ["Sheet1", "Extra"]
        workbook.close()

    def test_broken_xls_reports_engine_hint(self, tmp_path):
        broken = tmp_path / "broken.xls"
        broken.write_bytes(b"not an excel file")
        with pytest.raises(ValueError, match="无法读取 .xls"):
            read_excel_auto(str(broken))
        with pytest.raises(ValueError, match="python-calamine"):
            open_excel_auto(str(broken))


class TestSessionManager:
    def test_session_lifecycle(self, tmp_path):
        manager = SessionManager(default_dir=str(tmp_path))
        session_id = manager.create_session(name="测试会话", file_path="/tmp/a.xlsx")
        assert session_id
        assert manager.current_session["name"] == "测试会话"

        manager.add_analysis("spc", {"k": 1}, {"chart_type": "I-MR"})
        assert len(manager.current_session["analyses"]) == 1

        manager.set_config("usl", 10.0)
        assert manager.get_config("usl") == 10.0
        assert manager.get_config("missing", "fallback") == "fallback"

        saved = manager.save()
        assert saved.endswith(".json")

    def test_save_and_load_roundtrip(self, tmp_path):
        source = SessionManager(default_dir=str(tmp_path))
        source.create_session(name="往返")
        source.set_analyses({1: {"params": {"a": 1}, "result": {"ok": True}}})
        target_path = tmp_path / "explicit.json"
        source.save(str(target_path))

        restored = SessionManager(default_dir=str(tmp_path))
        payload = restored.load(str(target_path))
        assert payload["name"] == "往返"
        assert restored.get_analyses()[1]["result"]["ok"] is True

    def test_list_sessions_and_history(self, tmp_path):
        manager = SessionManager(default_dir=str(tmp_path))
        manager.create_session(name="甲")
        manager.save()
        manager.create_session(name="乙")
        manager.save()
        sessions = manager.list_sessions()
        assert len(sessions) >= 2
        assert isinstance(manager.get_history(limit=5), list)

    def test_clear_session_resets_state(self, tmp_path):
        manager = SessionManager(default_dir=str(tmp_path))
        manager.create_session(name="待清理")
        manager.clear_session()
        assert manager.current_session == {}


class TestAuditLog:
    def test_audit_writes_readable_line(self, tmp_path, monkeypatch):
        log_file = tmp_path / "audit.log"
        monkeypatch.setattr(audit_module, "LOG_FILE", str(log_file))
        audit_module.audit("import_data", "tester", "sheet=Sheet1")

        content = log_file.read_text(encoding="utf-8")
        assert re.match(
            r"^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\] tester: import_data sheet=Sheet1\n$",
            content), content

    def test_audit_rotates_oversized_log(self, tmp_path, monkeypatch):
        log_file = tmp_path / "audit.log"
        log_file.write_text("x" * 200, encoding="utf-8")
        monkeypatch.setattr(audit_module, "LOG_FILE", str(log_file))
        monkeypatch.setattr(audit_module, "_MAX_LOG_SIZE", 10)
        audit_module.audit("rotate", "tester")

        assert (tmp_path / "audit.log.1").exists()
        assert "rotate" in log_file.read_text(encoding="utf-8")


class TestBaseReportEngine:
    def test_iter_analyses_with_fallbacks(self):
        analyses = [
            {"analysis_type": "spc", "params": {"a": 1}, "result": {"r": 1}},
            {"chart_type": "I-MR", "result": {"r": 2}},
            {},
        ]
        rows = list(BaseReportEngine.iter_analyses(analyses))
        assert [row[0] for row in rows] == [0, 1, 2]
        assert rows[0][1] == "spc"
        assert rows[1][1] == "I-MR"
        assert rows[2][1] == "分析_3"
        assert rows[2][2] == {} and rows[2][3] == {}

    def test_footers_contain_app_identity(self):
        first, second = BaseReportEngine.footers()
        assert "AKIA" in first
        assert "v4." in first
        assert len(second) > 0

    def test_extract_conclusion_priority(self):
        assert BaseReportEngine.extract_conclusion(
            {"acceptance": {"message": "条件接受"}}) == "条件接受"
        assert "A+" in BaseReportEngine.extract_conclusion(
            {"capability": {"grade": "A+ (特优)"}})
        assert BaseReportEngine.extract_conclusion(
            {"p_value": 0.01, "is_significant": True}) != "-"
        assert BaseReportEngine.extract_conclusion(
            {"model": {"r_squared": 0.95}}) == "R² = 0.950"
        assert BaseReportEngine.extract_conclusion({}) == "-"

    def test_extract_key_result_variants(self):
        assert "Cpk=" in BaseReportEngine.extract_key_result(
            {"capability": {"cpk": 1.33, "grade": "A"}})
        assert "GRR%" in BaseReportEngine.extract_key_result(
            {"percentages": {"grr_pct_tv": 12.5}})
        assert "p=" in BaseReportEngine.extract_key_result(
            {"p_value": 0.02, "is_significant": True})
        assert BaseReportEngine.extract_key_result({}) == ""

    def test_classify_analysis_type(self):
        classify = BaseReportEngine.classify_analysis_type
        assert classify({"result": {"percentages": {}}}) == "msa"
        assert classify({"result": {"capability": {}}}) == "capability"
        assert classify({"result": {"model": {}}}) == "regression"
        assert classify({"analysis_type": "spc.imr"}) == "spc"
        assert classify({"analysis_type": "hypothesis.t_test"}) == "hypothesis"
        assert classify({"analysis_type": "doe.factorial"}) == "doe"
        assert classify({"analysis_type": "unknown"}) == "other"

    def test_safe_name_and_param_rows(self):
        assert BaseReportEngine.safe_name("a/b:c*d?e[f]") == "a_b_c_d_e_f_"
        assert len(BaseReportEngine.safe_name("x" * 80)) == 31
        assert BaseReportEngine.param_rows({"usl": 10, "n": None}) == [
            ("usl", "10"), ("n", "None")]
