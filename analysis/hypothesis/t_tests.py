"""
假设检验模块 — t检验 (单样本/双样本/配对)
"""

from typing import Dict, Any, Optional
import numpy as np
import pandas as pd
from scipy import stats


def one_sample(data: pd.Series, pop_mean: float, alternative: str = "two-sided") -> Dict[str, Any]:
    clean = data.dropna().astype(float)
    n = len(clean)
    if n < 2:
        raise ValueError(f"数据量不足: {n}")

    t_stat, p_value = stats.ttest_1samp(clean, pop_mean)
    if alternative == "greater":
        p_value = p_value / 2 if t_stat > 0 else 1 - p_value / 2
    elif alternative == "less":
        p_value = p_value / 2 if t_stat < 0 else 1 - p_value / 2

    mean = float(np.mean(clean))
    std = float(np.std(clean, ddof=1))
    se = std / np.sqrt(n)
    ci = stats.t.interval(0.95, df=n - 1, loc=mean, scale=se)

    return {
        "test_type": "One-Sample t-Test",
        "hypothesis": f"H0: μ = {pop_mean}",
        "alternative": alternative,
        "sample_size": n,
        "mean": round(mean, 6),
        "std_dev": round(std, 6),
        "se_mean": round(float(se), 6),
        "t_statistic": round(float(t_stat), 4),
        "p_value": round(float(p_value), 6),
        "ci_95": (round(float(ci[0]), 6), round(float(ci[1]), 6)),
        "is_significant": p_value < 0.05,
        "target_mean": pop_mean,
    }


def two_sample(
    group1: pd.Series,
    group2: pd.Series,
    equal_var: Optional[bool] = None,
    alternative: str = "two-sided",
) -> Dict[str, Any]:
    """双样本 t 检验

    equal_var 三态:
      - None: 自动选择 — 经 Levene 检验, 方差齐(p>=0.05)用 pooled, 否则 Welch
      - True: 强制等方差 (pooled)
      - False: 强制 Welch
    """
    g1 = group1.dropna().astype(float)
    g2 = group2.dropna().astype(float)

    if len(g1) < 2 or len(g2) < 2:
        raise ValueError("两组数据量均需 >= 2")

    lev_stat, lev_p = stats.levene(g1, g2)
    if equal_var is None:
        equal_var = bool(lev_p >= 0.05)  # 方差齐 → pooled; 方差不齐 → Welch

    t_stat, p_value = stats.ttest_ind(g1, g2, equal_var=equal_var)
    if alternative == "greater":
        p_value = p_value / 2 if t_stat > 0 else 1 - p_value / 2
    elif alternative == "less":
        p_value = p_value / 2 if t_stat < 0 else 1 - p_value / 2

    mean1, mean2 = float(np.mean(g1)), float(np.mean(g2))
    std1, std2 = float(np.std(g1, ddof=1)), float(np.std(g2, ddof=1))

    return {
        "test_type": "Two-Sample t-Test",
        "hypothesis": "H0: μ1 - μ2 = 0",
        "alternative": alternative,
        "equal_variance_assumed": equal_var,
        "group1": {
            "sample_size": len(g1), "mean": round(mean1, 6), "std_dev": round(std1, 6),
        },
        "group2": {
            "sample_size": len(g2), "mean": round(mean2, 6), "std_dev": round(std2, 6),
        },
        "difference": round(mean1 - mean2, 6),
        "t_statistic": round(float(t_stat), 4),
        "p_value": round(float(p_value), 6),
        "levene_statistic": round(float(lev_stat), 4),
        "levene_p_value": round(float(lev_p), 6),
        "is_significant": p_value < 0.05,
    }


def paired(before: pd.Series, after: pd.Series, alternative: str = "two-sided") -> Dict[str, Any]:
    # W19 fix: 按索引对齐后dropna，避免NaN位置不一致导致配对错位
    paired_df = pd.DataFrame({"before": before, "after": after}).dropna()
    b = paired_df["before"].astype(float)
    a = paired_df["after"].astype(float)
    common_len = len(b)

    if common_len < 2:
        raise ValueError(f"数据量不足: {common_len}")

    t_stat, p_value = stats.ttest_rel(b, a)
    if alternative == "greater":
        p_value = p_value / 2 if t_stat > 0 else 1 - p_value / 2
    elif alternative == "less":
        p_value = p_value / 2 if t_stat < 0 else 1 - p_value / 2

    diff = b.values - a.values

    return {
        "test_type": "Paired t-Test",
        "alternative": alternative,
        "pairs": common_len,
        "before_mean": round(float(np.mean(b)), 6),
        "after_mean": round(float(np.mean(a)), 6),
        "mean_difference": round(float(np.mean(diff)), 6),
        "std_difference": round(float(np.std(diff, ddof=1)), 6),
        "t_statistic": round(float(t_stat), 4),
        "p_value": round(float(p_value), 6),
        "is_significant": p_value < 0.05,
    }
