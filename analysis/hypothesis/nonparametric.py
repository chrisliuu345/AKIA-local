"""非参数检验 — Mann-Whitney U / Wilcoxon / Kruskal-Wallis / Mood中位数 / Friedman"""

import numpy as np
from typing import Dict, Any
from scipy import stats as sp_stats


def mann_whitney(a: np.ndarray, b: np.ndarray, alternative: str = "two-sided") -> Dict[str, Any]:
    """Mann-Whitney U 检验 (两独立样本, 非参数 t-test 替代)"""
    clean_a = a[np.isfinite(a)]; clean_b = b[np.isfinite(b)]
    if len(clean_a) < 3 or len(clean_b) < 3:
        return {"error": f"样本量不足 (a={len(clean_a)}, b={len(clean_b)})"}
    stat, p = sp_stats.mannwhitneyu(clean_a, clean_b, alternative=alternative)
    return {
        "test": "Mann-Whitney U",
        "u_statistic": round(float(stat), 4),
        "p_value": round(float(p), 6),
        "n_a": len(clean_a), "n_b": len(clean_b),
        "median_a": round(float(np.median(clean_a)), 4),
        "median_b": round(float(np.median(clean_b)), 4),
        "significant": p < 0.05,
    }


def wilcoxon_signed_rank(a: np.ndarray, b: np.ndarray = None,
                         alternative: str = "two-sided") -> Dict[str, Any]:
    """Wilcoxon 符号秩检验 (配对样本或单样本)"""
    if b is not None:
        min_len = min(len(a), len(b))
        valid_mask = np.isfinite(a[:min_len]) & np.isfinite(b[:min_len])
        clean_a = a[:min_len][valid_mask]
        clean_b = b[:min_len][valid_mask]
        n = len(clean_a)
        if n < 5: return {"error": f"样本量不足 ({n})"}
        stat, p = sp_stats.wilcoxon(clean_a, clean_b, alternative=alternative)
        return {
            "test": "Wilcoxon Signed-Rank (paired)",
            "statistic": round(float(stat), 4),
            "p_value": round(float(p), 6),
            "n": n, "significant": p < 0.05,
        }
    else:
        clean = a[np.isfinite(a)]
        if len(clean) < 5: return {"error": f"样本量不足 ({len(clean)})"}
        stat, p = sp_stats.wilcoxon(clean, alternative=alternative)
        return {
            "test": "Wilcoxon Signed-Rank (one-sample)",
            "statistic": round(float(stat), 4),
            "p_value": round(float(p), 6),
            "n": len(clean), "significant": p < 0.05,
        }


def kruskal_wallis(*groups: np.ndarray) -> Dict[str, Any]:
    """Kruskal-Wallis H 检验 (多独立样本, 非参数 ANOVA 替代)"""
    clean_groups = [g[np.isfinite(g)] for g in groups]
    clean_groups = [g for g in clean_groups if len(g) >= 3]
    if len(clean_groups) < 2:
        return {"error": f"有效组数不足 ({len(clean_groups)})"}
    stat, p = sp_stats.kruskal(*clean_groups)
    return {
        "test": "Kruskal-Wallis H",
        "h_statistic": round(float(stat), 4),
        "p_value": round(float(p), 6),
        "n_groups": len(clean_groups),
        "n_total": sum(len(g) for g in clean_groups),
        "group_medians": [round(float(np.median(g)), 4) for g in clean_groups],
        "significant": p < 0.05,
    }


def mood_median_test(*groups: np.ndarray) -> Dict[str, Any]:
    """Mood 中位数检验

    检验多个独立样本是否来自具有相同中位数的总体。
    是Kruskal-Wallis检验的简化版本，更稳健但统计功效略低。

    H0: 所有组的中位数相等
    H1: 至少有一组的中位数不同

    Args:
        *groups: 多个独立样本数组

    Returns:
        Dict包含检验统计量、p值和结果
    """
    clean_groups = [g[np.isfinite(g)] for g in groups]
    clean_groups = [g for g in clean_groups if len(g) >= 2]

    if len(clean_groups) < 2:
        return {"error": f"有效组数不足 ({len(clean_groups)})，至少需要2组"}

    stat, p, medians, contingency = sp_stats.median_test(*clean_groups)

    overall_median = float(medians) if np.isscalar(medians) else float(medians[0])

    return {
        "test": "Mood's Median",
        "chi2_statistic": round(float(stat), 4),
        "p_value": round(float(p), 6),
        "n_groups": len(clean_groups),
        "n_total": sum(len(g) for g in clean_groups),
        "group_medians": [round(float(np.median(g)), 4) for g in clean_groups],
        "overall_median": round(overall_median, 4),
        "contingency_table": contingency.tolist(),
        "significant": p < 0.05,
    }


def friedman_test(*groups: np.ndarray) -> Dict[str, Any]:
    """Friedman 检验 (完全区组设计, 非参数重复测量 ANOVA 替代)

    适用于：
    - 同一受试者在不同条件下的测量
    - 配对或区组设计
    - 数据不满足正态分布假设

    H0: 所有处理的效应相同
    H1: 至少有一个处理的效应不同

    Args:
        *groups: 多个处理条件下的测量值，每组代表一个处理

    Returns:
        Dict包含检验统计量、p值和结果
    """
    clean_groups = [g[np.isfinite(g)] for g in groups]
    clean_groups = [g for g in clean_groups if len(g) >= 2]

    if len(clean_groups) < 2:
        return {"error": f"有效组数不足 ({len(clean_groups)})，至少需要2个处理"}

    n_samples = [len(g) for g in clean_groups]
    if len(set(n_samples)) > 1:
        return {"error": f"完全区组设计要求所有处理的样本量相同，当前样本量: {n_samples}"}

    if len(clean_groups) == 2:
        stat, p = sp_stats.wilcoxon(clean_groups[0], clean_groups[1])
        data_matrix = np.column_stack(clean_groups)
        ranks = np.apply_along_axis(lambda row: sp_stats.rankdata(row), 1, data_matrix)
        mean_ranks = np.mean(ranks, axis=0)

        return {
            "test": "Friedman (via Wilcoxon)",
            "chi2_statistic": round(float(stat), 4),
            "p_value": round(float(p), 6),
            "n_blocks": n_samples[0],
            "n_treatments": len(clean_groups),
            "n_total": n_samples[0] * len(clean_groups),
            "mean_ranks": [round(float(r), 4) for r in mean_ranks],
            "group_medians": [round(float(np.median(g)), 4) for g in clean_groups],
            "significant": p < 0.05,
        }

    stat, p = sp_stats.friedmanchisquare(*clean_groups)

    data_matrix = np.column_stack(clean_groups)
    ranks = np.apply_along_axis(lambda row: sp_stats.rankdata(row), 1, data_matrix)
    mean_ranks = np.mean(ranks, axis=0)

    return {
        "test": "Friedman",
        "chi2_statistic": round(float(stat), 4),
        "p_value": round(float(p), 6),
        "n_blocks": n_samples[0],
        "n_treatments": len(clean_groups),
        "n_total": n_samples[0] * len(clean_groups),
        "mean_ranks": [round(float(r), 4) for r in mean_ranks],
        "group_medians": [round(float(np.median(g)), 4) for g in clean_groups],
        "significant": p < 0.05,
    }
