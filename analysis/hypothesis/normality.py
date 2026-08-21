"""
正态性检验 & 方差齐性检验
"""

from typing import Dict, Any, List
import numpy as np
import pandas as pd
from scipy import stats


def normality_test(data: pd.Series, confidence_level: float = 0.95) -> Dict[str, Any]:
    clean = data.dropna().astype(float)
    n = len(clean)
    if n < 3:
        raise ValueError(f"数据量不足: {n}")

    alpha = 1 - confidence_level

    results = {}

    if 3 <= n <= 5000:
        sw_stat, sw_p = stats.shapiro(clean)
        results["shapiro_wilk"] = {
            "statistic": round(float(sw_stat), 6),
            "p_value": round(float(sw_p), 6),
            "is_normal": sw_p > alpha,
        }

    # W21 fix: normaltest要求n≥8，n<8跳过
    if n >= 8:
        da_stat, da_p = stats.normaltest(clean)  # D'Agostino-Pearson
        results["dagostino_pearson"] = {
            "statistic": round(float(da_stat), 6),
            "p_value": round(float(da_p), 6),
            "is_normal": da_p > alpha,
        }

    mean_ks, std_ks = clean.mean(), clean.std(ddof=1)
    # W21 fix: std=0时跳过KS检验避免除零
    if std_ks > 0:
        ks_stat, ks_p = stats.kstest(clean, lambda x: stats.norm.cdf(x, loc=mean_ks, scale=std_ks))
    else:
        ks_stat, ks_p = 0.0, 1.0  # 常数数据视为正态
    results["kolmogorov_smirnov"] = {
        "statistic": round(float(ks_stat), 6),
        "p_value": round(float(ks_p), 6),
        "is_normal": ks_p > alpha,
    }

    qq_correlation = _qq_correlation(clean)
    results["qq_correlation"] = round(float(qq_correlation), 4)

    return {
        "test_type": "Normality Test",
        "sample_size": n,
        "confidence_level": confidence_level,
        "tests": results,
        "overall_conclusion": "正态分布" if results.get("shapiro_wilk", results.get("dagostino_pearson", {}).get("is_normal", False)).get("is_normal", False) else "非正态分布",
    }


def variance_test(*groups: pd.Series, confidence_level: float = 0.95) -> Dict[str, Any]:
    clean_groups = [g.dropna().astype(float).values for g in groups if len(g.dropna()) >= 2]
    if len(clean_groups) < 2:
        raise ValueError("需要至少2个有效组")

    alpha = 1 - confidence_level
    results = {}

    lev_stat, lev_p = stats.levene(*clean_groups)
    results["levene"] = {
        "statistic": round(float(lev_stat), 6),
        "p_value": round(float(lev_p), 6),
        "equal_variance": lev_p > alpha,
    }

    bart_stat, bart_p = stats.bartlett(*clean_groups)
    results["bartlett"] = {
        "statistic": round(float(bart_stat), 6),
        "p_value": round(float(bart_p), 6),
        "equal_variance": bart_p > alpha,
    }

    group_stats = []
    for i, g in enumerate(clean_groups):
        group_stats.append({
            "group": i + 1, "n": len(g),
            "std": round(float(np.std(g, ddof=1)), 6),
            "variance": round(float(np.var(g, ddof=1)), 6),
        })

    return {
        "test_type": "Variance Test",
        "num_groups": len(clean_groups),
        "confidence_level": confidence_level,
        "group_stats": group_stats,
        "tests": results,
        "overall_conclusion": "方差齐性" if lev_p > alpha else "方差不齐",
    }


def _qq_correlation(data: np.ndarray) -> float:
    n = len(data)
    sorted_data = np.sort(data)
    theoretical = stats.norm.ppf((np.arange(1, n + 1) - 0.5) / n)
    return float(np.corrcoef(sorted_data, theoretical)[0, 1])
