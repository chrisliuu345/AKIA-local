"""项目上下文 — 跨 Tab 共享数据模型

提供 QualityCharacteristic（质量特性）和 ProjectContext（项目级上下文），
支持五链贯通：FMEA → CP → SPC → PPAP → 8D。
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
from config.settings import RPN_HIGH


@dataclass
class QualityCharacteristic:
    """质量特性 — 五链贯通的核心数据单元"""
    id: str = ""                     # 唯一标识 (如 "QC-001")
    name: str = ""                   # 特性名称 (如 "轴径 φ10±0.02")
    process: str = ""                # 工序名称
    usl: Optional[float] = None      # 上规格限
    lsl: Optional[float] = None      # 下规格限
    target: Optional[float] = None   # 目标值
    unit: str = ""                   # 单位
    data_source: str = ""            # 数据源 (sheet_name:column)
    spc_method: str = ""             # 推荐 SPC 方法 (XBar-R, I-MR, etc.)
    notes: str = ""                  # 备注

    # 关联 ID (用于五链追踪)
    fmea_item_id: str = ""           # 关联 FMEA 条目
    cp_row_id: str = ""              # 关联控制计划行
    ppap_item_id: str = ""           # 关联 PPAP 条目
    eight_d_id: str = ""             # 关联 8D 报告

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "process": self.process,
            "usl": self.usl, "lsl": self.lsl, "target": self.target,
            "unit": self.unit, "data_source": self.data_source,
            "spc_method": self.spc_method, "notes": self.notes,
            "fmea_item_id": self.fmea_item_id, "cp_row_id": self.cp_row_id,
            "ppap_item_id": self.ppap_item_id, "eight_d_id": self.eight_d_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "QualityCharacteristic":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ProjectContext:
    """项目级上下文 — 跨 Tab 共享的数据容器"""
    project_name: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # 质量特性列表
    characteristics: List[QualityCharacteristic] = field(default_factory=list)

    # 工程数据 (FMEA / CP / PPAP / 8D)
    fmea_items: List[dict] = field(default_factory=list)      # FMEAItem 序列化
    control_plan_rows: List[dict] = field(default_factory=list)  # 控制计划行
    ppap_report: Dict[str, Any] = field(default_factory=dict)    # PPAP 报告状态
    eight_d_reports: List[dict] = field(default_factory=list)    # 8D 报告列表

    # 分析结果快照 (可选，用于跨 Tab 引用)
    analysis_snapshots: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def add_characteristic(self, qc: QualityCharacteristic):
        """添加质量特性"""
        if not qc.id:
            qc.id = f"QC-{len(self.characteristics) + 1:03d}"
        self.characteristics.append(qc)
        self.updated_at = datetime.now().isoformat()

    def get_characteristic(self, qc_id: str) -> Optional[QualityCharacteristic]:
        """按 ID 获取质量特性"""
        for qc in self.characteristics:
            if qc.id == qc_id:
                return qc
        return None

    def update_characteristic(self, qc_id: str, **kwargs):
        """更新质量特性字段"""
        qc = self.get_characteristic(qc_id)
        if qc:
            for k, v in kwargs.items():
                if hasattr(qc, k):
                    setattr(qc, k, v)
            self.updated_at = datetime.now().isoformat()

    def remove_characteristic(self, qc_id: str):
        """移除质量特性"""
        self.characteristics = [qc for qc in self.characteristics if qc.id != qc_id]
        self.updated_at = datetime.now().isoformat()

    def set_fmea_items(self, items: List[dict]):
        """设置 FMEA 条目"""
        self.fmea_items = items
        self.updated_at = datetime.now().isoformat()

    def set_control_plan(self, rows: List[dict]):
        """设置控制计划行"""
        self.control_plan_rows = rows
        self.updated_at = datetime.now().isoformat()

    def set_ppap_report(self, report: Dict[str, Any]):
        """设置 PPAP 报告状态"""
        self.ppap_report = report
        self.updated_at = datetime.now().isoformat()

    def add_eight_d_report(self, report: dict):
        """添加 8D 报告"""
        self.eight_d_reports.append(report)
        self.updated_at = datetime.now().isoformat()

    def set_analysis_snapshot(self, key: str, snapshot: Dict[str, Any]):
        """设置分析结果快照"""
        self.analysis_snapshots[key] = snapshot
        self.updated_at = datetime.now().isoformat()

    def get_analysis_snapshot(self, key: str) -> Optional[Dict[str, Any]]:
        """获取分析结果快照"""
        return self.analysis_snapshots.get(key)

    # ── 五链查询 ──────────────────────────────────────
    def get_high_risk_fmea_items(self, threshold: int = RPN_HIGH) -> List[dict]:
        """获取高风险 FMEA 条目 (RPN >= threshold)"""
        return [item for item in self.fmea_items if item.get("rpn", 0) >= threshold]

    def get_characteristics_for_spc(self) -> List[QualityCharacteristic]:
        """获取需要 SPC 监控的质量特性"""
        return [qc for qc in self.characteristics if qc.spc_method and qc.data_source]

    def get_fmea_items_for_cp(self) -> List[dict]:
        """获取需要生成控制计划的 FMEA 条目 (高风险项)"""
        return self.get_high_risk_fmea_items()

    # ── 序列化 ──────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "project_name": self.project_name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "characteristics": [qc.to_dict() for qc in self.characteristics],
            "fmea_items": self.fmea_items,
            "control_plan_rows": self.control_plan_rows,
            "ppap_report": self.ppap_report,
            "eight_d_reports": self.eight_d_reports,
            "analysis_snapshots": self.analysis_snapshots,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ProjectContext":
        chars = [QualityCharacteristic.from_dict(qc) for qc in d.get("characteristics", [])]
        return cls(
            project_name=d.get("project_name", ""),
            created_at=d.get("created_at", ""),
            updated_at=d.get("updated_at", ""),
            characteristics=chars,
            fmea_items=d.get("fmea_items", []),
            control_plan_rows=d.get("control_plan_rows", []),
            ppap_report=d.get("ppap_report", {}),
            eight_d_reports=d.get("eight_d_reports", []),
            analysis_snapshots=d.get("analysis_snapshots", {}),
        )
