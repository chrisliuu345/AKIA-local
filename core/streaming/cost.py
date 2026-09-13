"""成本损失估算（v3.8.0-④）— 超规格量 × 单件损失 + 停机成本。

对标 WinSPC Cost Inspector / 净含量控制思路: 用 plant.json 的单位成本、
废品成本、停机成本参数，把实时超规格数量与停机时长折算为货币损失。

纯计算模块（无 Qt / 无 IO），输入为 Sample 列表或实时 OEE 快照。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class CostEstimate:
    line: str
    samples: int = 0
    defects: int = 0
    defect_rate: float = 0.0
    scrap_loss: float = 0.0
    downtime_min: float = 0.0
    downtime_loss: float = 0.0
    total_loss: float = 0.0
    currency: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


class CostAnalyzer:
    """产线成本损失估算 — 单件损失与停机费率来自 Line 配置。"""

    def __init__(self, plant, currency: str = "", downtime=None):
        self.plant = plant
        self.currency = currency
        self.downtime = downtime      # DowntimeTracker | None（v3.8.0-⑤ 接线）

    # ---------- 缺陷计数 ----------
    @staticmethod
    def count_defects(samples, usl: float | None, lsl: float | None) -> int:
        """超规格样本数（每样本视为一件）— 无规格限则计 0。"""
        if usl is None and lsl is None:
            return 0
        n = 0
        for s in samples:
            value = float(getattr(s, "value", s))
            if ((usl is not None and value > float(usl))
                    or (lsl is not None and value < float(lsl))):
                n += 1
        return n

    # ---------- 估算 ----------
    def estimate_line(self, line, samples_by_device: dict) -> CostEstimate:
        est = CostEstimate(line=line.name, currency=self.currency)
        total = 0
        for st in line.stations:
            samples = samples_by_device.get(st.device, [])
            if not samples:
                continue
            total += len(samples)
            est.defects += self.count_defects(samples, st.usl, st.lsl)
        est.samples = total
        if total:
            est.defect_rate = round(est.defects / total, 4)
        est.scrap_loss = round(est.defects * line.loss_per_unit(), 2)
        if self.downtime is not None:
            est.downtime_min = round(
                self.downtime.downtime_seconds(line.name) / 60.0, 2)
        est.downtime_loss = round(est.downtime_min * float(line.downtime_cost_per_min), 2)
        est.total_loss = round(est.scrap_loss + est.downtime_loss, 2)
        return est

    def estimate(self, samples_by_device: dict | None = None,
                 oee_snapshot: dict | None = None) -> dict[str, dict]:
        """产线 → 损失明细。优先使用 OEE 快照（含真实缺陷/停机统计）。"""
        samples_by_device = samples_by_device or {}
        out: dict[str, dict] = {}
        for line in self.plant.lines:
            est = self.estimate_line(line, samples_by_device)
            snap = (oee_snapshot or {}).get(line.name)
            if snap:
                if snap.get("samples"):
                    est.samples = int(snap["samples"])
                if snap.get("defects") is not None:
                    est.defects = int(snap["defects"])
                if est.samples:
                    est.defect_rate = round(est.defects / est.samples, 4)
                est.scrap_loss = round(est.defects * line.loss_per_unit(), 2)
                if snap.get("downtime_s") is not None and self.downtime is not None:
                    est.downtime_min = round(float(snap["downtime_s"]) / 60.0, 2)
                    est.downtime_loss = round(
                        est.downtime_min * float(line.downtime_cost_per_min), 2)
                est.total_loss = round(est.scrap_loss + est.downtime_loss, 2)
            out[line.name] = est.as_dict()
        return out
