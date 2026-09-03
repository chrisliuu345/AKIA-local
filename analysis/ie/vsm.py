"""价值流分析 (VSM) — VA/NVA 统计、Lead Time、增值比

数据语义：
    Process.cycle_time  单位: 秒/件（增值时间）
    MaterialFlow.quantity  单位: 件（工序间在制品库存）
    daily_demand  单位: 件/天（由用户输入，用于库存→时间换算）

Lead Time(天) = Σ库存天数 + ΣCT/每班秒数
增值比 = ΣCT / (Lead Time × 每班秒数)
"""

from typing import Any, Dict, List, Optional

from core.data_objects import MaterialFlow, Process


class VSMEngine:
    WORKDAY_SECONDS = 28800.0

    def analyze(self, processes: List[Process],
                flows: List[MaterialFlow],
                daily_demand: float,
                workday_seconds: Optional[float] = None) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "steps": [], "summary": {}, "warnings": [], "error": None,
        }

        wds = float(workday_seconds) if workday_seconds else self.WORKDAY_SECONDS
        if not daily_demand or daily_demand <= 0:
            out["error"] = "请填写有效的日需求量（件/天）"
            return out

        valid = [p for p in processes if p.cycle_time and p.cycle_time > 0]
        skipped = len(processes) - len(valid)
        if skipped:
            out["warnings"].append(f"{skipped} 个工序 CT 缺失或为 0，已忽略")
        if not valid:
            out["error"] = "无有效工序（需要 CT>0 的工序表数据）"
            return out

        ordered, order_note = self._order_processes(valid, flows)
        if order_note:
            out["warnings"].append(order_note)

        inv_map: Dict[str, float] = {}
        for f in flows:
            if f.quantity and f.quantity > 0:
                key = f"{f.from_process}|{f.to_process}"
                inv_map[key] = inv_map.get(key, 0.0) + f.quantity

        steps: List[Dict[str, Any]] = []
        total_va = 0.0
        total_inv_qty = 0.0
        for i, p in enumerate(ordered):
            total_va += p.cycle_time
            step = {
                "process_id": p.process_id,
                "process_name": p.process_name,
                "equipment": p.equipment,
                "ct": round(p.cycle_time, 3),
                "labor": p.labor_count,
                "inv_qty": 0.0,
                "inv_days": 0.0,
            }
            if i < len(ordered) - 1:
                nxt = ordered[i + 1]
                qty = self._find_inventory(inv_map, p, nxt, flows)
                step["inv_qty"] = round(qty, 1)
                step["inv_days"] = round(qty / daily_demand, 4)
                total_inv_qty += qty
            steps.append(step)

        inv_days_total = total_inv_qty / daily_demand
        processing_days = total_va / wds
        lead_time_days = inv_days_total + processing_days
        lead_time_sec = lead_time_days * wds
        va_ratio = total_va / lead_time_sec if lead_time_sec > 0 else 0.0
        takt = wds / daily_demand

        out["steps"] = steps
        out["summary"] = {
            "process_count": len(ordered),
            "total_va_sec": round(total_va, 2),
            "processing_days": round(processing_days, 4),
            "total_inventory_qty": round(total_inv_qty, 1),
            "inventory_days": round(inv_days_total, 3),
            "lead_time_days": round(lead_time_days, 3),
            "va_ratio": round(va_ratio, 5),
            "takt_sec": round(takt, 2),
            "daily_demand": daily_demand,
            "over_takt": [s["process_name"] for s in steps if s["ct"] > takt],
        }
        if out["summary"]["over_takt"]:
            out["warnings"].append(
                f"工序 {', '.join(out['summary']['over_takt'])} CT 超过节拍 ({takt:.1f}s)，将成为瓶颈")
        return out

    @staticmethod
    def _order_processes(processes: List[Process],
                         flows: List[MaterialFlow]):
        by_id = {p.process_id: p for p in processes}
        name_map = {p.process_name: p.process_id for p in processes}

        links: Dict[str, str] = {}
        targets: set = set()
        for f in flows:
            src = f.from_process if f.from_process in by_id else name_map.get(f.from_process)
            dst = f.to_process if f.to_process in by_id else name_map.get(f.to_process)
            if src and dst and src in by_id and dst in by_id:
                links[src] = dst
                targets.add(dst)

        if not links:
            return processes, "未检测到有效物流关系，按工序表顺序展示"

        starts = [pid for pid in by_id if pid not in targets]
        starts.sort(key=lambda pid: 0 if pid in links else 1)
        ordered_ids: List[str] = []
        visited: set = set()
        for s in starts:
            cur: Optional[str] = s
            while cur and cur not in visited and cur in by_id:
                ordered_ids.append(cur)
                visited.add(cur)
                cur = links.get(cur)

        leftover = [pid for pid in by_id if pid not in visited]
        note = ""
        if leftover:
            ordered_ids.extend(leftover)
            note = f"{len(leftover)} 个工序不在物流链中，已追加到末尾"
        return [by_id[pid] for pid in ordered_ids], note

    @staticmethod
    def _find_inventory(inv_map: Dict[str, float], cur: Process,
                        nxt: Process, flows: List[MaterialFlow]) -> float:
        keys = (
            f"{cur.process_id}|{nxt.process_id}",
            f"{cur.process_name}|{nxt.process_name}",
            f"{cur.process_id}|{nxt.process_name}",
            f"{cur.process_name}|{nxt.process_id}",
        )
        for k in keys:
            if k in inv_map:
                return inv_map[k]
        return 0.0
