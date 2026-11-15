"""v4.7.0 契约：确认后的标准工时进入线平衡，并写入证据账本。

本模块冻结可复现路径，不新增 IE 方法，也不改界面。公式版本 ``IE-TIME-1``：

- 正常时间 = 观测时间均值 × 评比系数
- 标准工时 = 正常时间 × (1 + 宽放% / 100)
- 线平衡率 = Σ标准工时 / (工位数 × 瓶颈标准工时)

每道工序只接受一条已确认标准工时。基线与复测都记为 ``analysis_run``，
payload 保留观测值、评比、宽放、标准版本和平衡结果，便于事后还原。
"""

from __future__ import annotations

from typing import Any

from analysis.ie.line_balance import LineBalanceEngine
from analysis.ie.time_study import TimeStudyEngine
from core.data_objects import Process, TimeObservation
from core.evidence_ledger import EvidenceLedger

IE_STANDARD_VERSION = "IE-TIME-1"
IE_FORMULA = (
    "正常时间 = 观测时间均值 × 评比系数；"
    "标准工时 = 正常时间 × (1 + 宽放%/100)；"
    "线平衡率 = Σ标准工时 / (工位数 × 瓶颈标准工时)"
)
BALANCE_PHASES = ("baseline", "re_measure")


def _observed_time(item: TimeObservation) -> float:
    if item.observation_time and item.observation_time > 0:
        return float(item.observation_time)
    return float(item.cycle)


def confirm_standard_times(observations: list[TimeObservation], *,
                           rating: float = 1.0,
                           allowance_pct: float = 12.0) -> list[dict[str, Any]]:
    """按工序和作业员确认标准工时，并保留可还原的输入。"""
    result = TimeStudyEngine.analyze(
        observations, rating=rating, allowance_pct=allowance_pct)
    if not result.get("valid"):
        raise ValueError(result.get("error") or "工时研究无效")

    observed: dict[tuple[str, str], list[float]] = {}
    for item in observations:
        key = (str(item.process_id), str(item.operator))
        observed.setdefault(key, []).append(_observed_time(item))

    records: list[dict[str, Any]] = []
    for row in result["results"]:
        key = (str(row["process_id"]), str(row["operator"]))
        records.append({
            "process_id": key[0],
            "operator": key[1],
            "observation_times": list(observed.get(key, [])),
            "rating": float(row["rating"]),
            "allowance_pct": float(row["allowance_pct"]),
            "avg_time": float(row["avg_time"]),
            "normal_time": float(row["normal_time"]),
            "standard_time": float(row["standard_time"]),
            "outliers_removed": int(row["outliers_removed"]),
            "standard_version": IE_STANDARD_VERSION,
            "formula": IE_FORMULA,
        })
    return records


def processes_from_confirmed(records: list[dict[str, Any]], *,
                             names: dict[str, str] | None = None,
                             predecessors: dict[str, list[str]] | None = None
                             ) -> list[Process]:
    """把已确认标准工时写成线平衡工序。同一工序只允许一条记录。"""
    labels = names or {}
    upstream = predecessors or {}
    seen: set[str] = set()
    processes: list[Process] = []
    for record in records:
        process_id = str(record["process_id"])
        if process_id in seen:
            raise ValueError(
                f"工序 {process_id} 有多条确认工时，线平衡只接受每工序一条标准工时")
        seen.add(process_id)
        processes.append(Process(
            process_id=process_id,
            process_name=str(labels.get(process_id, process_id)),
            cycle_time=float(record["standard_time"]),
            predecessors=list(upstream.get(process_id, [])),
        ))
    return processes


def run_confirmed_balance(observations: list[TimeObservation], *,
                          rating: float = 1.0,
                          allowance_pct: float = 12.0,
                          names: dict[str, str] | None = None,
                          predecessors: dict[str, list[str]] | None = None,
                          takt: float | None = None) -> dict[str, Any]:
    """确认标准工时并立刻做线平衡。不访问模型或网络。"""
    records = confirm_standard_times(
        observations, rating=rating, allowance_pct=allowance_pct)
    processes = processes_from_confirmed(
        records, names=names, predecessors=predecessors)
    balance = LineBalanceEngine().analyze(processes, takt)
    if balance.get("error"):
        raise ValueError(balance["error"])
    return {
        "records": records,
        "processes": processes,
        "balance": balance,
        "standard_version": IE_STANDARD_VERSION,
        "formula": IE_FORMULA,
    }


def record_balance(ledger: EvidenceLedger, *, phase: str, case_id: str,
                   result: dict[str, Any], actor: str = "user",
                   at: str = "", event_id: str = ""):
    """把一次线平衡写成证据。``phase`` 只能是基线或复测。"""
    if phase not in BALANCE_PHASES:
        raise ValueError(f"阶段必须是 {BALANCE_PHASES} 之一，收到 {phase!r}")
    balance = result["balance"]
    current = balance["current"]
    payload = {
        "analysis_type": "LineBalance",
        "phase": phase,
        "case_id": str(case_id),
        "standard_version": result["standard_version"],
        "formula": result["formula"],
        "inputs": list(result["records"]),
        "takt": balance.get("takt"),
        "balance_rate": current["balance_rate"],
        "balance_loss": current["balance_loss"],
        "bottleneck_id": current["bottleneck_id"],
        "station_count": current["station_count"],
    }
    return ledger.append(
        "analysis_run",
        actor=actor,
        at=at,
        event_id=event_id,
        object_refs=[f"case:{case_id}", f"phase:{phase}"],
        payload=payload,
    )
