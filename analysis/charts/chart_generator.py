"""
通用统计图表生成器 — 12 种图表（分批交付，D1 前 6 种）
"""

from typing import List, OrderedDict
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from scipy import stats as sp_stats
from scipy.interpolate import griddata
from output.chart_engine import (
    create_histogram, create_pareto_chart,
    _ensure_font,
)
from output import chart_style
from analysis.charts.heatmap import (
    create_correlation_heatmap, create_scatter_matrix,
)
from analysis.charts.faceting import (
    create_small_multiples,
)
from config.settings import (
    CHART_DPI, FONT_SIZE_TITLE, FONT_SIZE_LABEL, FONT_SIZE_TICK,
    get_effective,
)

# 命名调色板（UI 下拉保留原名；全部取自统一色盲友好序列的组合）
_CHART_PALETTES = {
    "专业蓝": chart_style.palette(),
    "暖色调": ["#E69F00", "#D55E00", "#F0E442", "#CC79A7", "#0072B2"],
    "自然色": ["#009E73", "#56B4E9", "#0072B2", "#E69F00", "#CC79A7"],
    "质感灰": ["#6e7080", "#a0a3ae", "#5a5c6a", "#c9ccd4", "#8a8c96"],
}

def _dpi():
    return get_effective("chart_dpi", CHART_DPI)


def _apply_dark_theme(dark: bool = True):
    """兼容入口 — 统一走 output.chart_style（dark/light 双主题）。"""
    chart_style.apply_chart_style(
        chart_style.THEME_DARK if dark else chart_style.THEME_LIGHT)


def _get_palette(palette_name: str = "专业蓝") -> List[str]:
    return _CHART_PALETTES.get(palette_name, _CHART_PALETTES["专业蓝"])


CHART_TYPES = [
    "直方图", "箱线图", "散点图", "帕累托图", "概率图", "矩阵图", "散点矩阵图",
    "残差图", "主效应图", "交互效应图", "等值线图", "3D曲面图", "时间序列图",
    "气泡图", "雷达图", "瀑布图", "小多图",
]

CHART_CONFIGS = OrderedDict([
    ("直方图", [("数值列", "numeric")]),
    ("箱线图", [("数值列(可多选)", "multi_numeric")]),
    ("散点图", [("X 轴列", "numeric"), ("Y 轴列", "numeric")]),
    ("帕累托图", [("分类列", "text"), ("数值列", "numeric")]),
    ("概率图", [("数值列", "numeric")]),
    ("矩阵图", [("数值列(可多选)", "multi_numeric")]),
    ("散点矩阵图", [("数值列(可多选)", "multi_numeric")]),
    ("残差图", [("实际值列", "numeric"), ("预测值列", "numeric")]),
    ("主效应图", [("因子列(可多选)", "multi_text"), ("响应列", "numeric")]),
    ("交互效应图", [("因子1", "text"), ("因子2", "text"), ("响应列", "numeric")]),
    ("等值线图", [("X 因子", "numeric"), ("Y 因子", "numeric"), ("响应列", "numeric")]),
    ("3D曲面图", [("X 因子", "numeric"), ("Y 因子", "numeric"), ("响应列", "numeric")]),
    ("时间序列图", [("日期列", "datetime"), ("数值列", "numeric")]),
    ("气泡图", [("X 轴列", "numeric"), ("Y 轴列", "numeric"), ("气泡大小列", "numeric")]),
    ("雷达图", [("分类列", "text"), ("数值列(可多选)", "multi_numeric")]),
    ("瀑布图", [("分类列", "text"), ("数值列", "numeric")]),
    ("小多图", [("数值列", "numeric"), ("分组列", "text")]),
])


def _build_summary(data: pd.DataFrame, columns: List[str]) -> str:
    lines = []
    for col in columns:
        if col not in data.columns:
            continue
        series = pd.to_numeric(data[col], errors="coerce").dropna()
        if len(series) == 0:
            continue
        lines.append(f"● {col}")
        lines.append(f"  N={len(series):,}  μ={series.mean():.4f}  σ={series.std():.4f}")
        lines.append(f"  Min={series.min():.4f}  Q1={series.quantile(0.25):.4f}  "
                     f"Med={series.median():.4f}  Q3={series.quantile(0.75):.4f}  "
                     f"Max={series.max():.4f}")
    return "\n".join(lines)


def _build_histogram(data: dict, options: dict) -> Figure:
    df = data.get("df")
    col = data.get("columns", [None])[0]
    if df is None or col is None or col not in df.columns:
        fig, ax = plt.subplots(figsize=(8, 5), dpi=_dpi())
        ax.text(0.5, 0.5, "请选择数值列", ha="center", va="center", fontsize=14)
        return fig
    series = pd.to_numeric(df[col], errors="coerce").dropna()
    chart_opts = options.get("chart_options", {})
    fig = create_histogram(series.values, title=options.get("title", col), options=chart_opts)
    _apply_figure_palette(fig, options.get("palette", "专业蓝"))
    _apply_figure_theme(fig, options)
    return fig


def _build_boxplot(data: dict, options: dict) -> Figure:
    df = data.get("df")
    cols = data.get("columns", [])
    if df is None or not cols:
        fig, ax = plt.subplots(figsize=(8, 5), dpi=_dpi())
        ax.text(0.5, 0.5, "请选择数值列", ha="center", va="center", fontsize=14)
        return fig
    chart_opts = options.get("chart_options", {})
    label_fontsize = chart_opts.get("label_fontsize", FONT_SIZE_TICK)
    show_grid = chart_opts.get("show_grid", True)
    show_mean = chart_opts.get("show_mean", True)
    fig, ax = plt.subplots(figsize=(max(7, len(cols) * 2), 5), dpi=_dpi())
    values = [pd.to_numeric(df[c], errors="coerce").dropna().values for c in cols if c in df.columns]
    labels = [c for c in cols if c in df.columns]
    s = chart_style.semantic()
    bp = ax.boxplot(values, patch_artist=True,
                    medianprops={"color": s["text"], "linewidth": 1.5},
                    boxprops={"edgecolor": s["axis"]},
                    whiskerprops={"color": s["axis"]},
                    capprops={"color": s["axis"]})
    ax.set_xticklabels(labels, fontsize=label_fontsize)
    for patch, color in zip(bp["boxes"], chart_style.palette(len(values)),
                            strict=True):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)
    if show_mean:
        for i, vals in enumerate(values, start=1):
            if len(vals):
                ax.plot(i, np.mean(vals), marker="o", markersize=5,
                        color=s["limit"], alpha=0.9, zorder=3)
    ax.set_title(options.get("title", "箱线图"), fontsize=FONT_SIZE_TITLE, fontweight="bold")
    ax.set_ylabel("数值", fontsize=label_fontsize)
    chart_style.style_axes(ax, grid="y" if show_grid else None)
    chart_style.smart_ylim(ax, *values, include_zero=False)
    chart_style.finalize_figure(fig)
    return fig


def _build_scatter(data: dict, options: dict) -> Figure:
    df = data.get("df")
    cols = data.get("columns", [None, None])
    if df is None or len(cols) < 2 or cols[0] not in df.columns or cols[1] not in df.columns:
        fig, ax = plt.subplots(figsize=(8, 5), dpi=_dpi())
        ax.text(0.5, 0.5, "请选择 X 和 Y 轴列", ha="center", va="center", fontsize=14)
        return fig
    x = pd.to_numeric(df[cols[0]], errors="coerce").dropna()
    y = pd.to_numeric(df[cols[1]], errors="coerce").dropna()
    common = x.index.intersection(y.index)
    x, y = x.loc[common], y.loc[common]
    if len(x) < 3:
        fig, ax = plt.subplots(figsize=(8, 5), dpi=_dpi())
        ax.text(0.5, 0.5, "数据点不足", ha="center", va="center", fontsize=14)
        return fig
    palette = _get_palette(options.get("palette", "专业蓝"))
    chart_opts = options.get("chart_options", {})
    show_reg = chart_opts.get("show_regression", options.get("show_regression", True))
    point_size = chart_opts.get("point_size", 50)
    point_alpha = chart_opts.get("point_alpha", 0.6)
    fig, ax = plt.subplots(figsize=(8, 6), dpi=_dpi())
    ax.scatter(x, y, s=point_size, alpha=point_alpha,
               edgecolors=chart_style.semantic()["panel"], linewidth=0.4,
               color=palette[0])
    if show_reg:
        slope, intercept, r_val, _p_val, _std_err = sp_stats.linregress(x, y)
        x_line = np.linspace(x.min(), x.max(), 100)
        ax.plot(x_line, slope * x_line + intercept,
                color=chart_style.semantic()["fit"], linewidth=1.8,
                label=f"y={slope:.3f}x+{intercept:.3f}  R²={r_val**2:.4f}")
        ax.legend(fontsize=9)
    ax.set_xlabel(cols[0], fontsize=FONT_SIZE_LABEL)
    ax.set_ylabel(cols[1], fontsize=FONT_SIZE_LABEL)
    ax.set_title(options.get("title", f"{cols[0]} vs {cols[1]}"),
                 fontsize=FONT_SIZE_TITLE, fontweight="bold")
    chart_style.style_axes(ax, grid="y", legend=True)
    chart_style.finalize_figure(fig)
    return fig


def _build_pareto(data: dict, options: dict) -> Figure:
    df = data.get("df")
    cols = data.get("columns", [None, None])
    if df is None or len(cols) < 2 or cols[0] not in df.columns or cols[1] not in df.columns:
        fig, ax = plt.subplots(figsize=(8, 5), dpi=_dpi())
        ax.text(0.5, 0.5, "请选择分类列和数值列", ha="center", va="center", fontsize=14)
        return fig
    cat_col, val_col = cols[0], cols[1]
    df = df.copy()
    vals = pd.to_numeric(df[val_col], errors="coerce")
    grouped = df.groupby(cat_col)[vals.name if isinstance(vals, pd.Series) else val_col].sum()
    labels = grouped.index.tolist()
    values = grouped.values.tolist()
    chart_opts = options.get("chart_options", {})
    fig = create_pareto_chart(labels, values, title=options.get("title", "帕累托图"), options=chart_opts)
    _apply_figure_palette(fig, options.get("palette", "专业蓝"))
    _apply_figure_theme(fig, options)
    return fig


def _build_probplot(data: dict, options: dict) -> Figure:
    df = data.get("df")
    cols = data.get("columns", [None])
    if df is None or cols[0] not in df.columns:
        fig, ax = plt.subplots(figsize=(8, 5), dpi=_dpi())
        ax.text(0.5, 0.5, "请选择数值列", ha="center", va="center", fontsize=14)
        return fig
    series = pd.to_numeric(df[cols[0]], errors="coerce").dropna()
    if len(series) < 4:
        fig, ax = plt.subplots(figsize=(8, 5), dpi=_dpi())
        ax.text(0.5, 0.5, "数据点不足", ha="center", va="center", fontsize=14)
        return fig
    fig, ax = plt.subplots(figsize=(8, 6), dpi=_dpi())
    sp_stats.probplot(series.values, dist="norm", plot=ax)
    ax.get_lines()[1].set_color(chart_style.semantic()["fit"])
    ax.get_lines()[1].set_linewidth(1.5)
    ax.get_lines()[0].set_markerfacecolor(chart_style.semantic()["data"])
    ax.get_lines()[0].set_markeredgecolor(chart_style.semantic()["panel"])
    ax.get_lines()[0].set_markersize(5)
    ax.set_title(options.get("title", f"{cols[0]} — 概率图"),
                 fontsize=FONT_SIZE_TITLE, fontweight="bold")
    ax.set_xlabel("理论分位数", fontsize=FONT_SIZE_LABEL)
    ax.set_ylabel("观测分位数", fontsize=FONT_SIZE_LABEL)
    ax.grid(True, alpha=0.3)
    _apply_figure_palette(fig, options.get("palette", "专业蓝"))
    fig.tight_layout()
    return fig


def _build_matrix(data: dict, options: dict) -> Figure:
    df = data.get("df")
    cols = data.get("columns", [])
    if df is None or not cols:
        fig, ax = plt.subplots(figsize=(8, 5), dpi=_dpi())
        ax.text(0.5, 0.5, "请选择至少 2 个数值列", ha="center", va="center", fontsize=14)
        return fig
    valid_cols = [c for c in cols if c in df.columns]
    if len(valid_cols) < 2:
        fig, ax = plt.subplots(figsize=(8, 5), dpi=_dpi())
        ax.text(0.5, 0.5, "至少需要 2 个数值列", ha="center", va="center", fontsize=14)
        return fig
    fig = create_correlation_heatmap(df, numeric_cols=valid_cols,
                                     title=options.get("title", "相关矩阵热力图"),
                                     options=options.get("chart_options", {}))
    _apply_figure_palette(fig, options.get("palette", "专业蓝"))
    _apply_figure_theme(fig, options)
    return fig


def _build_scatter_matrix(data: dict, options: dict) -> Figure:
    df = data.get("df")
    cols = data.get("columns", [])
    if df is None or not cols:
        fig, ax = plt.subplots(figsize=(8, 5), dpi=_dpi())
        ax.text(0.5, 0.5, "请选择至少 2 个数值列", ha="center", va="center", fontsize=14)
        return fig
    valid_cols = [c for c in cols if c in df.columns]
    if len(valid_cols) < 2:
        fig, ax = plt.subplots(figsize=(8, 5), dpi=_dpi())
        ax.text(0.5, 0.5, "至少需要 2 个数值列", ha="center", va="center", fontsize=14)
        return fig
    fig = create_scatter_matrix(df, numeric_cols=valid_cols,
                                title=options.get("title", "散点矩阵图"),
                                options=options.get("chart_options", {}))
    _apply_figure_palette(fig, options.get("palette", "专业蓝"))
    _apply_figure_theme(fig, options)
    return fig


def _build_faceting(data: dict, options: dict) -> Figure:
    """小多图：数值列 + 分组列 → 每组分面子图"""
    df = data.get("df")
    cols = data.get("columns", [])
    if df is None or len(cols) < 2:
        fig, ax = plt.subplots(figsize=(8, 5), dpi=_dpi())
        ax.text(0.5, 0.5, "请选择数值列和分组列", ha="center", va="center", fontsize=14)
        return fig
    value_col, group_col = cols[0], cols[1]
    palette = _get_palette(options.get("palette", "专业蓝"))
    chart_opts = dict(options.get("chart_options", {}))
    chart_opts.setdefault("color", palette[0])
    fig = create_small_multiples(df, value_col, group_col,
                                 title=options.get("title", "小多图"),
                                 options=chart_opts)
    _apply_figure_theme(fig, options)
    return fig


def _build_residual(data: dict, options: dict) -> Figure:
    df = data.get("df")
    cols = data.get("columns", [])
    if df is None or len(cols) < 2 or cols[0] not in df.columns or cols[1] not in df.columns:
        fig, ax = plt.subplots(figsize=(8, 5), dpi=_dpi())
        ax.text(0.5, 0.5, "请选择实际值列和预测值列", ha="center", va="center", fontsize=14)
        return fig
    actual_col, pred_col = cols[0], cols[1]
    actual = pd.to_numeric(df[actual_col], errors="coerce")
    pred = pd.to_numeric(df[pred_col], errors="coerce")
    common = actual.index.intersection(pred.index)
    actual, pred = actual.loc[common], pred.loc[common]
    if len(actual) < 3:
        fig, ax = plt.subplots(figsize=(8, 5), dpi=_dpi())
        ax.text(0.5, 0.5, "数据点不足", ha="center", va="center", fontsize=14)
        return fig
    residuals = actual - pred
    palette = _get_palette(options.get("palette", "专业蓝"))
    chart_opts = options.get("chart_options", {})
    point_size = chart_opts.get("point_size", 50)
    point_alpha = chart_opts.get("point_alpha", 0.6)
    show_grid = chart_opts.get("show_grid", True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), dpi=_dpi())
    ax1 = axes[0]
    ax1.scatter(pred, residuals, s=point_size, alpha=point_alpha,
                edgecolors="white", linewidth=0.3, color=palette[0])
    ax1.axhline(y=0, color="red", linestyle="--", linewidth=1)
    ax1.set_xlabel("预测值", fontsize=FONT_SIZE_LABEL)
    ax1.set_ylabel("残差", fontsize=FONT_SIZE_LABEL)
    ax1.set_title("残差 vs 拟合值", fontsize=FONT_SIZE_TITLE - 2)
    if show_grid:
        ax1.grid(True, alpha=0.3)
    ax2 = axes[1]
    ax2.hist(residuals, bins=min(30, max(5, len(residuals)//5)), color=palette[0], alpha=0.7, edgecolor="white")
    ax2.axvline(x=0, color="red", linestyle="--", linewidth=1)
    ax2.set_xlabel("残差", fontsize=FONT_SIZE_LABEL)
    ax2.set_ylabel("频次", fontsize=FONT_SIZE_LABEL)
    ax2.set_title("残差分布", fontsize=FONT_SIZE_TITLE - 2)
    if show_grid:
        ax2.grid(True, alpha=0.3, axis="y")
    fig.suptitle(options.get("title", "残差分析图"), fontsize=FONT_SIZE_TITLE, fontweight="bold")
    fig.tight_layout()
    return fig


def _build_main_effects(data: dict, options: dict) -> Figure:
    df = data.get("df")
    multi = data.get("multi_columns", {})
    factor_cols = multi.get("multi_text", [])
    cols = data.get("columns", [])
    response_col = None
    for c in cols:
        if c not in factor_cols and c in df.columns if df is not None else False:
            response_col = c
            break
    if response_col is None and df is not None:
        for c in df.columns:
            if c not in factor_cols and pd.to_numeric(df[c], errors="coerce").notna().sum() > 5:
                response_col = c
                break
    if df is None or not factor_cols or response_col is None:
        fig, ax = plt.subplots(figsize=(8, 5), dpi=_dpi())
        ax.text(0.5, 0.5, "请选择因子列和响应列", ha="center", va="center", fontsize=14)
        return fig
    palette = _get_palette(options.get("palette", "专业蓝"))
    n = len(factor_cols)
    fig, axes = plt.subplots(1, n, figsize=(5 * n, 4), dpi=_dpi())
    if n == 1:
        axes = [axes]
    response = pd.to_numeric(df[response_col], errors="coerce")
    overall_mean = response.mean()
    for ax, factor in zip(axes, factor_cols, strict=True):
        means = df.groupby(factor)[response.name].mean().sort_index()
        ax.plot(range(len(means)), means.values, "o-", color=palette[0], linewidth=2, markersize=8)
        ax.axhline(y=overall_mean, color="red", linestyle="--", linewidth=0.8, label="整体均值")
        ax.set_xticks(range(len(means)))
        ax.set_xticklabels(means.index, fontsize=FONT_SIZE_TICK)
        ax.set_xlabel(factor, fontsize=FONT_SIZE_LABEL)
        ax.set_ylabel("均值", fontsize=FONT_SIZE_LABEL)
        ax.set_title(f"主效应: {factor}", fontsize=FONT_SIZE_TITLE - 2)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
    fig.suptitle(options.get("title", "主效应图"), fontsize=FONT_SIZE_TITLE, fontweight="bold")
    fig.tight_layout()
    return fig


def _build_interaction(data: dict, options: dict) -> Figure:
    df = data.get("df")
    cols = data.get("columns", [None, None, None])
    if df is None or len(cols) < 3 or any(c not in df.columns for c in cols[:3]):
        fig, ax = plt.subplots(figsize=(8, 5), dpi=_dpi())
        ax.text(0.5, 0.5, "请选择因子1、因子2和响应列", ha="center", va="center", fontsize=14)
        return fig
    f1, f2, resp = cols[0], cols[1], cols[2]
    palette = _get_palette(options.get("palette", "专业蓝"))
    response = pd.to_numeric(df[resp], errors="coerce")
    means = df.groupby([f1, f2])[response.name].mean().unstack()
    fig, ax = plt.subplots(figsize=(8, 5), dpi=_dpi())
    for i, col in enumerate(means.columns):
        c = palette[i % len(palette)]
        ax.plot(range(len(means)), means[col].values, "o-", color=c, linewidth=2, markersize=8, label=str(col))
    ax.set_xticks(range(len(means)))
    ax.set_xticklabels(means.index, fontsize=FONT_SIZE_TICK)
    ax.set_xlabel(f1, fontsize=FONT_SIZE_LABEL)
    ax.set_ylabel("均值", fontsize=FONT_SIZE_LABEL)
    ax.set_title(f"交互效应: {f1} × {f2}", fontsize=FONT_SIZE_TITLE, fontweight="bold")
    ax.legend(title=f2, fontsize=8)
    ax.grid(True, alpha=0.3)
    if options.get("title"):
        fig.suptitle(options["title"], fontsize=FONT_SIZE_TITLE - 2)
    fig.tight_layout()
    return fig


def _build_contour(data: dict, options: dict) -> Figure:
    df = data.get("df")
    cols = data.get("columns", [None, None, None])
    if df is None or len(cols) < 3 or any(c not in df.columns for c in cols[:3]):
        fig, ax = plt.subplots(figsize=(8, 5), dpi=_dpi())
        ax.text(0.5, 0.5, "请选择 X 因子、Y 因子和响应列", ha="center", va="center", fontsize=14)
        return fig
    x_col, y_col, resp = cols[0], cols[1], cols[2]
    x = pd.to_numeric(df[x_col], errors="coerce")
    y = pd.to_numeric(df[y_col], errors="coerce")
    z = pd.to_numeric(df[resp], errors="coerce")
    mask = x.notna() & y.notna() & z.notna()
    x, y, z = x[mask], y[mask], z[mask]
    if len(x) < 4:
        fig, ax = plt.subplots(figsize=(8, 5), dpi=_dpi())
        ax.text(0.5, 0.5, "数据点不足", ha="center", va="center", fontsize=14)
        return fig

    coords = np.column_stack([x.values, y.values])
    _, unique_idx = np.unique(coords, axis=0, return_index=True)
    x_u, y_u, z_u = x.values[unique_idx], y.values[unique_idx], z.values[unique_idx]

    fig, ax = plt.subplots(figsize=(8, 6), dpi=_dpi())
    xi = np.linspace(x.min(), x.max(), 50)
    yi = np.linspace(y.min(), y.max(), 50)
    X, Y = np.meshgrid(xi, yi)
    try:
        Z = griddata((x_u, y_u), z_u, (X, Y), method="cubic")
    except Exception:
        Z = griddata((x_u, y_u), z_u, (X, Y), method="linear")
    contour = ax.contourf(X, Y, Z, levels=20, cmap="RdYlBu_r")
    fig.colorbar(contour, ax=ax, label=resp)
    ax.scatter(x, y, c="black", s=20, alpha=0.5, edgecolors="white")
    ax.set_xlabel(x_col, fontsize=FONT_SIZE_LABEL)
    ax.set_ylabel(y_col, fontsize=FONT_SIZE_LABEL)
    ax.set_title(options.get("title", f"等值线图: {resp}"), fontsize=FONT_SIZE_TITLE, fontweight="bold")
    fig.tight_layout()
    return fig


def _build_surface_3d(data: dict, options: dict) -> Figure:
    df = data.get("df")
    cols = data.get("columns", [None, None, None])
    if df is None or len(cols) < 3 or any(c not in df.columns for c in cols[:3]):
        fig, ax = plt.subplots(figsize=(8, 5), dpi=_dpi())
        ax.text(0.5, 0.5, "请选择 X 因子、Y 因子和响应列", ha="center", va="center", fontsize=14)
        return fig
    x_col, y_col, resp = cols[0], cols[1], cols[2]
    x = pd.to_numeric(df[x_col], errors="coerce")
    y = pd.to_numeric(df[y_col], errors="coerce")
    z = pd.to_numeric(df[resp], errors="coerce")
    mask = x.notna() & y.notna() & z.notna()
    x, y, z = x[mask], y[mask], z[mask]
    if len(x) < 4:
        fig, ax = plt.subplots(figsize=(8, 5), dpi=_dpi())
        ax.text(0.5, 0.5, "数据点不足", ha="center", va="center", fontsize=14)
        return fig

    coords = np.column_stack([x.values, y.values])
    _, unique_idx = np.unique(coords, axis=0, return_index=True)
    x_u, y_u, z_u = x.values[unique_idx], y.values[unique_idx], z.values[unique_idx]

    fig = plt.figure(figsize=(10, 7), dpi=_dpi())
    ax = fig.add_subplot(111, projection="3d")
    xi = np.linspace(x.min(), x.max(), 30)
    yi = np.linspace(y.min(), y.max(), 30)
    X, Y = np.meshgrid(xi, yi)
    try:
        Z = griddata((x_u, y_u), z_u, (X, Y), method="cubic")
    except Exception:
        Z = griddata((x_u, y_u), z_u, (X, Y), method="linear")
    surf = ax.plot_surface(X, Y, Z, cmap="RdYlBu_r", alpha=0.8, linewidth=0, antialiased=True)
    fig.colorbar(surf, ax=ax, shrink=0.5, aspect=10, label=resp)
    ax.scatter(x, y, z, c="black", s=30, alpha=0.6)
    ax.set_xlabel(x_col, fontsize=FONT_SIZE_LABEL)
    ax.set_ylabel(y_col, fontsize=FONT_SIZE_LABEL)
    ax.set_zlabel(resp, fontsize=FONT_SIZE_LABEL)
    ax.set_title(options.get("title", f"3D 曲面图: {resp}"), fontsize=FONT_SIZE_TITLE, fontweight="bold")
    fig.tight_layout()
    return fig


def _build_time_series(data: dict, options: dict) -> Figure:
    df = data.get("df")
    cols = data.get("columns", [None, None])
    if df is None or len(cols) < 2 or cols[0] not in df.columns or cols[1] not in df.columns:
        fig, ax = plt.subplots(figsize=(8, 5), dpi=_dpi())
        ax.text(0.5, 0.5, "请选择日期列和数值列", ha="center", va="center", fontsize=14)
        return fig
    date_col, val_col = cols[0], cols[1]
    dates = pd.to_datetime(df[date_col], errors="coerce")
    values = pd.to_numeric(df[val_col], errors="coerce")
    mask = dates.notna() & values.notna()
    dates, values = dates[mask], values[mask]
    sorted_idx = np.argsort(dates)
    dates, values = dates.iloc[sorted_idx], values.iloc[sorted_idx]
    if len(dates) < 3:
        fig, ax = plt.subplots(figsize=(8, 5), dpi=_dpi())
        ax.text(0.5, 0.5, "数据点不足", ha="center", va="center", fontsize=14)
        return fig
    palette = _get_palette(options.get("palette", "专业蓝"))
    fig, ax = plt.subplots(figsize=(12, 5), dpi=_dpi())
    ax.plot(dates, values, "o-", color=palette[0], linewidth=1.5, markersize=4)
    ax.fill_between(dates, values, alpha=0.1, color=palette[0])
    ax.set_xlabel(date_col, fontsize=FONT_SIZE_LABEL)
    ax.set_ylabel(val_col, fontsize=FONT_SIZE_LABEL)
    ax.set_title(options.get("title", f"{val_col} 时间序列"), fontsize=FONT_SIZE_TITLE, fontweight="bold")
    chart_style.style_axes(ax, grid="y")
    chart_style.smart_ylim(ax, values)
    fig.autofmt_xdate()
    fig.tight_layout()
    return fig


def _build_bubble(data: dict, options: dict) -> Figure:
    df = data.get("df")
    cols = data.get("columns", [None, None, None])
    if df is None or len(cols) < 3 or any(c not in df.columns for c in cols[:3]):
        fig, ax = plt.subplots(figsize=(8, 5), dpi=_dpi())
        ax.text(0.5, 0.5, "请选择 X/Y/大小列", ha="center", va="center", fontsize=14)
        return fig
    x_col, y_col, s_col = cols[0], cols[1], cols[2]
    x = pd.to_numeric(df[x_col], errors="coerce")
    y = pd.to_numeric(df[y_col], errors="coerce")
    s = pd.to_numeric(df[s_col], errors="coerce")
    mask = x.notna() & y.notna() & s.notna()
    x, y, s = x[mask], y[mask], s[mask]
    if len(x) < 2:
        fig, ax = plt.subplots(figsize=(8, 5), dpi=_dpi())
        ax.text(0.5, 0.5, "数据点不足", ha="center", va="center", fontsize=14)
        return fig
    palette = _get_palette(options.get("palette", "专业蓝"))
    fig, ax = plt.subplots(figsize=(9, 6), dpi=_dpi())
    sizes = (s - s.min()) / (s.max() - s.min() + 0.001) * 400 + 20
    ax.scatter(x, y, s=sizes, alpha=0.55, c=palette[0],
                         edgecolors="white", linewidth=0.5)
    ax.set_xlabel(x_col, fontsize=FONT_SIZE_LABEL)
    ax.set_ylabel(y_col, fontsize=FONT_SIZE_LABEL)
    ax.set_title(options.get("title", f"气泡图: {x_col} vs {y_col}"),
                 fontsize=FONT_SIZE_TITLE, fontweight="bold")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig


def _build_radar(data: dict, options: dict) -> Figure:
    df = data.get("df")
    multi = data.get("multi_columns", {})
    val_cols = multi.get("multi_numeric", data.get("columns", []))
    cat_col = None
    for c in data.get("columns", []):
        if c not in val_cols and c in (df.columns if df is not None else []):
            cat_col = c
            break
    if df is None or not val_cols:
        fig, ax = plt.subplots(figsize=(8, 5), dpi=_dpi())
        ax.text(0.5, 0.5, "请选择至少 2 个数值列", ha="center", va="center", fontsize=14)
        return fig
    valid_cols = [c for c in val_cols if c in df.columns]
    if len(valid_cols) < 2:
        fig, ax = plt.subplots(figsize=(8, 5), dpi=_dpi())
        ax.text(0.5, 0.5, "至少需要 2 个数值列", ha="center", va="center", fontsize=14)
        return fig
    palette = _get_palette(options.get("palette", "专业蓝"))
    fig, ax = plt.subplots(figsize=(8, 7), dpi=_dpi(), subplot_kw=dict(polar=True))
    n = len(valid_cols)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    angles += angles[:1]

    if cat_col and cat_col in df.columns:
        groups = df[cat_col].unique()[:len(palette)]
        for gi, g in enumerate(groups):
            gdf = df[df[cat_col] == g]
            vals = [pd.to_numeric(gdf[c], errors="coerce").mean() for c in valid_cols]
            vals += vals[:1]
            ax.fill(angles, vals, alpha=0.15, color=palette[gi])
            ax.plot(angles, vals, "o-", linewidth=2, color=palette[gi], label=str(g))
        ax.legend(fontsize=8, loc="upper right", bbox_to_anchor=(1.2, 1.1))
    else:
        vals = [pd.to_numeric(df[c], errors="coerce").mean() for c in valid_cols]
        vals += vals[:1]
        ax.fill(angles, vals, alpha=0.2, color=palette[0])
        ax.plot(angles, vals, "o-", linewidth=2, color=palette[0])

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(valid_cols, fontsize=FONT_SIZE_TICK)
    ax.set_title(options.get("title", "雷达图"), fontsize=FONT_SIZE_TITLE, fontweight="bold", pad=20)
    ax.set_facecolor(chart_style.semantic()["panel"])
    chart_style.finalize_figure(fig)
    return fig


def _build_waterfall(data: dict, options: dict) -> Figure:
    df = data.get("df")
    cols = data.get("columns", [None, None])
    if df is None or len(cols) < 2 or cols[0] not in df.columns or cols[1] not in df.columns:
        fig, ax = plt.subplots(figsize=(9, 5), dpi=_dpi())
        ax.text(0.5, 0.5, "请选择分类列和数值列", ha="center", va="center", fontsize=14)
        return fig
    cat_col, val_col = cols[0], cols[1]
    vals = pd.to_numeric(df[val_col], errors="coerce")
    labels = df[cat_col].astype(str).tolist()
    valid = vals.notna()
    vals = vals[valid].values
    labels = [labels[i] for i in np.flatnonzero(valid.values)]
    if len(vals) < 2:
        fig, ax = plt.subplots(figsize=(9, 5), dpi=_dpi())
        ax.text(0.5, 0.5, "数据点不足", ha="center", va="center", fontsize=14)
        return fig
    palette = _get_palette(options.get("palette", "专业蓝"))
    s = chart_style.semantic()
    fig, ax = plt.subplots(figsize=(max(10, len(vals) * 1.2), 5), dpi=_dpi())

    bottom = 0.0
    for i, (_lbl, v) in enumerate(zip(labels, vals, strict=True)):
        color = palette[0] if v >= 0 else s["limit"]
        ax.bar(i, v, bottom=bottom, color=color, alpha=0.8,
               edgecolor=s["panel"], linewidth=0.5)
        if i > 0:
            ax.plot([i - 1, i], [bottom, bottom], linewidth=0.8, color=s["axis"])
        bottom += v

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=FONT_SIZE_TICK, rotation=30, ha="right")
    ax.set_ylabel(val_col, fontsize=FONT_SIZE_LABEL)
    ax.set_title(options.get("title", "瀑布图"), fontsize=FONT_SIZE_TITLE, fontweight="bold")
    ax.axhline(y=0, color=s["text_muted"], linewidth=0.8)
    chart_style.style_axes(ax, grid="y")
    chart_style.finalize_figure(fig)
    return fig


def _apply_figure_palette(fig: Figure, palette_name: str):
    """后置应用调色板到图表元素 (对 histogram/pareto/probplot/matrix 生效)"""
    palette = _get_palette(palette_name)
    for ax in fig.get_axes():
        for container in ax.containers:
            for patch in container.patches:
                patch.set_facecolor(palette[0])
                patch.set_alpha(0.75)
        for line in ax.get_lines():
            if line.get_marker() != 'None' and len(ax.get_lines()) > 1:
                line.set_markerfacecolor(palette[0])
                line.set_markeredgecolor(palette[1])
            elif len(ax.get_lines()) == 1 or line.get_linestyle() != '--':
                line.set_color(palette[0])
        for patch in ax.patches:
            if hasattr(patch, 'set_facecolor') and not hasattr(patch, 'get_height'):
                pass


def _apply_figure_theme(fig: Figure, options: dict):
    """后置主题（dark/light）— 统一走 output.chart_style。"""
    theme = (chart_style.THEME_DARK if options.get("dark_mode", True)
             else chart_style.THEME_LIGHT)
    chart_style.style_for_export(fig, theme=theme)


def _build_acf(data: dict, options: dict) -> Figure:
    """ACF 自相关函数图"""
    acf_data = data.get("acf", {})
    acf_vals = acf_data.get("acf_values", [])
    conf_lower = acf_data.get("confidence_lower", [])
    conf_upper = acf_data.get("confidence_upper", [])
    n_lags = len(acf_vals)

    fig, ax = plt.subplots(figsize=(8, 4), dpi=_dpi())
    lags_x = list(range(n_lags))
    ax.bar(lags_x, acf_vals, color="#4da6ff", width=0.6, alpha=0.8, label="ACF")
    if conf_lower and conf_upper:
        ax.fill_between(lags_x, conf_lower[:n_lags], conf_upper[:n_lags],
                        color="#4da6ff", alpha=0.15, label="置信区间")
    ax.axhline(y=0, color="#e1e2e6", linewidth=0.8)
    ax.set_xlabel("滞后阶数", fontsize=FONT_SIZE_LABEL)
    ax.set_ylabel("自相关系数", fontsize=FONT_SIZE_LABEL)
    ax.set_title("ACF 自相关函数", fontsize=FONT_SIZE_TITLE)
    ax.legend(fontsize=FONT_SIZE_TICK)
    fig.tight_layout()
    return fig


def _build_pacf(data: dict, options: dict) -> Figure:
    """PACF 偏自相关函数图"""
    pacf_data = data.get("pacf", {})
    pacf_vals = pacf_data.get("pacf_values", [])
    conf_lower = pacf_data.get("confidence_lower", [])
    conf_upper = pacf_data.get("confidence_upper", [])
    n_lags = len(pacf_vals)

    fig, ax = plt.subplots(figsize=(8, 4), dpi=_dpi())
    lags_x = list(range(n_lags))
    ax.bar(lags_x, pacf_vals, color="#e74c3c", width=0.6, alpha=0.8, label="PACF")
    if conf_lower and conf_upper:
        ax.fill_between(lags_x, conf_lower[:n_lags], conf_upper[:n_lags],
                        color="#e74c3c", alpha=0.15, label="置信区间")
    ax.axhline(y=0, color="#e1e2e6", linewidth=0.8)
    ax.set_xlabel("滞后阶数", fontsize=FONT_SIZE_LABEL)
    ax.set_ylabel("偏自相关系数", fontsize=FONT_SIZE_LABEL)
    ax.set_title("PACF 偏自相关函数", fontsize=FONT_SIZE_TITLE)
    ax.legend(fontsize=FONT_SIZE_TICK)
    fig.tight_layout()
    return fig


def _build_acf_pacf(data: dict, options: dict) -> Figure:
    """ACF/PACF 组合双子图"""
    acf_data = data.get("acf", {})
    pacf_data = data.get("pacf", {})
    acf_vals = acf_data.get("acf_values", [])
    pacf_vals = pacf_data.get("pacf_values", [])
    acf_cl = acf_data.get("confidence_lower", [])
    acf_cu = acf_data.get("confidence_upper", [])
    pacf_cl = pacf_data.get("confidence_lower", [])
    pacf_cu = pacf_data.get("confidence_upper", [])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 4), dpi=_dpi())
    n1 = len(acf_vals)
    n2 = len(pacf_vals)

    ax1.bar(range(n1), acf_vals, color="#4da6ff", width=0.6, alpha=0.8)
    if acf_cl and acf_cu:
        ax1.fill_between(range(n1), acf_cl[:n1], acf_cu[:n1], color="#4da6ff", alpha=0.15)
    ax1.axhline(y=0, color="#e1e2e6", linewidth=0.8)
    ax1.set_title("ACF", fontsize=FONT_SIZE_TITLE)
    ax1.set_xlabel("滞后阶数", fontsize=FONT_SIZE_LABEL)

    ax2.bar(range(n2), pacf_vals, color="#e74c3c", width=0.6, alpha=0.8)
    if pacf_cl and pacf_cu:
        ax2.fill_between(range(n2), pacf_cl[:n2], pacf_cu[:n2], color="#e74c3c", alpha=0.15)
    ax2.axhline(y=0, color="#e1e2e6", linewidth=0.8)
    ax2.set_title("PACF", fontsize=FONT_SIZE_TITLE)
    ax2.set_xlabel("滞后阶数", fontsize=FONT_SIZE_LABEL)

    fig.tight_layout()
    return fig


def _build_decomposition(data: dict, options: dict) -> Figure:
    """季节性分解三子图（趋势 + 季节 + 残差）"""
    trend = data.get("trend", [])
    seasonal = data.get("seasonal", [])
    residual = data.get("residual", [])

    n = max(len(trend), len(seasonal), len(residual))
    x = list(range(n))

    fig, axes = plt.subplots(3, 1, figsize=(10, 8), dpi=_dpi(), sharex=True)

    axes[0].plot(x[:len(trend)], trend, color="#4da6ff", linewidth=1.2)
    axes[0].set_title("趋势 (Trend)", fontsize=FONT_SIZE_TITLE)
    axes[0].set_ylabel("趋势分量", fontsize=FONT_SIZE_LABEL)

    axes[1].plot(x[:len(seasonal)], seasonal, color="#27ae60", linewidth=1.2)
    axes[1].set_title("季节 (Seasonal)", fontsize=FONT_SIZE_TITLE)
    axes[1].set_ylabel("季节分量", fontsize=FONT_SIZE_LABEL)

    axes[2].plot(x[:len(residual)], residual, color="#e74c3c", linewidth=0.8, alpha=0.7)
    axes[2].axhline(y=0, color="#e1e2e6", linewidth=0.6)
    axes[2].set_title("残差 (Residual)", fontsize=FONT_SIZE_TITLE)
    axes[2].set_ylabel("残差分量", fontsize=FONT_SIZE_LABEL)
    axes[2].set_xlabel("时间步", fontsize=FONT_SIZE_LABEL)

    fig.tight_layout()
    return fig


def _build_forecast(data: dict, options: dict) -> Figure:
    """预测曲线（历史 + 预测 + 置信区间）"""
    historical = data.get("historical", [])
    forecast = data.get("forecast", [])
    conf_lower = data.get("confidence_lower", [])
    conf_upper = data.get("confidence_upper", [])

    n_hist = len(historical)
    n_fc = len(forecast)
    x_hist = list(range(n_hist))
    x_fc = list(range(n_hist, n_hist + n_fc))

    fig, ax = plt.subplots(figsize=(10, 5), dpi=_dpi())
    ax.plot(x_hist, historical, color="#4da6ff", linewidth=1.2, label="历史数据")
    if forecast:
        ax.plot(x_fc, forecast, color="#e74c3c", linewidth=1.5, linestyle="--", label="预测值")
    if conf_lower and conf_upper:
        ax.fill_between(x_fc, conf_lower, conf_upper, color="#e74c3c", alpha=0.15, label="置信区间")
    ax.axvline(x=n_hist - 0.5, color="#ffa726", linewidth=0.8, linestyle=":", alpha=0.7)
    ax.legend(fontsize=FONT_SIZE_TICK)
    ax.set_xlabel("时间步", fontsize=FONT_SIZE_LABEL)
    ax.set_ylabel("值", fontsize=FONT_SIZE_LABEL)
    ax.set_title("预测结果", fontsize=FONT_SIZE_TITLE)
    fig.tight_layout()
    return fig


def _build_qq(data: dict, options: dict) -> Figure:
    """残差 Q-Q 正态概率图"""
    theoretical = data.get("qq_theoretical", [])
    sample = data.get("qq_sample", [])
    if not theoretical or not sample:
        fig, ax = plt.subplots(figsize=(6, 6), dpi=_dpi())
        ax.text(0.5, 0.5, "无 Q-Q 数据", ha="center", va="center", fontsize=14)
        return fig

    fig, ax = plt.subplots(figsize=(6, 6), dpi=_dpi())
    ax.scatter(theoretical, sample, s=8, alpha=0.6, color="#4da6ff", label="残差分位数")
    mn = min(min(theoretical), min(sample))
    mx = max(max(theoretical), max(sample))
    ax.plot([mn, mx], [mn, mx], color="#e74c3c", linewidth=1.2, linestyle="--", label="参考线")
    ax.set_xlabel("理论分位数", fontsize=FONT_SIZE_LABEL)
    ax.set_ylabel("样本分位数", fontsize=FONT_SIZE_LABEL)
    ax.set_title("Q-Q 正态概率图", fontsize=FONT_SIZE_TITLE)
    ax.legend(fontsize=FONT_SIZE_TICK)
    fig.tight_layout()
    return fig


def _build_resid_acf_pacf(data: dict, options: dict) -> Figure:
    """残差 ACF/PACF 组合图"""
    resid_acf = data.get("resid_acf", [])
    resid_pacf = data.get("resid_pacf", [])
    n1 = len(resid_acf)
    n2 = len(resid_pacf)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 4), dpi=_dpi())

    ax1.bar(range(n1), resid_acf, color="#4da6ff", width=0.6, alpha=0.8)
    ax1.axhline(y=0, color="#e1e2e6", linewidth=0.8)
    ci = 1.96 / np.sqrt(n1) if n1 > 1 else 0.2
    ax1.axhline(y=ci, color="#ffa726", linewidth=0.6, linestyle="--", alpha=0.5)
    ax1.axhline(y=-ci, color="#ffa726", linewidth=0.6, linestyle="--", alpha=0.5)
    ax1.set_title("残差 ACF", fontsize=FONT_SIZE_TITLE)
    ax1.set_xlabel("滞后阶数", fontsize=FONT_SIZE_LABEL)

    ax2.bar(range(n2), resid_pacf, color="#e74c3c", width=0.6, alpha=0.8)
    ax2.axhline(y=0, color="#e1e2e6", linewidth=0.8)
    ci2 = 1.96 / np.sqrt(n2) if n2 > 1 else 0.2
    ax2.axhline(y=ci2, color="#ffa726", linewidth=0.6, linestyle="--", alpha=0.5)
    ax2.axhline(y=-ci2, color="#ffa726", linewidth=0.6, linestyle="--", alpha=0.5)
    ax2.set_title("残差 PACF", fontsize=FONT_SIZE_TITLE)
    ax2.set_xlabel("滞后阶数", fontsize=FONT_SIZE_LABEL)

    fig.tight_layout()
    return fig


def _build_km_curve(data: dict, options: dict) -> Figure:
    """Kaplan-Meier 生存曲线"""
    timeline = data.get("timeline", [])
    sf = data.get("survival_function", [])
    ci_lower = data.get("confidence_lower", [])
    ci_upper = data.get("confidence_upper", [])
    label = data.get("label", "KM Estimate")

    fig, ax = plt.subplots(figsize=(10, 5), dpi=_dpi())

    if timeline and sf:
        ax.step(timeline, sf, where="post", color="#4da6ff", linewidth=1.5, label=label)
        if ci_lower and ci_upper and len(ci_lower) == len(timeline):
            ax.fill_between(timeline, ci_lower, ci_upper, alpha=0.15, color="#4da6ff",
                            step="post", label="置信区间")

    ax.set_xlabel("时间", fontsize=FONT_SIZE_LABEL)
    ax.set_ylabel("生存概率 S(t)", fontsize=FONT_SIZE_LABEL)
    ax.set_title("Kaplan-Meier 生存曲线", fontsize=FONT_SIZE_TITLE)
    ax.set_ylim(-0.05, 1.05)
    ax.legend(fontsize=FONT_SIZE_TICK)
    fig.tight_layout()
    return fig


def _build_km_compare(data: dict, options: dict) -> Figure:
    """双组 Kaplan-Meier 生存曲线对比"""
    fig, ax = plt.subplots(figsize=(10, 5), dpi=_dpi())

    for key, color, lbl in [("group_a", "#4da6ff", "A"), ("group_b", "#e74c3c", "B")]:
        group = data.get(key, {})
        t = group.get("timeline", [])
        sf = group.get("survival_function", [])
        ci_l = group.get("confidence_lower", [])
        ci_u = group.get("confidence_upper", [])
        name = group.get("label", lbl)
        if t and sf:
            ax.step(t, sf, where="post", color=color, linewidth=1.5, label=name)
            if ci_l and ci_u and len(ci_l) == len(t):
                ax.fill_between(t, ci_l, ci_u, alpha=0.1, color=color, step="post")

    p_val = data.get("summary", {}).get("logrank_p_value", None)
    if p_val is not None:
        sig = "显著" if p_val < 0.05 else "不显著"
        ax.text(0.02, 0.02, f"Log-rank p={p_val:.4f} ({sig})",
                transform=ax.transAxes, fontsize=10, color="#e1e2e6")

    ax.set_xlabel("时间", fontsize=FONT_SIZE_LABEL)
    ax.set_ylabel("生存概率 S(t)", fontsize=FONT_SIZE_LABEL)
    ax.set_title("Kaplan-Meier 双组对比", fontsize=FONT_SIZE_TITLE)
    ax.set_ylim(-0.05, 1.05)
    ax.legend(fontsize=FONT_SIZE_TICK)
    fig.tight_layout()
    return fig


def _build_rbd(data: dict, options: dict) -> Figure:
    """可靠性框图可视化"""
    components = data.get("components", [])
    structure = data.get("summary", {}).get("structure", "series")
    sys_r = data.get("summary", {}).get("system_reliability", 0)

    fig, ax = plt.subplots(figsize=(max(8, len(components) * 2), 4), dpi=_dpi())
    ax.set_xlim(-0.5, len(components) + 0.5)
    ax.set_ylim(-1, 2)
    ax.axis("off")

    for i, comp in enumerate(components):
        r = comp.get("reliability", 0)
        name = comp.get("name", f"C{i+1}")
        color = "#27ae60" if r > 0.95 else "#ffa726" if r > 0.8 else "#e74c3c"

        rect = plt.Rectangle((i + 0.1, 0.3), 0.8, 1.0, facecolor=color, alpha=0.3,
                              edgecolor=color, linewidth=1.5)
        ax.add_patch(rect)
        ax.text(i + 0.5, 1.0, name, ha="center", va="center", fontsize=10, color="#e1e2e6")
        ax.text(i + 0.5, 0.6, f"R={r:.3f}", ha="center", va="center", fontsize=9, color="#a0a3ae")

        if i < len(components) - 1:
            ax.annotate("", xy=(i + 1.1, 0.8), xytext=(i + 0.9, 0.8),
                        arrowprops=dict(arrowstyle="->", color="#e1e2e6", lw=1.5))

    ax.text(0.5, -0.3, f"结构: {structure}  |  系统 R = {sys_r:.4f}",
            transform=ax.transAxes, fontsize=11, color="#e1e2e6",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#262632", edgecolor="#3a3a48"))

    fig.tight_layout()
    return fig


def _build_warranty_cost(data: dict, options: dict) -> Figure:
    """保修成本分析图"""
    summary = data.get("summary", {})
    r_warranty = summary.get("reliability_at_warranty_end", 0)
    failure_prob = summary.get("failure_probability", 0)
    expected_failures = summary.get("expected_failures", 0)
    warranty_cost = summary.get("warranty_cost_estimate", 0)
    summary.get("total_units", 0)

    chart_opts = options.get("chart_options", {})
    label_fontsize = chart_opts.get("label_fontsize", 11)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4), dpi=_dpi())

    sizes = [r_warranty, failure_prob]
    labels = [f"可靠\n{r_warranty:.1%}", f"失效\n{failure_prob:.1%}"]
    colors = ["#27ae60", "#e74c3c"]
    ax1.pie(sizes, labels=labels, colors=colors, autopct="", startangle=90,
            textprops={"fontsize": label_fontsize, "color": "#e1e2e6"})
    ax1.set_title("保修期末状态", fontsize=FONT_SIZE_TITLE)

    cost_fail = warranty_cost
    ax2.bar(["可靠产品", "失效产品"], [0, cost_fail], color=["#27ae60", "#e74c3c"], alpha=0.7)
    ax2.set_ylabel("成本", fontsize=FONT_SIZE_LABEL)
    ax2.set_title(f"保修总成本: {warranty_cost:,.0f}", fontsize=FONT_SIZE_TITLE)
    ax2.text(1, cost_fail * 0.5, f"{expected_failures:.0f} 次失效\n× {summary.get('cost_per_failure', 0)} /次",
             ha="center", va="center", fontsize=10, color="#e1e2e6")

    fig.tight_layout()
    return fig


BUILDERS = {
    "直方图": _build_histogram,
    "箱线图": _build_boxplot,
    "散点图": _build_scatter,
    "帕累托图": _build_pareto,
    "概率图": _build_probplot,
    "矩阵图": _build_matrix,
    "散点矩阵图": _build_scatter_matrix,
    "小多图": _build_faceting,
    "残差图": _build_residual,
    "主效应图": _build_main_effects,
    "交互效应图": _build_interaction,
    "等值线图": _build_contour,
    "3D曲面图": _build_surface_3d,
    "时间序列图": _build_time_series,
    "气泡图": _build_bubble,
    "雷达图": _build_radar,
    "瀑布图": _build_waterfall,
    "ACF图": _build_acf,
    "PACF图": _build_pacf,
    "ACF/PACF图": _build_acf_pacf,
    "分解图": _build_decomposition,
    "预测图": _build_forecast,
    "Q-Q图": _build_qq,
    "残差ACF/PACF图": _build_resid_acf_pacf,
    "KM生存曲线": _build_km_curve,
    "KM双组对比": _build_km_compare,
    "RBD框图": _build_rbd,
    "保修成本图": _build_warranty_cost,
}


def generate_chart(chart_type: str, data: dict, options: dict = None) -> Figure:
    _ensure_font()
    if options is None:
        options = {}
    _apply_dark_theme(options.get("dark_mode", True))
    builder = BUILDERS.get(chart_type)
    if builder is None:
        fig, ax = plt.subplots(figsize=(8, 5), dpi=_dpi())
        ax.text(0.5, 0.5, f"图表未实现: {chart_type}", ha="center", va="center", fontsize=14)
        return fig
    return builder(data, options)
