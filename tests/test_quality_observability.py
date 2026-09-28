"""2026-09-28 质量审查 P2 — 静默失败可观测性 + 批量任务默认执行器回归

覆盖:
- core/audit.py：审计写入失败必须计数并告警（不再静默丢审计痕迹）
- core/session_manager.py：损坏会话文件跳过时留下 warning
- core/batch_scheduler.py：run_task_headless 端到端产出报告 + 缺数据源显式报错
"""

import json
import logging

import pandas as pd
import pytest

from core import audit as audit_module
from core.batch_scheduler import BatchTask, _selected_analysis_types, run_task_headless
from core.session_manager import SessionManager


class TestAuditObservability:
    def test_write_failure_is_counted_and_warned(self, tmp_path, monkeypatch, caplog):
        before = audit_module.write_failures()
        monkeypatch.setattr(audit_module, "LOG_FILE", str(tmp_path))  # 目录无法当作日志文件写
        with caplog.at_level(logging.WARNING, logger="core.audit"):
            audit_module.audit("export", "user", "test")
        assert audit_module.write_failures() == before + 1
        assert any("审计写入失败" in r.message for r in caplog.records)

    def test_successful_write_keeps_counter(self, tmp_path, monkeypatch):
        target = tmp_path / "audit.log"
        monkeypatch.setattr(audit_module, "LOG_FILE", str(target))
        before = audit_module.write_failures()
        audit_module.audit("import_data", "user", "ok")
        assert target.exists() and "import_data" in target.read_text(encoding="utf-8")
        assert audit_module.write_failures() == before


class TestSessionListObservability:
    def test_corrupt_session_file_skipped_with_warning(self, tmp_path, caplog):
        manager = SessionManager(default_dir=str(tmp_path))
        (tmp_path / "session_good.json").write_text(
            json.dumps({"name": "good", "session_id": "1", "created_at": "2026-09-28"}),
            encoding="utf-8")
        (tmp_path / "session_bad.json").write_text("{not json", encoding="utf-8")
        with caplog.at_level(logging.WARNING, logger="core.session_manager"):
            sessions = manager.list_sessions()
        assert [s["name"] for s in sessions] == ["good"]
        assert any("session_bad.json" in r.message for r in caplog.records)


class TestBatchTaskExecutor:
    @pytest.fixture
    def sheet_file(self, tmp_path):
        path = tmp_path / "batch_source.xlsx"
        pd.DataFrame({
            "测量值": [10.0 + (i % 7) * 0.1 for i in range(120)],
            "批次": [f"L{i % 3}" for i in range(120)],
        }).to_excel(path, sheet_name="Sheet1", index=False)
        return path

    def test_selected_types_map_from_template(self):
        task = BatchTask(name="t", analyses=[
            {"analysis_type": "xbar_r"}, {"analysis_type": "imr"},
            {"analysis_type": "normal_capability"}, {"analysis_type": "gage_rr_crossed"},
            {"analysis_type": "未知类型"},
        ])
        assert _selected_analysis_types(task) == ["spc", "capability", "msa"]

    def test_selected_types_default_when_empty(self):
        assert _selected_analysis_types(BatchTask(name="t")) == ["spc", "capability"]

    def test_run_task_headless_writes_report(self, sheet_file, tmp_path):
        out = tmp_path / "report.md"
        task = BatchTask(name="夜间巡检", data_source=str(sheet_file),
                         output_path=str(out), output_format="md")
        written = run_task_headless(task)
        assert written == str(out)
        text = out.read_text(encoding="utf-8")
        assert "夜间巡检" in text
        assert "## 1." in text

    def test_run_task_headless_requires_source(self, tmp_path):
        task = BatchTask(name="缺失数据源", data_source=str(tmp_path / "nope.xlsx"),
                         output_path=str(tmp_path / "r.md"), output_format="md")
        with pytest.raises(FileNotFoundError):
            run_task_headless(task)
