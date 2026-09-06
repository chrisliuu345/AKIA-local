"""
等价检验 (TOST) — 单样本/双样本均值等价检验

TOST (Two One-Sided Tests) 用于证明两个均值之间的差异在临床上不重要。
"""

from typing import Dict, Any
import numpy as np
import pandas as pd
from scipy import stats


def one_sample_tost(
    data: pd.Series,
    target_mean: float,
    margin: float,
    alpha: float = 0.05,
) -> Dict[str, Any]:
    """
    单样本 TOST 等价检验

    H0: |μ - target| >= margin (不等价)
    H1: -margin < μ - target < margin (等价)

    Args:
        data: 样本数据
        target_mean: 目标均值
        margin: 等效边界（绝对值）
        alpha: 显著性水平

    Returns:
        检验结果字典
    """
    clean = data.dropna().astype(float)
    n = len(clean)
    if n < 2:
        raise ValueError(f"数据量不足: {n}")

    mean = float(np.mean(clean))
    std = float(np.std(clean, ddof=1))
    se = std / np.sqrt(n)

    t_low = (mean - target_mean + margin) / se
    t_high = (mean - target_mean - margin) / se

    df = n - 1
    p_low = 1 - stats.t.cdf(t_low, df)
    p_high = stats.t.cdf(t_high, df)

    p_tost = max(p_low, p_high)

    diff = mean - target_mean
    ci = stats.t.interval(1 - 2*alpha, df=df, loc=diff, scale=se)

    is_equivalent = p_tost < alpha

    return {
        "test_type": "One-Sample TOST",
        "hypothesis": f"H0: |μ - {target_mean}| >= {margin} (不等价)",
        "alternative": f"H1: -{margin} < μ - {target_mean} < {margin} (等价)",
        "sample_size": n,
        "mean": round(mean, 6),
        "std_dev": round(std, 6),
        "target_mean": target_mean,
        "margin": margin,
        "difference": round(diff, 6),
        "ci_lower": round(float(ci[0]), 6),
        "ci_upper": round(float(ci[1]), 6),
        "t_statistic_low": round(float(t_low), 4),
        "t_statistic_high": round(float(t_high), 4),
        "p_value_low": round(float(p_low), 6),
        "p_value_high": round(float(p_high), 6),
        "p_value": round(float(p_tost), 6),
        "alpha": alpha,
        "is_equivalent": is_equivalent,
        "interpretation": "等价" if is_equivalent else "不等价",
    }


def two_sample_tost(
    group1: pd.Series,
    group2: pd.Series,
    margin: float,
    alpha: float = 0.05,
    equal_var: bool = False,
) -> Dict[str, Any]:
    """
    双样本 TOST 等价检验

    H0: |μ1 - μ2| >= margin (不等价)
    H1: -margin < μ1 - μ2 < margin (等价)

    Args:
        group1: 样本1数据
        group2: 样本2数据
        margin: 等效边界（绝对值）
        alpha: 显著性水平
        equal_var: 是否假设等方差

    Returns:
        检验结果字典
    """
    g1 = group1.dropna().astype(float)
    g2 = group2.dropna().astype(float)

    if len(g1) < 2 or len(g2) < 2:
        raise ValueError("两组数据量均需 >= 2")

    n1, n2 = len(g1), len(g2)
    mean1, mean2 = float(np.mean(g1)), float(np.mean(g2))
    std1, std2 = float(np.std(g1, ddof=1)), float(np.std(g2, ddof=1))

    if equal_var:
        sp2 = ((n1 - 1) * std1**2 + (n2 - 1) * std2**2) / (n1 + n2 - 2)
        se = np.sqrt(sp2 * (1/n1 + 1/n2))
        df = n1 + n2 - 2
    else:
        se = np.sqrt(std1**2/n1 + std2**2/n2)
        df = (std1**2/n1 + std2**2/n2)**2 / (
            (std1**2/n1)**2/(n1-1) + (std2**2/n2)**2/(n2-1)
        )

    diff = mean1 - mean2

    t_low = (diff + margin) / se
    t_high = (diff - margin) / se

    p_low = 1 - stats.t.cdf(t_low, df)
    p_high = stats.t.cdf(t_high, df)

    p_tost = max(p_low, p_high)

    ci = stats.t.interval(1 - 2*alpha, df=df, loc=diff, scale=se)

    is_equivalent = p_tost < alpha

    return {
        "test_type": "Two-Sample TOST",
        "hypothesis": f"H0: |μ1 - μ2| >= {margin} (不等价)",
        "alternative": f"H1: -{margin} < μ1 - μ2 < {margin} (等价)",
        "group1": {
            "sample_size": n1,
            "mean": round(mean1, 6),
            "std_dev": round(std1, 6),
        },
        "group2": {
            "sample_size": n2,
            "mean": round(mean2, 6),
            "std_dev": round(std2, 6),
        },
        "margin": margin,
        "difference": round(diff, 6),
        "ci_lower": round(float(ci[0]), 6),
        "ci_upper": round(float(ci[1]), 6),
        "t_statistic_low": round(float(t_low), 4),
        "t_statistic_high": round(float(t_high), 4),
        "p_value_low": round(float(p_low), 6),
        "p_value_high": round(float(p_high), 6),
        "p_value": round(float(p_tost), 6),
        "alpha": alpha,
        "equal_variance": equal_var,
        "is_equivalent": is_equivalent,
        "interpretation": "等价" if is_equivalent else "不等价",
    }
