"""
热力图与散点矩阵 — 相关系数可视化 + 显著性检验

支持:
- 相关系数矩阵热力图（Pearson/Spearman/Kendall）
- 散点矩阵图（多变量两两散点 + 直方图对角线）
- 显著性标记（*p<0.05, **p<0.01, ***p<0.001）
- 配色方案选择
"""

from typing import Any
import numpy as np
import pandas as pd
from scipy import stats
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from config.settings import (
    CHART_DPI,
    FONT_SIZE_TITLE, FONT_SIZE_TICK,
    get_effective,
)
from output.chart_engine import _ensure_font
from output import chart_style


def _dpi():
    return get_effective("chart_dpi", CHART_DPI)


def _compute_correlation_matrix(
    df: pd.DataFrame,
    numeric_cols: list[str],
    method: str = "pearson",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """计算相关系数矩阵和 p 值矩阵"""
    corr = df[numeric_cols].corr(method=method)
    len(df)
    p_values = pd.DataFrame(np.zeros((len(numeric_cols), len(numeric_cols))),
                            index=numeric_cols, columns=numeric_cols)

    for i, col1 in enumerate(numeric_cols):
        for j, col2 in enumerate(numeric_cols):
            if i == j:
                p_values.loc[col1, col2] = 0.0
            else:
                valid = df[[col1, col2]].dropna()
                if len(valid) < 3:
                    p_values.loc[col1, col2] = 1.0
                else:
                    if method == "pearson":
                        _, p = stats.pearsonr(valid[col1], valid[col2])
                    elif method == "spearman":
                        _, p = stats.spearmanr(valid[col1], valid[col2])
                    else:
                        _, p = stats.kendalltau(valid[col1], valid[col2])
                    p_values.loc[col1, col2] = p

    return corr, p_values


def _significance_stars(p_value: float) -> str:
    """将 p 值转换为显著性星号"""
    if p_value <= 0.001:
        return "***"
    if p_value <= 0.01:
        return "**"
    if p_value <= 0.05:
        return "*"
    return ""


def create_correlation_heatmap(
    df: pd.DataFrame,
    numeric_cols: list[str] | None = None,
    title: str = "相关矩阵热力图",
    options: dict[str, Any] | None = None,
) -> Figure:
    """
    创建相关系数矩阵热力图

    参数:
        df: 数据框
        numeric_cols: 数值列列表（None 则自动选择）
        title: 图表标题
        options: 可选参数
            - method: 相关系数方法 (pearson/spearman/kendall)
            - colormap: 配色方案
            - show_annotations: 是否显示数值
            - show_significance: 是否显示显著性标记
            - label_fontsize: 标签字号
            - annot_fontsize: 数值字号
    """
    _ensure_font()
    opts = options or {}
    method = opts.get("method", "pearson")
    colormap = opts.get("colormap", "RdBu_r")
    show_annotations = opts.get("show_annotations", True)
    show_significance = opts.get("show_significance", True)
    label_fontsize = opts.get("label_fontsize", FONT_SIZE_TICK)
    annot_fontsize = opts.get("annot_fontsize", 8)

    if numeric_cols is None:
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
    else:
        numeric_cols = [c for c in numeric_cols if c in df.columns]

    if len(numeric_cols) < 2:
        fig, ax = plt.subplots(figsize=(6, 4), dpi=_dpi())
        ax.text(0.5, 0.5, "至少需要 2 个数值列", ha="center", va="center", fontsize=14)
        ax.set_title(title, fontsize=FONT_SIZE_TITLE, fontweight="bold")
        return fig

    corr, p_values = _compute_correlation_matrix(df, numeric_cols, method)

    mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
    fig, ax = plt.subplots(figsize=(9, 7), dpi=_dpi())

    sns_annot = None
    if show_annotations:
        if show_significance:
            annot = corr.copy().astype(str)
            for i in range(len(numeric_cols)):
                for j in range(len(numeric_cols)):
                    if i != j:
                        r = corr.iloc[i, j]
                        p = p_values.iloc[i, j]
                        stars = _significance_stars(p)
                        annot.iloc[i, j] = f"{r:.2f}{stars}"
                    else:
                        annot.iloc[i, j] = f"{corr.iloc[i, j]:.2f}"
            sns_annot = annot
        else:
            sns_annot = corr.round(2).astype(str)

    import seaborn as sns
    sns.heatmap(
        corr, mask=mask, annot=sns_annot, fmt="", cmap=colormap,
        vmin=-1, vmax=1, center=0, square=True,
        linewidths=0.6, linecolor=chart_style.semantic()["panel"],
        cbar_kws={"shrink": 0.8},
        annot_kws={"size": annot_fontsize},
        ax=ax,
    )

    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right", fontsize=label_fontsize)
    ax.set_yticklabels(ax.get_yticklabels(), fontsize=label_fontsize)

    if title:
        ax.set_title(title, fontsize=FONT_SIZE_TITLE, fontweight="bold", pad=12)
    # 注释文字按单元格明暗自动取色（深色格用面板色，浅色格用正文色）
    for text in ax.texts:
        x, y = text.get_position()
        col_idx, row_idx = int(float(x)), int(float(y))
        if 0 <= row_idx < len(corr) and 0 <= col_idx < len(corr):
            value = float(corr.iloc[row_idx, col_idx])
            text.set_color(chart_style.semantic()["panel"] if abs(value) > 0.55
                           else chart_style.semantic()["text"])

    chart_style.style_axes(ax, grid=None, hide_spines=())
    chart_style.finalize_figure(fig)
    return fig


def create_scatter_matrix(
    df: pd.DataFrame,
    numeric_cols: list[str] | None = None,
    title: str = "散点矩阵图",
    options: dict[str, Any] | None = None,
) -> Figure:
    """
    创建散点矩阵图（多变量两两散点 + 直方图对角线）

    参数:
        df: 数据框
        numeric_cols: 数值列列表
        title: 图表标题
        options: 可选参数
            - point_size: 点大小
            - point_alpha: 透明度
            - show_regression: 是否显示回归线
            - label_fontsize: 标签字号
    """
    _ensure_font()
    opts = options or {}
    point_size = opts.get("point_size", 30)
    point_alpha = opts.get("point_alpha", 0.5)
    show_regression = opts.get("show_regression", True)
    label_fontsize = opts.get("label_fontsize", FONT_SIZE_TICK)

    if numeric_cols is None:
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
    else:
        numeric_cols = [c for c in numeric_cols if c in df.columns]

    if len(numeric_cols) < 2:
        fig, ax = plt.subplots(figsize=(6, 4), dpi=_dpi())
        ax.text(0.5, 0.5, "至少需要 2 个数值列", ha="center", va="center", fontsize=14)
        ax.set_title(title, fontsize=FONT_SIZE_TITLE, fontweight="bold")
        return fig

    n = len(numeric_cols)
    fig, axes = plt.subplots(n, n, figsize=(2.5 * n + 1, 2.5 * n + 1), dpi=_dpi())

    for i in range(n):
        for j in range(n):
            ax = axes[i, j]
            if i == j:
                ax.hist(df[numeric_cols[i]].dropna(), bins=20,
                        color=chart_style.semantic()["data"], alpha=0.7,
                        edgecolor=chart_style.semantic()["panel"])
            else:
                x = df[numeric_cols[j]].dropna()
                y = df[numeric_cols[i]].dropna()
                common_idx = x.index.intersection(y.index)
                x, y = x[common_idx], y[common_idx]

                ax.scatter(x, y, s=point_size, alpha=point_alpha,
                           color=chart_style.semantic()["data"],
                           edgecolors=chart_style.semantic()["panel"], linewidth=0.5)

                if show_regression and len(x) > 2:
                    z = np.polyfit(x, y, 1)
                    p = np.poly1d(z)
                    x_line = np.linspace(x.min(), x.max(), 100)
                    ax.plot(x_line, p(x_line), "r--", alpha=0.8, linewidth=1)

            if i == n - 1:
                ax.set_xlabel(numeric_cols[j], fontsize=label_fontsize)
            else:
                ax.set_xlabel("")

            if j == 0:
                ax.set_ylabel(numeric_cols[i], fontsize=label_fontsize)
            else:
                ax.set_ylabel("")

            ax.tick_params(labelsize=max(label_fontsize - 2, 6))

    if title:
        fig.suptitle(title, fontsize=FONT_SIZE_TITLE, fontweight="bold", y=1.02)

    fig.tight_layout()
    return fig
