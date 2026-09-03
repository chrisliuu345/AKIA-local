"""FMEA 失效模式与影响分析引擎 — DFMEA/PFMEA 数据模型 + RPN 计算

RPN = 严重度(S) × 发生度(O) × 检出度(D)
分级: RPN >= RPN_HIGH(100) 高风险(红), >= RPN_MEDIUM(50) 中风险(橙), < 50 低风险
"""

from dataclasses import dataclass
from typing import List
from config.settings import RPN_CRITICAL, RPN_HIGH, RPN_MEDIUM


@dataclass
class FMEAItem:
    """单条 FMEA 记录"""
    function: str = ""
    failure_mode: str = ""
    effect: str = ""
    severity: int = 1
    cause: str = ""
    occurrence: int = 1
    control: str = ""
    detection: int = 1
    rpn: int = 0
    recommended_action: str = ""
    responsible: str = ""
    action_status: str = ""

    def calc_rpn(self) -> int:
        self.rpn = self.severity * self.occurrence * self.detection
        return self.rpn

    @property
    def risk_level(self) -> str:
        if self.rpn >= RPN_HIGH:
            return "high"
        if self.rpn >= RPN_MEDIUM:
            return "medium"
        return "low"

    HEADERS = [
        "功能/工序", "失效模式", "失效后果", "严重度S",
        "失效原因", "发生度O", "现行控制", "检出度D",
        "RPN", "建议措施", "责任人", "措施状态",
    ]

    def to_row(self) -> list:
        return [
            self.function, self.failure_mode, self.effect, str(self.severity),
            self.cause, str(self.occurrence), self.control, str(self.detection),
            str(self.rpn), self.recommended_action, self.responsible, self.action_status,
        ]

    @classmethod
    def from_row(cls, row: list) -> "FMEAItem":
        try:
            s = int(row[3]) if row[3] else 1
        except (ValueError, IndexError):
            s = 1
        try:
            o = int(row[5]) if row[5] else 1
        except (ValueError, IndexError):
            o = 1
        try:
            d = int(row[7]) if row[7] else 1
        except (ValueError, IndexError):
            d = 1
        item = cls(
            function=row[0] if len(row) > 0 else "",
            failure_mode=row[1] if len(row) > 1 else "",
            effect=row[2] if len(row) > 2 else "",
            severity=s,
            cause=row[4] if len(row) > 4 else "",
            occurrence=o,
            control=row[6] if len(row) > 6 else "",
            detection=d,
            recommended_action=row[9] if len(row) > 9 else "",
            responsible=row[10] if len(row) > 10 else "",
            action_status=row[11] if len(row) > 11 else "",
        )
        item.calc_rpn()
        return item


class FMEAEngine:
    """FMEA 数据管理 — CRUD + RPN 排序 + 统计"""

    @staticmethod
    def create_default(mode: str = "pfmea") -> List[FMEAItem]:
        """创建默认示例条目"""
        if mode == "dfmea":
            items = [
                FMEAItem("轴承", "疲劳断裂", "设备停机", 8, "材料缺陷", 4, "抽检", 5,
                         recommended_action="增加超声探伤", responsible="张三", action_status="未开始"),
                FMEAItem("密封圈", "老化泄漏", "污染产品", 6, "高温环境", 5, "定期更换", 3,
                         recommended_action="改用氟橡胶材质", responsible="李四", action_status="进行中"),
            ]
        else:
            items = [
                FMEAItem("焊接工序", "虚焊", "电路断路", 7, "温度不足", 5, "目视检查", 6,
                         recommended_action="增加温度监控", responsible="王五", action_status="未开始"),
                FMEAItem("装配工序", "错位", "产品尺寸超差", 5, "夹具松动", 3, "首件检验", 4,
                         recommended_action="增加防错装置", responsible="赵六", action_status="已完成"),
                FMEAItem("测试工序", "漏检", "不良品流出", 9, "测试时间不足", 6, "抽检", 7,
                         recommended_action="全检+自动化测试", responsible="钱七", action_status="未开始"),
            ]
        for i in items:
            i.calc_rpn()
        return items

    @staticmethod
    def sort_by_rpn(items: List[FMEAItem], descending: bool = True) -> List[FMEAItem]:
        return sorted(items, key=lambda x: x.rpn, reverse=descending)

    @staticmethod
    def get_stats(items: List[FMEAItem]) -> dict:
        if not items:
            return {"total": 0, "high": 0, "medium": 0, "low": 0, "max_rpn": 0, "top3": []}
        levels = [i.risk_level for i in items]
        return {
            "total": len(items),
            "high": levels.count("high"),
            "medium": levels.count("medium"),
            "low": levels.count("low"),
            "max_rpn": max(i.rpn for i in items),
            "top3": [i.failure_mode for i in sorted(items, key=lambda x: x.rpn, reverse=True)[:3]],
        }

    @staticmethod
    def to_dataframe(items: List[FMEAItem]):
        import pandas as pd
        data = [i.to_row() for i in items]
        return pd.DataFrame(data, columns=FMEAItem.HEADERS)

    @staticmethod
    def generate_cp_rows(items: List[FMEAItem], rpn_threshold: int = RPN_HIGH) -> list:
        """从高风险 FMEA 条目生成控制计划行

        映射关系:
        - FMEA.function → CP.工序名称
        - FMEA.failure_mode + FMEA.cause → CP.特性
        - FMEA.control → CP.控制方法
        - FMEA.recommended_action → CP.反应计划
        - FMEA.severity → 决定抽样频率

        Returns: List[list]，每个 list 对应 CP_HEADERS 的一行
        """
        cp_rows = []
        for item in items:
            if item.rpn < rpn_threshold:
                continue

            if item.severity >= 8:
                frequency = "每件"
                sample_size = "100%"
            elif item.severity >= 5:
                frequency = "每小时"
                sample_size = "5"
            else:
                frequency = "每批"
                sample_size = "10"

            characteristic = f"{item.failure_mode} ({item.cause})" if item.cause else item.failure_mode

            control_method = item.control
            if item.recommended_action:
                control_method = f"{item.control} → {item.recommended_action}"

            if item.rpn >= RPN_CRITICAL:
                reaction = "停线+通知质量/工程"
            elif item.rpn >= RPN_HIGH:
                reaction = "隔离+通知责任人"
            else:
                reaction = "记录+跟踪"

            cp_row = [
                f"OP{len(cp_rows)*10+10:02d}",
                item.function,
                characteristic,
                "",
                "",
                sample_size,
                frequency,
                control_method,
                reaction,
            ]
            cp_rows.append(cp_row)

        return cp_rows
