"""
图表渲染引擎 — matplotlib/seaborn 生成专业质量分析图表
"""

import io
from typing import Dict, Any, List, Tuple
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from config.settings import (
    CHART_DPI, CHART_FIGSIZE,
    FONT_SIZE_TITLE, FONT_SIZE_LABEL, FONT_SIZE_TICK,
    get_effective,
)
from output import chart_style
from core.i18n import i18n


def _dpi():
    return get_effective("chart_dpi", CHART_DPI)


def setup_chinese_font():
    """兼容入口 — 字体配置已统一到 output.chart_style。"""
    chart_style.setup_fonts()


_font_initialized = False


def _ensure_font():
    global _font_initialized
    if not _font_initialized:
        chart_style.apply_chart_style()
        _font_initialized = True

MAX_VISIBLE_POINTS = 300
MAX_FIG_WIDTH = 30


def _smart_thin(data: list, violations: list,
                max_points: int = MAX_VISIBLE_POINTS):
    """智能系统抽样 + 判异点强制保留

    Returns:
        (thinned_data, x_labels, was_thinned, sample_note)
    """
    n = len(data)
    if n <= max_points:
        return data, list(range(1, n + 1)), False, ""

    violation_indices = set()
    for v in (violations or []):
        pt = v.get("point", 0) - 1
        if 0 <= pt < n:
            violation_indices.add(pt)

    step = n / max_points
    sampled = []
    for i in range(max_points):
        idx = int(i * step)
        sampled.append(idx)

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
    d = chart_data.get("data", [])
    if isinstance(d, list) and not isinstance(d, dict):
        max_n = max(max_n, len(d))
    return max_n


def create_control_chart(
    chart_data: Dict[str, Any],
    title: str = "",
    figsize: Tuple[float, float] = CHART_FIGSIZE,
    options: Dict[str, Any] = None,
) -> Figure:
    _ensure_font()
    opts = options or {}
    chart_type = chart_data.get("chart_type", "SPC")
    show_limits = opts.get("show_limits", True)

    n_points = _get_max_data_length(chart_data)
    if n_points > 200:
        extra = min((n_points - 200) / 40, MAX_FIG_WIDTH - CHART_FIGSIZE[0])
        figsize = (CHART_FIGSIZE[0] + extra, CHART_FIGSIZE[1])

    if chart_type in ("XBar-R", "XBar-S", "I-MR"):
        fig, axes = plt.subplots(2, 1, figsize=figsize, dpi=_dpi(), sharex=True)
        note1 = _plot_xbar_chart(axes[0], chart_data, chart_type, show_limits=show_limits)
        note2 = _plot_range_chart(axes[1], chart_data, chart_type, show_limits=show_limits)
        sample_note = note1 or note2
    elif chart_type in ("CUSUM", "EWMA"):
        fig, axes = plt.subplots(1, 1, figsize=(figsize[0], figsize[1] * 0.7), dpi=_dpi())
        sample_note = _plot_advanced_control_chart(axes, chart_data, chart_type, show_limits=show_limits)
    else:
        fig, axes = plt.subplots(1, 1, figsize=(figsize[0], figsize[1] * 0.7), dpi=_dpi())
        sample_note = _plot_simple_control_chart(axes, chart_data, title, show_limits=show_limits)

    if title:
        full_title = f"{title}\n{sample_note}" if sample_note else title
        fig.suptitle(full_title, fontsize=FONT_SIZE_TITLE, fontweight="bold")
    elif sample_note:
        fig.suptitle(sample_note, fontsize=9, color="#888888")

    show_grid = opts.get("show_grid")
    label_fontsize = opts.get("label_fontsize")
    if show_grid is not None or label_fontsize:
        for ax in fig.axes:
            if show_grid is False:
                ax.grid(False)
            if label_fontsize:
                fs = max(label_fontsize - 2, 6)
                ax.tick_params(labelsize=fs)
                if ax.get_xlabel():
                    ax.set_xlabel(ax.get_xlabel(), fontsize=label_fontsize)
                if ax.get_ylabel():
                    ax.set_ylabel(ax.get_ylabel(), fontsize=label_fontsize)

    fig.tight_layout(pad=2.0)

    return fig


def _plot_xbar_chart(ax: plt.Axes, chart_data: Dict[str, Any],
                     chart_type: str, show_limits: bool = True) -> str:
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
    s = chart_style.semantic()
    ax.plot(x_labels, data, "o-", color=s["data"],
            markersize=ms, linewidth=lw, label=i18n.tr("chart.data_points"))
    limits = chart_style.add_limit_lines(
        ax, cl=cl, ucl=ucl if show_limits else None,
        lcl=lcl if show_limits else None, labels=True)

    vx = [v.get("point") for v in violations if 1 <= v.get("point", 0) <= n_raw]
    vy = [data_raw[pt - 1] for pt in vx]
    chart_style.mark_violations(ax, vx, vy, label=i18n.tr("chart.violations"))

    ax.set_ylabel(i18n.tr("chart.sample_mean"), fontsize=FONT_SIZE_LABEL)
    spec_values = _draw_spec_lines(ax, chart_data)
    chart_style.style_axes(ax, grid="y", legend=True)
    chart_style.smart_ylim(ax, data, *limits, *spec_values)
    ax.set_title(key.replace("_chart", "").upper() + " "
                 + i18n.tr("chart.control_chart"), fontsize=FONT_SIZE_TITLE)
    return note


def _plot_range_chart(ax: plt.Axes, chart_data: Dict[str, Any],
                      chart_type: str, show_limits: bool = True) -> str:
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
    s = chart_style.semantic()
    ax.plot(x_labels, data, "s-", color=s["data_alt"],
            markersize=ms, linewidth=lw, label=i18n.tr("chart.range"))
    limits = chart_style.add_limit_lines(
        ax, cl=cl, ucl=ucl if show_limits else None,
        lcl=lcl if (show_limits and lcl > 0) else None, labels=True)

    vx = [v.get("point") for v in violations if 1 <= v.get("point", 0) <= n_raw]
    vy = [data_raw[pt - 1] for pt in vx]
    chart_style.mark_violations(ax, vx, vy)

    ax.set_xlabel(i18n.tr("chart.subgroup_no"), fontsize=FONT_SIZE_LABEL)
    ax.set_ylabel(i18n.tr("chart.range"), fontsize=FONT_SIZE_LABEL)
    chart_style.style_axes(ax, grid="y", legend=True)
    chart_style.smart_ylim(ax, data, *limits)
    ax.set_title(key.replace("_chart", "").upper() + " "
                 + i18n.tr("chart.control_chart"), fontsize=FONT_SIZE_TITLE)
    return note


def _plot_simple_control_chart(ax: plt.Axes, chart_data: Dict[str, Any],
                                title: str, show_limits: bool = True) -> str:
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
    s = chart_style.semantic()
    ax.plot(x_labels, data, "o-", color=s["data"],
            markersize=ms, linewidth=lw, label=i18n.tr("chart.data_points"))
    limits: List[float] = []

    if show_limits and ucl_vals_raw and was_thinned:
        idxs = [x - 1 for x in x_labels]
        ucl_thin = [ucl_vals_raw[i] for i in idxs]
        lcl_thin = [lcl_vals_raw[i] for i in idxs]
        ax.plot(x_labels, ucl_thin, "--", color=s["limit"],
                linewidth=1.1, label="UCL")
        ax.plot(x_labels, lcl_thin, "--", color=s["limit"],
                linewidth=1.1, label="LCL")
        limits = [*ucl_thin, *lcl_thin]
    elif show_limits:
        if ucl_vals_raw:
            ax.plot(range(1, len(data_raw) + 1), ucl_vals_raw, "--",
                    color=s["limit"], linewidth=1.1, label="UCL")
            limits.extend(ucl_vals_raw)
        if lcl_vals_raw:
            ax.plot(range(1, len(data_raw) + 1), lcl_vals_raw, "--",
                    color=s["limit"], linewidth=1.1, label="LCL")
            limits.extend(lcl_vals_raw)

    ax.axhline(y=cl, color=s["center"], linestyle="-",
               linewidth=1.4, label=f"CL={cl:.4f}")
    limits.append(float(cl))

    vx = [v.get("point") for v in violations if 1 <= v.get("point", 0) <= len(data_raw)]
    vy = [data_raw[pt - 1] for pt in vx]
    chart_style.mark_violations(ax, vx, vy)

    ax.set_xlabel(i18n.tr("chart.subgroup_no"), fontsize=FONT_SIZE_LABEL)
    ax.set_ylabel("Statistic", fontsize=FONT_SIZE_LABEL)
    limits.extend(_draw_spec_lines(ax, chart_data))
    chart_style.style_axes(ax, grid="y", legend=True)
    chart_style.smart_ylim(ax, data, *limits)
    if title:
        ax.set_title(title, fontsize=FONT_SIZE_TITLE)
    return note


def _plot_advanced_control_chart(ax: plt.Axes, chart_data: Dict[str, Any],
                                  chart_type: str, show_limits: bool = True) -> str:
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

        s = chart_style.semantic()
        ax.plot(xp, data_p, "o-", color=s["data"],
                markersize=ms, linewidth=lw, label="CUSUM+")
        ax.plot(xm, [-v for v in data_m], "s-", color=s["data_alt"],
                markersize=ms, linewidth=lw, label="CUSUM-")
        ax.axhline(y=0, color=s["center"], linestyle="-",
                   linewidth=1.2, label="CL=0")
        if show_limits:
            ax.axhline(y=ucl, color=s["limit"], linestyle="--",
                       linewidth=1.2, label=f"h={ucl:.3f}")
            ax.axhline(y=lcl, color=s["limit"], linestyle="--",
                       linewidth=1.2, label=f"-h={lcl:.3f}")
        ax.set_ylabel("CUSUM", fontsize=FONT_SIZE_LABEL)

        vx, vy = [], []
        for v in violations:
            pt = v.get("point", 0) - 1
            if 0 <= pt < len(cusum_plus):
                if "CUSUM+" in str(v.get("rule", "")):
                    vx.append(pt + 1), vy.append(cusum_plus[pt])
                else:
                    vx.append(pt + 1), vy.append(-cusum_minus[pt])
        chart_style.mark_violations(ax, vx, vy, size=9)
        chart_style.smart_ylim(ax, data_p, [-v for v in data_m], ucl, lcl, 0)

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

        s = chart_style.semantic()
        ax.plot(xr, data_r, "o", color=s["text_muted"], markersize=ms - 1,
                label="原始数据")
        ax.plot(xe, data_e, "o-", color=s["data"],
                markersize=ms, linewidth=1.5, label="EWMA")
        ax.axhline(y=cl, color=s["center"], linestyle="-",
                   linewidth=1.2, label=f"CL={cl:.3f}")

        n_full = len(ewma_data)
        if show_limits and isinstance(ucl, list) and len(ucl) == n_full:
            idxs = [x - 1 for x in xe] if was_e else list(range(n_full))
            ucl_thin = [ucl[i] for i in idxs]
            lcl_thin = [lcl[i] for i in idxs]
            x_axis = xe if was_e else list(range(1, n_full + 1))
            ax.plot(x_axis, ucl_thin, "--", color=s["limit"],
                    linewidth=1.2, label="UCL")
            ax.plot(x_axis, lcl_thin, "--", color=s["limit"],
                    linewidth=1.2, label="LCL")
        elif show_limits:
            ax.axhline(y=chart.get("ucl_const", 0),
                       color=s["limit"],
                       linestyle="--", linewidth=1.2, label="Steady UCL")
            ax.axhline(y=chart.get("lcl_const", 0),
                       color=s["limit"],
                       linestyle="--", linewidth=1.2, label="Steady LCL")
        ax.set_ylabel("EWMA", fontsize=FONT_SIZE_LABEL)

        vx = [v.get("point", 0) for v in violations
              if 1 <= v.get("point", 0) <= len(ewma_data)]
        chart_style.mark_violations(ax, vx, [ewma_data[pt - 1] for pt in vx],
                                    size=9)
        chart_style.smart_ylim(ax, data_e, data_r, cl,
                               ucl if isinstance(ucl, list) else [ucl],
                               lcl if isinstance(lcl, list) else [lcl])

    ax.set_xlabel(i18n.tr("chart.subgroup_no"), fontsize=FONT_SIZE_LABEL)
    chart_style.style_axes(ax, grid="y", legend=True)
    return note


def _draw_spec_lines(ax: plt.Axes, chart_data: Dict[str, Any]) -> List[float]:
    """绘制规格限参考线（USL/LSL），返回纳入的数值（供 y 轴范围计算）。

    来源: chart_data["spec"] = {"usl": float, "lsl": float}，或顶层 usl/lsl。
    与 UCL/LCL 区分: 橙色点划线 + USL/LSL 前缀（统一取自 chart_style）。
    """
    spec = chart_data.get("spec") or {}
    usl = spec.get("usl", chart_data.get("usl"))
    lsl = spec.get("lsl", chart_data.get("lsl"))
    if usl is None and lsl is None:
        return []
    return chart_style.add_limit_lines(ax, usl=usl, lsl=lsl, orientation="h")


def create_capability_chart(
    cap_data: Dict[str, Any],
    original_data: np.ndarray,
    title: str = "",
    options: Dict[str, Any] = None,
) -> Figure:
    _ensure_font()
    opts = options or {}
    label_fontsize = opts.get("label_fontsize", FONT_SIZE_LABEL)
    show_grid = opts.get("show_grid", True)
    show_limits = opts.get("show_limits", True)

    if original_data is None or len(original_data) == 0:
        fig, ax = plt.subplots(figsize=(8, 5), dpi=_dpi())
        ax.text(0.5, 0.5, "无数据", ha="center", va="center", fontsize=14)
        return fig

    fig, axes = plt.subplots(2, 1, figsize=(10, 8), dpi=_dpi(),
                              gridspec_kw={"height_ratios": [3, 1]})

    ax_hist = axes[0]
    ax_stats = axes[1]

    s = chart_style.semantic()
    ax_hist.hist(original_data, bins=min(50, int(np.sqrt(len(original_data))) * 2),
                 color=s["data"], alpha=0.55, edgecolor=s["panel"], density=True)

    mean = cap_data.get("summary", {}).get("mean", np.mean(original_data))
    std = cap_data.get("summary", {}).get("std_overall", np.std(original_data, ddof=1))
    x_range = np.linspace(min(original_data), max(original_data), 200)
    from scipy import stats as sp_stats
    y_norm = sp_stats.norm.pdf(x_range, mean, std)
    ax_hist.plot(x_range, y_norm, "-", color=s["fit"], linewidth=1.8,
                 label=i18n.tr("chart.norm_fit"))

    cap = cap_data.get("capability", {})
    usl = cap.get("usl")
    lsl = cap.get("lsl")
    if show_limits:
        chart_style.add_limit_lines(ax_hist, usl=usl, lsl=lsl, orientation="v")

    ax_hist.set_ylabel(i18n.tr("chart.density"), fontsize=label_fontsize)
    chart_style.style_axes(ax_hist, grid="y" if show_grid else None, legend=True)

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
                  color=chart_style.semantic()["text"],
                  bbox=dict(boxstyle="round", facecolor=chart_style.semantic()["panel"],
                            edgecolor=chart_style.semantic()["axis"], alpha=0.9))

    if title:
        fig.suptitle(title, fontsize=FONT_SIZE_TITLE, fontweight="bold",
                     color=chart_style.semantic()["text"])
    chart_style.finalize_figure(fig, pad=1.6)

    return fig


def create_pareto_chart(
    labels: List[str],
    values: List[float],
    title: str = "Pareto图",
    options: Dict[str, Any] = None,
) -> Figure:
    _ensure_font()
    opts = options or {}
    label_rotation = opts.get("label_rotation", 45)
    label_fontsize = opts.get("label_fontsize", FONT_SIZE_TICK)
    show_cumulative = opts.get("show_cumulative", True)
    show_grid = opts.get("show_grid", True)

    fig, ax1 = plt.subplots(figsize=(10, 5), dpi=_dpi())

    total = sum(values)

    sorted_indices = np.argsort(values)[::-1]
    sorted_labels = [labels[i] for i in sorted_indices]
    sorted_values = [values[i] for i in sorted_indices]

    cumulative = np.cumsum(sorted_values) / total * 100 if total > 0 else np.zeros_like(sorted_values)

    s = chart_style.semantic()
    ax1.bar(range(len(sorted_labels)), sorted_values, color=s["data"], alpha=0.85,
            edgecolor=s["panel"], linewidth=0.6)
    ax1.set_ylabel("效应绝对值", fontsize=FONT_SIZE_LABEL)
    ax1.set_xticks(range(len(sorted_labels)))
    ax1.set_xticklabels(sorted_labels, rotation=label_rotation, ha="right", fontsize=label_fontsize)

    if show_cumulative:
        ax2 = ax1.twinx()
        ax2.plot(range(len(sorted_labels)), cumulative, "o-", color=s["fit"],
                 linewidth=1.8, markersize=5)
        ax2.set_ylabel("累计百分比 (%)", fontsize=FONT_SIZE_LABEL, color=s["fit"])
        ax2.tick_params(axis="y", colors=s["fit"])
        ax2.set_ylim(0, 105)
        chart_style.style_axes(ax2, grid=None, hide_spines=("top",))

    if show_grid:
        chart_style.style_axes(ax1, grid="y")
    chart_style.smart_ylim(ax1, sorted_values, include_zero=True)
    if title:
        ax1.set_title(title, fontsize=FONT_SIZE_TITLE, fontweight="bold")
    chart_style.finalize_figure(fig)

    return fig


def create_histogram(data: np.ndarray, title: str = "", bins: int = 0, options: Dict[str, Any] = None) -> Figure:
    _ensure_font()
    opts = options or {}
    label_fontsize = opts.get("label_fontsize", FONT_SIZE_LABEL)
    show_grid = opts.get("show_grid", True)
    show_mean = opts.get("show_mean", True)
    show_density = opts.get("show_density", False)
    histtype = opts.get("histtype", "bar")

    fig, ax = plt.subplots(figsize=(8, 5), dpi=_dpi())

    if not bins:
        bins = opts.get("bins", min(50, int(np.sqrt(len(data))) * 2))
    bins = int(bins)  # 滑块经缩放还原可能为 45.0 之类整数值浮点，numpy 不接受 float bins

    s = chart_style.semantic()
    ax.hist(data, bins=bins, color=s["data"], alpha=0.75, edgecolor=s["panel"],
            histtype=histtype)

    if show_mean:
        ax.axvline(x=np.mean(data), color=s["center"], linestyle="--",
                   linewidth=1.5, label=f"Mean={np.mean(data):.4f}")

    if show_density and len(data) > 1:
        from scipy import stats as sp_stats
        x_range = np.linspace(data.min(), data.max(), 200)
        kde = sp_stats.gaussian_kde(data)
        ax.plot(x_range, kde(x_range) * len(data) * (data.max() - data.min()) / bins,
                color=s["fit"], linewidth=2, label="Density")

    ax.set_xlabel("数值", fontsize=label_fontsize)
    ax.set_ylabel("频次", fontsize=label_fontsize)
    chart_style.style_axes(ax, grid="y" if show_grid else None,
                           legend=bool(ax.get_legend_handles_labels()[0]))
    chart_style.finalize_figure(fig)

    if title:
        ax.set_title(title, fontsize=FONT_SIZE_TITLE, fontweight="bold")

    return fig


def create_pie_chart(
    labels: List[str],
    values: List[float],
    title: str = "",
    options: Dict[str, Any] = None,
) -> Figure:
    _ensure_font()
    opts = options or {}
    label_fontsize = opts.get("label_fontsize", 11)
    min_slice_percent = opts.get("min_slice_percent", 5) / 100
    explode_amount = opts.get("explode_amount", 2) / 100
    label_position = opts.get("label_position", "outside")
    show_percentage = opts.get("show_percentage", True)
    show_labels = opts.get("show_labels", True)

    total = sum(values)
    if total == 0:
        fig, ax = plt.subplots(figsize=(8, 6), dpi=_dpi())
        ax.text(0.5, 0.5, "无数据", ha="center", va="center", fontsize=14)
        return fig

    new_labels, new_sizes = [], []
    other_size = 0
    for label, size in zip(labels, values, strict=True):
        if size / total >= min_slice_percent:
            new_labels.append(label)
            new_sizes.append(size)
        else:
            other_size += size
    if other_size > 0:
        new_labels.append("其他")
        new_sizes.append(other_size)

    explode = [explode_amount if s / sum(new_sizes) < 0.1 else 0 for s in new_sizes]

    if label_position == "autopct":
        autopct_str = "%1.1f%%" if show_percentage else ""
    elif show_percentage:
        autopct_str = "%1.1f%%"
    else:
        autopct_str = ""

    fig, ax = plt.subplots(figsize=(8, 6), dpi=_dpi())
    result = ax.pie(
        new_sizes,
        labels=new_labels if show_labels else None,
        explode=explode,
        autopct=autopct_str if show_percentage else None,
        startangle=90,
        colors=chart_style.palette(len(new_sizes)),
        wedgeprops={"edgecolor": chart_style.semantic()["panel"], "linewidth": 1.0},
        textprops={"fontsize": label_fontsize,
                   "color": chart_style.semantic()["text"]},
    )

    try:
        _wedges, _texts, autotexts = result
    except ValueError:
        _wedges, _texts = result
        autotexts = []

    if show_percentage and autotexts:
        for at in autotexts:
            at.set_fontsize(max(label_fontsize - 2, 8))

    if title:
        ax.set_title(title, fontsize=FONT_SIZE_TITLE, fontweight="bold")

    return fig


def figure_to_bytes(fig: Figure, fmt: str = "png") -> io.BytesIO:
    buf = io.BytesIO()
    fig.savefig(buf, format=fmt, dpi=_dpi(), bbox_inches="tight")
    buf.seek(0)
    plt.close(fig)
    return buf


def save_figure(fig: Figure, file_path: str) -> str:
    fig.savefig(file_path, dpi=_dpi(), bbox_inches="tight")
    plt.close(fig)
    return file_path


def create_correlation_heatmap(df, numeric_cols=None, title="相关矩阵热力图") -> Figure:
    """兼容入口 — 新版实现在 analysis/charts/heatmap.py"""
    from analysis.charts.heatmap import create_correlation_heatmap as _new
    return _new(df, numeric_cols=numeric_cols, title=title)
