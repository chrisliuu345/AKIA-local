"""
小多图（分面图）— 按分组变量生成多子图网格

支持:
- 每个分组画直方图或箱线图（facet_kind）
- col/row/grid 三种排列方式 + 每行(列)数 + 子图高度
- 共享 X/Y 轴（直方图共享时用统一 bin 边界，组间可比）
- 分组水平按样本数降序保留前 GROUP_LIMIT 组，其余在摘要中说明

参数（options 键）:
- facet_kind: "直方图" | "箱线图"
- facet_mode: "col" | "row" | "grid"
- col_wrap: 每行列数（mode=row 时为每列行数）
- height: 子图高度（英寸）
- share_x / share_y: 是否共享轴
- color: 主色
"""

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from config.settings import (
    CHART_COLORS, FONT_SIZE_TITLE, FONT_SIZE_TICK,
    get_effective,
)
from output.chart_engine import _ensure_font, CHART_DPI

GROUP_LIMIT = 12
_MISSING_LABEL = "(缺失)"


def _dpi():
    return get_effective("chart_dpi", CHART_DPI)


def facet_group_table(
    df: pd.DataFrame,
    value_col: str,
    group_col: str,
    limit: int = GROUP_LIMIT,
) -> Tuple[List[str], List[str], Dict[str, int]]:
    """清洗后分组计数并按样本数降序截断，返回 (保留组, 省略组, 各组合法样本数)"""
    _vals, groups, _ok = _clean(df, value_col, group_col)
    counts = groups.value_counts()
    kept = counts.head(limit).index.tolist()
    dropped = counts.index.tolist()[limit:]
    return kept, dropped, counts.to_dict()


def _clean(
    df: pd.DataFrame,
    value_col: str,
    group_col: str,
) -> Tuple[pd.Series, pd.Series, bool]:
    """返回 (数值, 分组, 可用标志)。值列非数值/分组缺失均剔除；可用样本 <2 视为不可用"""
    if df is None or len(df) == 0:
        return pd.Series(dtype=float), pd.Series(dtype=str), False
    if value_col not in df.columns or group_col not in df.columns:
        return pd.Series(dtype=float), pd.Series(dtype=str), False
    vals = pd.to_numeric(df[value_col], errors="coerce")
    groups = df[group_col].fillna(_MISSING_LABEL).astype(str)
    mask = vals.notna() & groups.str.len().gt(0)
    vals, groups = vals[mask], groups[mask]
    if len(vals) < 2:
        return vals, groups, False
    return vals, groups, True


def layout(n_groups: int, mode: str, col_wrap: int) -> Tuple[int, int]:
    """按排列方式计算 (nrows, ncols)"""
    wrap = max(1, int(col_wrap))
    if mode == "row":
        nrows = min(wrap, n_groups)
        ncols = int(np.ceil(n_groups / nrows))
    elif mode == "col":
        ncols = min(wrap, n_groups)
        nrows = int(np.ceil(n_groups / ncols))
    else:  # grid
        ncols = int(np.ceil(np.sqrt(n_groups)))
        nrows = int(np.ceil(n_groups / ncols))
    return nrows, ncols


def _bin_count(n: int) -> int:
    return min(50, max(5, int(np.sqrt(n)) * 2))


def create_small_multiples(
    df: pd.DataFrame,
    value_col: str,
    group_col: str,
    title: str = "小多图",
    options: Optional[Dict[str, Any]] = None,
) -> Figure:
    """按分组变量生成多子图网格图"""
    _ensure_font()
    opts = options or {}
    kind = opts.get("facet_kind", "直方图")
    mode = opts.get("facet_mode", "col")
    col_wrap = int(opts.get("col_wrap", 3))
    height = float(opts.get("height", 4))
    share_x = opts.get("share_x", True)
    share_y = opts.get("share_y", True)
    color = opts.get("color", CHART_COLORS["primary"])

    vals, groups, ok = _clean(df, value_col, group_col)
    if not ok:
        return _message_fig(title, "请选择数值列和分组列（至少 2 个有效样本）")

    counts = groups.value_counts()
    kept = counts.head(GROUP_LIMIT).index.tolist()
    dropped = counts.index.tolist()[GROUP_LIMIT:]

    n_groups = len(kept)
    nrows, ncols = layout(n_groups, mode, col_wrap)
    width_in = max(2.5 * ncols + 0.6, 8.0)
    height_in = nrows * height + 0.9
    fig, axes = plt.subplots(nrows, ncols, figsize=(width_in, height_in), dpi=_dpi(),
                             squeeze=False)

    shared_edges = None
    if kind == "直方图" and share_x:
        bins = _bin_count(len(vals))
        shared_edges = np.linspace(vals.min(), vals.max(), bins + 1)

    drawn = []
    for idx, group in enumerate(kept):
        ax = axes[idx // ncols, idx % ncols]
        gvals = vals[groups == group]
        if kind == "箱线图":
            ax.boxplot(gvals, patch_artist=True, widths=0.5,
                       boxprops=dict(facecolor=color, alpha=0.6),
                       medianprops=dict(color="#e1e2e6", linewidth=1.5))
            ax.set_xticks([])
        else:
            if shared_edges is not None:
                ax.hist(gvals, bins=shared_edges, color=color, alpha=0.7,
                        edgecolor="white")
            else:
                ax.hist(gvals, bins=_bin_count(len(gvals)), color=color, alpha=0.7,
                        edgecolor="white")
        ax.set_title(f"{group} (n={counts[group]})", fontsize=FONT_SIZE_TICK + 1)
        ax.tick_params(labelsize=FONT_SIZE_TICK)
        ax.grid(True, alpha=0.25)
        drawn.append(ax)

    for idx in range(n_groups, nrows * ncols):
        axes[idx // ncols, idx % ncols].axis("off")

    if share_y and kind == "直方图" and drawn:
        ymax = max(ax.get_ylim()[1] for ax in drawn)
        for ax in drawn:
            ax.set_ylim(0, ymax)

    note = f"分组: {group_col}"
    if dropped:
        note += f"（另有 {len(dropped)} 组因超过 {GROUP_LIMIT} 组上限被省略）"
    fig.text(0.02, 1.0, note, fontsize=FONT_SIZE_TICK, color="#a0a3ae", va="bottom")

    if title:
        fig.suptitle(title, fontsize=FONT_SIZE_TITLE, fontweight="bold", y=1.04)
    fig.tight_layout(rect=[0, 0, 1, 0.995])
    return fig


def _message_fig(title: str, message: str) -> Figure:
    fig, ax = plt.subplots(figsize=(8, 5), dpi=_dpi())
    ax.text(0.5, 0.5, message, ha="center", va="center", fontsize=14)
    ax.axis("off")
    if title:
        ax.set_title(title, fontsize=FONT_SIZE_TITLE, fontweight="bold")
    return fig


def faceting_summary_lines(df: pd.DataFrame, value_col: str, group_col: str) -> List[str]:
    """摘要文本：值列统计 + 分组水平（含省略说明）"""
    lines = []
    vals, groups, ok = _clean(df, value_col, group_col)
    if not ok or len(vals) == 0:
        return lines
    lines.append(f"● {value_col}: 有效样本 n={len(vals)}，均值={vals.mean():.4f}，"
                 f"标准差={vals.std(ddof=1):.4f}")
    counts = groups.value_counts()
    lines.append(f"● 分组变量 {group_col}: {len(counts)} 组，合计 n={int(counts.sum())}")
    for g in counts.head(GROUP_LIMIT).index:
        lines.append(f"  - {g}: n={int(counts[g])}")
    dropped = counts.index.tolist()[GROUP_LIMIT:]
    if dropped:
        shown = ", ".join(map(str, dropped[:8]))
        lines.append(f"  （另有 {len(dropped)} 组被省略: {shown}{'…' if len(dropped) > 8 else ''}）")
    return lines
