"""改善案例工作流测试（v4.2.0 P5）

覆盖:
1. 端到端闭环：基线 → 时间研究 → 线平衡 → 改善 → 复测 → 配对检验 → 结论 → 标准
2. 每步留痕：时间戳 + 数据引用 + 判定凭证（含数据指纹）
3. 配对检验真实接线（既有 t 检验引擎）与结论方向
4. Markdown 导出、字典往返（`.qap` cases 段）、缺步提示
5. 参数校验与旧案例兼容
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pandas as pd
import pytest

from core.case_workflow import PHASES, CaseWorkflow


def _baseline_frame(n: int = 30, seed: int = 3) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame({"cycle": rng.normal(32.0, 1.0, n)})


class TestHappyPath:
    def test_full_chain_records_all_phases(self):
        workflow = CaseWorkflow(title="总装线节拍改善", product="A100", owner="张三")
        baseline = _baseline_frame()
        workflow.record_step("baseline", {"params": {"n": len(baseline)},
                                          "mean": float(baseline["cycle"].mean())},
                             data_ref="sheet:工时!A2:A31", frame=baseline,
                             note="改善前 30 个周期")

        study = pd.DataFrame({"element": ["取件", "装配", "检验"],
                              "observed_s": [8.0, 15.0, 6.0]})
        workflow.record_step("time_study", {"params": {"elements": len(study)},
                                           "standard_time": 31.0},
                             data_ref="sheet:工时!B2:C4", frame=study)

        balance = pd.DataFrame({"station": ["S1", "S2", "S3"],
                                "cycle_time": [36.0, 28.0, 30.0]})
        workflow.record_step("line_balance", {"params": {"stations": 3},
                                              "bottleneck": "S1", "line_balance_rate": 86.7},
                             data_ref="sheet:线平衡", frame=balance)

        workflow.record_step("improvement", {"params": {"action": "拆分取件动作"},
                                             "expected_gain_s": 4.0},
                             data_ref="方案:A100-002", note="工装改善")

        after = _baseline_frame(n=30, seed=9) - 4.0
        workflow.record_step("remeasure", {"params": {"n": len(after)},
                                           "mean": float(after["cycle"].mean())},
                             data_ref="sheet:工时!A33:A62", frame=after)

        before = _baseline_frame()["cycle"]
        workflow.run_paired_test(before, after["cycle"],
                                 data_ref="sheet:工时!A2:A31 vs A33:A62")
        workflow.conclude("节拍由 32.0s 降至 28.0s，配对检验显著，改善有效",
                          data_ref="case:conclusion")
        workflow.standard_draft("更新作业标准：取件动作拆分为两步，节拍 28s",
                                data_ref="standard:A100-SOP")

        assert workflow.missing_phases() == []
        assert [step["phase"] for step in workflow.case.steps] == list(PHASES)
        assert workflow.case.status == "active"
        assert workflow.case.standard_draft.startswith("更新作业标准")

    def test_step_carries_timestamp_reference_and_credential(self):
        workflow = CaseWorkflow(title="凭证留痕")
        frame = _baseline_frame()
        step = workflow.record_step("baseline", {"mean": 32.0},
                                    data_ref="sheet:工时!A2:A31", frame=frame)
        assert step["recorded_at"]
        assert step["ref"] == "sheet:工时!A2:A31"
        credential = step["credential"]
        assert credential["rule_version"] == "baseline"
        assert credential["data_fingerprint"].startswith("pd-hash-v1:")
        assert credential["params"]["data_ref"] == "sheet:工时!A2:A31"

    def test_step_without_frame_uses_no_data_fingerprint(self):
        workflow = CaseWorkflow(title="无数据步骤")
        step = workflow.record_step("improvement", {"params": {}})
        assert step["credential"]["data_fingerprint"] == "no-data"


class TestPairedTestStep:
    def test_engine_is_wired_and_direction_correct(self):
        rng = np.random.default_rng(7)
        before = pd.Series(rng.normal(32.0, 1.0, 30))
        after = before - 4.0 + rng.normal(0, 0.3, 30)
        workflow = CaseWorkflow(title="配对检验接线")
        step = workflow.run_paired_test(before, after, data_ref="sheet:工时")

        result = step["result"]
        assert result["test_type"] == "Paired t-Test"
        assert result["p_value"] < 0.01
        assert result["is_significant"] is True
        assert "显著" in step["note"]
        assert step["credential"]["data_fingerprint"].startswith("pd-hash-v1:")

    def test_no_effect_is_not_significant(self):
        rng = np.random.default_rng(8)
        before = pd.Series(rng.normal(30.0, 1.0, 25))
        after = pd.Series(rng.normal(30.0, 1.0, 25))
        workflow = CaseWorkflow(title="无效应")
        step = workflow.run_paired_test(before, after)
        assert step["result"]["is_significant"] is False
        assert "无显著差异" in step["note"]


class TestExportAndRoundtrip:
    @staticmethod
    def _workflow() -> CaseWorkflow:
        workflow = CaseWorkflow(title="导出案例", product="B200", owner="李四")
        frame = _baseline_frame(n=10)
        workflow.record_step("baseline", {"mean": 32.0},
                            data_ref="sheet:工时!A2:A11", frame=frame)
        workflow.conclude("结论文本", data_ref="case:conclusion")
        workflow.standard_draft("标准草稿文本")
        return workflow

    def test_markdown_contains_labels_and_missing_hint(self):
        markdown = self._workflow().to_markdown()
        assert "# 改善案例: 导出案例" in markdown
        assert "基线测量（baseline）" in markdown
        assert "结论（conclusion）" in markdown
        assert "待补" in markdown  # 未走完的步骤应提示
        assert "sheet:工时!A2:A11" in markdown
        assert "pd-hash-v1:" in markdown

    def test_dict_roundtrip_keeps_steps(self):
        original = self._workflow()
        payload = original.to_dict()
        restored = CaseWorkflow.from_dict(payload)
        assert restored.case.id == original.case.id
        assert restored.case.title == "导出案例"
        assert restored.owner == "李四"
        assert [step["phase"] for step in restored.case.steps] == ["baseline", "conclusion", "standard"]
        assert restored.case.standard_draft == "标准草稿文本"

    def test_legacy_case_without_workflow_metadata(self):
        """旧 `.qap` cases 段（纯 ImprovementCase）应能恢复。"""
        legacy = {"schema_version": "0", "id": "CASE-OLD", "title": "旧案例",
                  "steps": [{"phase": "baseline", "ref": "sheet:旧", "note": "", "at": "2026-01-01T00:00:00"}]}
        restored = CaseWorkflow.from_dict(legacy)
        assert restored.case.id == "CASE-OLD"
        assert restored.case.steps[0]["ref"] == "sheet:旧"


class TestValidation:
    def test_empty_title_rejected(self):
        with pytest.raises(ValueError, match="标题"):
            CaseWorkflow(title="  ")

    def test_unknown_phase_rejected(self):
        workflow = CaseWorkflow(title="阶段校验")
        with pytest.raises(ValueError, match="未知阶段"):
            workflow.record_step("bogus")

    def test_empty_conclusion_rejected(self):
        workflow = CaseWorkflow(title="结论校验")
        with pytest.raises(ValueError, match="结论"):
            workflow.conclude("   ")

    def test_missing_phases_reported_in_order(self):
        workflow = CaseWorkflow(title="缺步提示")
        workflow.record_step("time_study", {"params": {}})
        missing = workflow.missing_phases()
        assert missing[0] == "baseline"
        assert "time_study" not in missing
        assert missing[-1] == "standard"


class TestWorkspaceEntry:
    """P5 UI 入口：菜单动作 + 对话框（离屏）。"""

    def test_menu_action_exists(self):
        pytest.importorskip("PySide6")
        from ui.main_window import MainWindow

        window = MainWindow()
        try:
            tools_menu = next(action.menu() for action in window.menuBar().actions()
                              if "工具" in action.text())
            texts = [action.text() for action in tools_menu.actions()]
            assert any("改善案例工作台" in text for text in texts)
        finally:
            window.close()

    def test_handler_builds_baseline_from_imported_data(self, monkeypatch):
        pytest.importorskip("PySide6")
        import pandas as pd

        from ui.dialogs import case_workflow_dialog as dialog_module
        from ui.main_window import MainWindow

        opened = {}

        class _FakeDialog:
            def __init__(self, workflow, parent=None):
                opened["workflow"] = workflow

            def exec(self):
                return 0

        monkeypatch.setattr(dialog_module, "CaseWorkflowDialog", _FakeDialog)
        window = MainWindow()
        try:
            window.current_data = {
                "source": "/tmp/line_a.xlsx",
                "raw_data": {"工时": pd.DataFrame({"cycle": [31.0, 32.0, 33.0]})},
            }
            window._on_case_workbench()
            workflow = opened["workflow"]
            assert workflow.case.title.endswith("line_a.xlsx")
            assert [step["phase"] for step in workflow.case.steps] == ["baseline"]
            credential = workflow.case.steps[0]["credential"]
            assert credential["data_fingerprint"].startswith("pd-hash-v1:")
            assert workflow.case.steps[0]["ref"] == "sheet:工时"
            assert window._last_case_workflow is workflow
        finally:
            window.close()


class TestCaseId:
    def test_same_second_creation_does_not_collide(self):
        """同一秒内连续创建案例不得撞号（旧实现 CASE-时间戳 会重复）。"""
        first = CaseWorkflow("案例A")
        second = CaseWorkflow("案例B")
        assert first.case.id != second.case.id
        assert first.case.id.startswith("CASE-")
