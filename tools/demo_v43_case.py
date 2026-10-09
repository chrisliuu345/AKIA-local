#!/usr/bin/env python3
"""v4.3.0 端到端演示：测量 → 分析 → 改善 → 标准 → 复测 → 判定 → 证据 → 脱敏分享。

用法::

    python tools/demo_v43_case.py --output TEMP/demo_v43

输出：evidence.zip（可独立校验的证据包）· share.zip（脱敏分享包）·
report.html（带追溯码）· summary.json（全流程摘要）。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def run_demo(output_dir: str) -> dict:
    """执行完整 v4.3.0 闭环并返回摘要（供测试与命令行复用）。"""
    from analysis.capability import normal_cap
    from core.case_workflow import CaseWorkflow
    from core.evidence import credential_trace_code, make_credential
    from core.evidence_ledger import EvidenceLedger
    from core.evidence_pack import export_evidence_pack
    from core.measurement_event import MeasurementEvent
    from core.measurement_store import MeasurementStore
    from core.project_context import ProjectContext
    from core.share_pack import build_share_pack
    from core.standard_record import resolve_standard_context
    from output.html_export import export_html

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(20261008)
    before = pd.DataFrame({"cycle": rng.normal(32.0, 0.6, 30)})
    after = pd.DataFrame({"cycle": rng.normal(28.0, 0.5, 30)})
    raw_data = {"改善前": before, "改善后": after}

    ledger = EvidenceLedger()
    context = ProjectContext(project_name="E2E 节拍改善")
    context.event_sink = lambda event_type, refs, payload: ledger.append(
        event_type, object_refs=refs, payload=payload)
    store = MeasurementStore()
    store.event_sink = lambda event: ledger.append(
        "measurement_recorded",
        object_refs=[event.event_id, event.characteristic_id or event.channel],
        payload={"n": event.summary.get("n", 0),
                 "fingerprint": event.fingerprint, "raw_ref": event.raw_ref})

    ledger.append("data_imported", object_refs=["demo_line.xlsx"],
                  payload={"sheets": 2, "rows": 60})
    standard_v1 = context.record_specification(
        "cycle", usl=33.0, lsl=31.0, target=32.0, change_reason="初始规范")
    baseline_event = MeasurementEvent.from_dataframe(
        before, source_kind="file", source_id="demo_line.xlsx", channel="cycle")
    store.add(baseline_event)

    baseline_result = normal_cap.analyze(before["cycle"], 33.0, 31.0, 32.0)
    standard_ctx = resolve_standard_context(context.standards, ["cycle"])
    baseline_credential = make_credential(
        "capability@1", {**standard_ctx, "usl": 33.0, "lsl": 31.0,
                         "phase": "baseline"}, df=before).to_dict()
    baseline_analysis = {
        "analysis_type": "正态过程能力",
        "params": {"column": "cycle", "usl": 33.0, "lsl": 31.0},
        "result": baseline_result, "credential": baseline_credential}
    ledger.append("analysis_run",
                  object_refs=["tab:2", baseline_credential["data_fingerprint"]],
                  payload={"analysis_type": "正态过程能力",
                           "standard_ref": baseline_credential["params"]["standard_ref"]})

    workflow = CaseWorkflow(title="节拍改善 E2E", product="L1",
                            owner="demo", ledger=ledger)
    workflow.record_step("baseline", baseline_result, data_ref="sheet:改善前",
                         frame=before, note="改善前 30 个周期",
                         measurement_refs=[baseline_event.event_id])
    study = pd.DataFrame({"element": ["取件", "装配", "检验"],
                          "observed_s": [8.0, 15.0, 6.0]})
    workflow.record_step("time_study",
                         {"params": {"elements": 3}, "standard_time": 31.0},
                         data_ref="sheet:工时研究", frame=study,
                         note="作业要素测时")
    balance = pd.DataFrame({"station": ["S1", "S2", "S3"],
                            "cycle_time": [36.0, 28.0, 30.0]})
    workflow.record_step("line_balance",
                         {"params": {"stations": 3}, "line_balance_rate": 86.7},
                         data_ref="sheet:线平衡", frame=balance,
                         note="瓶颈工位 S1")
    workflow.record_step("improvement", {"action": "工装与动作拆分"},
                         note="拆分取件动作，减少等待")

    standard_v2 = context.record_specification(
        "cycle", usl=30.0, lsl=26.0, target=28.0,
        change_reason="改善后收紧至 28±2s")
    after_event = MeasurementEvent.from_dataframe(
        after, source_kind="file", source_id="demo_line.xlsx", channel="cycle")
    store.add(after_event)
    after_result = normal_cap.analyze(after["cycle"], 30.0, 26.0, 28.0)
    workflow.record_step("remeasure", after_result, data_ref="sheet:改善后",
                         frame=after, note="改善后 30 个周期",
                         measurement_refs=[after_event.event_id])
    workflow.run_paired_test(before["cycle"], after["cycle"],
                             data_ref="sheet:改善前/改善后")
    workflow.conclude("节拍由约 32s 降至约 28s，配对检验显著，改善有效",
                      data_ref="case:conclusion")
    workflow.standard_draft("更新作业标准：节拍 28s，规格 28±2s",
                            data_ref="standard:draft")
    workflow.close_case("统计显著且标准已更新")

    trace = credential_trace_code([baseline_credential])
    report_path = out / "report.html"
    export_html([baseline_analysis], output_path=str(report_path))
    ledger.append("report_exported", object_refs=["report.html", f"trace:{trace}"],
                  payload={"format": "html", "trace": trace})

    pack = export_evidence_pack(
        str(out / "evidence.zip"), case=workflow.to_dict(),
        case_markdown=workflow.to_markdown(), analyses={2: baseline_analysis},
        ledger=ledger, standards=context.standards.to_dict(), measurements=store)
    share = build_share_pack(
        str(out / "share.zip"), raw_data=raw_data, case=workflow.to_dict(),
        ledger=ledger, forbidden=["demo_line.xlsx", "demo"])
    ledger.append("share_pack_exported",
                  object_refs=[f"case:{workflow.case.id}"],
                  payload={"scan_ok": bool(share["scan"]["ok"])})

    summary = {
        "case_id": workflow.case.id,
        "case_status": workflow.case.status,
        "missing_phases": workflow.missing_phases(),
        "steps_total": len(workflow.case.steps),
        "steps_with_credential": sum(
            1 for step in workflow.case.steps if step.get("credential")),
        "case_measurement_refs": list(workflow.case.measurement_refs),
        "measurement_events": [baseline_event.event_id, after_event.event_id],
        "standard_versions": [standard_v1.record_id, standard_v2.record_id],
        "standard_as_of_v1_usl": context.standard_as_of(
            "cycle", standard_v1.valid_from).payload["usl"],
        "trace_code": trace,
        "ledger": ledger.export_manifest(),
        "evidence_pack_ok": bool(pack["verify"]["ok"]),
        "share_pack_scan_ok": bool(share["scan"]["ok"]),
        "evidence_pack": str(out / "evidence.zip"),
        "share_pack": str(out / "share.zip"),
        "report": str(report_path),
    }
    (out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="AKIA v4.3.0 端到端演示")
    parser.add_argument("--output", default="TEMP/demo_v43",
                        help="输出目录（默认 TEMP/demo_v43）")
    args = parser.parse_args()
    summary = run_demo(args.output)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
