"""SMED 快速换模分析引擎 — 内外作业分离 + 改善对比"""

from dataclasses import dataclass, field
from typing import List

@dataclass
class SMEDTask:
    name: str = ""
    task_type: str = "internal"  # "internal" | "external"
    time_sec: float = 0.0
    improved_time: float = 0.0          # 改善后时间 (None=未设置, 0=作业消除)
    convert_to_external: bool = False   # 是否可转化为外部作业

    @property
    def is_internal(self) -> bool:
        return self.task_type == "internal"

    @property
    def is_external(self) -> bool:
        return self.task_type == "external"

    @property
    def improvement_pct(self) -> float:
        if self.time_sec > 0:
            # W82 fix: improved_time=0 表示作业消除(100%改善)
            # improved_time=None 表示未设置(返回0)
            if self.improved_time is None:
                return 0.0
            return round((self.time_sec - self.improved_time) / self.time_sec * 100, 1)
        return 0.0

@dataclass
class SMEDResult:
    tasks: List[SMEDTask] = field(default_factory=list)

    @property
    def total_internal_before(self) -> float:
        return sum(t.time_sec for t in self.tasks if t.is_internal)

    @property
    def total_external_before(self) -> float:
        return sum(t.time_sec for t in self.tasks if t.is_external)

    @property
    def total_internal_after(self) -> float:
        total = 0.0
        for t in self.tasks:
            if t.convert_to_external:
                continue
            if t.is_internal:
                total += max(t.improved_time, 0) if t.improved_time > 0 else t.time_sec
        return total

    @property
    def total_external_after(self) -> float:
        total = 0.0
        for t in self.tasks:
            if t.convert_to_external:
                total += max(t.improved_time, 0) if t.improved_time > 0 else t.time_sec
            elif t.is_external:
                total += max(t.improved_time, 0) if t.improved_time > 0 else t.time_sec
        return total

    @property
    def total_before(self) -> float:
        return self.total_internal_before + self.total_external_before

    @property
    def total_after(self) -> float:
        return self.total_internal_after + self.total_external_after

    @property
    def improvement_pct(self) -> float:
        if self.total_before > 0:
            return round((self.total_before - self.total_after) / self.total_before * 100, 1)
        return 0.0

    @property
    def internal_reduction_pct(self) -> float:
        if self.total_internal_before > 0:
            before = self.total_internal_before
            after = self.total_internal_after
            return round((before - after) / before * 100, 1)
        return 0.0

    def to_dict(self) -> dict:
        return {
            "tasks": [
                {"name": t.name, "task_type": t.task_type, "time_sec": t.time_sec,
                 "improved_time": t.improved_time, "convert_to_external": t.convert_to_external}
                for t in self.tasks
            ],
            "total_before": self.total_before,
            "total_after": self.total_after,
            "total_internal_before": self.total_internal_before,
            "total_internal_after": self.total_internal_after,
            "total_external_before": self.total_external_before,
            "total_external_after": self.total_external_after,
            "improvement_pct": self.improvement_pct,
            "internal_reduction_pct": self.internal_reduction_pct,
        }

class SMEDEngine:
    def __init__(self):
        self.tasks: List[SMEDTask] = []

    def add_task(self, name: str, task_type: str = "internal", time_sec: float = 0.0) -> SMEDTask:
        t = SMEDTask(name=name, task_type=task_type, time_sec=time_sec)
        self.tasks.append(t)
        return t

    def remove_task(self, index: int):
        if 0 <= index < len(self.tasks):
            self.tasks.pop(index)

    def analyze(self) -> SMEDResult:
        return SMEDResult(tasks=list(self.tasks))

    def to_dict(self) -> dict:
        return self.analyze().to_dict()
