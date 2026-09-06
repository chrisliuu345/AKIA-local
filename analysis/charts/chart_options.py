"""
图表参数定义 — 每种图表类型的可调参数 schema

用于图表编辑面板，支持实时调整和持久化到 .qap 项目文件
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict
import json


@dataclass
class SliderOption:
    """滑块参数"""
    key: str
    label: str
    min_val: float
    max_val: float
    default: float
    step: float = 1.0
    unit: str = ""


@dataclass
class RadioOption:
    """单选参数"""
    key: str
    label: str
    options: List[str]
    default: str = ""


@dataclass
class CheckboxOption:
    """复选参数"""
    key: str
    label: str
    default: bool = False


@dataclass
class ChartTypeOptions:
    """单种图表类型的参数集合"""
    chart_type: str
    sliders: List[SliderOption] = field(default_factory=list)
    radios: List[RadioOption] = field(default_factory=list)
    checkboxes: List[CheckboxOption] = field(default_factory=list)

    def get_defaults(self) -> Dict[str, Any]:
        defaults = {}
        for s in self.sliders:
            defaults[s.key] = s.default
        for r in self.radios:
            defaults[r.key] = r.default or r.options[0]
        for c in self.checkboxes:
            defaults[c.key] = c.default
        return defaults

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chart_type": self.chart_type,
            "sliders": [asdict(s) for s in self.sliders],
            "radios": [asdict(r) for r in self.radios],
            "checkboxes": [asdict(c) for c in self.checkboxes],
        }


# ========== 图表参数定义 ==========

PIE_OPTIONS = ChartTypeOptions(
    chart_type="饼图",
    sliders=[
        SliderOption("label_fontsize", "标签字号", 8, 20, 11, 1, "pt"),
        SliderOption("min_slice_percent", "小扇区合并阈值", 0, 20, 5, 1, "%"),
        SliderOption("explode_amount", "分离程度", 0, 15, 2, 1, "%"),
    ],
    radios=[
        RadioOption("label_position", "标签位置", ["inside", "outside", "autopct"], "outside"),
    ],
    checkboxes=[
        CheckboxOption("show_percentage", "显示百分比", True),
        CheckboxOption("show_labels", "显示标签", True),
    ],
)

BAR_OPTIONS = ChartTypeOptions(
    chart_type="柱状图",
    sliders=[
        SliderOption("label_rotation", "标签旋转", 0, 90, 45, 5, "°"),
        SliderOption("label_fontsize", "标签字号", 6, 16, 10, 1, "pt"),
        SliderOption("bar_width", "柱宽", 0.5, 1.0, 0.8, 0.1, ""),
    ],
    radios=[],
    checkboxes=[
        CheckboxOption("show_values", "显示数值标签", False),
        CheckboxOption("show_grid", "显示网格", True),
    ],
)

PARETO_OPTIONS = ChartTypeOptions(
    chart_type="帕累托图",
    sliders=[
        SliderOption("label_rotation", "标签旋转", 0, 90, 45, 5, "°"),
        SliderOption("label_fontsize", "标签字号", 6, 16, 10, 1, "pt"),
    ],
    radios=[],
    checkboxes=[
        CheckboxOption("show_cumulative", "显示累积线", True),
        CheckboxOption("show_grid", "显示网格", True),
    ],
)

SCATTER_OPTIONS = ChartTypeOptions(
    chart_type="散点图",
    sliders=[
        SliderOption("point_size", "点大小", 10, 200, 50, 10, ""),
        SliderOption("point_alpha", "透明度", 0.1, 1.0, 0.6, 0.1, ""),
    ],
    radios=[],
    checkboxes=[
        CheckboxOption("show_regression", "显示回归线", False),
        CheckboxOption("show_confidence", "显示置信区间", False),
        CheckboxOption("show_grid", "显示网格", True),
    ],
)

HISTOGRAM_OPTIONS = ChartTypeOptions(
    chart_type="直方图",
    sliders=[
        SliderOption("bins", "分箱数", 5, 100, 20, 5, ""),
        SliderOption("label_fontsize", "标签字号", 6, 16, 10, 1, "pt"),
    ],
    radios=[
        RadioOption("histtype", "类型", ["bar", "step", "stepfilled"], "bar"),
    ],
    checkboxes=[
        CheckboxOption("show_density", "显示密度曲线", False),
        CheckboxOption("show_mean", "显示均值线", True),
        CheckboxOption("show_grid", "显示网格", True),
    ],
)

BOXPLOT_OPTIONS = ChartTypeOptions(
    chart_type="箱线图",
    sliders=[
        SliderOption("label_fontsize", "标签字号", 6, 16, 10, 1, "pt"),
    ],
    radios=[],
    checkboxes=[
        CheckboxOption("show_mean", "显示均值", True),
        CheckboxOption("show_grid", "显示网格", True),
    ],
)

HEATMAP_OPTIONS = ChartTypeOptions(
    chart_type="矩阵图",
    sliders=[
        SliderOption("label_fontsize", "标签字号", 6, 16, 10, 1, "pt"),
        SliderOption("annot_fontsize", "数值字号", 6, 14, 8, 1, "pt"),
    ],
    radios=[
        RadioOption("colormap", "配色", ["RdYlGn_r", "coolwarm", "viridis", "RdBu_r"], "RdYlGn_r"),
    ],
    checkboxes=[
        CheckboxOption("show_annotations", "显示数值", True),
        CheckboxOption("show_significance", "显示显著性标记", True),
    ],
)

RESIDUAL_OPTIONS = ChartTypeOptions(
    chart_type="残差图",
    sliders=[
        SliderOption("point_size", "点大小", 10, 200, 50, 10, ""),
        SliderOption("point_alpha", "透明度", 0.1, 1.0, 0.6, 0.1, ""),
    ],
    radios=[],
    checkboxes=[
        CheckboxOption("show_grid", "显示网格", True),
    ],
)

SCATTER_MATRIX_OPTIONS = ChartTypeOptions(
    chart_type="散点矩阵图",
    sliders=[
        SliderOption("point_size", "点大小", 10, 200, 30, 10, ""),
        SliderOption("point_alpha", "透明度", 0.1, 1.0, 0.5, 0.1, ""),
    ],
    radios=[],
    checkboxes=[
        CheckboxOption("show_regression", "显示回归线", True),
    ],
)

FACETING_OPTIONS = ChartTypeOptions(
    chart_type="小多图",
    sliders=[
        SliderOption("col_wrap", "每行列数", 1, 6, 3, 1, ""),
        SliderOption("height", "子图高度", 2, 6, 4, 0.5, "英寸"),
    ],
    radios=[
        RadioOption("facet_kind", "子图类型", ["直方图", "箱线图"], "直方图"),
        RadioOption("facet_mode", "排列方式", ["col", "row", "grid"], "col"),
    ],
    checkboxes=[
        CheckboxOption("share_x", "共享X轴", True),
        CheckboxOption("share_y", "共享Y轴", True),
    ],
)

SPC_OPTIONS = ChartTypeOptions(
    chart_type="SPC控制图",
    sliders=[
        SliderOption("label_fontsize", "标签字号", 6, 16, 10, 1, "pt"),
    ],
    radios=[],
    checkboxes=[
        CheckboxOption("show_grid", "显示网格", True),
        CheckboxOption("show_limits", "显示控制限", True),
    ],
)

# ========== 注册表 ==========
# 键必须与触发编辑的图表类型名一致（ChartTab/SPCTab 等传入 set_chart_type 的名称）

CHART_OPTIONS_REGISTRY: Dict[str, ChartTypeOptions] = {
    "饼图": PIE_OPTIONS,
    "柱状图": BAR_OPTIONS,
    "帕累托图": PARETO_OPTIONS,
    "散点图": SCATTER_OPTIONS,
    "直方图": HISTOGRAM_OPTIONS,
    "箱线图": BOXPLOT_OPTIONS,
    "矩阵图": HEATMAP_OPTIONS,
    "散点矩阵图": SCATTER_MATRIX_OPTIONS,
    "残差图": RESIDUAL_OPTIONS,
    "小多图": FACETING_OPTIONS,
    "能力图": SPC_OPTIONS,
    "XBar-R": SPC_OPTIONS,
    "XBar-S": SPC_OPTIONS,
    "I-MR": SPC_OPTIONS,
    "P Chart": SPC_OPTIONS,
    "NP Chart": SPC_OPTIONS,
    "C Chart": SPC_OPTIONS,
    "U Chart": SPC_OPTIONS,
    "CUSUM": SPC_OPTIONS,
    "EWMA": SPC_OPTIONS,
    "Laney P'": SPC_OPTIONS,
    "Laney U'": SPC_OPTIONS,
    "Hotelling T²": SPC_OPTIONS,
}


def get_chart_options(chart_type: str) -> Optional[ChartTypeOptions]:
    """获取指定图表类型的参数定义"""
    return CHART_OPTIONS_REGISTRY.get(chart_type)


def get_all_chart_types() -> List[str]:
    """获取所有支持编辑的图表类型"""
    return list(CHART_OPTIONS_REGISTRY.keys())


def get_default_options(chart_type: str) -> Dict[str, Any]:
    """获取指定图表类型的默认参数"""
    opts = get_chart_options(chart_type)
    return opts.get_defaults() if opts else {}


def options_to_json(options: Dict[str, Any]) -> str:
    """参数序列化为 JSON"""
    return json.dumps(options, ensure_ascii=False, indent=2)


def options_from_json(json_str: str) -> Dict[str, Any]:
    """从 JSON 反序列化参数"""
    return json.loads(json_str)
