"""
通用统计图表生成器 — 12 种图表（分批交付，D1 前 6 种）
"""

from typing import Dict, Any, List, Optional, OrderedDict
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from scipy import stats as sp_stats
from scipy.interpolate import griddata
from output.chart_engine import (
    create_histogram, create_pareto_chart, create_correlation_heatmap,
)
from config.settings import (
    CHART_DPI, FONT_SIZE_TITLE, FONT_SIZE_LABEL, FONT_SIZE_TICK,
    get_effective,
)

# ── 暗色主题 ──
_DARK_AXES = {
    "axes.facecolor": "#262632",
    "axes.edgecolor": "#3a3a48",
    "axes.labelcolor": "#e1e2e6",
    "axes.titlecolor": "#e1e2e6",
    "xtick.color": "#a0a3ae",
    "ytick.color": "#a0a3ae",
    "grid.color": "#2a2a36",
    "text.color": "#e1e2e6",
    "figure.facecolor": "#181822",
    "figure.edgecolor": "#181822",
}

_CHART_PALETTES = {
    "专业蓝": ["#1b5faa", "#4da6ff", "#14508a", "#7fc1ff", "#0d3d73"],
    "暖色调": ["#e67e22", "#f39c12", "#d35400", "#f1c40f", "#e74c3c"],
    "自然色": ["#27ae60", "#2ecc71", "#1abc9c", "#16a085", "#3498db"],
    "质感灰": ["#6e7080", "#a0a3ae", "#3a3a48", "#5a5c6a", "#e1e2e6"],
}

def _dpi():
    return get_effective("chart_dpi", CHART_DPI)


def _apply_dark_theme(dark: bool = True):
    if dark:
        plt.rcParams.update(_DARK_AXES)
    else:
        for k in _DARK_AXES:
            plt.rcParams[k] = "#ffffff" if "color" in k.lower() else plt.rcParams[k]


def _get_palette(palette_name: str = "专业蓝") -> List[str]:
    return _CHART_PALETTES.get(palette_name, _CHART_PALETTES["专业蓝"])


# ── 图表类型定义 ──

CHART_TYPES = [
    "直方图", "箱线图", "散点图", "帕累托图", "概率图", "矩阵图",
    "残差图", "主效应图", "交互效应图", "等值线图", "3D曲面图", "时间序列图",
    "气泡图", "雷达图", "瀑布图",
]

CHART_CONFIGS = OrderedDict([
    ("直方图", [("数值列", "numeric")]),
    ("箱线图", [("数值列(可多选)", "multi_numeric")]),
    ("散点图", [("X 轴列", "numeric"), ("Y 轴列", "numeric")]),
    ("帕累托图", [("分类列", "text"), ("数值列", "numeric")]),
    ("概率图", [("数值列", "numeric")]),
    ("矩阵图", [("数值列(可多选)", "multi_numeric")]),
    ("残差图", [("实际值列", "numeric"), ("预测值列", "numeric")]),
    ("主效应图", [("因子列(可多选)", "multi_text"), ("响应列", "numeric")]),
    ("交互效应图", [("因子1", "text"), ("因子2", "text"), ("响应列", "numeric")]),
    ("等值线图", [("X 因子", "numeric"), ("Y 因子", "numeric"), ("响应列", "numeric")]),
    ("3D曲面图", [("X 因子", "numeric"), ("Y 因子", "numeric"), ("响应列", "numeric")]),
    ("时间序列图", [("日期列", "datetime"), ("数值列", "numeric")]),
    ("气泡图", [("X 轴列", "numeric"), ("Y 轴列", "numeric"), ("气泡大小列", "numeric")]),
    ("雷达图", [("分类列", "text"), ("数值列(可多选)", "multi_numeric")]),
    ("瀑布图", [("分类列", "text"), ("数值列", "numeric")]),
])


# ── 统计摘要 ──

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


# ── 6 种 D1 图表 ──

def _build_histogram(data: dict, options: dict) -> Figure:
    df = data.get("df")
    col = data.get("columns", [None])[0]
    if df is None or col is None or col not in df.columns:
        fig, ax = plt.subplots(figsize=(8, 5), dpi=_dpi())
        ax.text(0.5, 0.5, "请选择数值列", ha="center", va="center", fontsize=14)
        return fig
    series = pd.to_numeric(df[col], errors="coerce").dropna()
    fig = create_histogram(series.values, title=options.get("title", col), bins=0)
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
    palette = _get_palette(options.get("palette", "专业蓝"))
    fig, ax = plt.subplots(figsize=(max(7, len(cols) * 2), 5), dpi=_dpi())
    values = [pd.to_numeric(df[c], errors="coerce").dropna().values for c in cols if c in df.columns]
    labels = [c for c in cols if c in df.columns]
    bp = ax.boxplot(values, patch_artist=True,
                    medianprops={"color": "#e1e2e6", "linewidth": 1.5})
    ax.set_xticklabels(labels)
    for patch, color in zip(bp["boxes"], palette[:len(values)]):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)
    ax.set_title(options.get("title", "箱线图"), fontsize=FONT_SIZE_TITLE, fontweight="bold")
    ax.set_ylabel("数值", fontsize=FONT_SIZE_LABEL)
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
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
    show_reg = options.get("show_regression", True)
    fig, ax = plt.subplots(figsize=(8, 6), dpi=_dpi())
    ax.scatter(x, y, alpha=0.6, edgecolors="white", linewidth=0.3, color=palette[0])
    if show_reg:
        slope, intercept, r_val, p_val, std_err = sp_stats.linregress(x, y)
        x_line = np.linspace(x.min(), x.max(), 100)
        ax.plot(x_line, slope * x_line + intercept, color=palette[1], linewidth=1.5,
                label=f"y={slope:.3f}x+{intercept:.3f}  R²={r_val**2:.4f}")
        ax.legend(fontsize=9)
    ax.set_xlabel(cols[0], fontsize=FONT_SIZE_LABEL)
    ax.set_ylabel(cols[1], fontsize=FONT_SIZE_LABEL)
    ax.set_title(options.get("title", f"{cols[0]} vs {cols[1]}"),
                 fontsize=FONT_SIZE_TITLE, fontweight="bold")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
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
    fig = create_pareto_chart(labels, values, title=options.get("title", "帕累托图"))
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
    ax.get_lines()[1].set_color("#4da6ff")
    ax.get_lines()[1].set_linewidth(1.5)
    ax.get_lines()[0].set_markerfacecolor("#1b5faa")
    ax.get_lines()[0].set_markeredgecolor("white")
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
                                     title=options.get("title", "相关矩阵热力图"))
    _apply_figure_palette(fig, options.get("palette", "专业蓝"))
    _apply_figure_theme(fig, options)
    return fig


# ── 6 种 D2 图表 ──

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
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), dpi=_dpi())
    ax1 = axes[0]
    ax1.scatter(pred, residuals, alpha=0.6, edgecolors="white", linewidth=0.3, color=palette[0])
    ax1.axhline(y=0, color="red", linestyle="--", linewidth=1)
    ax1.set_xlabel("预测值", fontsize=FONT_SIZE_LABEL)
    ax1.set_ylabel("残差", fontsize=FONT_SIZE_LABEL)
    ax1.set_title("残差 vs 拟合值", fontsize=FONT_SIZE_TITLE - 2)
    ax1.grid(True, alpha=0.3)
    ax2 = axes[1]
    ax2.hist(residuals, bins=min(30, max(5, len(residuals)//5)), color=palette[0], alpha=0.7, edgecolor="white")
    ax2.axvline(x=0, color="red", linestyle="--", linewidth=1)
    ax2.set_xlabel("残差", fontsize=FONT_SIZE_LABEL)
    ax2.set_ylabel("频次", fontsize=FONT_SIZE_LABEL)
    ax2.set_title("残差分布", fontsize=FONT_SIZE_TITLE - 2)
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
    for ax, factor in zip(axes, factor_cols):
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

    # W79 fix: 去除重复坐标避免griddata QhullError
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
        Z = griddata((x_u, y_u), z_u, (X, Y), method="linear")  # 降级到linear
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

    # W79 fix: 去除重复坐标避免griddata QhullError
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
        Z = griddata((x_u, y_u), z_u, (X, Y), method="linear")  # 降级到linear
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
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()
    return fig


# ── 3 种新图表 (气泡/雷达/瀑布) ──

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
    scatter = ax.scatter(x, y, s=sizes, alpha=0.55, c=palette[0],
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
    ax.set_facecolor("#1c1c26")
    fig.tight_layout()
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
    fig, ax = plt.subplots(figsize=(max(10, len(vals) * 1.2), 5), dpi=_dpi())

    bottom = 0.0
    for i, (lbl, v) in enumerate(zip(labels, vals)):
        color = palette[0] if v >= 0 else palette[2] if len(palette) > 2 else "#e74c3c"
        # C16 fix: all bars start from accumulated bottom
        bar = ax.bar(i, v, bottom=bottom, color=color, alpha=0.8,
                     edgecolor="white", linewidth=0.5)
        # 连接线从前一根柱子顶部到当前柱子底部
        if i > 0:
            ax.plot([i - 1, i], [bottom, bottom], linewidth=0.8, color="#6e7080")
        # C16 fix: accumulate bottom for all bars including first
        bottom += v

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=FONT_SIZE_TICK, rotation=30, ha="right")
    ax.set_ylabel(val_col, fontsize=FONT_SIZE_LABEL)
    ax.set_title(options.get("title", "瀑布图"), fontsize=FONT_SIZE_TITLE, fontweight="bold")
    ax.axhline(y=0, color="#a0a3ae", linewidth=0.8)
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    return fig


# ── 主题应用 ──

def _apply_figure_palette(fig: Figure, palette_name: str):
    """后置应用调色板到图表元素 (对 histogram/pareto/probplot/matrix 生效)"""
    palette = _get_palette(palette_name)
    for ax in fig.get_axes():
        # 直方图/帕累托 bars
        for container in ax.containers:
            for patch in container.patches:
                patch.set_facecolor(palette[0])
                patch.set_alpha(0.75)
        # 概率图散点线
        for line in ax.get_lines():
            if line.get_marker() != 'None' and len(ax.get_lines()) > 1:
                line.set_markerfacecolor(palette[0])
                line.set_markeredgecolor(palette[1])
            elif len(ax.get_lines()) == 1 or line.get_linestyle() != '--':
                line.set_color(palette[0])
        # 饼图 wedges (如果有)
        for patch in ax.patches:
            if hasattr(patch, 'set_facecolor') and not hasattr(patch, 'get_height'):
                pass  # 不处理非bar patches


def _apply_figure_theme(fig: Figure, options: dict):
    dark = options.get("dark_mode", True)
    if dark:
        fig.patch.set_facecolor("#181822")
        for ax in fig.get_axes():
            ax.set_facecolor("#262632")
            for spine in ax.spines.values():
                spine.set_color("#3a3a48")
            ax.tick_params(colors="#a0a3ae")
            ax.yaxis.label.set_color("#e1e2e6")
            ax.xaxis.label.set_color("#e1e2e6")


# ── 统一入口 ──

BUILDERS = {
    "直方图": _build_histogram,
    "箱线图": _build_boxplot,
    "散点图": _build_scatter,
    "帕累托图": _build_pareto,
    "概率图": _build_probplot,
    "矩阵图": _build_matrix,
    "残差图": _build_residual,
    "主效应图": _build_main_effects,
    "交互效应图": _build_interaction,
    "等值线图": _build_contour,
    "3D曲面图": _build_surface_3d,
    "时间序列图": _build_time_series,
    "气泡图": _build_bubble,
    "雷达图": _build_radar,
    "瀑布图": _build_waterfall,
}


def generate_chart(chart_type: str, data: dict, options: dict = None) -> Figure:
    if options is None:
        options = {}
    _apply_dark_theme(options.get("dark_mode", True))
    builder = BUILDERS.get(chart_type)
    if builder is None:
        fig, ax = plt.subplots(figsize=(8, 5), dpi=_dpi())
        ax.text(0.5, 0.5, f"图表未实现: {chart_type}", ha="center", va="center", fontsize=14)
        return fig
    return builder(data, options)
