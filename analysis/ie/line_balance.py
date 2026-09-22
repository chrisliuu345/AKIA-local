"""生产线平衡分析 — 平衡率、瓶颈识别、自动平衡建议（LPT + 前置约束）

现状评估：每工序一工位 → 平衡率 = ΣCT / (工位数 × 瓶颈CT)
自动平衡：给定目标节拍，最长作业时间优先（LPT）在前置约束下分配最少工位
"""

from typing import Any

from core.data_objects import Process


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
