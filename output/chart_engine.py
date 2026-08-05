"""
图表渲染引擎 — matplotlib/seaborn 生成专业质量分析图表
"""

import io
import os
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
import seaborn as sns
from config.settings import (
    CHART_COLORS, CHART_DPI, CHART_FIGSIZE,
    FONT_FAMILY, FONT_SIZE_TITLE, FONT_SIZE_LABEL, FONT_SIZE_TICK,
    get_effective,
)
from core.i18n import i18n


def _dpi():
    return get_effective("chart_dpi", CHART_DPI)


def setup_chinese_font():
    import matplotlib.font_manager as fm
    fm._load_fontmanager(try_read_cache=False)
    available = {f.name for f in fm.fontManager.ttflist}

    preferred = [
        "Microsoft YaHei", "SimHei", "Noto Sans SC",
        "Noto Sans JP", "Noto Sans", "DejaVu Sans",
        "Arial Unicode MS", "WenQuanYi Micro Hei",
    ]
    matched = [p for p in preferred if p in available]
    if matched:
        current = list(plt.rcParams["font.sans-serif"])
        for m in reversed(matched):
            if m in current:
                current.remove(m)
            current.insert(0, m)
        plt.rcParams["font.sans-serif"] = current
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["axes.unicode_minus"] = False


setup_chinese_font()

# ── 智能系统抽样 ──────────────────────────────────────
# 图表渲染采用智能系统抽样（非随机抽样），原因：
#   图宽固定 10-30 英寸 ≈ 1200-3600 px，marker 4-5px
#   超过 300 个数据点 marker 开始重叠，超过 600 点完全不可辨
# 策略:
#   1. 等距系统抽样保证时间趋势完整可见（非随机）
#   2. 所有判异点（Nelson规则/超控制限）强制保留
#   3. 分析计算始终用全量数据，仅在渲染层抽样
#   4. 图表副标题显示抽样提示文字
MAX_VISIBLE_POINTS = 300
MAX_FIG_WIDTH = 30  # 英寸


def _smart_thin(data: list, violations: list,
                max_points: int = MAX_VISIBLE_POINTS):
    """智能系统抽样 + 判异点强制保留

    Returns:
        (thinned_data, x_labels, was_thinned, sample_note)
    """
    n = len(data)
    if n <= max_points:
        return data, list(range(1, n + 1)), False, ""

    # 收集违规点 0-based 索引
    violation_indices = set()
    for v in (violations or []):
        pt = v.get("point", 0) - 1
        if 0 <= pt < n:
            violation_indices.add(pt)

    # 等距系统抽样
    step = n / max_points
    sampled = []
    for i in range(max_points):
        idx = int(i * step)
        sampled.append(idx)

    # 判异点强制插入（替换最近采样位）
    for vi in sorted(violation_indices):
        if vi not in sampled:
            closest = min(range(len(sampled)),
                          key=lambda j: abs(sampled[j] - vi))
            sampled[closest] = vi

    sampled = sorted(set(sampled))
    thinned = [data[i] for i in sampled]
    x_labels = [i + 1 for i in sampled]
    info = (f"（原始 {n} 点，"
            f"图表智能系统抽样至 {len(thinned)} 点，"
            f"判异点已全部保留）")
    return thinned, x_labels, True, info


def _get_max_data_length(chart_data: Dict[str, Any]) -> int:
    """估算图表数据点数，用于动态图宽"""
    max_n = 0
    for key in ("xbar_chart", "i_chart", "r_chart", "mr_chart", "s_chart",
                "p_chart", "np_chart", "c_chart", "u_chart",
                "cusum_chart", "ewma_chart"):
        d = chart_data.get(key, {})
        if isinstance(d, dict):
            arr = d.get("data", d.get("raw_data", d.get("cusum_plus", [])))
            if isinstance(arr, list):
                max_n = max(max_n, len(arr))
    # fallback: direct data key
    d = chart_data.get("data", [])
    if isinstance(d, list) and not isinstance(d, dict):
        max_n = max(max_n, len(d))
    return max_n


def create_control_chart(
    chart_data: Dict[str, Any],
    title: str = "",
    figsize: Tuple[float, float] = CHART_FIGSIZE,
) -> Figure:
    chart_type = chart_data.get("chart_type", "SPC")

    # 动态图宽：超过 200 点后每 40 点加 1 英寸，上限 MAX_FIG_WIDTH
    n_points = _get_max_data_length(chart_data)
    if n_points > 200:
        extra = min((n_points - 200) / 40, MAX_FIG_WIDTH - CHART_FIGSIZE[0])
        figsize = (CHART_FIGSIZE[0] + extra, CHART_FIGSIZE[1])

    if chart_type in ("XBar-R", "XBar-S", "I-MR"):
        fig, axes = plt.subplots(2, 1, figsize=figsize, dpi=_dpi(), sharex=True)
        note1 = _plot_xbar_chart(axes[0], chart_data, chart_type)
        note2 = _plot_range_chart(axes[1], chart_data, chart_type)
        sample_note = note1 or note2
    elif chart_type in ("CUSUM", "EWMA"):
        fig, axes = plt.subplots(1, 1, figsize=(figsize[0], figsize[1] * 0.7), dpi=_dpi())
        sample_note = _plot_advanced_control_chart(axes, chart_data, chart_type)
    else:
        fig, axes = plt.subplots(1, 1, figsize=(figsize[0], figsize[1] * 0.7), dpi=_dpi())
        sample_note = _plot_simple_control_chart(axes, chart_data, title)

    if title:
        full_title = f"{title}\n{sample_note}" if sample_note else title
        fig.suptitle(full_title, fontsize=FONT_SIZE_TITLE, fontweight="bold")
    elif sample_note:
        fig.suptitle(sample_note, fontsize=9, color="#888888")
    fig.tight_layout(pad=2.0)

    return fig


def _plot_xbar_chart(ax: plt.Axes, chart_data: Dict[str, Any],
                     chart_type: str) -> str:
    """绘制 XBar/I 控制图，返回抽样提示文字"""
    key = "xbar_chart" if chart_type in ("XBar-R", "XBar-S") else "i_chart"
    chart = chart_data.get(key, chart_data)

    data_raw = chart.get("data", [])
    violations = chart.get("violations", [])
    data, x_labels, was_thinned, note = _smart_thin(data_raw, violations)

    cl = chart.get("cl", 0)
    ucl = chart.get("ucl", 0)
    lcl = chart.get("lcl", 0)
    n_raw = len(data_raw)

    ms = 5 if was_thinned else 4
    lw = 1.5 if was_thinned else 1.2
    ax.plot(x_labels, data, "o-", color=CHART_COLORS["data_points"],
            markersize=ms, linewidth=lw, label=i18n.tr("chart.data_points"))
    ax.axhline(y=cl, color=CHART_COLORS["center_line"], linestyle="-",
               linewidth=1.5, label=f"CL={cl:.4f}")
    ax.axhline(y=ucl, color=CHART_COLORS["ucl_lcl"], linestyle="--",
               linewidth=1.2, label=f"UCL={ucl:.4f}")
    ax.axhline(y=lcl, color=CHART_COLORS["ucl_lcl"], linestyle="--",
               linewidth=1.2, label=f"LCL={lcl:.4f}")

    # 判异点使用原始坐标（1-based point 直接对应 x 轴序号）
    for v in violations:
        pt = v.get("point", 0)
        if 1 <= pt <= n_raw:
            ax.plot(pt, data_raw[pt - 1], "ro", markersize=10,
                    markeredgewidth=2, fillstyle="none")

    ax.set_ylabel(i18n.tr("chart.sample_mean"), fontsize=FONT_SIZE_LABEL)
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.set_title(key.replace("_chart", "").upper() + " "
                 + i18n.tr("chart.control_chart"), fontsize=FONT_SIZE_TITLE)
    return note


def _plot_range_chart(ax: plt.Axes, chart_data: Dict[str, Any],
                      chart_type: str) -> str:
    """绘制 R/S/MR 控制图，返回抽样提示文字"""
    key = "r_chart" if chart_type in ("XBar-R", "XBar-S") else "mr_chart"
    chart = chart_data.get(key, chart_data)

    data_raw = chart.get("data", [])
    violations = chart.get("violations", [])
    data, x_labels, was_thinned, note = _smart_thin(data_raw, violations)

    cl = chart.get("cl", 0)
    ucl = chart.get("ucl", 0)
    lcl = chart.get("lcl", 0)
    n_raw = len(data_raw)

    ms = 5 if was_thinned else 4
    lw = 1.5 if was_thinned else 1.2
    ax.plot(x_labels, data, "s-", color=CHART_COLORS["secondary"],
            markersize=ms, linewidth=lw, label=i18n.tr("chart.range"))
    ax.axhline(y=cl, color=CHART_COLORS["center_line"], linestyle="-",
               linewidth=1.5, label=f"CL={cl:.4f}")
    ax.axhline(y=ucl, color=CHART_COLORS["ucl_lcl"], linestyle="--",
               linewidth=1.2, label=f"UCL={ucl:.4f}")
    if lcl > 0:
        ax.axhline(y=lcl, color=CHART_COLORS["ucl_lcl"], linestyle="--",
                   linewidth=1.2, label=f"LCL={lcl:.4f}")

    for v in violations:
        pt = v.get("point", 0)
        if 1 <= pt <= n_raw:
            ax.plot(pt, data_raw[pt - 1], "ro", markersize=10,
                    markeredgewidth=2, fillstyle="none")

    ax.set_xlabel(i18n.tr("chart.subgroup_no"), fontsize=FONT_SIZE_LABEL)
    ax.set_ylabel(i18n.tr("chart.range"), fontsize=FONT_SIZE_LABEL)
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.set_title(key.replace("_chart", "").upper() + " "
                 + i18n.tr("chart.control_chart"), fontsize=FONT_SIZE_TITLE)
    return note


def _plot_simple_control_chart(ax: plt.Axes, chart_data: Dict[str, Any],
                                title: str) -> str:
    """绘制 P/NP/C/U 单图控制图，返回抽样提示文字"""
    data_raw = chart_data.get("data", chart_data.get("p_values", []))
    if isinstance(data_raw, dict):
        data_raw = data_raw.get("p_values",
                    data_raw.get("u_values",
                    data_raw.get("data", [])))

    violations = chart_data.get("violations", [])
    data, x_labels, was_thinned, note = _smart_thin(data_raw, violations)

    cl = chart_data.get("cl", 0)
    ucl = chart_data.get("ucl", [])
    lcl = chart_data.get("lcl", [])

    if isinstance(ucl, list) and len(ucl) != len(data_raw):
        ucl_vals_raw = [ucl[0]] * len(data_raw) if ucl else [0] * len(data_raw)
        lcl_vals_raw = [lcl[0]] * len(data_raw) if lcl else [0] * len(data_raw)
    else:
        ucl_vals_raw = ucl if isinstance(ucl, list) else [ucl] * len(data_raw)
        lcl_vals_raw = lcl if isinstance(lcl, list) else [lcl] * len(data_raw)

    ms = 5 if was_thinned else 4
    lw = 1.5 if was_thinned else 1.2
    ax.plot(x_labels, data, "o-", color=CHART_COLORS["data_points"],
            markersize=ms, linewidth=lw)
    ax.axhline(y=cl, color=CHART_COLORS["center_line"], linestyle="-",
               linewidth=1.5, label=f"CL={cl:.4f}")

    # UCL/LCL 同样抽样
    if ucl_vals_raw and was_thinned:
        idxs = [x - 1 for x in x_labels]
        ucl_thin = [ucl_vals_raw[i] for i in idxs]
        lcl_thin = [lcl_vals_raw[i] for i in idxs]
        ax.plot(x_labels, ucl_thin, "--", color=CHART_COLORS["ucl_lcl"],
                linewidth=1.2, label="UCL")
        ax.plot(x_labels, lcl_thin, "--", color=CHART_COLORS["ucl_lcl"],
                linewidth=1.2, label="LCL")
    else:
        if ucl_vals_raw:
            ax.plot(range(1, len(data_raw) + 1), ucl_vals_raw, "--",
                    color=CHART_COLORS["ucl_lcl"], linewidth=1.2, label="UCL")
        if lcl_vals_raw:
            ax.plot(range(1, len(data_raw) + 1), lcl_vals_raw, "--",
                    color=CHART_COLORS["ucl_lcl"], linewidth=1.2, label="LCL")

    ax.set_xlabel(i18n.tr("chart.subgroup_no"), fontsize=FONT_SIZE_LABEL)
    ax.set_ylabel("Statistic", fontsize=FONT_SIZE_LABEL)
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, alpha=0.3)
    if title:
        ax.set_title(title, fontsize=FONT_SIZE_TITLE)
    return note


def _plot_advanced_control_chart(ax: plt.Axes, chart_data: Dict[str, Any],
                                  chart_type: str) -> str:
    """绘制 CUSUM/EWMA 高级控制图，返回抽样提示文字"""
    note = ""
    if chart_type == "CUSUM":
        chart = chart_data.get("cusum_chart", chart_data)
        cusum_plus = chart.get("cusum_plus", [])
        cusum_minus = chart.get("cusum_minus", [])
        violations = chart.get("violations", [])
        data_p, xp, was_p, note = _smart_thin(cusum_plus, violations)
        data_m, xm, was_m, _ = _smart_thin(cusum_minus, violations)

        ucl = chart.get("ucl", 0)
        lcl = chart.get("lcl", 0)
        ms = 4 if (was_p or was_m) else 3
        lw = 1.2 if (was_p or was_m) else 1.0

        ax.plot(xp, data_p, "o-", color=CHART_COLORS["primary"],
                markersize=ms, linewidth=lw, label="CUSUM+")
        ax.plot(xm, [-v for v in data_m], "s-", color=CHART_COLORS["warning"],
                markersize=ms, linewidth=lw, label="CUSUM-")
        ax.axhline(y=0, color=CHART_COLORS["center_line"], linestyle="-",
                   linewidth=1.2, label="CL=0")
        ax.axhline(y=ucl, color=CHART_COLORS["ucl_lcl"], linestyle="--",
                   linewidth=1.2, label=f"h={ucl:.3f}")
        ax.axhline(y=lcl, color=CHART_COLORS["ucl_lcl"], linestyle="--",
                   linewidth=1.2, label=f"-h={lcl:.3f}")
        ax.set_ylabel("CUSUM", fontsize=FONT_SIZE_LABEL)

        for v in violations:
            pt = v.get("point", 0) - 1
            if 0 <= pt < len(cusum_plus):
                if "CUSUM+" in str(v.get("rule", "")):
                    ax.plot(pt + 1, cusum_plus[pt], "ro", markersize=8)
                else:
                    ax.plot(pt + 1, -cusum_minus[pt], "ro", markersize=8)

    elif chart_type == "EWMA":
        chart = chart_data.get("ewma_chart", chart_data)
        raw_data = chart.get("raw_data", [])
        ewma_data = chart.get("data", [])
        violations = chart.get("violations", [])
        data_e, xe, was_e, note = _smart_thin(ewma_data, violations)
        data_r, xr, _, _ = _smart_thin(raw_data, violations)

        cl = chart.get("cl", 0)
        ucl = chart.get("ucl", [])
        lcl = chart.get("lcl", [])
        ms = 4 if was_e else 3

        ax.plot(xr, data_r, "o", color="#cccccc", markersize=ms - 1,
                label="原始数据")
        ax.plot(xe, data_e, "o-", color=CHART_COLORS["primary"],
                markersize=ms, linewidth=1.5, label="EWMA")
        ax.axhline(y=cl, color=CHART_COLORS["center_line"], linestyle="-",
                   linewidth=1.2, label=f"CL={cl:.3f}")

        n_full = len(ewma_data)
        if isinstance(ucl, list) and len(ucl) == n_full:
            idxs = [x - 1 for x in xe] if was_e else list(range(n_full))
            ucl_thin = [ucl[i] for i in idxs]
            lcl_thin = [lcl[i] for i in idxs]
            x_axis = xe if was_e else list(range(1, n_full + 1))
            ax.plot(x_axis, ucl_thin, "--", color=CHART_COLORS["ucl_lcl"],
                    linewidth=1.2, label="UCL")
            ax.plot(x_axis, lcl_thin, "--", color=CHART_COLORS["ucl_lcl"],
                    linewidth=1.2, label="LCL")
        else:
            ax.axhline(y=chart.get("ucl_const", 0),
                       color=CHART_COLORS["ucl_lcl"],
                       linestyle="--", linewidth=1.2, label="Steady UCL")
            ax.axhline(y=chart.get("lcl_const", 0),
                       color=CHART_COLORS["ucl_lcl"],
                       linestyle="--", linewidth=1.2, label="Steady LCL")
        ax.set_ylabel("EWMA", fontsize=FONT_SIZE_LABEL)

        for v in violations:
            pt = v.get("point", 0) - 1
            if 0 <= pt < len(ewma_data):
                ax.plot(pt + 1, ewma_data[pt], "ro", markersize=8)

    ax.set_xlabel(i18n.tr("chart.subgroup_no"), fontsize=FONT_SIZE_LABEL)
    ax.legend(loc="upper right", fontsize=7)
    ax.grid(True, alpha=0.3)
    return note


def create_capability_chart(
    cap_data: Dict[str, Any],
    original_data: np.ndarray,
    title: str = "",
) -> Figure:
    fig, axes = plt.subplots(2, 1, figsize=(10, 8), dpi=_dpi(),
                              gridspec_kw={"height_ratios": [3, 1]})

    ax_hist = axes[0]
    ax_stats = axes[1]

    ax_hist.hist(original_data, bins=min(50, int(np.sqrt(len(original_data))) * 2),
                 color=CHART_COLORS["primary"], alpha=0.7, edgecolor="white", density=True)

    mean = cap_data.get("summary", {}).get("mean", np.mean(original_data))
    std = cap_data.get("summary", {}).get("std_overall", np.std(original_data, ddof=1))
    x_range = np.linspace(min(original_data), max(original_data), 200)
    from scipy import stats as sp_stats
    y_norm = sp_stats.norm.pdf(x_range, mean, std)
    ax_hist.plot(x_range, y_norm, "r-", linewidth=1.5, label=i18n.tr("chart.norm_fit"))

    cap = cap_data.get("capability", {})
    usl = cap.get("usl")
    lsl = cap.get("lsl")
    if usl:
        ax_hist.axvline(x=usl, color="red", linestyle="--", linewidth=1.5, label=f"USL={usl}")
    if lsl:
        ax_hist.axvline(x=lsl, color="red", linestyle="--", linewidth=1.5, label=f"LSL={lsl}")

    ax_hist.set_ylabel(i18n.tr("chart.density"), fontsize=FONT_SIZE_LABEL)
    ax_hist.legend(fontsize=8)
    ax_hist.grid(True, alpha=0.3)

    ax_stats.axis("off")
    stats_text = f"Mean={mean:.4f}  Std={std:.4f}  n={len(original_data)}\n"
    if cap:
        cp = cap.get("cp", cap.get("pp", ""))
        cpk = cap.get("cpk", cap.get("ppk", ""))
        ppm = cap.get("ppm_total", "")
        grade = cap.get("grade", "")
        stats_text += f"Cp/Pp={cp}  Cpk/Ppk={cpk}  PPM={ppm}\n等级: {grade}"

    ax_stats.text(0.5, 0.5, stats_text, transform=ax_stats.transAxes,
                  fontsize=FONT_SIZE_LABEL, ha="center", va="center",
                  bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))

    if title:
        fig.suptitle(title, fontsize=FONT_SIZE_TITLE, fontweight="bold")
    fig.tight_layout(pad=2.0)

    return fig


def create_pareto_chart(labels: List[str], values: List[float], title: str = "Pareto图") -> Figure:
    fig, ax1 = plt.subplots(figsize=(10, 5), dpi=_dpi())

    sorted_indices = np.argsort(values)[::-1]
    sorted_labels = [labels[i] for i in sorted_indices]
    sorted_values = [values[i] for i in sorted_indices]

    cumulative = np.cumsum(sorted_values) / sum(sorted_values) * 100

    bars = ax1.bar(range(len(sorted_labels)), sorted_values, color=CHART_COLORS["primary"], alpha=0.8)
    ax1.set_ylabel("效应绝对值", fontsize=FONT_SIZE_LABEL)
    ax1.set_xticks(range(len(sorted_labels)))
    ax1.set_xticklabels(sorted_labels, rotation=45, ha="right", fontsize=FONT_SIZE_TICK)

    ax2 = ax1.twinx()
    ax2.plot(range(len(sorted_labels)), cumulative, "ro-", linewidth=2, markersize=6)
    ax2.set_ylabel("累计百分比 (%)", fontsize=FONT_SIZE_LABEL, color="red")
    ax2.set_ylim(0, 105)

    ax1.grid(True, alpha=0.3, axis="y")
    if title:
        ax1.set_title(title, fontsize=FONT_SIZE_TITLE, fontweight="bold")

    return fig


def create_histogram(data: np.ndarray, title: str = "", bins: int = 0) -> Figure:
    fig, ax = plt.subplots(figsize=(8, 5), dpi=_dpi())

    if not bins:
        bins = min(50, int(np.sqrt(len(data))) * 2)

    ax.hist(data, bins=bins, color=CHART_COLORS["primary"], alpha=0.7, edgecolor="white")
    ax.axvline(x=np.mean(data), color="red", linestyle="--", linewidth=1.5, label=f"Mean={np.mean(data):.4f}")
    ax.set_xlabel("数值", fontsize=FONT_SIZE_LABEL)
    ax.set_ylabel("频次", fontsize=FONT_SIZE_LABEL)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    if title:
        ax.set_title(title, fontsize=FONT_SIZE_TITLE, fontweight="bold")

    return fig


def figure_to_bytes(fig: Figure, fmt: str = "png") -> io.BytesIO:
    buf = io.BytesIO()
    fig.savefig(buf, format=fmt, dpi=_dpi(), bbox_inches="tight")
    buf.seek(0)
    return buf


def save_figure(fig: Figure, file_path: str) -> str:
    fig.savefig(file_path, dpi=_dpi(), bbox_inches="tight")
    plt.close(fig)
    return file_path


def create_correlation_heatmap(df, numeric_cols=None, title="相关矩阵热力图") -> Figure:
    import pandas as pd
    if numeric_cols is None:
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
    else:
        numeric_cols = [c for c in numeric_cols if c in df.columns]

    if len(numeric_cols) < 2:
        fig, ax = plt.subplots(figsize=(6, 4), dpi=_dpi())
        ax.text(0.5, 0.5, "至少需要 2 个数值列", ha="center", va="center", fontsize=14)
        ax.set_title(title, fontsize=FONT_SIZE_TITLE, fontweight="bold")
        return fig

    corr = df[numeric_cols].corr()
    mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
    fig, ax = plt.subplots(figsize=(9, 7), dpi=_dpi())
    sns.heatmap(corr, mask=mask, annot=True, fmt=".3f", cmap="RdBu_r",
                vmin=-1, vmax=1, center=0, square=True,
                linewidths=0.5, cbar_kws={"shrink": 0.8}, ax=ax)
    ax.set_title(title, fontsize=FONT_SIZE_TITLE, fontweight="bold", pad=12)
    fig.tight_layout()
    return fig
