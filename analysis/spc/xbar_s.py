"""
XBar-S 控制图分析
"""

from typing import Any
import numpy as np
import pandas as pd
from config.settings import CONTROL_CHART_CONSTANTS
from ._rules import check_all_nelson_rules


def analyze(data: pd.Series, subgroup_size: int = 5) -> dict[str, Any]:
    n = len(data)
    if n < subgroup_size * 2:
        raise ValueError(f"数据量不足: 需要至少 {subgroup_size * 2} 点, 当前 {n}")

    num_subgroups = n // subgroup_size
    trimmed = data[: num_subgroups * subgroup_size].values
    subgroups = trimmed.reshape(num_subgroups, subgroup_size)

    xbar = subgroups.mean(axis=1)
    s = subgroups.std(ddof=1, axis=1)

    zero_s_mask = s == 0
    if zero_s_mask.any():
        zero_count = int(zero_s_mask.sum())
        valid_mask = ~zero_s_mask
        if valid_mask.sum() < 2:
            raise ValueError(
                f"有效子组不足：{zero_count} 个子组标准差为 0（其余不足 2 个）——"
                "序列可能为常量、或量具分辨率低于过程波动；XBar-S 无法估计控制限"
            )
        xbar = xbar[valid_mask]
        s = s[valid_mask]
        num_subgroups = len(s)
        import warnings
        warnings.warn(f"剔除{zero_count}个零标准差子组（标准差=0），剩余{num_subgroups}个子组",
                      UserWarning, stacklevel=2)

    xbar_bar = xbar.mean()
    s_bar = s.mean()

    const = CONTROL_CHART_CONSTANTS.get(subgroup_size)
    if not const:
        raise ValueError(f"子组大小 {subgroup_size} 不在常数表范围内 (2~25)")

    a3 = const["A3"]
    b3 = const["B3"]
    b4 = const["B4"]
    c4 = const["c4"]

    xbar_ucl = xbar_bar + a3 * s_bar
    xbar_lcl = xbar_bar - a3 * s_bar
    xbar_cl = xbar_bar

    s_ucl = b4 * s_bar
    s_lcl = b3 * s_bar
    s_cl = s_bar

    sigma_hat = s_bar / c4

    xbar_violations = check_all_nelson_rules(xbar, xbar_bar, sigma_hat / np.sqrt(subgroup_size))
    s_violations = _check_limit_violations(s, s_ucl, s_lcl)

    return {
        "chart_type": "XBar-S",
        "subgroup_size": subgroup_size,
        "num_subgroups": num_subgroups,
        "constants": {"A3": a3, "B3": b3, "B4": b4, "c4": c4},
        "xbar_chart": {
            "data": xbar.tolist(),
            "cl": round(float(xbar_cl), 6),
            "ucl": round(float(xbar_ucl), 6),
            "lcl": round(float(xbar_lcl), 6),
            "violations": xbar_violations,
        },
        "s_chart": {
            "data": s.tolist(),
            "cl": round(float(s_cl), 6),
            "ucl": round(float(s_ucl), 6),
            "lcl": round(float(s_lcl), 6),
            "violations": s_violations,
        },
        "summary": {
            "xbar_bar": round(float(xbar_bar), 6),
            "s_bar": round(float(s_bar), 6),
            "sigma_hat": round(float(sigma_hat), 6),
        },
    }


def _check_limit_violations(values: np.ndarray, ucl: float, lcl: float) -> list[dict]:
    violations = []
    for i, v in enumerate(values):
        if v > ucl:
            violations.append({"point": i + 1, "rule": "above_ucl", "value": round(float(v), 6)})
        if v < lcl and lcl > 0:
            violations.append({"point": i + 1, "rule": "below_lcl", "value": round(float(v), 6)})
    return violations
