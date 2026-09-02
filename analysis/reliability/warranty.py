"""
保修分析 — 首次失效预测 + 保修成本估算

基于可靠性函数估计保修期内的失效数量和成本。
"""

import math
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd


def analyze(
    failure_times: pd.Series,
    warranty_period: float,
    cost_per_failure: float,
    total_units: int,
    censored: Optional[pd.Series] = None,
    confidence_level: float = 0.95,
) -> Dict[str, Any]:
    """
    保修分析

    Args:
        failure_times: 失效时间数据
        warranty_period: 保修期（与 failure_times 同单位）
        cost_per_failure: 每次失效的成本
        total_units: 总出货量
        censored: 删失指示（1=失效, 0=删失），默认全部失效
        confidence_level: 置信水平

    Returns:
        保修分析结果字典
    """
    from scipy import stats as sp_stats

    T = failure_times.dropna().astype(float)
    n = len(T)

    if n < 5:
        return {
            "analysis_type": "reliability.warranty",
            "error": f"数据点不足: {n}（至少需要 5 个）",
        }

    if warranty_period <= 0:
        return {"analysis_type": "reliability.warranty", "error": "保修期必须为正"}
    if cost_per_failure < 0:
        return {"analysis_type": "reliability.warranty", "error": "成本不能为负"}
    if total_units <= 0:
        return {"analysis_type": "reliability.warranty", "error": "总出货量必须为正"}

    if censored is not None:
        E = censored.loc[T.index].astype(int)
    else:
        E = pd.Series(np.ones(n, dtype=int), index=T.index)

    # Weibull 拟合 (2P)
    failures = T[E == 1].values
    if len(failures) < 3:
        return {"analysis_type": "reliability.warranty", "error": "失效事件不足（至少3个）"}

    from scipy.stats import weibull_min
    shape, loc, scale = weibull_min.fit(failures, floc=0)
    beta = shape
    eta = scale

    # 保修期内可靠性: R(t) = exp(-(t/eta)^beta)
    r_warranty = math.exp(-((warranty_period / eta) ** beta))

    # 预期失效数
    expected_failures = total_units * (1 - r_warranty)

    # 首次失效预测: F(t) = 0.01 → t = eta * (-ln(0.99))^(1/beta)
    first_failure_1pct = eta * (-math.log(0.99)) ** (1 / beta)
    first_failure_5pct = eta * (-math.log(0.95)) ** (1 / beta)

    # 保修成本
    warranty_cost = expected_failures * cost_per_failure
    cost_per_unit = warranty_cost / total_units if total_units > 0 else 0

    # 置信区间（基于二项分布）
    z = sp_stats.norm.ppf((1 + confidence_level) / 2)
    p_fail = 1 - r_warranty
    se_fail = math.sqrt(p_fail * (1 - p_fail) / n)
    ci_low = max(0, p_fail - z * se_fail)
    ci_high = min(1, p_fail + z * se_fail)

    return {
        "analysis_type": "reliability.warranty",
        "summary": {
            "warranty_period": warranty_period,
            "total_units": total_units,
            "cost_per_failure": cost_per_failure,
            "reliability_at_warranty_end": round(r_warranty, 6),
            "failure_probability": round(p_fail, 6),
            "expected_failures": round(expected_failures, 2),
            "warranty_cost_estimate": round(warranty_cost, 2),
            "cost_per_unit": round(cost_per_unit, 4),
        },
        "first_failure_predictions": {
            "1pct_failure": round(first_failure_1pct, 2),
            "5pct_failure": round(first_failure_5pct, 2),
        },
        "weibull_params": {
            "beta": round(beta, 4),
            "eta": round(eta, 4),
        },
        "confidence_intervals": {
            "failure_probability_ci_low": round(ci_low, 6),
            "failure_probability_ci_high": round(ci_high, 6),
        },
    }
