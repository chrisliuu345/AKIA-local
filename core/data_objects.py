"""
统一数据模型 — 所有 IE 模块共享的数据对象定义
Process, TimeObservation, QualityRecord, MaterialFlow, Resource
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional


@dataclass
class Process:
    """工序 — 支撑线平衡、VSM、OEE、流程分析"""
    process_id: str
    process_name: str
    equipment: str = ""
    cycle_time: float = 0.0
    labor_count: int = 1
    predecessors: List[str] = field(default_factory=list)

    REQUIRED = ["process_id", "process_name"]
    OPTIONAL = ["equipment", "cycle_time", "labor_count", "predecessors"]

    FIELD_ALIASES = {
        "process_id": ["工序编号", "工序ID", "process id", "id", "编号", "序号", "代码", "code", "站号"],
        "process_name": ["工序名称", "工序", "工序名", "process name", "name", "名称", "步骤", "工位名称", "岗位", "作业内容"],
        "equipment": ["设备", "设备名称", "equipment", "machine", "设备编号", "机台", "机器", "机床"],
        "cycle_time": ["ct", "周期时间", "cycle time", "节拍", "时间", "秒", "工时", "标准工时", "加工时间", "作业时间", "耗时"],
        "labor_count": ["人数", "作业人数", "labor", "工人", "人员", "人数(人)", "定员", "操作人数", "人工"],
        "predecessors": ["前置工序", "前置关系", "紧前工序", "predecessors", "prev", "前置", "上游工序", "前工序"],
    }

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> "Process":
        return cls(
            process_id=str(d.get("process_id", "")),
            process_name=str(d.get("process_name", "")),
            equipment=str(d.get("equipment", "")),
            cycle_time=float(d.get("cycle_time", 0) or 0),
            labor_count=int(d.get("labor_count", 1) or 1),
            predecessors=_parse_list(d.get("predecessors", [])),
        )

    @classmethod
    def format_example(cls) -> str:
        return "工序编号 | 工序名称 | 设备 | CT(s) | 人数 | 前置工序"


@dataclass
class TimeObservation:
    """时间观测 — 支撑工时研究、人机分析、双手分析"""
    process_id: str
    operator: str
    cycle: int
    observation_time: float

    REQUIRED = ["process_id", "operator", "cycle", "observation_time"]
    OPTIONAL = []

    FIELD_ALIASES = {
        "process_id": ["工序编号", "工序ID", "process id", "id", "编号", "工序", "序号", "工位号", "代码"],
        "operator": ["作业员", "操作员", "operator", "人员", "工人", "员工", "姓名", "操作者", "测定者", "观测者"],
        "cycle": ["循环", "周期", "cycle", "次数", "循环编号", "第几次", "次", "回", "round"],
        "observation_time": ["时间", "观测时间", "time", "秒", "秒表", "工时", "耗时", "秒数", "观测值", "测量值", "实测", "实际时间"],
    }

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> "TimeObservation":
        return cls(
            process_id=str(d.get("process_id", "")),
            operator=str(d.get("operator", "")),
            cycle=int(d.get("cycle", 0) or 0),
            observation_time=float(d.get("observation_time", 0) or 0),
        )

    @classmethod
    def format_example(cls) -> str:
        return "工序编号 | 作业员 | 循环 | 观测时间(s)"


@dataclass
class QualityRecord:
    """质量记录 — 支撑 SPC、MSA、DOE、过程能力分析"""
    product_id: str
    characteristic: str
    measurement: float
    usl: Optional[float] = None
    lsl: Optional[float] = None
    target: Optional[float] = None

    REQUIRED = ["product_id", "characteristic", "measurement"]
    OPTIONAL = ["usl", "lsl", "target"]

    FIELD_ALIASES = {
        "product_id": ["产品", "产品ID", "product id", "product", "零件", "料号", "编号", "样品"],
        "characteristic": ["特性", "质量特性", "characteristic", "char", "检测项目", "指标", "尺寸"],
        "measurement": ["测量值", "measurement", "值", "value", "结果", "实测", "检测值"],
        "usl": ["usl", "上限", "上规格限", "规格上限", "upper limit", "上限值"],
        "lsl": ["lsl", "下限", "下规格限", "规格下限", "lower limit", "下限值"],
        "target": ["target", "目标值", "目标", "标称值", "中心值", "规格中心"],
    }

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> "QualityRecord":
        def _maybe_float(v):
            if v is None or str(v).strip() == "":
                return None
            return float(v)

        return cls(
            product_id=str(d.get("product_id", "")),
            characteristic=str(d.get("characteristic", "")),
            measurement=float(d.get("measurement", 0) or 0),
            usl=_maybe_float(d.get("usl")),
            lsl=_maybe_float(d.get("lsl")),
            target=_maybe_float(d.get("target")),
        )

    @classmethod
    def format_example(cls) -> str:
        return "产品编号 | 质量特性 | 测量值 | USL | LSL | 目标值"


@dataclass
class MaterialFlow:
    """物流 — 支撑布置优化、搬运分析、VSM"""
    from_process: str
    to_process: str
    quantity: float = 0.0
    distance: float = 0.0

    REQUIRED = ["from_process", "to_process"]
    OPTIONAL = ["quantity", "distance"]

    FIELD_ALIASES = {
        "from_process": ["起点", "来源", "from", "上游", "起始工序", "起始", "from process"],
        "to_process": ["终点", "目标", "to", "下游", "目标工序", "到达", "to process"],
        "quantity": ["数量", "quantity", "qty", "搬运量", "件数", "重量"],
        "distance": ["距离", "distance", "dist", "米", "m", "搬运距离"],
    }

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> "MaterialFlow":
        return cls(
            from_process=str(d.get("from_process", "")),
            to_process=str(d.get("to_process", "")),
            quantity=float(d.get("quantity", 0) or 0),
            distance=float(d.get("distance", 0) or 0),
        )

    @classmethod
    def format_example(cls) -> str:
        return "起点工序 | 终点工序 | 数量 | 距离(m)"


@dataclass
class Resource:
    """资源 — 支撑 OEE、利用率、工时分析、AI 根因分析"""
    resource_type: str = "设备"
    resource_id: str = ""
    group: str = ""
    shift: str = ""
    available_time: float = 0.0
    downtime: float = 0.0
    ideal_cycle_time: float = 0.0
    total_qty: float = 0.0
    good_qty: float = 0.0

    REQUIRED = ["resource_id"]
    OPTIONAL = ["resource_type", "group", "shift", "available_time", "downtime",
                "ideal_cycle_time", "total_qty", "good_qty"]

    FIELD_ALIASES = {
        "resource_id": ["id", "编号", "资源ID", "resource id", "名称", "设备编号", "工号"],
        "resource_type": ["类型", "资源类型", "type", "类别", "人员设备"],
        "group": ["班组", "group", "部门", "小组", "班", "组"],
        "shift": ["班次", "shift", "白班夜班", "班制"],
        "available_time": ["可用时间", "available time", "计划时间", "应工作时间", "小时"],
        "downtime": ["停机时间", "downtime", "停机", "故障时间", "等待时间"],
        "ideal_cycle_time": ["理想节拍", "标准节拍", "理论节拍", "ideal cycle", "ideal_cycle", "额定节拍"],
        "total_qty": ["总产量", "产出", "total", "生产数", "产出数量", "总数"],
        "good_qty": ["良品数", "合格数", "good", "良品", "合格品数", "合格数量"],
    }

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> "Resource":
        return cls(
            resource_type=str(d.get("resource_type", "设备") or "设备"),
            resource_id=str(d.get("resource_id", "")),
            group=str(d.get("group", "")),
            shift=str(d.get("shift", "")),
            available_time=float(d.get("available_time", 0) or 0),
            downtime=float(d.get("downtime", 0) or 0),
            ideal_cycle_time=float(d.get("ideal_cycle_time", 0) or 0),
            total_qty=float(d.get("total_qty", 0) or 0),
            good_qty=float(d.get("good_qty", 0) or 0),
        )

    @classmethod
    def format_example(cls) -> str:
        return "资源类型 | 资源ID | 班组 | 班次 | 可用时间(h) | 停机时间(h) | 理想节拍(s) | 总产量 | 良品数"


_OBJECT_TYPES = {
    "Process": Process,
    "TimeObservation": TimeObservation,
    "QualityRecord": QualityRecord,
    "MaterialFlow": MaterialFlow,
    "Resource": Resource,
}

OBJECT_CLASSES = _OBJECT_TYPES


def _parse_list(value) -> List[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    s = str(value or "").strip()
    if not s:
        return []
    for sep in (",", ";", "、", "，", "；"):
        if sep in s:
            return [v.strip() for v in s.split(sep) if v.strip()]
    return [s]


def get_type_by_name(name: str) -> Optional[type]:
    return _OBJECT_TYPES.get(name)


def get_all_types() -> List[str]:
    return list(_OBJECT_TYPES.keys())
