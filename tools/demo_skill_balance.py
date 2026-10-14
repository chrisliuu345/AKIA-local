#!/usr/bin/env python3
"""技能约束线平衡端到端演示（v4.4.0 B5）。

合成数据 → 技能约束排班（不可行明细不静默降级）→ 案例基线与复测步骤
（凭证含技能矩阵指纹）→ 输出排班表 / 案例摘要 / 账本事件数。

用法::

    python tools/demo_skill_balance.py [--output TEMP/demo_skill_balance]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="技能约束线平衡端到端演示")
    parser.add_argument("--output", default=str(ROOT / "TEMP" / "demo_skill_balance"))
    args = parser.parse_args()
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    import pandas as pd

    from analysis.ie.line_balance import LineBalanceEngine
    from core.case_workflow import CaseWorkflow
    from core.data_objects import Process
    from core.evidence_ledger import EvidenceLedger
    from core.skill_matrix import ProcessSkillReq, SkillMatrix

    # ---- 合成产线：8 工序（含前置与设备），节拍 30s
    cycle_times = {"OP10": 12.0, "OP20": 18.0, "OP30": 22.0, "OP40": 15.0,
                   "OP50": 19.0, "OP60": 11.0, "OP70": 24.0, "OP80": 13.0}
    predecessors = {"OP20": ["OP10"], "OP30": ["OP20"], "OP40": ["OP30"],
                    "OP50": ["OP40"], "OP60": ["OP50"], "OP70": ["OP60"],
                    "OP80": ["OP70"]}
    equipment = {"OP30": "压机", "OP70": "压机"}
    processes = [Process(process_id=pid, process_name=f"工序{pid}",
                         cycle_time=ct, equipment=equipment.get(pid, ""),
                         predecessors=predecessors.get(pid, []))
                 for pid, ct in cycle_times.items()]
    takt = 45.0  # LPT 下 4 工位：恰好放得下"培训后 4 人"，而基线只有 2 人

    # ---- 技能矩阵（基线）：2 名操作员覆盖关键工序；OP30/OP70 需 4 级
    baseline_levels = {"张三": 5, "李四": 4}
    entries = [{"operator": operator, "process_id": pid, "level": level}
               for operator, level in baseline_levels.items()
               for pid in cycle_times]
    matrix = SkillMatrix(
        entries=entries,
        requirements=[ProcessSkillReq("OP30", 4).to_dict(),
                      ProcessSkillReq("OP70", 4).to_dict()])

    plan = LineBalanceEngine.schedule_with_skills(
        processes, takt, matrix, equipment_parallel={"压机": 1})
    print("== 技能约束排班 ==")
    print(f"工位数 {plan.constraints['headcount_required']} · "
          f"平衡率 {plan.balance_rate_before:.2%} → "
          + (f"{plan.balance_rate_after:.2%}" if plan.balance_rate_after
             is not None else "不可行"))
    roster = pd.DataFrame(plan.assignments)
    print(roster.to_string(index=False))
    if plan.unmet:
        print("不可行明细:")
        for reason in plan.unmet:
            print(f"- {reason}")
    print(f"技能矩阵指纹: {plan.plan_ref}")

    # ---- 案例：基线（2 人 + 1 台压机，不可行）→ 复测（培训 2 人 + 增配压机，可行）
    ledger = EvidenceLedger()
    workflow = CaseWorkflow(title="技能约束线平衡演示", ledger=ledger)
    frame = pd.DataFrame([{
        "process_id": p.process_id, "cycle_time": p.cycle_time,
        "equipment": p.equipment} for p in processes])
    workflow.record_step("baseline", plan.to_dict(), frame=frame,
                         rule_version="skills-lpt@1",
                         analysis_type="技能约束线平衡",
                         params={"skill_fingerprint": matrix.fingerprint()},
                         note="基线：现状技能矩阵")
    upgraded_levels = {"张三": 5, "李四": 4, "王五": 5, "赵六": 4}
    upgraded = SkillMatrix(entries=[
        {"operator": operator, "process_id": pid, "level": level}
        for operator, level in upgraded_levels.items()
        for pid in cycle_times],
        requirements=matrix.requirements)
    re_plan = LineBalanceEngine.schedule_with_skills(
        processes, takt, upgraded, equipment_parallel={"压机": 2})
    workflow.record_step("re_measure", re_plan.to_dict(), frame=frame,
                         rule_version="skills-lpt@1",
                         analysis_type="技能约束线平衡",
                         params={"skill_fingerprint": upgraded.fingerprint()},
                         note="复测：全员技能提升至 5 级")
    markdown_path = output_dir / "skill_balance_case.md"
    markdown_path.write_text(workflow.to_markdown(), encoding="utf-8")

    print("\n== 案例 ==")
    print(f"案例号: {workflow.case.id} · 步骤: "
          f"{[step['phase'] for step in workflow.case.steps]}")
    print(f"复测可行性: {'可行' if re_plan.feasible else '不可行'} · "
          f"账本事件: {len(ledger.events)} 条")
    print(f"案例摘要: {markdown_path}")
    ok = (not plan.feasible) and re_plan.feasible  # 演示契约：基线不可行 → 复测可行
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
