"""TPM 全面生产维护引擎 — MTBF/MTTR + 六大损失 + 维护计划"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class TPMRecord:
    """单条设备运行记录"""
    date: str = ""
    operating_time: float = 0.0
    planned_downtime: float = 0.0
    breakdown_time: float = 0.0
    setup_time: float = 0.0
    idle_time: float = 0.0
    reduced_speed_loss: float = 0.0
    defect_loss: float = 0.0
    startup_loss: float = 0.0
    total_output: int = 0
    good_output: int = 0
    breakdown_count: int = 0

    @property
    def planned_production_time(self) -> float:
        return self.operating_time - self.planned_downtime

    @property
    def actual_runtime(self) -> float:
        return self.planned_production_time - self.breakdown_time

    @property
    def availability(self) -> float:
        v = self.actual_runtime / max(self.planned_production_time, 0.001)
        return max(0.0, min(1.0, v))

    @property
    def performance(self) -> float:
        """性能稼动率 (简化: 有效产出时间/实际运行时间)"""
        loss = self.setup_time + self.idle_time + self.reduced_speed_loss
        effective = max(0.0, self.actual_runtime - loss)
        return effective / max(self.actual_runtime, 0.001)

    @property
    def quality_rate(self) -> float:
        return self.good_output / max(self.total_output, 1)

    @property
    def oee(self) -> float:
        return self.availability * self.performance * self.quality_rate


@dataclass
class TPMResult:
    records: List[TPMRecord] = field(default_factory=list)

    @property
    def avg_mtbf(self) -> float:
        total_runtime = sum(r.actual_runtime for r in self.records)
        total_breakdowns = sum(r.breakdown_count for r in self.records)
        return total_runtime / max(total_breakdowns, 1)

    @property
    def avg_mttr(self) -> float:
        total_breakdown_time = sum(r.breakdown_time for r in self.records)
        total_breakdowns = sum(r.breakdown_count for r in self.records)
        return total_breakdown_time / max(total_breakdowns, 1)

    @property
    def avg_oee(self) -> float:
        if not self.records:
            return 0.0
        return sum(r.oee for r in self.records) / len(self.records)

    @property
    def record_count(self) -> int:
        return len(self.records)

    @property
    def six_losses(self) -> dict:
        """六大损失合计"""
        return {
            "故障停机": sum(r.breakdown_time for r in self.records),
            "换模调整": sum(r.setup_time for r in self.records),
            "空转小停机": sum(r.idle_time for r in self.records),
            "速度降低": sum(r.reduced_speed_loss for r in self.records),
            "不良返工": sum(r.defect_loss for r in self.records),
            "启动损失": sum(r.startup_loss for r in self.records),
        }

    def to_dict(self) -> dict:
        return {
            "avg_mtbf": self.avg_mtbf,
            "avg_mttr": self.avg_mttr,
            "avg_oee": self.avg_oee,
            "six_losses": self.six_losses,
            "record_count": len(self.records),
        }


class TPMEngine:
    def __init__(self):
        self.records: List[TPMRecord] = []
        self.maintenance_plan: List[dict] = []

    def add_record(self, **kwargs) -> TPMRecord:
        r = TPMRecord(**kwargs)
        self.records.append(r)
        return r

    def add_maintenance(self, task: str, due_date: str, interval_days: int = 30):
        self.maintenance_plan.append({"task": task, "due_date": due_date, "interval_days": interval_days, "completed": False})

    def analyze(self) -> TPMResult:
        return TPMResult(records=list(self.records))
