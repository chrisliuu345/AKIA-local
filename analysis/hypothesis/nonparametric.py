"""非参数检验 — Mann-Whitney U / Wilcoxon / Kruskal-Wallis"""

import numpy as np
from typing import Dict, Any, List
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
        clean_a = a[np.isfinite(a)]; clean_b = b[np.isfinite(b)]
        n = min(len(clean_a), len(clean_b))
        if n < 5: return {"error": f"样本量不足 ({n})"}
        stat, p = sp_stats.wilcoxon(clean_a[:n], clean_b[:n], alternative=alternative)
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
