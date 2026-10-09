"""ImprovementCase v1 / CaseWorkflow v1 生命周期与类型化接线测试（v4.3.0 B1-1/B1-2/B1-5）。"""

import numpy as np
import pandas as pd
import pytest

from core.case_workflow import CaseWorkflow
from core.evidence_ledger import EvidenceLedger
from core.improvement_case import (
    CASE_SCHEMA_VERSION,
    PHASE_TO_STAGE,
    ImprovementCase,
)

CRED = {"rule_version": "paired-t/two-sided",
        "data_fingerprint": "pd-hash-v1:abc", "app_version": "4.3.0"}


def _closed_ready_case(status="active") -> ImprovementCase:
    case = ImprovementCase(id="CASE-1", title="节拍改善", status=status,
                           owner="张三", product="A100")
    case.add_step("baseline", ref="sheet:工时!A2:A31")
    case.add_step("remeasure", ref="sheet:工时!A33:A62")
    case.add_step("verify", result={"p_value": 0.001, "is_significant": True},
                  credential=CRED)
    return case


class TestCaseV1Fields:
    def test_defaults_and_new_fields(self):
        case = ImprovementCase(id="CASE-1")
        assert case.schema_version == CASE_SCHEMA_VERSION == "1"
        assert case.status == "active"
        assert case.owner == "" and case.product == ""
        assert case.measurement_refs == [] and case.standard_refs == []
        assert case.reopen_count == 0
        assert case.created_at and case.updated_at

    def test_add_step_with_result_credential_and_refs(self):
        case = ImprovementCase(id="CASE-2")
        step = case.add_step("baseline", ref="sheet:x", note="改善前",
                             result={"mean": 32.0}, credential=CRED,
                             measurement_refs=["MEV-1", "MEV-1"],
                             standard_refs=["S1"])
        assert step["result"] == {"mean": 32.0}
        assert step["credential"] == CRED
        assert step["measurement_refs"] == ["MEV-1", "MEV-1"]
        assert case.measurement_refs == ["MEV-1"]
        assert case.standard_refs == ["S1"]

    def test_unknown_phase_rejected(self):
        case = ImprovementCase(id="CASE-3")
        with pytest.raises(ValueError, match="未知阶段"):
            case.add_step("bogus")

    def test_stage_mapping_covers_workflow_vocabulary(self):
        assert PHASE_TO_STAGE["time_study"] == "analyse"
        assert PHASE_TO_STAGE["line_balance"] == "analyse"
        assert PHASE_TO_STAGE["improvement"] == "improve"
        assert PHASE_TO_STAGE["remeasure"] == "re_measure"
        assert PHASE_TO_STAGE["paired_test"] == "verify"
        assert PHASE_TO_STAGE["conclusion"] == "verify"
        assert PHASE_TO_STAGE["standard"] == "standardise"

    def test_covered_and_missing_stages(self):
        case = ImprovementCase(id="CASE-4")
        case.add_step("time_study")
        case.add_step("remeasure")
        assert case.covered_stages() == ["analyse", "re_measure"]
        assert "baseline" in case.missing_stages()
        assert "verify" in case.missing_stages()


class TestClosureGate:
    def test_missing_stages_reported(self):
        case = ImprovementCase(id="CASE-5")
        check = case.closure_check()
        assert check["ok"] is False
        assert set(check["missing_stages"]) == {"baseline", "re_measure", "verify"}
        with pytest.raises(ValueError, match="关闭条件未满足"):
            case.close_case("完成")

    def test_verify_without_credential_rejected(self):
        case = _closed_ready_case()
        case.steps[-1]["credential"] = {}
        check = case.closure_check()
        assert check["ok"] is False
        assert "统计判定" in "；".join(check["problems"])

    def test_verify_without_statistical_key_rejected(self):
        case = _closed_ready_case()
        case.steps[-1]["result"] = {"note": "看起来好了"}
        assert case.has_statistical_verification() is False
        assert case.closure_check()["ok"] is False

    def test_close_requires_reason(self):
        case = _closed_ready_case()
        with pytest.raises(ValueError, match="关闭原因"):
            case.close_case("   ")

    def test_close_success_sets_fields(self):
        case = _closed_ready_case()
        check = case.close_case("复测显著，标准已更新")
        assert check["ok"] is True
        assert case.status == "closed"
        assert case.closed_at
        assert case.close_reason == "复测显著，标准已更新"

    def test_draft_cannot_close(self):
        case = _closed_ready_case(status="draft")
        assert case.closure_check()["ok"] is False
        with pytest.raises(ValueError, match="不允许关闭"):
            case.close_case("提前关闭")

    def test_capability_verification_key_accepted(self):
        case = ImprovementCase(id="CASE-6")
        case.add_step("baseline")
        case.add_step("re_measure")
        case.add_step("verify", result={"cpk": 1.67}, credential=CRED)
        assert case.has_statistical_verification() is True


class TestTransitionsAndReopen:
    def test_normal_transitions(self):
        case = ImprovementCase(id="CASE-7", status="draft")
        assert case.transition("active") == "active"
        assert case.transition("verifying") == "verifying"
        assert case.transition("active", reason="补充数据") == "active"

    def test_illegal_transition_rejected(self):
        case = ImprovementCase(id="CASE-8", status="draft")
        with pytest.raises(ValueError, match="非法状态迁移"):
            case.transition("verifying")

    def test_abandon_requires_reason(self):
        case = ImprovementCase(id="CASE-9")
        with pytest.raises(ValueError, match="原因"):
            case.transition("abandoned")
        case.transition("abandoned", reason="项目取消")
        assert case.status == "abandoned"

    def test_reopen_from_closed_and_abandoned(self):
        case = _closed_ready_case()
        case.close_case("完成")
        case.reopen("客户要求继续跟踪")
        assert case.status == "active"
        assert case.reopen_count == 1
        assert case.reopen_history[0]["reason"] == "客户要求继续跟踪"
        assert case.closed_at == "" and case.close_reason == ""
        case.transition("abandoned", reason="取消")
        case.reopen("重新立项")
        assert case.reopen_count == 2

    def test_reopen_requires_reason_and_valid_state(self):
        case = ImprovementCase(id="CASE-10")
        with pytest.raises(ValueError, match="不需重开"):
            case.reopen("原因")
        case.status = "closed"
        with pytest.raises(ValueError, match="原因"):
            case.reopen(" ")

    def test_closed_case_cannot_transition(self):
        case = _closed_ready_case()
        case.close_case("完成")
        with pytest.raises(ValueError, match="reopen"):
            case.transition("active")


class TestSchemaCompatibility:
    def test_v1_roundtrip_preserves_all_fields(self):
        case = _closed_ready_case(status="verifying")
        case.measurement_refs.append("MEV-9")
        case.standard_refs.append("S9")
        data = case.to_dict()
        assert ImprovementCase.from_dict(data).to_dict() == data

    def test_v0_case_reads_and_upgrades(self):
        legacy = {"schema_version": "0", "id": "CASE-OLD", "title": "旧案例",
                  "status": "active",
                  "steps": [{"phase": "baseline", "ref": "sheet:旧", "note": "",
                             "at": "2026-01-01T00:00:00"}]}
        case = ImprovementCase.from_dict(legacy)
        assert case.schema_version == "1"
        assert case.id == "CASE-OLD"
        assert case.steps[0]["ref"] == "sheet:旧"
        assert case.owner == "" and case.reopen_count == 0

    def test_unknown_schema_rejected(self):
        with pytest.raises(ValueError, match="schema"):
            ImprovementCase.from_dict({"id": "X", "schema_version": "99"})

    def test_unknown_keys_ignored(self):
        data = ImprovementCase(id="CASE-11").to_dict()
        data["future"] = {"x": 1}
        assert ImprovementCase.from_dict(data).id == "CASE-11"

    def test_invalid_refs_and_count(self):
        with pytest.raises(ValueError, match="tags"):
            ImprovementCase(id="CASE-12", tags=[1])
        with pytest.raises(ValueError, match="reopen_count"):
            ImprovementCase(id="CASE-13", reopen_count=-1)


class TestWorkflowV1:
    def test_workflow_populates_case_owner_and_product(self):
        workflow = CaseWorkflow(title="换型改善", product="B200", owner="李四")
        assert workflow.case.product == "B200"
        assert workflow.case.owner == "李四"

    def test_step_refs_are_recorded_and_exported(self):
        workflow = CaseWorkflow(title="引用留痕")
        frame = pd.DataFrame({"x": [1.0, 2.0, 3.0]})
        step = workflow.record_step("baseline", {"mean": 2.0}, data_ref="sheet:x",
                                    frame=frame,
                                    measurement_refs=["MEV-1"],
                                    standard_refs=["S1"])
        assert step["measurement_refs"] == ["MEV-1"]
        assert step["standard_refs"] == ["S1"]
        assert workflow.case.measurement_refs == ["MEV-1"]
        markdown = workflow.to_markdown()
        assert "测量事件: MEV-1" in markdown
        assert "标准版本: S1" in markdown

    def test_record_analysis_step_maps_types(self):
        workflow = CaseWorkflow(title="分析接线")
        frame = pd.DataFrame({"cycle": [31.0, 32.0, 33.0]})
        record = {"analysis_type": "时间研究",
                  "params": {"rating": 100}, "result": {"summary": {"n": 3}}}
        step = workflow.record_analysis_step(record, data_ref="sheet:工时", frame=frame)
        assert step["phase"] == "time_study"
        assert step["credential"]["params"]["rating"] == 100
        assert step["credential"]["algorithm"] == "时间研究"

    def test_record_analysis_step_line_balance_and_capability(self):
        workflow = CaseWorkflow(title="多类型")
        workflow.record_analysis_step(
            {"analysis_type": "生产线平衡", "params": {}, "result": {"efficiency": 0.8}})
        workflow.record_analysis_step(
            {"analysis_type": "过程能力分析", "params": {"usl": 10}, "result": {"cpk": 1.2}})
        phases = [step["phase"] for step in workflow.case.steps]
        assert phases == ["line_balance", "verify"]
        assert workflow.case.covered_stages() == ["analyse", "verify"]

    def test_record_analysis_step_unknown_type_rejected(self):
        workflow = CaseWorkflow(title="未知类型")
        with pytest.raises(ValueError, match="尚未接入"):
            workflow.record_analysis_step({"analysis_type": "神秘分析", "result": {}})

    def test_record_step_rejects_non_dict_result(self):
        workflow = CaseWorkflow(title="类型校验")
        with pytest.raises(ValueError, match="dict"):
            workflow.record_step("baseline", result=["not-a-dict"])

    def test_wrapper_roundtrip_and_legacy_payload(self):
        workflow = CaseWorkflow(title="往返", product="P1", owner="王五")
        workflow.record_step("baseline", {"mean": 1.0}, data_ref="sheet:x")
        payload = workflow.to_dict()
        restored = CaseWorkflow.from_dict(payload)
        assert restored.case.id == workflow.case.id
        assert restored.owner == "王五"
        assert [s["phase"] for s in restored.case.steps] == ["baseline"]

        legacy = workflow.case.to_dict()
        legacy["schema_version"] = "0"
        restored_legacy = CaseWorkflow.from_dict(legacy)
        assert restored_legacy.case.id == workflow.case.id

    def test_close_and_reopen_use_closure_gate(self):
        workflow = CaseWorkflow(title="关闭")
        rng = np.random.default_rng(3)
        before = pd.Series(rng.normal(32.0, 1.0, 20))
        after = before - 3.0 + rng.normal(0, 0.2, 20)
        workflow.record_step("baseline", {"mean": float(before.mean())},
                             data_ref="sheet:before")
        workflow.record_step("remeasure", {"mean": float(after.mean())},
                             data_ref="sheet:after")
        workflow.run_paired_test(before, after, data_ref="sheet:before/after")
        workflow.close_case("复测显著")
        assert workflow.case.status == "closed"
        workflow.reopen("继续跟踪")
        assert workflow.case.status == "active"
        assert workflow.case.reopen_count == 1


class TestLedgerWiring:
    def test_lifecycle_events_are_chained(self):
        ledger = EvidenceLedger()
        workflow = CaseWorkflow(title="证据链", owner="张三", ledger=ledger)
        workflow.record_step("baseline", {"mean": 1.0}, data_ref="sheet:x")
        workflow.record_step("remeasure", {"mean": 0.9}, data_ref="sheet:y")
        workflow.record_step("paired_test",
                             {"p_value": 0.01, "is_significant": True},
                             data_ref="sheet:verify", frame=pd.DataFrame({"x": [1, 2]}))
        workflow.close_case("显著")
        workflow.reopen("再跟踪")

        types = [event.event_type for event in ledger.events]
        assert types == ["case_created", "case_step", "case_step", "case_step",
                         "case_closed", "case_reopened"]
        result = ledger.verify()
        assert result["ok"] is True
        assert result["count"] == 6
        closed = [e for e in ledger.events if e.event_type == "case_closed"][0]
        assert closed.payload["reason"] == "显著"
