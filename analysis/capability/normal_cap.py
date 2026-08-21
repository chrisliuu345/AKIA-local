"""
正态过程能力分析 — Cp, Cpk, Pp, Ppk
"""

from typing import Dict, Any, Optional
import numpy as np
import pandas as pd
from scipy import stats
from config.settings import CAPABILITY_GRADES, CONTROL_CHART_CONSTANTS


def analyze(
    data: pd.Series,
    usl: Optional[float] = None,
    lsl: Optional[float] = None,
    target: Optional[float] = None,
    subgroup_size: int = 5,
) -> Dict[str, Any]:
    clean = data.dropna().values.astype(float)
    n = len(clean)
    if n < 2:
        raise ValueError(f"数据量不足: {n}")

    mean = float(np.mean(clean))
    std_overall = float(np.std(clean, ddof=1))
    std_within = float(_estimate_within_sigma(clean, subgroup_size))

    result = {
        "chart_type": "Normal Capability",
        "summary": {
            "sample_size": n,
            "mean": round(mean, 6),
            "std_overall": round(std_overall, 6),
            "std_within": round(std_within, 6),
            "subgroup_size": subgroup_size,
        },
    }

    if usl is not None and lsl is not None:
        usl, lsl = float(usl), float(lsl)
        # W23 fix: std=0时用None替代inf，避免json.dumps抛异常
        if std_within > 0:
            cp = (usl - lsl) / (6 * std_within)
            cpk = min((usl - mean) / (3 * std_within), (mean - lsl) / (3 * std_within))
        else:
            cp, cpk = None, None
        if std_overall > 0:
            pp = (usl - lsl) / (6 * std_overall)
            ppk = min((usl - mean) / (3 * std_overall), (mean - lsl) / (3 * std_overall))
        else:
            pp, ppk = None, None

        if std_overall > 0:
            z_usl = (usl - mean) / std_overall
            z_lsl = (mean - lsl) / std_overall
            ppm_usl = stats.norm.sf(z_usl) * 1e6
            ppm_lsl = stats.norm.cdf(-z_lsl) * 1e6
        else:
            z_usl, z_lsl = 0.0, 0.0
            ppm_usl, ppm_lsl = 0.0, 0.0
        ppm_total = ppm_usl + ppm_lsl

        expected_within = stats.norm.cdf((usl - mean) / std_within) - stats.norm.cdf((lsl - mean) / std_within) if std_within > 0 else 1

        result["capability"] = {
            "usl": float(usl),
            "lsl": float(lsl),
            "target": float(target) if target is not None else None,
            "cp": round(float(cp), 4) if cp is not None else None,
            "cpk": round(float(cpk), 4) if cpk is not None else None,
            "pp": round(float(pp), 4) if pp is not None else None,
            "ppk": round(float(ppk), 4) if ppk is not None else None,
            "ppm_total": round(float(ppm_total), 2),
            "ppm_usl": round(float(ppm_usl), 2),
            "ppm_lsl": round(float(ppm_lsl), 2),
            "expected_yield_within": round(float(expected_within * 100), 2),
            "expected_yield_overall": round(float((1 - ppm_total / 1e6) * 100), 2),
            "grade": _get_capability_grade(cpk) if cpk is not None else "N/A",
            "sigma_level": round(float(min(cpk * 3, 6)), 2) if cpk is not None else None,
        }
    elif usl is not None:
        result["capability"] = {
            "usl": float(usl),
            "lsl": None,
            "cpu": round(float((usl - mean) / (3 * std_within)), 4) if std_within > 0 else None,
            "ppu": round(float((usl - mean) / (3 * std_overall)), 4) if std_overall > 0 else None,
        }
    elif lsl is not None:
        result["capability"] = {
            "usl": None,
            "lsl": float(lsl),
            "cpl": round(float((mean - lsl) / (3 * std_within)), 4) if std_within > 0 else None,
            "ppl": round(float((mean - lsl) / (3 * std_overall)), 4) if std_overall > 0 else None,
        }
    else:
        result["capability"] = {"usl": None, "lsl": None}

    if n <= 5000 and n >= 3:
        # W22 fix: shapiro要求n≥3，n<3跳过
        normality_result = stats.shapiro(clean)
    else:
        normality_result = stats.kstest(clean, lambda x: stats.norm.cdf(x, loc=mean, scale=std_overall))
    result["normality"] = {
        "statistic": round(float(normality_result.statistic), 6),
        "p_value": round(float(normality_result.pvalue), 6),
        "is_normal": normality_result.pvalue > 0.05,
    }

    return result


def _estimate_within_sigma(data: np.ndarray, subgroup_size: int) -> float:
    if len(data) < subgroup_size * 2:
        return float(np.std(data, ddof=1))

    num_subgroups = len(data) // subgroup_size
    trimmed = data[:num_subgroups * subgroup_size]
    subgroups = trimmed.reshape(num_subgroups, subgroup_size)
    r_bar = np.mean(np.max(subgroups, axis=1) - np.min(subgroups, axis=1))

    const = CONTROL_CHART_CONSTANTS.get(subgroup_size, {})
    d2 = const.get("d2")

    if d2 and subgroup_size <= 25:
        return r_bar / d2

    s_bar = np.mean(np.std(subgroups, ddof=1, axis=1))
    c4 = const.get("c4")
    if c4 and subgroup_size <= 25:
        return s_bar / c4

    return np.sqrt(np.mean(np.var(subgroups, ddof=1, axis=1)))


def _get_capability_grade(cpk: float) -> str:
    for grade, (low, high, desc) in CAPABILITY_GRADES.items():
        if low <= cpk < high:
            return f"{grade} ({desc})"
    return "D (差)"
