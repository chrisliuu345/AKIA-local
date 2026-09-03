"""8D 问题解决引擎 — D1-D8 数据模型 + PDF 报告生成"""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class D1Step:
    """D1: 组建团队"""
    team_leader: str = ""
    members: str = ""
    date_started: str = ""

@dataclass
class D2Step:
    """D2: 描述问题"""
    problem_statement: str = ""
    what: str = ""
    where: str = ""
    when: str = ""
    who: str = ""
    why: str = ""
    how: str = ""
    how_many: str = ""

@dataclass
class D3Step:
    """D3: 临时遏制措施 (ICA)"""
    ica_description: str = ""
    implementation_date: str = ""
    verified: bool = False

@dataclass
class D4Step:
    """D4: 根因分析"""
    fishbone_data: Optional[dict] = None
    five_why: str = ""
    root_cause: str = ""

@dataclass
class D5Step:
    """D5: 永久纠正措施 (PCA)"""
    pca_items: List[dict] = field(default_factory=list)
    verification_method: str = ""

@dataclass
class D6Step:
    """D6: 实施验证"""
    implementation_notes: str = ""
    validation_result: str = ""
    validated_date: str = ""

@dataclass
class D7Step:
    """D7: 预防再发"""
    preventive_actions: str = ""
    standards_updated: str = ""
    training_completed: bool = False

@dataclass
class D8Step:
    """D8: 团队表彰"""
    recognition_notes: str = ""
    closure_date: str = ""


@dataclass
class EightDReport:
    title: str = ""
    product: str = ""
    customer: str = ""
    d1: D1Step = field(default_factory=D1Step)
    d2: D2Step = field(default_factory=D2Step)
    d3: D3Step = field(default_factory=D3Step)
    d4: D4Step = field(default_factory=D4Step)
    d5: D5Step = field(default_factory=D5Step)
    d6: D6Step = field(default_factory=D6Step)
    d7: D7Step = field(default_factory=D7Step)
    d8: D8Step = field(default_factory=D8Step)
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    STEP_LABELS = {
        "D1": "组建团队", "D2": "描述问题", "D3": "临时遏制",
        "D4": "根因分析", "D5": "永久措施", "D6": "实施验证",
        "D7": "预防再发", "D8": "团队表彰",
    }

    def to_markdown(self) -> str:
        lines = [
            f"# 8D 报告: {self.title}",
            f"产品: {self.product} | 客户: {self.customer} | 日期: {self.created_at}\n",
        ]
        steps = [
            ("D1", f"团队长: {self.d1.team_leader}\n成员: {self.d1.members}"),
            ("D2", f"问题: {self.d2.problem_statement}\n5W2H: 何事={self.d2.what} 何处={self.d2.where} 何时={self.d2.when}"),
            ("D3", f"ICA: {self.d3.ica_description}\n实施: {self.d3.implementation_date} 验证: {'是' if self.d3.verified else '否'}"),
            ("D4", f"根因: {self.d4.root_cause}\n5Why:\n{self.d4.five_why}"),
            ("D5", f"PCA 项数: {len(self.d5.pca_items)}\n验证方法: {self.d5.verification_method}"),
            ("D6", f"实施: {self.d6.implementation_notes}\n验证: {self.d6.validation_result}"),
            ("D7", f"预防: {self.d7.preventive_actions}\n标准更新: {self.d7.standards_updated}"),
            ("D8", f"表彰: {self.d8.recognition_notes}\n关闭日期: {self.d8.closure_date}"),
        ]
        for code, content in steps:
            lines.append(f"## {code}: {self.STEP_LABELS[code]}\n{content}\n")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "title": self.title, "product": self.product, "customer": self.customer,
            "created_at": self.created_at,
            "steps": {f"D{i}": getattr(self, f"d{i}").__dict__ for i in range(1, 9)},
        }
