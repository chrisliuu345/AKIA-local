"""OEE 设备综合效率分析 — 可用率 × 性能 × 良品率 + 损失分解

数据语义（Resource 行）：某资源 × 某班次 × 某日 的一条记录
    available_time / downtime 单位: 小时
    ideal_cycle_time 单位: 秒/件
    total_qty / good_qty 单位: 件

分项缺失时按 1.0 计并标注（P 缺理想节拍或产量、Q 缺产量或良品数）。
聚合采用加权和：A=Σop/Σavail，P=Σ(ideal×qty)/Σop，Q=Σgood/Σtotal。
"""

from typing import Any, Dict, List, Optional

from core.data_objects import Resource


class OEEEngine:
    WORLD_CLASS = 0.85

    def analyze(self, resources: List[Resource],
                group_by: str = "all") -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "overall": {}, "buckets": [], "warnings": [], "error": None,
        }

        valid = [r for r in resources if r.available_time and r.available_time > 0]
        skipped = len(resources) - len(valid)
        if skipped:
            out["warnings"].append(f"{skipped} 条记录可用时间缺失或为 0，已忽略")
        if not valid:
            out["error"] = "无有效记录（需要 available_time > 0 的资源数据）"
            return out

        if group_by == "group":
            buckets = self._bucketize(valid, key=lambda r: r.group or "(未分组)")
        elif group_by == "shift":
            buckets = self._bucketize(valid, key=lambda r: r.shift or "(未分班)")
        else:
            buckets = [("全部", valid)]

        bucket_results = [self._metrics(label, rows) for label, rows in buckets]
        out["buckets"] = bucket_results
        out["overall"] = self._metrics("全部", valid)
        return out

    @staticmethod
    def _bucketize(rows: List[Resource], key) -> List:
        buckets: Dict[str, List[Resource]] = {}
        for r in rows:
            buckets.setdefault(key(r), []).append(r)
        return sorted(buckets.items(), key=lambda kv: kv[0])

    def _metrics(self, label: str, rows: List[Resource]) -> Dict[str, Any]:
        sum_avail = sum(r.available_time for r in rows)
        sum_down = sum(max(r.downtime, 0.0) for r in rows)
        sum_op = max(sum_avail - sum_down, 0.0)

        if sum_avail <= 0:
            return {
                "label": label, "rows": len(rows),
                "available_h": 0.0, "downtime_h": round(sum_down, 2),
                "operating_h": 0.0,
                "availability": 0.0, "performance": None, "quality": None,
                "oee": 0.0, "grade": "无效",
                "losses": {"停机损失(h)": 0.0, "速度/小停损失(h)": 0.0,
                           "质量损失(h)": 0.0, "有效产出时间(h)": 0.0},
                "has_performance": False, "has_quality": False,
                "notes": [f"'{label}' 分组可用时间为 0，已跳过计算"],
            }

        notes: List[str] = []
        a = sum_op / sum_avail

        perf_rows = [r for r in rows
                     if r.ideal_cycle_time > 0 and r.total_qty > 0]
        p: Optional[float] = None
        perf_time_h = 0.0
        if perf_rows:
            perf_sec = sum(r.ideal_cycle_time * r.total_qty for r in perf_rows)
            op_rows = sum(max(r.available_time - max(r.downtime, 0.0), 0.0)
                          for r in perf_rows)
            perf_time_h = perf_sec / 3600.0
            p = perf_time_h / op_rows if op_rows > 0 else None
            if p is not None and p > 1.0:
                notes.append(f"性能 {p:.1%} > 100%：理想节拍可能偏保守或计时口径不一致")
        else:
            notes.append("缺少理想节拍/产量，性能按 100% 计")

        q_rows = [r for r in rows if r.total_qty > 0]
        q: Optional[float] = None
        if q_rows and all(r.good_qty >= 0 for r in q_rows):
            total = sum(r.total_qty for r in q_rows)
            good = sum(min(r.good_qty, r.total_qty) for r in q_rows)
            q = good / total if total > 0 else None
            if any(r.good_qty == 0 and r.total_qty > 0 for r in q_rows):
                notes.append("存在良品数为 0 的记录，请确认是数据缺失还是全数不良")
        else:
            notes.append("缺少产量/良品数，良品率按 100% 计")

        p_eff = p if p is not None else 1.0
        q_eff = q if q is not None else 1.0
        oee = a * p_eff * q_eff

        speed_loss_h = max(sum_op - perf_time_h, 0.0) if perf_rows else 0.0
        quality_loss_h = 0.0
        if perf_rows and q is not None:
            scrap_sec = sum(r.ideal_cycle_time * max(r.total_qty - r.good_qty, 0.0)
                            for r in perf_rows)
            quality_loss_h = scrap_sec / 3600.0
        value_time_h = max(perf_time_h - quality_loss_h, 0.0) if perf_rows else 0.0

        return {
            "label": label,
            "rows": len(rows),
            "available_h": round(sum_avail, 2),
            "downtime_h": round(sum_down, 2),
            "operating_h": round(sum_op, 2),
            "availability": round(a, 4),
            "performance": round(p, 4) if p is not None else None,
            "quality": round(q, 4) if q is not None else None,
            "oee": round(oee, 4),
            "grade": self._grade(oee),
            "losses": {
                "停机损失(h)": round(sum_down, 2),
                "速度/小停损失(h)": round(speed_loss_h, 2),
                "质量损失(h)": round(quality_loss_h, 2),
                "有效产出时间(h)": round(value_time_h, 2),
            },
            "has_performance": bool(perf_rows),
            "has_quality": bool(q_rows),
            "notes": notes,
        }

    @staticmethod
    def _grade(oee: float) -> str:
        from config.settings import OEE_WORLD_CLASS, OEE_GOOD, OEE_FAIR
        if oee >= OEE_WORLD_CLASS:
            return "世界级"
        if oee >= OEE_GOOD:
            return "良好"
        if oee >= OEE_FAIR:
            return "一般"
        return "落后"
