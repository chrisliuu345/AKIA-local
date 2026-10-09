"""v4.3.0 端到端演示测试（B5-1）— 一条命令复现完整证据闭环。"""

import json
from pathlib import Path

from core.evidence_pack import verify_evidence_pack
from tools.demo_v43_case import run_demo


class TestCaseE2E:
    def test_full_chain_is_reproducible(self, tmp_path):
        output = tmp_path / "demo"
        summary = run_demo(str(output))

        # 案例闭环：8 阶段齐全 + 关闭 + 每步凭证
        assert summary["case_status"] == "closed"
        assert summary["missing_phases"] == []
        assert summary["steps_total"] == summary["steps_with_credential"] == 8
        assert set(summary["measurement_events"]) <= set(
            summary["case_measurement_refs"])

        # 标准 as-of：历史批次还原到当时标准（USL=33），现行已收紧（USL=30）
        assert summary["standard_as_of_v1_usl"] == 33.0
        assert len(summary["standard_versions"]) == 2

        # 账本链完整 + 关键事件类型齐全
        ledger = summary["ledger"]
        assert ledger["chain_ok"] is True
        types = ledger["types"]
        for event_type in ("data_imported", "measurement_recorded",
                           "standard_changed", "analysis_run", "case_created",
                           "case_step", "case_closed", "report_exported",
                           "share_pack_exported"):
            assert types.get(event_type, 0) >= 1, event_type

        # 证据包可独立校验；脱敏包扫描通过；HTML 追溯码可回读
        assert summary["evidence_pack_ok"] is True
        assert verify_evidence_pack(summary["evidence_pack"])["ok"] is True
        assert summary["share_pack_scan_ok"] is True
        assert Path(summary["share_pack"]).exists()
        html = Path(summary["report"]).read_text(encoding="utf-8")
        assert summary["trace_code"] in html
        assert "追溯码" in html

        saved = json.loads((output / "summary.json").read_text(encoding="utf-8"))
        assert saved["case_id"] == summary["case_id"]
