"""
XBar-R 控制图分析
"""

from typing import Dict, Any, List
import numpy as np
import pandas as pd
from config.settings import CONTROL_CHART_CONSTANTS
from ._rules import check_all_nelson_rules


def analyze(data: pd.Series, subgroup_size: int = 5) -> Dict[str, Any]:
    n = len(data)
    if n < subgroup_size * 2:
        raise ValueError(f"数据量不足: 需要至少 {subgroup_size * 2} 点, 当前 {n}")

    num_subgroups = n // subgroup_size
    trimmed = data[: num_subgroups * subgroup_size].values
    subgroups = trimmed.reshape(num_subgroups, subgroup_size)

    xbar = subgroups.mean(axis=1)
    r = subgroups.max(axis=1) - subgroups.min(axis=1)

    xbar_bar = xbar.mean()
    r_bar = r.mean()

    const = CONTROL_CHART_CONSTANTS.get(subgroup_size)
    if not const:
        raise ValueError(f"子组大小 {subgroup_size} 不在常数表范围内 (2~25)")

    a2 = const["A2"]
    d3 = const["D3"]
    d4 = const["D4"]

    xbar_ucl = xbar_bar + a2 * r_bar
    xbar_lcl = xbar_bar - a2 * r_bar
    xbar_cl = xbar_bar

    r_ucl = d4 * r_bar
    r_lcl = d3 * r_bar
    r_cl = r_bar

    sigma_hat = r_bar / const["d2"]
    xbar_violations = check_all_nelson_rules(xbar, xbar_bar, sigma_hat / np.sqrt(subgroup_size))
    r_violations = _check_range_violations(r, r_ucl, r_lcl)

    return {
        "chart_type": "XBar-R",
        "subgroup_size": subgroup_size,
        "num_subgroups": num_subgroups,
        "constants": {"A2": a2, "D3": d3, "D4": d4, "d2": const["d2"]},
        "xbar_chart": {
            "data": xbar.tolist(),
            "cl": round(float(xbar_cl), 6),
            "ucl": round(float(xbar_ucl), 6),
            "lcl": round(float(xbar_lcl), 6),
            "violations": xbar_violations,
        },
        "r_chart": {
            "data": r.tolist(),
            "cl": round(float(r_cl), 6),
            "ucl": round(float(r_ucl), 6),
            "lcl": round(float(r_lcl), 6),
            "violations": r_violations,
        },
        "summary": {
            "xbar_bar": round(float(xbar_bar), 6),
            "r_bar": round(float(r_bar), 6),
            "sigma_hat": round(float(r_bar / const["d2"]), 6),
        },
    }


def _check_range_violations(r_values: np.ndarray, ucl: float, lcl: float) -> List[Dict]:
    violations = []
    for i, r_val in enumerate(r_values):
        if r_val > ucl:
            violations.append({"point": i + 1, "rule": "above_ucl", "ucl": round(float(ucl), 6), "value": round(float(r_val), 6)})
        if r_val < lcl and lcl > 0:
            violations.append({"point": i + 1, "rule": "below_lcl", "lcl": round(float(lcl), 6), "value": round(float(r_val), 6)})
    return violations
