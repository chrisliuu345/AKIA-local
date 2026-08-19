"""W06-W17 安全加固测试 — Commit D"""

import os
import sys
import base64
import logging
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── W06: SQL 连接串密码 URL 编码 ──────────────────────

class TestW06PasswordEncoding:
    """W06: 密码含 @ 等特殊字符时 URL 编码，确保 sanitize 正确打码"""

    def test_password_with_at_is_encoded(self):
        from core.sql_loader import build_connection_string
        config = {
            "db_type": "mysql", "host": "localhost", "port": 3306,
            "database": "testdb", "user": "root", "password": "p@ss",
        }
        conn_str = build_connection_string(config)
        assert "p%40ss" in conn_str
        assert conn_str.count("@") == 1

    def test_password_with_special_chars_encoded(self):
        from core.sql_loader import build_connection_string
        config = {
            "db_type": "postgresql", "host": "localhost", "port": 5432,
            "database": "testdb", "user": "user@1", "password": "p#s/w:r:d",
        }
        conn_str = build_connection_string(config)
        assert "user%401" in conn_str
        assert "p%23s%2Fw%3Ar%3Ad" in conn_str
        assert conn_str.count("@") == 1

    def test_sanitize_error_with_encoded_password(self):
        from core.sql_loader import sanitize_connection_error
        err = Exception("connect failed: mysql+pymysql://root:p%40ss@localhost:3306/db")
        sanitized = sanitize_connection_error(err)
        assert "p%40ss" not in sanitized
        assert "******" in sanitized

    def test_mssql_password_encoded(self):
        from core.sql_loader import build_connection_string
        config = {
            "db_type": "mssql", "host": "localhost", "port": 1433,
            "database": "testdb", "user": "sa", "password": "P@ssw0rd!",
        }
        conn_str = build_connection_string(config)
        assert "P%40ssw0rd%21" in conn_str
        assert conn_str.count("@") == 1


# ── W08: 共享项目路径穿越防护 ─────────────────────────

class TestW08PathTraversal:
    """W08: save_shared 部门参数路径穿越防护"""

    def test_traversal_sanitized_to_basename(self, tmp_path, monkeypatch):
        import core.project_manager as pm
        monkeypatch.setattr(pm, "SHARED_DIR", str(tmp_path))
        saved_paths = []

        def mock_save(path, *args, **kwargs):
            saved_paths.append(path)
            return path
        monkeypatch.setattr(pm.ProjectManager, "save_project", mock_save)

        pm.SharedProjectManager.save_shared("test.qap", {}, {}, {}, "../../etc", "")
        assert len(saved_paths) == 1
        assert saved_paths[0].startswith(str(tmp_path))
        assert "etc" in saved_paths[0]
        assert ".." not in saved_paths[0]

    def test_dotdot_rejected_by_containment(self, tmp_path, monkeypatch):
        import core.project_manager as pm
        monkeypatch.setattr(pm, "SHARED_DIR", str(tmp_path))
        with pytest.raises(ValueError, match="非法"):
            pm.SharedProjectManager.save_shared("test.qap", {}, {}, {}, "..", "")

    def test_normal_department_works(self, tmp_path, monkeypatch):
        import core.project_manager as pm
        monkeypatch.setattr(pm, "SHARED_DIR", str(tmp_path))
        saved_paths = []

        def mock_save(path, *args, **kwargs):
            saved_paths.append(path)
            return path
        monkeypatch.setattr(pm.ProjectManager, "save_project", mock_save)

        pm.SharedProjectManager.save_shared("test.qap", {}, {}, {}, "质量部", "")
        assert saved_paths[0].startswith(str(tmp_path))
        assert "质量部" in saved_paths[0]


# ── W09: 日志器不再单例缓存 ───────────────────────────

class TestW09DistinctLoggers:
    """W09: get_logger 返回不同名称的独立 logger"""

    def test_distinct_names_return_distinct_loggers(self):
        from core.log_util import get_logger
        logger_a = get_logger("TestModuleA")
        logger_b = get_logger("TestModuleB")
        assert logger_a.name == "TestModuleA"
        assert logger_b.name == "TestModuleB"
        assert logger_a is not logger_b

    def test_same_name_returns_same_logger(self):
        from core.log_util import get_logger
        logger1 = get_logger("TestSame")
        logger2 = get_logger("TestSame")
        assert logger1 is logger2


# ── W15: DPAPI 降级告警 ───────────────────────────────

class TestW15DPAPIDegradation:
    """W15: _obscure DPAPI 失败时记录 warning 日志"""

    def test_warning_logged_on_dpapi_failure(self, caplog):
        import ui.dialogs.db_connection_dialog as dbcd
        with patch("core.secret_store.encrypt_secret", side_effect=Exception("DPAPI unavailable")):
            with caplog.at_level(logging.WARNING, logger="QA-Tool.DbConnection"):
                result = dbcd._obscure("mysecret")
        assert "DPAPI" in caplog.text or "降级" in caplog.text
        assert base64.b64decode(result.encode()).decode() == "mysecret"


# ── W16: 合规模板路径穿越防护 ─────────────────────────

class TestW16TemplateTraversal:
    """W16: load_template 拒绝路径穿越"""

    def test_dotdot_rejected(self):
        from output.compliance_report import ComplianceReportGenerator
        with pytest.raises(ValueError, match="非法"):
            ComplianceReportGenerator.load_template("../secret")

    def test_slash_rejected(self):
        from output.compliance_report import ComplianceReportGenerator
        with pytest.raises(ValueError, match="非法"):
            ComplianceReportGenerator.load_template("foo/bar")

    def test_backslash_rejected(self):
        from output.compliance_report import ComplianceReportGenerator
        with pytest.raises(ValueError, match="非法"):
            ComplianceReportGenerator.load_template("foo\\bar")

    def test_empty_rejected(self):
        from output.compliance_report import ComplianceReportGenerator
        with pytest.raises(ValueError, match="非法"):
            ComplianceReportGenerator.load_template("")


# ── W17: Excel 公式注入防护 ───────────────────────────

class TestW17FormulaInjection:
    """W17: _safe_write 字符串使用 write_string 防止公式注入"""

    def test_string_uses_write_string(self):
        from output.excel_report import ExcelReport
        report = ExcelReport.__new__(ExcelReport)
        ws = MagicMock()
        report._safe_write(ws, 0, 0, "=cmd|' /c calc'!A1", None)
        ws.write_string.assert_called_once_with(0, 0, "=cmd|' /c calc'!A1", None)
        ws.write.assert_not_called()

    def test_number_uses_write(self):
        from output.excel_report import ExcelReport
        report = ExcelReport.__new__(ExcelReport)
        ws = MagicMock()
        report._safe_write(ws, 0, 0, 42, None)
        ws.write.assert_called_once_with(0, 0, 42, None)
        ws.write_string.assert_not_called()

    def test_normal_string_uses_write_string(self):
        from output.excel_report import ExcelReport
        report = ExcelReport.__new__(ExcelReport)
        ws = MagicMock()
        report._safe_write(ws, 0, 0, "Cpk = 1.33", None)
        ws.write_string.assert_called_once_with(0, 0, "Cpk = 1.33", None)
        ws.write.assert_not_called()

    def test_float_uses_write(self):
        from output.excel_report import ExcelReport
        report = ExcelReport.__new__(ExcelReport)
        ws = MagicMock()
        report._safe_write(ws, 0, 0, 1.33, None)
        ws.write.assert_called_once_with(0, 0, 1.33, None)
        ws.write_string.assert_not_called()
