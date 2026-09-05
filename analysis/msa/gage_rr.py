"""
量具R&R分析 — 交叉(Crossed)和嵌套(Nested)

增强功能:
- 方差分量图数据
- 交互效应图数据
- 不确定度预算 (GUM 方法)
"""

from typing import Dict, Any, Optional
import numpy as np
import pandas as pd
from config import settings as _cfg


def analyze_crossed(
    df: pd.DataFrame,
    measurement_col: str,
    part_col: str,
    operator_col: str,
    tolerance: Optional[float] = None,
) -> Dict[str, Any]:
    data = df.copy()
    data[measurement_col] = pd.to_numeric(data[measurement_col], errors="coerce")
    data = data.dropna(subset=[measurement_col, part_col, operator_col])

    parts = data[part_col].unique()
    operators = data[operator_col].unique()
    p, o = len(parts), len(operators)

    if p < 2 or o < 2:
        raise ValueError(f"需要至少2个零件和2个操作员，当前零件={p}, 操作员={o}")

    repeats = data.groupby([part_col, operator_col]).size()
    r = int(repeats.mode().iloc[0])

    overall_mean = float(data[measurement_col].mean())

    part_means = data.groupby(part_col)[measurement_col].mean()
    op_means = data.groupby(operator_col)[measurement_col].mean()

    r_bar = _avg_range(data, measurement_col, part_col, operator_col)
    d2 = _cfg.CONTROL_CHART_CONSTANTS.get(r, {}).get("d2", 1.128 * (r ** 0.3))

    ev = r_bar / d2

    r_op = float(op_means.max() - op_means.min())
    d2_star_op = _cfg.MSA_D2_STAR.get(o, _cfg.CONTROL_CHART_CONSTANTS.get(o, {}).get("d2", 1.128))
    av = np.sqrt(max((r_op / d2_star_op) ** 2 - ev ** 2 / (p * r), 0))

    grr = np.sqrt(ev ** 2 + av ** 2)
    r_part = float(part_means.max() - part_means.min())
    d2_star_part = _cfg.MSA_D2_STAR.get(p, _cfg.CONTROL_CHART_CONSTANTS.get(p, {}).get("d2", 1.128))
    pv = r_part / d2_star_part

    tv = np.sqrt(grr ** 2 + pv ** 2)

    grr_pct_tv = (grr / tv * 100) if tv > 0 else 0
    grr_pct_tol = (grr / tolerance * 100) if tolerance else None
    ndc = int(1.41 * (pv / grr)) if grr > 0 else 0
    ev_pct = (ev / tv * 100) if tv > 0 else 0
    av_pct = (av / tv * 100) if tv > 0 else 0
    pv_pct = (pv / tv * 100) if tv > 0 else 0

    variance_chart = _variance_component_data(ev, av, pv, grr, tv)
    interaction_chart = _interaction_chart_data(data, measurement_col, part_col, operator_col)
    uncertainty = _uncertainty_budget(ev, av, pv, grr, tv, p, o, r, tolerance)

    return {
        "chart_type": "Gage R&R (Crossed)",
        "design": {"parts": p, "operators": o, "replicates": r, "total_measurements": len(data)},
        "variance_components": {
            "ev": round(float(ev), 6),
            "av": round(float(av), 6),
            "grr": round(float(grr), 6),
            "pv": round(float(pv), 6),
            "tv": round(float(tv), 6),
        },
        "percentages": {
            "ev_pct": round(float(ev_pct), 2),
            "av_pct": round(float(av_pct), 2),
            "grr_pct_tv": round(float(grr_pct_tv), 2),
            "grr_pct_tol": round(float(grr_pct_tol), 2) if grr_pct_tol is not None else None,
            "pv_pct": round(float(pv_pct), 2),
        },
        "ndc": ndc,
        "acceptance": _grr_acceptance(grr_pct_tv, ndc),
        "tolerance": float(tolerance) if tolerance else None,
        "summary": {
            "overall_mean": round(overall_mean, 6),
            "r_bar": round(float(r_bar), 6),
        },
        "variance_chart": variance_chart,
        "interaction_chart": interaction_chart,
        "uncertainty": uncertainty,
    }


def analyze_nested(
    df: pd.DataFrame,
    measurement_col: str,
    part_col: str,
    operator_col: str,
    tolerance: Optional[float] = None,
) -> Dict[str, Any]:
    data = df.copy()
    data[measurement_col] = pd.to_numeric(data[measurement_col], errors="coerce")
    data = data.dropna(subset=[measurement_col, part_col, operator_col])

    overall_mean = float(data[measurement_col].mean())
    grand_std = float(data[measurement_col].std(ddof=1))

    groups = data.groupby([operator_col, part_col])[measurement_col]
    r_bar = groups.apply(lambda x: x.max() - x.min() if len(x) > 1 else 0).mean()
    r = int(groups.size().mode().iloc[0] if not groups.size().empty else 1)

    d2 = _cfg.CONTROL_CHART_CONSTANTS.get(r, {}).get("d2", 1.128)
    ev = float(r_bar) / d2 if d2 > 0 else 0
    tv = grand_std
    pv = np.sqrt(max(tv ** 2 - ev ** 2, 0))

    grr = ev
    grr_pct = (ev / tv * 100) if tv > 0 else 0
    ndc = int(1.41 * (pv / ev)) if ev > 0 else 0

    return {
        "chart_type": "Gage R&R (Nested)",
        "design": {"total_measurements": len(data), "approximate_replicates": r},
        "variance_components": {
            "ev": round(float(ev), 6),
            "pv": round(float(pv), 6),
            "tv": round(float(tv), 6),
        },
        "percentages": {
            "grr_pct_tv": round(float(grr_pct), 2),
        },
        "ndc": ndc,
        "acceptance": _grr_acceptance(grr_pct, ndc),
        "tolerance": float(tolerance) if tolerance else None,
        "summary": {
            "overall_mean": round(overall_mean, 6),
            "r_bar": round(float(r_bar), 6),
        },
    }


def _avg_range(df: pd.DataFrame, measurement_col: str, part_col: str, operator_col: str) -> float:
    ranges = []
    for (part, op), group in df.groupby([part_col, operator_col]):
        if len(group) >= 2:
            ranges.append(group[measurement_col].max() - group[measurement_col].min())
    return float(np.mean(ranges)) if ranges else 0.0


def _variance_component_data(
    ev: float, av: float, pv: float, grr: float, tv: float
) -> Dict[str, Any]:
    """
    方差分量图数据

    用于绘制 EV/AV/PV/GRR 的条形图
    """
    components = [
        {"name": "EV (重复性)", "value": round(float(ev ** 2), 6), "pct": round(float(ev ** 2 / tv ** 2 * 100), 2) if tv > 0 else 0},
        {"name": "AV (再现性)", "value": round(float(av ** 2), 6), "pct": round(float(av ** 2 / tv ** 2 * 100), 2) if tv > 0 else 0},
        {"name": "GRR (量具R&R)", "value": round(float(grr ** 2), 6), "pct": round(float(grr ** 2 / tv ** 2 * 100), 2) if tv > 0 else 0},
        {"name": "PV (零件间)", "value": round(float(pv ** 2), 6), "pct": round(float(pv ** 2 / tv ** 2 * 100), 2) if tv > 0 else 0},
        {"name": "TV (总变异)", "value": round(float(tv ** 2), 6), "pct": 100.0},
    ]

    return {
        "components": components,
        "standard_deviation": [
            {"name": "EV", "value": round(float(ev), 6)},
            {"name": "AV", "value": round(float(av), 6)},
            {"name": "GRR", "value": round(float(grr), 6)},
            {"name": "PV", "value": round(float(pv), 6)},
            {"name": "TV", "value": round(float(tv), 6)},
        ],
    }


def _interaction_chart_data(
    df: pd.DataFrame,
    measurement_col: str,
    part_col: str,
    operator_col: str,
) -> Dict[str, Any]:
    """
    交互效应图数据

    绘制零件×操作员的均值连线图
    """
    pivot = df.pivot_table(
        values=measurement_col,
        index=part_col,
        columns=operator_col,
        aggfunc="mean",
    )

    operators = pivot.columns.tolist()
    parts = pivot.index.tolist()

    series = []
    for op in operators:
        op_means = pivot[op].values
        series.append({
            "name": str(op),
            "data": [round(float(x), 4) for x in op_means],
        })

    overall_means = pivot.mean(axis=1).values

    return {
        "categories": parts,
        "series": series,
        "overall_means": [round(float(x), 4) for x in overall_means],
    }


def _uncertainty_budget(
    ev: float,
    av: float,
    pv: float,
    grr: float,
    tv: float,
    p: int,
    o: int,
    r: int,
    tolerance: Optional[float],
) -> Dict[str, Any]:
    """
    不确定度预算 (GUM 方法)

    基于 Gage R&R 结果计算测量不确定度
    """
    u_repeatability = ev / np.sqrt(2)
    u_reproducibility = av / np.sqrt(2)
    u_grr = grr / np.sqrt(2)

    u_combined = np.sqrt(u_repeatability ** 2 + u_reproducibility ** 2)

    k = 2
    u_expanded = k * u_combined

    if tolerance is not None:
        t_ratio = u_expanded / (tolerance / 2) if tolerance > 0 else 0
    else:
        t_ratio = None

    return {
        "standard_uncertainty": {
            "repeatability": round(float(u_repeatability), 6),
            "reproducibility": round(float(u_reproducibility), 6),
            "gage_rr": round(float(u_grr), 6),
        },
        "combined_uncertainty": round(float(u_combined), 6),
        "coverage_factor": k,
        "expanded_uncertainty": round(float(u_expanded), 6),
        "tolerance_ratio": round(float(t_ratio), 4) if t_ratio is not None else None,
        "interpretation": _uncertainty_interpretation(u_expanded, tolerance),
    }


def _uncertainty_interpretation(u_expanded: float, tolerance: Optional[float]) -> str:
    """不确定度解释"""
    if tolerance is None:
        return "未提供公差，无法判断不确定度是否可接受"

    t_ratio = u_expanded / (tolerance / 2) if tolerance > 0 else 0

    if t_ratio < 0.1:
        return "不确定度极小，测量系统非常适合"
    elif t_ratio < 0.3:
        return "不确定度较小，测量系统适合"
    elif t_ratio < 0.5:
        return "不确定度适中，测量系统可接受"
    elif t_ratio < 1.0:
        return "不确定度较大，测量系统边缘"
    else:
        return "不确定度过大，测量系统不可接受"


def _grr_acceptance(grr_pct: float, ndc: int) -> Dict[str, Any]:
    if grr_pct <= _cfg.MSA_GRR_ACCEPTABLE * 100 and ndc >= _cfg.MSA_NDC_THRESHOLD:
        level = "acceptable"
        message = "测量系统可接受"
    elif grr_pct <= _cfg.MSA_GRR_MARGINAL * 100:
        level = "marginal"
        message = "测量系统条件接受，建议改进"
    else:
        level = "unacceptable"
        message = "测量系统不可接受，需要改进"
    return {"level": level, "message": message}
