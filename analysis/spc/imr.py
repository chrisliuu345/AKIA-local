"""
I-MR (单值-移动极差) 控制图分析
"""

from typing import Dict, Any, List
import numpy as np
import pandas as pd
from ._rules import check_all_nelson_rules


def analyze(data: pd.Series) -> Dict[str, Any]:
    n = len(data)
    if n < 2:
        raise ValueError(f"数据量不足: 需要至少 2 点, 当前 {n}")

    values = data.values.astype(float)

    mr = np.abs(np.diff(values))
    mr = np.insert(mr, 0, np.nan)

    x_bar = np.nanmean(values)
    mr_bar = np.nanmean(mr[1:])

    d2 = 1.128  # n=2 for moving range
    sigma_hat = mr_bar / d2

    i_ucl = x_bar + 3 * sigma_hat
    i_lcl = x_bar - 3 * sigma_hat
    i_cl = x_bar

    mr_ucl = 3.267 * mr_bar  # D4 for n=2
    mr_lcl = 0.0
    mr_cl = mr_bar

    i_violations = check_all_nelson_rules(values, x_bar, sigma_hat)
    mr_violations = _check_mr_violations(mr[1:], mr_ucl)

    return {
        "chart_type": "I-MR",
        "num_points": n,
        "i_chart": {
            "data": values.tolist(),
            "cl": round(float(i_cl), 6),
            "ucl": round(float(i_ucl), 6),
            "lcl": round(float(i_lcl), 6),
            "violations": i_violations,
        },
        "mr_chart": {
            "data": mr.tolist(),
            "cl": round(float(mr_cl), 6),
            "ucl": round(float(mr_ucl), 6),
            "lcl": float(mr_lcl),
            "violations": mr_violations,
        },
        "summary": {
            "x_bar": round(float(x_bar), 6),
            "mr_bar": round(float(mr_bar), 6),
            "sigma_hat": round(float(sigma_hat), 6),
        },
    }


def _check_mr_violations(mr_values: np.ndarray, ucl: float) -> List[Dict]:
    violations = []
    for i, v in enumerate(mr_values):
        if v > ucl:
            violations.append({"point": i + 2, "rule": "above_ucl", "value": round(float(v), 6)})
    return violations
