#!/usr/bin/env python3
"""v4.4.0 闭环八链路端到端演示（B7-1）——一条命令全绿，输出可粘贴证据。

八链路::

    1) 告警 → 2) 自动立案（含同案续报合并）→ 3) 抽样转移（加严）→
    4) 量具漂移判定 → 5) 技能约束排班（不可行 → 培训后可行）→
    6) 复测 + 统计判定 → 7) 案例关闭（D6 数据门禁）→ 8) 收益入账与月度复算

另附：证据包导出 + 独立校验、案例 Markdown、链路清单 summary.json。
用法::

    python tools/demo_v44_case.py [--output TEMP/demo_v44]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


class _FakeAlert:
    """合成告警（属性形态，orchestrator 鸭子类型读取）。"""

    def __init__(self, alert_id: str, *, device: str = "line1",
                 channel: str = "节拍", severity: str = "critical",
                 value: float = 42.0, desc: str = "连续 9 点在中心线同侧",
                 usl: float | None = 40.0, lsl: float | None = 30.0):
        self.id = alert_id
        self.device = device
        self.channel = channel
        self.kind = "oos"
        self.desc = desc
        self.value = value
        self.ts = datetime.now().astimezone().timestamp()
        self.severity = severity
        self.usl = usl
        self.lsl = lsl


def main() -> int:
    parser = argparse.ArgumentParser(description="AKIA v4.4.0 闭环八链路演示")
    parser.add_argument("--output", default=str(ROOT / "TEMP" / "demo_v44"))
    args = parser.parse_args()
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    import numpy as np
    import pandas as pd

    from analysis.hypothesis.t_tests import paired
    from analysis.ie.line_balance import LineBalanceEngine
    from core.alert_case import AlertCaseOrchestrator
    from core.benefit_ledger import BenefitLedger, record_case_benefit
    from core.case_workflow import CaseWorkflow
    from core.data_objects import Process
    from core.evidence_ledger import EvidenceLedger
    from core.evidence_pack import export_evidence_pack
    from core.gauge_study import GaugeMonitor, GaugeStudyPolicy
    from core.project_context import ProjectContext
    from core.sampling_plan import scope_key_for
    from core.sampling_state import SamplingStateManager
    from core.skill_matrix import SkillMatrix
    from core.standard_record import StandardRegistry

    summary: dict = {}
    ledger = EvidenceLedger()
    registry = StandardRegistry()
    context = ProjectContext()
    cases: list[CaseWorkflow] = []

    # ---- 1) 告警 → 2) 自动立案（临界告警立案；同规则续报合并同案）
    def create_case(title, product="", owner=""):
        workflow = CaseWorkflow(title=title, product=product, owner=owner,
                                ledger=ledger)
        cases.append(workflow)
        return workflow

    orchestrator = AlertCaseOrchestrator(
        ledger=ledger, context=context, create_case=create_case,
        case_lookup=lambda cid: next(
            (w for w in cases if w.case.id == cid), None))
    first = orchestrator.handle(_FakeAlert("ALERT-V44-1"))
    second = orchestrator.handle(_FakeAlert("ALERT-V44-2", value=43.5))
    workflow = cases[0]
    summary["alert_case"] = {
        "opened": first.action == "opened",
        "merged": second.action == "merged",
        "case_id": workflow.case.id,
        "evidence_required": workflow.case.evidence_required,
    }

    # ---- 3) 抽样转移：两批拒收 → 加严（方案随状态变化）
    sampling = SamplingStateManager(ledger=ledger, standards=registry)
    scope = scope_key_for("供应商A", "P100")
    plan_normal = sampling.select_plan(scope, lot_size=2000, aql=1.0, seed=42)
    frame = pd.DataFrame({"x": np.arange(5000.0)})
    sampled, decision = sampling.sample(frame, scope, method="systematic",
                                        seed=42)
    sampling.record_lot(scope_key=scope, qty=2000, inspected=125, defects=5,
                        decision="reject")
    sampling.record_lot(scope_key=scope, qty=2000, inspected=125, defects=6,
                        decision="reject")
    plan_tightened = sampling.select_plan(scope, lot_size=2000, aql=1.0)
    summary["sampling"] = {
        "state": sampling.state_for(scope).state,
        "normal_draw": len(sampled),
        "fingerprint": decision.row_fingerprint,
        "accept_normal": plan_normal["plan"]["accept"],
        "accept_tightened": plan_tightened["plan"]["accept"],
    }

    # ---- 4) 量具漂移：12 点基线后 3σ+ 跳变 → MPC 判异
    gauge = GaugeMonitor()
    gauge.set_policy(GaugeStudyPolicy(
        gauge_id="caliper-1:value", expected_value=10.0, window_n=50,
        drift_rule={}))
    for value in [10.000, 10.001] * 6:
        gauge.ingest_values("caliper-1:value", [value])
    gauge_outcome = gauge.ingest_values("caliper-1:value", [12.0])
    summary["gauge"] = {
        "state": gauge_outcome.state,
        "reasons": gauge_outcome.drift_reasons,
        "health": gauge_outcome.health_score,
    }

    # ---- 5) 技能约束排班：基线（1 人）不可行 → 培训后（2 人）可行
    processes = [Process(process_id=f"OP{i}", process_name=f"工序{i}",
                         cycle_time=10.0) for i in range(1, 5)]
    single = SkillMatrix(entries=[
        {"operator": "张三", "process_id": p.process_id, "level": 4}
        for p in processes])
    baseline_plan = LineBalanceEngine.schedule_with_skills(
        processes, 20.0, single)
    trained = SkillMatrix(entries=[
        {"operator": operator, "process_id": p.process_id, "level": 4}
        for operator in ("张三", "李四") for p in processes])
    trained_plan = LineBalanceEngine.schedule_with_skills(
        processes, 20.0, trained)
    summary["skills"] = {
        "baseline_feasible": baseline_plan.feasible,
        "baseline_unmet": baseline_plan.unmet,
        "trained_feasible": trained_plan.feasible,
        "fingerprint": trained_plan.plan_ref,
        "assignments": len(trained_plan.assignments),
    }

    # ---- 6) 复测 + 统计判定（真实配对检验）+ 技能排班记入案例
    rng = np.random.default_rng(7)
    before = rng.normal(32.0, 1.0, 30)
    after = rng.normal(30.0, 1.0, 30)
    paired_result = paired(pd.Series(before), pd.Series(after))
    evidence_frame = pd.DataFrame({"before": before, "after": after})
    workflow.record_step(
        "re_measure", {
            "paired": paired_result,
            "skills": trained_plan.to_dict(),
            "params": {"p_value": paired_result.get("p_value")},
        },
        data_ref="synthetic://recheck", frame=evidence_frame,
        rule_version="paired-t@v44", analysis_type="配对检验",
        measurement_refs=["MEV-V44-BEFORE", "MEV-V44-AFTER"],
        params={"skill_fingerprint": trained.fingerprint()},
        note="复测：节拍显著下降 + 技能排班可行")
    verify_result = {"p_value": paired_result.get("p_value"),
                     "is_significant": paired_result.get("is_significant"),
                     "verdict": "复测显著改善"}
    workflow.record_step(
        "verify", verify_result, data_ref="synthetic://recheck",
        frame=evidence_frame, rule_version="verify@v44",
        analysis_type="配对检验",
        measurement_refs=["MEV-V44-BEFORE", "MEV-V44-AFTER"],
        note="验证：统计判定 + 复测数据引用齐备")

    # ---- 7) 案例关闭（D6 数据门禁：复测引用 + 统计判定）
    close_check = workflow.case.closure_check()
    workflow.close_case("复测显著（p<0.05）且技能排班可执行")
    summary["case_closure"] = {
        "gate_ok": close_check["ok"],
        "status": workflow.case.status,
        "steps": [step["phase"] for step in workflow.case.steps],
    }

    # ---- 8) 收益入账 + 月度复算（标准升版后口径前移）
    benefit_ledger = BenefitLedger()
    standard_v1 = registry.record_change(
        "standard_time", "OP10", {"standard_time_s": 32.0},
        change_reason="初始标准工时", changed_by="system")
    workflow.case.standard_refs.append("OP10")
    record = record_case_benefit(
        benefit_ledger, workflow.case, month=datetime.now().strftime("%Y-%m"),
        baseline_value=32.0, new_value=30.0, quantity=1000, unit_cost=0.5,
        confidence="A", unit="s", currency="CNY", standards=registry,
        event_sink=lambda event_type, refs, payload: ledger.append(
            event_type, object_refs=refs, payload=payload))
    recorded_as_of = record.basis["standard_as_of"]
    standard_v2 = registry.record_change(
        "standard_time", "OP10", {"standard_time_s": 30.0},
        change_reason="改善后标准工时", changed_by="system")
    recompute = benefit_ledger.recompute_month(
        datetime.now().strftime("%Y-%m"), standards=registry)
    summary["benefit"] = {
        "amount": record.amount,
        "confidence": record.confidence,
        "standard_as_of_v1": recorded_as_of == standard_v1.valid_from,
        "recompute_moved": record.basis["standard_as_of"] == standard_v2.valid_from,
        "recompute_updates": len(recompute["updates"]),
        "roi": benefit_ledger.summary()["roi"],
    }

    # ---- 证据包导出 + 独立校验 + 案例 Markdown
    pack = export_evidence_pack(
        str(output_dir / "evidence_v44.zip"), case=workflow.to_dict(),
        case_markdown=workflow.to_markdown(), ledger=ledger,
        standards=registry.to_dict())
    (output_dir / "case_v44.md").write_text(workflow.to_markdown(),
                                            encoding="utf-8")
    summary["evidence"] = {
        "pack_ok": pack["verify"]["ok"],
        "event_count": len(ledger),
        "event_types": sorted({e.event_type for e in ledger.events}),
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8")

    print("== v4.4.0 闭环八链路演示 ==")
    for name, info in summary.items():
        print(f"[{name}] {json.dumps(info, ensure_ascii=False, default=str)}")
    print(f"\n输出目录: {output_dir}")

    ok = (
        summary["alert_case"]["opened"] and summary["alert_case"]["merged"]
        and summary["sampling"]["state"] == "tightened"
        and summary["gauge"]["state"] == "drift"
        and summary["skills"]["baseline_feasible"] is False
        and summary["skills"]["trained_feasible"] is True
        and summary["case_closure"]["gate_ok"]
        and summary["case_closure"]["status"] == "closed"
        and summary["benefit"]["standard_as_of_v1"]
        and summary["benefit"]["recompute_moved"]
        and summary["benefit"]["recompute_updates"] == 1
        and summary["evidence"]["pack_ok"]
    )
    print("结果: " + ("全链路通过" if ok else "存在未通过链路"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
