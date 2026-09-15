"""统一图表风格层（v4.1.0 B1）— QA-Tool 图表的唯一事实源。

设计:
  - **两套主题**: ``dark``（应用内，与 ui/theme.py 深色一致）/ ``light``（报告与导出白底）
  - **色盲友好调色板**（Okabe-Ito）+ 固定语义色：数据 / 中心线 / 控制限 / 规格限 / 拟合 / 违规
  - **统一 rcParams**：字体、字号、网格、脊线、图例、坐标轴负号
  - **工具函数**：apply_chart_style / style_axes / smart_ylim / add_limit_lines /
    mark_violations / finalize_figure / style_for_export

约定:
  - 本模块属 output 基础层，**禁止 import ui**（tests/test_layering.py 守卫）
  - 主题可用 settings 的 ``chart_theme`` 覆盖（dark/light）
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np

THEME_DARK = "dark"
THEME_LIGHT = "light"
DEFAULT_THEME = THEME_DARK

# Okabe-Ito 色盲友好序列（首色为数据蓝）
PALETTE: List[str] = [
    "#0072B2",  # 蓝
    "#E69F00",  # 橙
    "#009E73",  # 蓝绿
    "#D55E00",  # 朱红
    "#CC79A7",  # 品红
    "#56B4E9",  # 天蓝
    "#F0E442",  # 黄
    "#7F7F7F",  # 灰
]

# 语义色（与主题相关）
_THEMES: Dict[str, Dict[str, str]] = {
    THEME_DARK: {
        "figure_bg": "#181822",
        "panel": "#262632",
        "text": "#e1e2e6",
        "text_muted": "#a0a3ae",
        "axis": "#3a3a48",
        "grid": "#32323f",
        "data": "#56B4E9",
        "data_alt": "#E69F00",
        "center": "#009E73",
        "limit": "#D55E00",
        "spec": "#E69F00",
        "fit": "#CC79A7",
        "violation": "#D55E00",
        "good": "#009E73",
        "warning": "#F0E442",
        "bad": "#D55E00",
        "neutral": "#8a8c96",
    },
    THEME_LIGHT: {
        "figure_bg": "#ffffff",
        "panel": "#ffffff",
        "text": "#2b2b33",
        "text_muted": "#666a73",
        "axis": "#c9ccd4",
        "grid": "#e6e8ee",
        "data": "#0072B2",
        "data_alt": "#E69F00",
        "center": "#009E73",
        "limit": "#D55E00",
        "spec": "#E69F00",
        "fit": "#CC79A7",
        "violation": "#D55E00",
        "good": "#009E73",
        "warning": "#B8860B",
        "bad": "#D55E00",
        "neutral": "#9aa0a6",
    },
}

_FONT_CANDIDATES = (
    "Microsoft YaHei", "SimHei", "Noto Sans SC", "Noto Sans JP",
    "WenQuanYi Micro Hei", "WenQuanYi Zen Hei", "Source Han Sans SC",
    "DejaVu Sans",
)


def current_theme() -> str:
    """当前默认主题（settings.chart_theme → dark/light）。"""
    try:
        from config.settings import get_effective
        name = str(get_effective("chart_theme", DEFAULT_THEME) or DEFAULT_THEME).lower()
    except Exception:  # noqa: BLE001 - 无配置环境（测试/脚本）
        name = DEFAULT_THEME
    return name if name in _THEMES else DEFAULT_THEME


def semantic(theme: Optional[str] = None) -> Dict[str, str]:
    """主题语义色字典（副本，调用方可安全修改）。"""
    return dict(_THEMES.get(str(theme or current_theme()).lower(), _THEMES[DEFAULT_THEME]))


def palette(n: Optional[int] = None, theme: Optional[str] = None) -> List[str]:
    """取调色板；n 超出长度时自动循环。"""
    colors = list(PALETTE)
    if n is None or int(n) <= 0:
        return colors
    count = int(n)
    return [colors[i % len(colors)] for i in range(count)]


def setup_fonts() -> None:
    """配置中文字体（跨平台候选 + 用户设置优先）。"""
    try:
        import matplotlib.font_manager as fm
        fm._load_fontmanager(try_read_cache=False)
        available = {f.name for f in fm.fontManager.ttflist}
        preferred: List[str] = []
        try:
            from core.fonts import get_ui_font
            preferred.append(get_ui_font())
        except Exception:  # noqa: BLE001
            pass
        try:
            from config.settings import get_setting
            user_font = get_setting("font_family", "")
            if user_font:
                preferred.insert(0, str(user_font))
        except Exception:  # noqa: BLE001
            pass
        preferred.extend(_FONT_CANDIDATES)
        matched = [name for name in preferred if name in available]
        if matched:
            current = list(plt.rcParams["font.sans-serif"])
            for name in reversed(matched):
                if name in current:
                    current.remove(name)
                current.insert(0, name)
            plt.rcParams["font.sans-serif"] = current
    except Exception:  # noqa: BLE001 - 字体不可用时保持 matplotlib 默认
        pass
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["axes.unicode_minus"] = False


def apply_chart_style(theme: Optional[str] = None, *, dpi: Optional[int] = None) -> str:
    """应用统一 rcParams，返回实际生效主题名。"""
    name = str(theme or current_theme()).lower()
    if name not in _THEMES:
        name = DEFAULT_THEME
    s = _THEMES[name]
    plt.rcParams.update({
        "figure.facecolor": s["figure_bg"],
        "figure.edgecolor": s["figure_bg"],
        "savefig.facecolor": s["figure_bg"],
        "savefig.edgecolor": s["figure_bg"],
        "axes.facecolor": s["panel"],
        "axes.edgecolor": s["axis"],
        "axes.labelcolor": s["text"],
        "axes.titlecolor": s["text"],
        "text.color": s["text"],
        "xtick.color": s["text_muted"],
        "ytick.color": s["text_muted"],
        "axes.titlesize": 15,
        "axes.labelsize": 12,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 9,
        "legend.frameon": False,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": s["grid"],
        "grid.alpha": 0.45,
        "grid.linewidth": 0.7,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.prop_cycle": plt.cycler(color=list(PALETTE)),
        "figure.dpi": int(dpi) if dpi else plt.rcParams.get("figure.dpi", 100),
    })
    setup_fonts()
    return name


def style_axes(ax, *, grid: str = "y", legend: bool = False,
               hide_spines: Sequence[str] = ("top", "right"),
               legend_outside: bool = False,
               legend_loc: str = "best", legend_cols: int = 1) -> None:
    """统一坐标轴：网格方向 / 脊线 / 子图背景。"""
    s = semantic()
    ax.set_facecolor(s["panel"])
    if grid:
        ax.grid(True, axis=grid, color=s["grid"], alpha=0.45, linewidth=0.7)
        ax.set_axisbelow(True)
    else:
        ax.grid(False)
    for side in hide_spines:
        if side in ax.spines:
            ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        if side in ax.spines:
            ax.spines[side].set_color(s["axis"])
    if legend and ax.get_legend_handles_labels()[0]:
        if legend_outside:
            ax.legend(frameon=False, fontsize=9, loc="upper left",
                      bbox_to_anchor=(1.01, 1.0), borderaxespad=0,
                      ncol=int(legend_cols))
        else:
            ax.legend(frameon=False, fontsize=9, loc=legend_loc,
                      ncol=int(legend_cols))


def smart_ylim(ax, *values, pad: float = 0.08, include_zero: bool = False,
               min_span: Optional[float] = None) -> Optional[Tuple[float, float]]:
    """按数据幅度设置 y 轴范围，避免"平线贴底"（0 锚定）与贴边。

    参数:
        values: 任意数量的标量 / 数组（含控制限、规格限）
        pad: 上下留白比例（相对数据跨度）
        include_zero: 是否强制包含 0（柱状图等语义需要时）
        min_span: 最小跨度（数据完全恒定或跨度极小时兜底）
    """
    arrays = []
    for value in values:
        if value is None:
            continue
        arr = np.asarray(value, dtype=float).ravel()
        arr = arr[np.isfinite(arr)]
        if arr.size:
            arrays.append(arr)
    if not arrays:
        return None
    merged = np.concatenate(arrays)
    lo, hi = float(np.min(merged)), float(np.max(merged))
    span = hi - lo
    if span <= 0:
        span = max(abs(hi) * 0.05, 1e-9)
    lo, hi = lo - span * pad, hi + span * pad
    if min_span is not None and (hi - lo) < float(min_span):
        center = (lo + hi) / 2
        lo, hi = center - float(min_span) / 2, center + float(min_span) / 2
    if include_zero:
        lo, hi = min(lo, 0.0), max(hi, 0.0)
    ax.set_ylim(lo, hi)
    ax.set_autoscaley_on(False)
    return lo, hi


def add_limit_lines(ax, *, cl=None, ucl=None, lcl=None, usl=None, lsl=None,
                    orientation: str = "h", labels: bool = True,
                    fontsize: int = 9) -> List[float]:
    """绘制 CL / UCL / LCL / USL / LSL 参考线，返回纳入的数值列表。

    - 控制限（UCL/LCL）: 朱红虚线
    - 规格限（USL/LSL）: 橙色点划线（与拟合线、控制限区分）
    - 中心线（CL）: 蓝绿实线
    """
    s = semantic()
    included: List[float] = []
    draw = ax.axhline if orientation == "h" else ax.axvline
    if cl is not None:
        draw(float(cl), color=s["center"], linestyle="-", linewidth=1.4,
             label=f"CL={float(cl):.4g}" if labels else None)
        included.append(float(cl))
    for name, value in (("UCL", ucl), ("LCL", lcl)):
        if value is None:
            continue
        draw(float(value), color=s["limit"], linestyle="--", linewidth=1.1,
             label=f"{name}={float(value):.4g}" if labels else None)
        included.append(float(value))
    for name, value in (("USL", usl), ("LSL", lsl)):
        if value is None:
            continue
        draw(float(value), color=s["spec"], linestyle="-.", linewidth=1.3,
             label=f"{name}={float(value):.4g}" if labels else None)
        included.append(float(value))
    return included


def mark_violations(ax, xs, ys, *, annotate: Optional[Sequence[str]] = None,
                    size: int = 11, label: Optional[str] = None) -> None:
    """判异点：空心圈 + 可选规则注释（形式区别于细虚线控制限）。"""
    s = semantic()
    xs = list(xs)
    ys = list(ys)
    if not xs:
        return
    ax.plot(xs, ys, "o", mfc="none", mec=s["violation"], mew=1.8,
            ms=size, zorder=6, label=label)
    if annotate:
        for x, y, text in zip(xs, ys, annotate, strict=False):
            if not text:
                continue
            ax.annotate(str(text), (x, y), textcoords="offset points",
                        xytext=(0, 9), ha="center", fontsize=8,
                        color=s["violation"])


def finalize_figure(fig, *, tight: bool = True, pad: float = 1.05) -> None:
    """收尾：统一图背景与边距。"""
    fig.patch.set_facecolor(semantic()["figure_bg"])
    if tight:
        try:
            fig.tight_layout(pad=pad)
        except Exception:  # noqa: BLE001 - 特殊布局（colorbar/3D）
            pass


def style_for_export(fig, theme: str = THEME_LIGHT) -> None:
    """把已生成的图形切成导出主题（报告/PPT 默认白底）。"""
    s = semantic(theme)
    fig.patch.set_facecolor(s["figure_bg"])
    for ax in fig.get_axes():
        ax.set_facecolor(s["panel"])
        ax.tick_params(colors=s["text_muted"])
        ax.xaxis.label.set_color(s["text"])
        ax.yaxis.label.set_color(s["text"])
        ax.title.set_color(s["text"])
        for side, spine in ax.spines.items():
            spine.set_color(s["axis"])
            spine.set_visible(side not in ("top", "right"))
        ax.grid(True, axis="y", color=s["grid"], alpha=0.45, linewidth=0.7)
        legend = ax.get_legend()
        if legend is not None:
            for text in legend.get_texts():
                text.set_color(s["text"])
