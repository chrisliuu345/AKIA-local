"""告警自动立案 8D 测试（v4.4.0 B1）。"""

import os
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pandas as pd
import pytest

from core.alert_case import (
    ALERT_REPORT_PREFIX,
    AlertCaseLink,
    AlertCaseOrchestrator,
    AlertCasePolicy,
    AlertSnapshot,
    collect_context_evidence,
)
from core.case_workflow import CaseWorkflow
from core.evidence_ledger import EvidenceLedger
from core.project_context import ProjectContext, QualityCharacteristic

TZ = timezone(timedelta(hours=8))
BASE = datetime(2026, 10, 13, 8, 0, 0, tzinfo=TZ)


class _FakeAlert:
    """模拟 AlertEvent（属性形态；orchestrator 按鸭子类型读取）。"""

    def __init__(self, *, device="line1", channel="cycle", kind="oos",
                 desc="超规格上界", value=42.0, ts=None, severity="critical",
                 id=None, usl=40.0, lsl=30.0):
        self.device = device
        self.channel = channel
        self.kind = kind
        self.desc = desc
        self.value = value
        moment = ts if ts is not None else datetime.now().astimezone()
        self.ts = moment.timestamp()
        self.severity = severity
        self.id = id or f"ALERT-{uuid4().hex[:8]}"
        self.usl = usl
        self.lsl = lsl


def _alert(**kwargs):
    return _FakeAlert(**kwargs)


class _Clock:
    def __init__(self, start=BASE):
        self.now = start

    def __call__(self):
        return self.now

    def advance(self, minutes=0, seconds=0):
        self.now = self.now + timedelta(minutes=minutes, seconds=seconds)


def _setup(**kwargs):
    ledger = EvidenceLedger()
    context = ProjectContext()
    workflows = []

    def create_case(title, product="", owner=""):
        workflow = CaseWorkflow(title=title, product=product, owner=owner,
                                ledger=ledger)
        workflows.append(workflow)
        return workflow

    def lookup(case_id):
        return next((w for w in workflows if w.case.id == case_id), None)

    clock = kwargs.pop("clock", None)
    orchestrator = AlertCaseOrchestrator(
        ledger=ledger, context=context, create_case=create_case,
        case_lookup=lookup, clock=clock, **kwargs)
    return orchestrator, ledger, context, workflows


class TestSnapshot:
    def test_snapshot_from_event(self):
        snapshot = AlertSnapshot.from_event(_alert())
        assert snapshot.rule_key == "line1|cycle"
        assert snapshot.severity == "critical"
        assert snapshot.usl == 40.0 and snapshot.lsl == 30.0
        assert snapshot.ts.endswith("+08:00")

    def test_missing_subject_rejected(self):
        with pytest.raises(ValueError, match="设备/通道"):
            AlertSnapshot.from_event(_alert(device="", channel=""))

    def test_bad_severity_rejected(self):
        with pytest.raises(ValueError, match="非法告警等级"):
            AlertSnapshot.from_event(_alert(severity="panic"))


class TestPolicy:
    def test_default_threshold_is_critical(self):
        policy = AlertCasePolicy()
        assert policy.admits("critical") is True
        assert policy.admits("warning") is False
        assert policy.admits("info") is False

    def test_invalid_policy(self):
        with pytest.raises(ValueError, match="阈值等级"):
            AlertCasePolicy(severity_threshold="panic")
        with pytest.raises(ValueError, match="冷却"):
            AlertCasePolicy(cooldown_s=-1)


class TestOpenCase:
    def test_warning_ignored(self):
        orchestrator, _ledger, _ctx, workflows = _setup()
        decision = orchestrator.handle(_alert(severity="warning"))
        assert decision.action == "ignored"
        assert not workflows

    def test_critical_opens_case_with_full_evidence(self):
        orchestrator, ledger, _context, workflows = _setup()
        decision = orchestrator.handle(_alert(id="ALERT-OPEN"))
        assert decision.action == "opened"
        assert decision.case_id
        assert len(workflows) == 1
        case = workflows[0].case
        assert "auto_alert" in case.tags
        assert "alert:line1|cycle" in case.tags
        assert case.evidence_required is True
        baseline = case.steps[0]
        assert baseline["phase"] == "baseline"
        payload = baseline["result"]["alert"]
        assert payload["alert_id"] == "ALERT-OPEN"
        assert payload["rule_key"] == "line1|cycle"
        types = [event.event_type for event in ledger.events]
        assert types[0] == "case_created"
        assert "alert_case_opened" in types
        opened = next(e for e in ledger.events
                      if e.event_type == "alert_case_opened")
        assert f"case:{case.id}" in opened.object_refs
        assert "alert:ALERT-OPEN" in opened.object_refs

    def test_8d_draft_prefilled(self):
        orchestrator, _ledger, context, workflows = _setup()
        orchestrator.handle(_alert(id="ALERT-8D"))
        assert len(context.eight_d_reports) == 1
        report = context.eight_d_reports[0]
        assert report["id"] == f"{ALERT_REPORT_PREFIX}ALERT-8D"
        assert report["auto"] is True
        assert report["case_id"] == workflows[0].case.id
        assert workflows[0].case.report_refs == [report["id"]]
        d2 = report["steps"]["D2"]
        assert "超规格上界" in d2["problem_statement"]
        assert "USL=40" in d2["problem_statement"]
        assert d2["where"] == "line1/cycle"
        assert report["steps"]["D3"]["ica_description"] == ""
        assert report["steps"]["D4"]["root_cause"] == ""
        assert report["steps"]["D1"]["date_started"] == "2026-10-13"

    def test_context_evidence_linked(self):
        orchestrator, _ledger, context, workflows = _setup()
        context.add_characteristic(QualityCharacteristic(
            id="cycle", name="节拍", usl=40.0, lsl=30.0, target=35.0))
        orchestrator.handle(_alert(id="ALERT-CTX"))
        evidence = workflows[0].case.steps[0]["result"]["context"]
        assert evidence["characteristic"]["name"] == "节拍"


class TestCooldownMerge:
    def test_three_alerts_merge_into_one_case(self):
        clock = _Clock()
        orchestrator, ledger, _ctx, workflows = _setup(clock=clock)
        first = orchestrator.handle(_alert(id="A1", ts=clock.now))
        clock.advance(minutes=10)
        second = orchestrator.handle(_alert(id="A2", ts=clock.now))
        clock.advance(minutes=10)
        third = orchestrator.handle(_alert(id="A3", ts=clock.now))
        assert first.action == "opened"
        assert second.action == "merged" and third.action == "merged"
        assert len(workflows) == 1
        assert [step["phase"] for step in workflows[0].case.steps] == \
            ["baseline", "analyse", "analyse"]
        assert len(orchestrator.links) == 3
        assert orchestrator.case_for_alert("A2") == workflows[0].case.id
        opened_events = [e for e in ledger.events
                         if e.event_type == "alert_case_opened"]
        assert len(opened_events) == 1

    def test_beyond_cooldown_opens_new_case(self):
        clock = _Clock()
        orchestrator, _ledger, _ctx, workflows = _setup(clock=clock)
        orchestrator.handle(_alert(id="B1", ts=clock.now))
        clock.advance(minutes=31)
        decision = orchestrator.handle(_alert(id="B2", ts=clock.now))
        assert decision.action == "opened"
        assert len(workflows) == 2
        assert orchestrator.case_for_rule("line1|cycle") == workflows[1].case.id

    def test_different_rule_key_opens_new_case(self):
        orchestrator, _ledger, _ctx, workflows = _setup()
        orchestrator.handle(_alert(id="C1"))
        decision = orchestrator.handle(_alert(id="C2", channel="force"))
        assert decision.action == "opened"
        assert len(workflows) == 2

    def test_rebuild_restores_sessions_after_restart(self):
        clock = _Clock()
        orchestrator, ledger, context, workflows = _setup(clock=clock)
        orchestrator.handle(_alert(id="D1", ts=clock.now))
        clock.advance(minutes=5)

        def create_case(title, product="", owner=""):
            workflow = CaseWorkflow(title=title, ledger=ledger)
            workflows.append(workflow)
            return workflow

        def lookup(case_id):
            return next((w for w in workflows if w.case.id == case_id), None)

        restarted = AlertCaseOrchestrator(
            ledger=ledger, context=context, create_case=create_case,
            case_lookup=lookup, clock=clock)
        assert restarted.rebuild(workflows) >= 1
        decision = restarted.handle(_alert(id="D2", ts=clock.now))
        assert decision.action == "merged"
        assert len(workflows) == 1
        assert restarted.case_for_alert("D1") == workflows[0].case.id


class TestD6Gate:
    def test_evidence_required_blocks_close_without_refs(self):
        orchestrator, _ledger, _ctx, workflows = _setup()
        orchestrator.handle(_alert(id="E1"))
        workflow = workflows[0]
        frame = pd.DataFrame({"x": [1.0, 2.0, 3.0]})
        workflow.record_step("re_measure", {"n": 3}, frame=frame)
        workflow.record_step("verify", {"p_value": 0.01, "is_significant": True},
                             frame=frame)
        check = workflow.case.closure_check()
        assert check["ok"] is False
        assert any("D6 门禁" in problem for problem in check["problems"])
        with pytest.raises(ValueError, match="D6 门禁"):
            workflow.close_case("复测显著")
        # 关联复测数据后放行
        workflow.record_step("verify", {"p_value": 0.01, "is_significant": True},
                             frame=frame, measurement_refs=["MEV-1"])
        workflow.close_case("复测显著且数据齐备")
        assert workflow.case.status == "closed"

    def test_normal_case_not_affected(self):
        workflow = CaseWorkflow(title="普通案例")
        frame = pd.DataFrame({"x": [1.0, 2.0]})
        workflow.record_step("baseline", {"n": 2}, frame=frame)
        workflow.record_step("re_measure", {"n": 2}, frame=frame)
        workflow.record_step("verify", {"p_value": 0.02, "is_significant": True},
                             frame=frame)
        assert workflow.case.closure_check()["ok"] is True


class TestLinkContract:
    def test_roundtrip_and_validation(self):
        link = AlertCaseLink(alert_id="A", case_id="C", rule_key="d|c",
                             severity="critical", at="2026-10-13T08:00:00+08:00",
                             snapshot={"alert_id": "A"})
        restored = AlertCaseLink.from_dict(link.to_dict())
        assert restored == link
        with pytest.raises(ValueError, match="alert_id"):
            AlertCaseLink(alert_id="", case_id="C", rule_key="d",
                          severity="critical", at="2026-10-13T08:00:00+08:00")


class TestDraftBuilder:
    def test_collect_evidence_matches_fmea_objects(self):
        context = ProjectContext()
        context.add_characteristic(QualityCharacteristic(id="cycle", name="节拍"))
        context.set_fmea_items([
            SimpleNamespace(function="车削", failure_mode="节拍波动",
                            effect="产能损失", cause="刀具磨损"),
        ])
        snapshot = AlertSnapshot.from_event(_alert(channel="cycle"))
        evidence = collect_context_evidence(context, snapshot)
        assert evidence["characteristic"]["id"] == "cycle"
        assert evidence["fmea_items"][0]["failure_mode"] == "节拍波动"


class TestAlertEngineHook:
    def test_hook_invoked_and_isolated(self):
        from core.streaming.alerts import AlertEngine, AlertRule

        engine = AlertEngine(bus=None, rules=[
            AlertRule(device="dev", channel="ch", usl=40.0, lsl=30.0)])
        engine.debounce = False
        seen = []
        engine.alert_hook = seen.append
        engine._handle("dev", "ch",
                       SimpleNamespace(kind="oos", desc="超限", value=42.0))
        assert len(seen) == 1
        assert seen[0].severity == "critical"
        assert seen[0].usl == 40.0 and seen[0].lsl == 30.0
        def _boom(event):
            raise RuntimeError("boom")

        engine.alert_hook = _boom
        # 钩子异常被隔离，不向上抛
        engine._handle("dev", "ch",
                       SimpleNamespace(kind="oos", desc="超限", value=42.0))
