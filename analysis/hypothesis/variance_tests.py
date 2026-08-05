"""
方差齐性检验
"""

from typing import Dict, Any, List
import numpy as np
import pandas as pd
from scipy import stats


def variance_tests(*groups: pd.Series, confidence_level: float = 0.95) -> Dict[str, Any]:
    clean_groups = [g.dropna().astype(float).values for g in groups if len(g.dropna()) >= 2]
    if len(clean_groups) < 2:
        raise ValueError("需要至少2个有效组")

    alpha = 1 - confidence_level
    results = {}

    lev_stat, lev_p = stats.levene(*clean_groups)
    results["levene"] = {
        "statistic": round(float(lev_stat), 4),
        "p_value": round(float(lev_p), 6),
        "equal_variance": lev_p > alpha,
    }

    bart_stat, bart_p = stats.bartlett(*clean_groups)
    results["bartlett"] = {
        "statistic": round(float(bart_stat), 4),
        "p_value": round(float(bart_p), 6),
        "equal_variance": bart_p > alpha,
    }

    grouped = []
    for i, g in enumerate(clean_groups):
        grouped.append({
            "group": i + 1,
            "n": len(g),
            "mean": round(float(np.mean(g)), 6),
            "std": round(float(np.std(g, ddof=1)), 6),
            "variance": round(float(np.var(g, ddof=1)), 6),
        })

    return {
        "test_type": "Variance Equality",
        "num_groups": len(clean_groups),
        "confidence_level": confidence_level,
        "groups": grouped,
        "tests": results,
        "overall_conclusion": "方差齐性" if lev_p > alpha else "方差不齐",
    }
