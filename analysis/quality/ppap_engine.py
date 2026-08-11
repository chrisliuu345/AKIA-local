"""PPAP 生产件批准引擎 — 18项提交清单 + 提交等级 + 状态追踪"""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

# 18项提交要求 (AIAG PPAP 第4版)
PPAP_ITEMS = [
    (1, "设计记录", "design_records"),
    (2, "工程变更文件", "engineering_changes"),
    (3, "顾客工程批准", "customer_approval"),
    (4, "DFMEA", "dfmea"),
    (5, "过程流程图", "process_flow"),
    (6, "PFMEA", "pfmea"),
    (7, "控制计划", "control_plan"),
    (8, "MSA", "msa"),
    (9, "尺寸结果", "dimensional_results"),
    (10, "材料/性能结果", "material_test"),
    (11, "初始过程能力", "initial_capability"),
    (12, "合格实验室文件", "lab_documents"),
    (13, "外观批准报告", "appearance_approval"),
    (14, "散装材料检查表", "bulk_material"),
    (15, "样品产品", "sample_product"),
    (16, "标准样品", "master_sample"),
    (17, "检查辅具", "checking_aids"),
    (18, "PSW 零件提交保证书", "psw"),
]

SUBMISSION_LEVELS = {
    1: "仅 PSW",
    2: "PSW + 样品 + 有限支持数据",
    3: "PSW + 样品 + 完整支持数据",
    4: "PSW + 顾客定义的其他要求",
    5: "PSW + 样品 + 全套数据在现场审核",
}

SUBMISSION_ITEMS = {
    1: [18],                              # 仅PSW
    2: [18, 15],                           # PSW+样品
    3: [1,2,4,5,6,7,8,9,10,11,15,18],     # 完整
    4: [18],                               # 自定义
    5: list(range(1, 19)),                 # 全部
}


@dataclass
class PPAPItem:
    number: int
    name: str
    key: str
    status: str = "pending"     # pending | in_progress | complete | n_a
    notes: str = ""

    STATUS_COLORS = {"pending": "#888", "in_progress": "#f1c40f", "complete": "#2ecc71", "n_a": "#555"}


@dataclass
class DimensionRecord:
    characteristic: str = ""
    spec_nominal: float = 0.0
    usl: float = 0.0
    lsl: float = 0.0
    measurements: List[float] = field(default_factory=list)
    cp: Optional[float] = None
    cpk: Optional[float] = None


@dataclass
class PPAPReport:
    part_number: str = ""
    part_name: str = ""
    supplier: str = ""
    submission_level: int = 3
    items: List[PPAPItem] = field(default_factory=list)
    dimensions: List[DimensionRecord] = field(default_factory=list)
    psw_notes: str = ""
    created_at: str = ""

    def __post_init__(self):
        if not self.items:
            self.items = [PPAPItem(n, name, key) for n, name, key in PPAP_ITEMS]
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d")

    @property
    def completion_pct(self) -> float:
        required = SUBMISSION_ITEMS.get(self.submission_level, [18])
        done = sum(1 for i in self.items if i.number in required and i.status in ("complete", "n_a"))
        return round(done / max(len(required), 1) * 100, 1)

    def required_items(self) -> List[int]:
        return SUBMISSION_ITEMS.get(self.submission_level, [18])

    def to_dict(self) -> dict:
        return {
            "part_number": self.part_number, "part_name": self.part_name,
            "submission_level": self.submission_level, "completion_pct": self.completion_pct,
            "items": [{"number": i.number, "name": i.name, "status": i.status} for i in self.items],
            "dimensions": [{"characteristic": d.characteristic, "cp": d.cp, "cpk": d.cpk} for d in self.dimensions],
        }
