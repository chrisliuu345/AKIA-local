"""鱼骨图 (石川图 / Ishikawa Diagram) — 数据模型 + matplotlib 渲染

6M 默认分类: 人(Man) / 机(Machine) / 料(Material) / 法(Method) / 环(Environment) / 测(Measurement)

支持: 自定义分支名 · 多级子原因 · 颜色编码 · 导出图片
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List

import numpy as np


@dataclass
class CauseNode:
    """鱼骨图节点 — 可递归嵌套子原因"""
    name: str
    children: List["CauseNode"] = field(default_factory=list)
    level: int = 0  # 0=主分支, 1=子原因, 2=孙原因


# 默认 6M 配色
M6_COLORS = [
    "#4da6ff",  # 人 - 蓝
    "#ff6b6b",  # 机 - 红
    "#51cf66",  # 料 - 绿
    "#ffa726",  # 法 - 橙
    "#cc5de8",  # 环 - 紫
    "#20c997",  # 测 - 青
]

M6_DEFAULTS = {
    "人": ["技能不足", "培训缺失", "疲劳/疏忽", "沟通不畅"],
    "机": ["设备老化", "保养不及时", "精度下降", "工装磨损"],
    "料": ["来料不良", "批次波动", "存储不当", "规格不符"],
    "法": ["SOP不明确", "参数偏离", "方法不统一", "流程缺陷"],
    "环": ["温湿度异常", "振动干扰", "照明不足", "粉尘/静电"],
    "测": ["量具偏差", "测量方法不当", "取样代表性差", "记录错误"],
}


class FishboneEngine:
    """鱼骨图数据模型 + 渲染"""

    @staticmethod
    def create_default(problem: str = "质量问题") -> Dict[str, CauseNode]:
        """创建默认 6M 模板"""
        branches = {}
        for m_name, sub_causes in M6_DEFAULTS.items():
            root = CauseNode(name=m_name, level=0)
            for sc in sub_causes:
                root.children.append(CauseNode(name=sc, level=1))
            branches[m_name] = root
        return branches

    @staticmethod
    def to_dict(branches: Dict[str, CauseNode]) -> Dict[str, Any]:
        """序列化为可 JSON 存储的 dict"""
        def node_to_dict(node: CauseNode) -> dict:
            return {
                "name": node.name,
                "children": [node_to_dict(c) for c in node.children],
            }
        return {k: node_to_dict(v) for k, v in branches.items()}

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> Dict[str, CauseNode]:
        """从 dict 反序列化"""
        def dict_to_node(d: dict, level: int = 0) -> CauseNode:
            node = CauseNode(name=d["name"], level=level)
            for child_d in d.get("children", []):
                node.children.append(dict_to_node(child_d, level + 1))
            return node

        return {k: dict_to_node(v) for k, v in data.items()}

    @staticmethod
    def count_causes(branches: Dict[str, CauseNode]) -> int:
        """统计所有子原因总数"""
        def _count(node: CauseNode) -> int:
            return 1 + sum(_count(c) for c in node.children)
        return sum(_count(root) for root in branches.values()) - len(branches)

    # ──────────────────────────────────────────────
    # matplotlib 渲染
    # ──────────────────────────────────────────────
    @staticmethod
    def render(branches: Dict[str, CauseNode],
               problem: str = "质量问题",
               figsize: tuple = (14, 7),
               dpi: int = 100):
        """使用 matplotlib 绘制鱼骨图，返回 Figure"""
        import matplotlib.pyplot as plt
        from matplotlib.figure import Figure

        plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
        plt.rcParams["axes.unicode_minus"] = False

        fig = Figure(figsize=figsize, dpi=dpi)
        fig.set_facecolor("#262632")
        ax = fig.add_axes([0.02, 0.02, 0.96, 0.92])
        ax.set_xlim(-10, 12)
        ax.set_ylim(-8, 8)
        ax.axis("off")
        ax.set_facecolor("#262632")

        branch_names = list(branches.keys())
        n = len(branch_names)
        if n == 0:
            ax.text(1, 0, "请添加分析分支", fontsize=16, color="#a0a3ae",
                    ha="center", va="center")
            return fig

        colors = M6_COLORS[:n] if n <= len(M6_COLORS) else M6_COLORS * ((n // len(M6_COLORS)) + 1)

        # ── 主脊骨 ──
        ax.annotate("", xy=(8.5, 0), xytext=(-6, 0),
                     arrowprops=dict(arrowstyle="->", color="#e1e2e6",
                                     lw=3, connectionstyle="arc3,rad=0"))
        ax.text(9, 0, problem, fontsize=14, fontweight="bold",
                color="#e1e2e6", ha="left", va="center",
                bbox=dict(boxstyle="round,pad=0.5", facecolor="#363648",
                          edgecolor="#4da6ff", linewidth=1.5))

        # ── 分支位置 (上下交错) ──
        spine_angles = np.linspace(15, 55, max(n, 1))
        for i, (bname, root) in enumerate(branches.items()):
            color = colors[i]
            # 上/下半区交错
            if i % 2 == 0:
                angle = spine_angles[i // 2] if i // 2 < len(spine_angles) else 30
                y_dir = 1
            else:
                angle = spine_angles[i // 2] if i // 2 < len(spine_angles) else 30
                y_dir = -1

            rad_angle = np.radians(angle)
            bx = (i - n / 2 + 0.5) * 1.8  # 分支在脊骨上的 x 位置
            branch_len = 5.5
            ex = bx + branch_len * np.cos(rad_angle)
            ey = y_dir * branch_len * np.sin(rad_angle)

            # 主分支线
            ax.annotate("", xy=(ex, ey), xytext=(bx, 0),
                         arrowprops=dict(arrowstyle="->", color=color, lw=2.5))

            # 分支标签
            ax.text(ex + 0.3, ey + 0.2 * y_dir, bname, fontsize=11,
                    fontweight="bold", color=color, ha="left", va="center")

            # 子原因刺 (沿分支线排列)
            sub_count = len(root.children)
            for j, child in enumerate(root.children):
                t = (j + 1) / (sub_count + 1)
                sx = bx + t * (ex - bx)
                sy = t * ey
                # 小刺 (垂直于分支)
                perp_angle = rad_angle + np.pi / 2
                spike_len = 0.9
                spike_dx = spike_len * np.cos(perp_angle)
                spike_dy = spike_len * np.sin(perp_angle)

                # 上下交替小刺
                if j % 2 == 0:
                    ax.annotate("", xy=(sx + spike_dx, sy + spike_dy),
                                xytext=(sx, sy),
                                arrowprops=dict(arrowstyle="-", color=color, lw=1, alpha=0.7))
                    tx = sx + spike_dx * 1.5
                    ty = sy + spike_dy * 1.5
                    ha = "left" if spike_dx > 0 else "right"
                else:
                    ax.annotate("", xy=(sx - spike_dx, sy - spike_dy),
                                xytext=(sx, sy),
                                arrowprops=dict(arrowstyle="-", color=color, lw=1, alpha=0.7))
                    tx = sx - spike_dx * 1.5
                    ty = sy - spike_dy * 1.5
                    ha = "right" if sx - spike_dx * 1.5 < sx else "left"

                ax.text(tx, ty, child.name, fontsize=8, color="#d0d2d8",
                        ha=ha, va="center", alpha=0.9)

                # 三级原因 (child.children)
                for k, grandchild in enumerate(child.children):
                    t2_x = tx - 0.15
                    t2_y = ty + (0.35 if k % 2 == 0 else -0.35) * (k // 2 + 1)
                    ax.text(t2_x, t2_y, f"·{grandchild.name}", fontsize=6.5,
                            color="#8a8c96", ha=ha, va="center", alpha=0.75)

        return fig


if __name__ == "__main__":
    # 快速自测
    engine = FishboneEngine()
    branches = engine.create_default("焊接不良")
    fig = engine.render(branches, "焊接不良")
    fig.savefig("fishbone_test.png", dpi=120, bbox_inches="tight")
    print("[OK] fishbone_test.png saved")
