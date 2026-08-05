"""
方差分析 (ANOVA) — 单因素/双因素/一般线性模型
"""

from typing import Dict, Any, List
import numpy as np
import pandas as pd
from scipy import stats


def one_way(
    df: pd.DataFrame,
    measurement_col: str,
    factor_col: str,
) -> Dict[str, Any]:
    data = df.copy()
    data[measurement_col] = pd.to_numeric(data[measurement_col], errors="coerce")
    data = data.dropna(subset=[measurement_col, factor_col])

    groups = [group[measurement_col].dropna().values for _, group in data.groupby(factor_col)]
    groups = [g for g in groups if len(g) >= 2]

    if len(groups) < 2:
        raise ValueError(f"需要至少2个有效组, 当前 {len(groups)}")

    f_stat, p_value = stats.f_oneway(*groups)

    factor_levels = data[factor_col].unique()
    level_stats = []
    for level in factor_levels:
        ld = data[data[factor_col] == level][measurement_col]
        level_stats.append({
            "level": str(level),
            "n": len(ld),
            "mean": round(float(ld.mean()), 6),
            "std": round(float(ld.std(ddof=1)), 6),
        })

    ss_between = sum(len(g) * (g.mean() - data[measurement_col].mean()) ** 2 for g in groups)
    ss_within = sum(((g - g.mean()) ** 2).sum() for g in groups)
    ss_total = ss_between + ss_within
    df_between = len(groups) - 1
    df_within = len(data) - len(groups)

    return {
        "test_type": "One-Way ANOVA",
        "factor": factor_col,
        "levels": len(groups),
        "total_observations": len(data),
        "level_stats": level_stats,
        "f_statistic": round(float(f_stat), 4),
        "p_value": round(float(p_value), 6),
        "is_significant": p_value < 0.05,
        "anova_table": {
            "source": ["Between", "Within", "Total"],
            "ss": [round(float(ss_between), 4), round(float(ss_within), 4), round(float(ss_total), 4)],
            "df": [int(df_between), int(df_within), int(df_between + df_within)],
            "ms": [
                round(float(ss_between / df_between), 4) if df_between > 0 else 0,
                round(float(ss_within / df_within), 4) if df_within > 0 else 0,
                0,
            ],
        },
    }


def two_way(
    df: pd.DataFrame,
    measurement_col: str,
    factor_a_col: str,
    factor_b_col: str,
) -> Dict[str, Any]:
    data = df.copy()
    data[measurement_col] = pd.to_numeric(data[measurement_col], errors="coerce")
    data = data.dropna(subset=[measurement_col, factor_a_col, factor_b_col])

    groups = []
    labels_a = []
    labels_b = []
    for (a, b), group in data.groupby([factor_a_col, factor_b_col]):
        groups.append(group[measurement_col].values)
        labels_a.append(a)
        labels_b.append(b)

    grand_mean = data[measurement_col].mean()
    levels_a = sorted(data[factor_a_col].unique())
    levels_b = sorted(data[factor_b_col].unique())
    a, b_count = len(levels_a), len(levels_b)

    means_a = {lv: data[data[factor_a_col] == lv][measurement_col].mean() for lv in levels_a}
    means_b = {lv: data[data[factor_b_col] == lv][measurement_col].mean() for lv in levels_b}

    counts_a = {lv: len(data[data[factor_a_col] == lv]) for lv in levels_a}
    counts_b = {lv: len(data[data[factor_b_col] == lv]) for lv in levels_b}

    ss_a = sum(counts_a[lv] * (means_a[lv] - grand_mean) ** 2 for lv in levels_a)
    ss_b = sum(counts_b[lv] * (means_b[lv] - grand_mean) ** 2 for lv in levels_b)
    ss_total = ((data[measurement_col] - grand_mean) ** 2).sum()
    ss_error = ss_total - ss_a - ss_b

    df_a = a - 1
    df_b = b_count - 1
    df_error = len(data) - a - b_count + 1

    ms_a = ss_a / df_a if df_a > 0 else 0
    ms_b = ss_b / df_b if df_b > 0 else 0
    ms_e = ss_error / df_error if df_error > 0 else 1

    f_a = ms_a / ms_e if ms_e > 0 else 0
    f_b = ms_b / ms_e if ms_e > 0 else 0
    p_a = 1 - stats.f.cdf(f_a, df_a, df_error)
    p_b = 1 - stats.f.cdf(f_b, df_b, df_error)

    return {
        "test_type": "Two-Way ANOVA",
        "factors": [factor_a_col, factor_b_col],
        "levels": {"factor_a": a, "factor_b": b_count},
        "total_observations": len(data),
        "grand_mean": round(float(grand_mean), 6),
        "anova_table": {
            "source": [factor_a_col, factor_b_col, "Error", "Total"],
            "ss": [
                round(float(ss_a), 4), round(float(ss_b), 4),
                round(float(ss_error), 4), round(float(ss_total), 4),
            ],
            "df": [df_a, df_b, df_error, df_a + df_b + df_error],
            "ms": [
                round(float(ms_a), 4), round(float(ms_b), 4),
                round(float(ms_e), 4), 0,
            ],
            "f": [
                round(float(f_a), 4), round(float(f_b), 4),
                None, None,
            ],
            "p_value": [
                round(float(p_a), 6), round(float(p_b), 6),
                None, None,
            ],
        },
        "significant_factors": {
            factor_a_col: p_a < 0.05,
            factor_b_col: p_b < 0.05,
        },
    }
