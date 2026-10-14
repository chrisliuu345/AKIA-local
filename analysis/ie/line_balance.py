"""生产线平衡分析 — 平衡率、瓶颈识别、自动平衡建议（LPT + 前置约束）

现状评估：每工序一工位 → 平衡率 = ΣCT / (工位数 × 瓶颈CT)
自动平衡：给定目标节拍，最长作业时间优先（LPT）在前置约束下分配最少工位
"""

from typing import Any

from core.data_objects import Process
from core.skill_matrix import SchedulePlan


class LineBalanceEngine:
    """输入 Process 列表（cycle_time 必填），输出现状评估 + 平衡建议"""

    def analyze(self, processes: list[Process],
                takt: float | None = None) -> dict[str, Any]:
        out: dict[str, Any] = {
            "takt": None, "current": {}, "stations": [], "balanced": {},
            "warnings": [], "error": None,
        }

        valid = [p for p in processes if p.cycle_time and p.cycle_time > 0]
        skipped = len(processes) - len(valid)
        if skipped:
            out["warnings"].append(f"{skipped} 个工序 CT 缺失或为 0，已忽略")
        if len(valid) < 2:
            out["error"] = "有效工序不足（至少需要 2 个 CT>0 的工序）"
            return out

        total_ct = sum(p.cycle_time for p in valid)
        bottleneck = max(valid, key=lambda p: p.cycle_time)
        n = len(valid)

        current_rate = total_ct / (n * bottleneck.cycle_time)
        out["current"] = {
            "station_count": n,
            "total_ct": round(total_ct, 3),
            "max_ct": round(bottleneck.cycle_time, 3),
            "min_ct": round(min(p.cycle_time for p in valid), 3),
            "balance_rate": round(current_rate, 4),
            "balance_loss": round(1 - current_rate, 4),
            "bottleneck_id": bottleneck.process_id,
            "bottleneck_name": bottleneck.process_name,
        }

        takt_time = float(takt) if takt and takt > 0 else bottleneck.cycle_time
        out["takt"] = round(takt_time, 3)

        stations = self._balance_lpt(valid, takt_time)
        out["stations"] = stations

        station_count = len(stations)
        max_station_time = max(s["total_time"] for s in stations)
        new_rate = total_ct / (station_count * max_station_time)
        out["balanced"] = {
            "station_count": station_count,
            "max_station_time": round(max_station_time, 3),
            "balance_rate": round(new_rate, 4),
            "balance_loss": round(1 - new_rate, 4),
            "rate_improvement": round(new_rate - current_rate, 4),
            "stations_reduced": n - station_count,
            "over_takt_stations": sum(1 for s in stations if s["over_takt"]),
        }
        return out

    @staticmethod
    def _balance_lpt(processes: list[Process], takt: float) -> list[dict[str, Any]]:
        by_id = {p.process_id: p for p in processes}
        remaining = set(by_id.keys())
        assigned: set = set()
        stations: list[dict[str, Any]] = []

        max_iterations = len(processes) * 2
        iteration = 0

        def ready(cands_ids):
            result = []
            for pid in cands_ids:
                preds = [x for x in by_id[pid].predecessors if x in by_id]
                if all(x in assigned for x in preds):
                    result.append(by_id[pid])
            result.sort(key=lambda p: p.cycle_time, reverse=True)
            return result

        while remaining:
            iteration += 1
            if iteration > max_iterations:
                for pid in sorted(remaining):
                    p = by_id[pid]
                    stations.append({
                        "station_id": len(stations) + 1,
                        "process_ids": [p.process_id],
                        "process_names": [p.process_name],
                        "cts": [round(p.cycle_time, 3)],
                        "total_time": round(p.cycle_time, 3),
                        "idle": round(max(takt - p.cycle_time, 0.0), 3),
                        "utilization": round(min(p.cycle_time / takt, 1.0), 4) if takt > 0 else 0.0,
                        "over_takt": p.cycle_time > takt + 1e-9,
                    })
                break
            station_time = 0.0
            members: list[Process] = []

            while True:
                cands = [p for p in ready(remaining)
                         if station_time + p.cycle_time <= takt + 1e-9]
                if not cands:
                    break
                pick = cands[0]
                members.append(pick)
                station_time += pick.cycle_time
                remaining.discard(pick.process_id)
                assigned.add(pick.process_id)

            if not members:
                cands = ready(remaining) or [by_id[min(remaining)]]
                pick = cands[0]
                members.append(pick)
                station_time = pick.cycle_time
                remaining.discard(pick.process_id)
                assigned.add(pick.process_id)

            stations.append({
                "station_id": len(stations) + 1,
                "process_ids": [p.process_id for p in members],
                "process_names": [p.process_name for p in members],
                "cts": [round(p.cycle_time, 3) for p in members],
                "total_time": round(station_time, 3),
                "idle": round(max(takt - station_time, 0.0), 3),
                "utilization": round(min(station_time / takt, 1.0), 4) if takt > 0 else 0.0,
                "over_takt": station_time > takt + 1e-9,
            })

        return stations

    # ------------------------------------------------------------ 技能约束排班（v4.4.0 B5）
    @staticmethod
    def schedule_with_skills(processes: list[Process], takt: float | None,
                             skill_matrix, *, headcount: int | None = None,
                             equipment_parallel: dict[str, int] | None = None
                             ) -> SchedulePlan:
        """在 LPT 平衡结果上做技能约束工位指派（可执行排班，不破坏原 LPT）。

        判定规则（保守口径，已在 PLAN §3.5 冻结）：

        - 工位内每个工序：矩阵为该工序设置了最低等级 → 需 level ≥ 最低等级；
          未设置最低等级 → 需该操作员有任意录入（level ≥ 1）；未录入 = 不具备；
        - 一人一工位；``headcount`` 缺省取矩阵中的人员数；
        - ``equipment_parallel``：各设备类并发上限；并行产线下并发需求
          = 各工位对该设备使用次数之和，超限记 ``unmet``；
        - 不可行不静默降级：可行的工位照常指派，问题逐条进 ``unmet``。

        时间窗为单件作业窗口（并行工位）：``[0, 工位合计工时]``。
        ``plan_ref`` = 技能矩阵指纹（``skill-hash-v1``），供案例凭证引用。
        """
        base = LineBalanceEngine().analyze(processes, takt)
        if base.get("error"):
            raise ValueError(base["error"])
        stations = base["stations"]
        by_id = {p.process_id: p for p in processes if p.cycle_time and p.cycle_time > 0}
        unmet: list[str] = []
        operators = sorted({str(item.get("operator") or "")
                            for item in getattr(skill_matrix, "entries", []) or []
                            if str(item.get("operator") or "").strip()})
        available = operators[:int(headcount)] if headcount else list(operators)
        constraints: dict[str, Any] = {
            "takt_s": base["takt"],
            "headcount_required": len(stations),
            "headcount_available": (int(headcount) if headcount else len(operators)),
        }
        assignments: list[dict[str, Any]] = []
        if not operators:
            unmet.append("技能矩阵为空：请先录入人员技能后再排班")
        else:
            if headcount and int(headcount) < len(stations):
                unmet.append(
                    f"可用人数不足：需要 {len(stations)} 人（工位数），"
                    f"仅 {int(headcount)} 人")
            used: set[str] = set()
            for station in stations:
                process_ids = list(station["process_ids"])
                eligible: list[tuple[str, int, int]] = []
                for operator in available:
                    if operator in used:
                        continue
                    levels: list[int] = []
                    qualified = True
                    for pid in process_ids:
                        level = skill_matrix.level_of(operator, pid) or 0
                        need = skill_matrix.min_level_for(pid)
                        if level < (need if need is not None else 1):
                            qualified = False
                            break
                        levels.append(level)
                    if qualified:
                        eligible.append((operator, min(levels), sum(levels)))
                if not eligible:
                    remaining = [op for op in available if op not in used]
                    if not remaining:
                        unmet.append(
                            f"工位 {station['station_id']} 无剩余人员可派"
                            f"（已用 {len(used)} 人）")
                    else:
                        unmet.append(
                            f"工位 {station['station_id']} 无可派人员"
                            f"（工序 {'、'.join(process_ids)} 技能不满足）")
                    continue
                eligible.sort(key=lambda item: (-item[2], item[0]))
                operator = eligible[0][0]
                used.add(operator)
                end_s = float(round(station["total_time"], 3))
                for pid in process_ids:
                    assignments.append({
                        "process_id": pid, "operator": operator,
                        "start_s": 0.0, "end_s": end_s})
        equipment_usage: dict[str, int] = {}
        for station in stations:
            for pid in station["process_ids"]:
                equipment = str(getattr(by_id.get(pid), "equipment", "") or "").strip()
                if equipment:
                    equipment_usage[equipment] = equipment_usage.get(equipment, 0) + 1
        if equipment_parallel:
            for equipment, capacity in equipment_parallel.items():
                demand = equipment_usage.get(str(equipment), 0)
                if demand > int(capacity):
                    unmet.append(
                        f"设备「{equipment}」并发需求 {demand} 超出上限 {capacity}")
            constraints["equipment_parallel"] = {
                str(k): int(v) for k, v in equipment_parallel.items()}
        constraints["equipment_concurrent"] = equipment_usage
        balance_rate = base["balanced"]["balance_rate"]
        return SchedulePlan(
            assignments=assignments, constraints=constraints,
            balance_rate_before=balance_rate,
            balance_rate_after=(balance_rate if not unmet else None),
            unmet=unmet, plan_ref=skill_matrix.fingerprint())
