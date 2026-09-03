"""
量具R&R分析 — 交叉(Crossed)和嵌套(Nested)
"""

from typing import Dict, Any
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
    ev_pct = ev

    r_op = float(op_means.max() - op_means.min())
    d2_star_op = _cfg.MSA_D2_STAR.get(o, _cfg.CONTROL_CHART_CONSTANTS.get(o, {}).get("d2", 1.128))
    av = np.sqrt(max((r_op / d2_star_op) ** 2 - ev ** 2 / (p * r), 0))
    av_pct = av

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
