"""标准工时进入线平衡，基线与复测写入证据账本。不使用模型或网络。"""

from analysis.ie.chain import (
    IE_STANDARD_VERSION,
    apply_confirmed_standard_times,
    confirm_standard_times,
    record_balance,
    run_confirmed_balance,
)
from core.data_objects import Process, TimeObservation
from core.evidence_ledger import EvidenceLedger, verify_chain
from core.project_context import ProjectContext


def _obs(process: str, seconds: float, cycle: int) -> TimeObservation:
    return TimeObservation(process, "OP", cycle, seconds)


def _study(p2: float) -> list[TimeObservation]:
    rows = [_obs("P1", value, index) for index, value in enumerate((8, 10, 12, 10), start=1)]
    rows.extend(_obs("P2", p2, index) for index in range(1, 5))
    return rows


def test_confirmed_standard_time_becomes_line_balance_evidence():
    names = {"P1": "装配", "P2": "检验"}
    baseline = run_confirmed_balance(
        _study(20), rating=1.25, allowance_pct=20, names=names)
    retest = run_confirmed_balance(
        _study(16), rating=1.25, allowance_pct=20, names=names)

    assert [item.cycle_time for item in baseline["processes"]] == [15.0, 30.0]
    assert baseline["balance"]["current"]["balance_rate"] == 0.75
    assert [item.cycle_time for item in retest["processes"]] == [15.0, 24.0]
    assert retest["balance"]["current"]["balance_rate"] == 0.8125

    ledger = EvidenceLedger()
    record_balance(ledger, phase="baseline", case_id="CASE-1", result=baseline,
                   at="2026-11-15T09:00:00+08:00", event_id="EVT-baseline")
    record_balance(ledger, phase="re_measure", case_id="CASE-1", result=retest,
                   at="2026-11-15T10:00:00+08:00", event_id="EVT-retest")

    check = verify_chain(ledger.events)
    assert check["ok"] is True
    assert check["count"] == 2

    first, second = ledger.events
    assert first.payload["phase"] == "baseline"
    assert second.payload["phase"] == "re_measure"
    for event in ledger.events:
        assert event.payload["standard_version"] == IE_STANDARD_VERSION
        assert event.payload["inputs"][0]["rating"] == 1.25
        assert event.payload["inputs"][0]["allowance_pct"] == 20
        assert event.payload["inputs"][0]["observation_times"] == [8.0, 10.0, 12.0, 10.0]
        assert event.object_refs == ["case:CASE-1", f"phase:{event.payload['phase']}"]
    assert second.payload["balance_rate"] == 0.8125
    assert second.payload["inputs"][1]["standard_time"] == 24.0


def test_saved_standard_time_replaces_imported_cycle_time():
    context = ProjectContext()
    context.record_standard_time(
        "P1", standard_time_s=15.0, normal_time_s=12.5, allowance_pct=20,
        rating=1.25, cycles=4, operator="OP",
        observation_times=[8, 10, 12, 10], change_reason="确认标准工时")
    imported = [
        Process("P1", "装配", cycle_time=99),
        Process("P2", "检验", cycle_time=30),
    ]
    processes, applied = apply_confirmed_standard_times(imported, context.standards)
    assert imported[0].cycle_time == 99
    assert [item.cycle_time for item in processes] == [15.0, 30.0]
    assert applied[0]["standard_record_id"] == context.standards.current("P1").record_id
    assert applied[0]["observation_times"] == [8.0, 10.0, 12.0, 10.0]
    assert applied[0]["source"] == "confirmed_standard_time"


def test_evidence_observations_exclude_removed_outliers():
    """证据里的观测要能复算出标准工时：被剔除的异常值不能留在里面。"""
    rows = [_obs("P1", value, index)
            for index, value in enumerate((10, 10.2, 9.8, 10.1, 9.9, 10.0, 60.0), start=1)]
    record = confirm_standard_times(rows, rating=1.0, allowance_pct=0)[0]
    assert record["outliers_removed"] == 1
    assert 60.0 not in record["observation_times"]
    recomputed = sum(record["observation_times"]) / len(record["observation_times"])
    assert abs(recomputed - record["avg_time"]) < 1e-3
