"""
EWMA (指数加权移动平均) 控制图分析
"""

from typing import Dict, Any, List
import numpy as np
import pandas as pd


def analyze(
    data: pd.Series,
    lam: float = 0.2,
    L: float = 3.0,
) -> Dict[str, Any]:
    values = data.values.astype(float)
    n = len(values)
    if n < 2:
        raise ValueError(f"数据量不足: {n}")
    if not 0 < lam <= 1:
        raise ValueError(f"lam 必须在 (0, 1] 范围内: {lam}")

    mean = float(np.mean(values))
    sigma = float(np.std(values, ddof=1)) if n > 1 else 1.0

    ewma = np.zeros(n)
    # W32 fix: 初值用μ0（均值），符合Montgomery/Minitab标准
    ewma[0] = mean
    for i in range(1, n):
        ewma[i] = lam * values[i] + (1 - lam) * ewma[i - 1]

    ucl = np.zeros(n)
    lcl = np.zeros(n)
    for i in range(n):
        factor = np.sqrt((lam / (2 - lam)) * (1 - (1 - lam) ** (2 * (i + 1))))
        sigma_ewma = sigma * factor
        ucl[i] = mean + L * sigma_ewma
        lcl[i] = mean - L * sigma_ewma

    violations = []
    for i in range(n):
        if ewma[i] > ucl[i]:
            violations.append({
                "point": i + 1, "rule": "EWMA+",
                "desc": f"EWMA超出UCL ({ewma[i]:.3f} > {ucl[i]:.3f})",
                "value": round(float(ewma[i]), 6),
            })
        elif ewma[i] < lcl[i]:
            violations.append({
                "point": i + 1, "rule": "EWMA-",
                "desc": f"EWMA超出LCL ({ewma[i]:.3f} < {lcl[i]:.3f})",
                "value": round(float(ewma[i]), 6),
            })

    return {
        "chart_type": "EWMA",
        "num_points": n,
        "ewma_chart": {
            "raw_data": values.tolist(),
            "data": ewma.tolist(),
            "cl": round(float(mean), 6),
            "ucl": ucl.tolist(),
            "lcl": lcl.tolist(),
            "ucl_const": round(float(mean + L * sigma * np.sqrt(lam / (2 - lam))), 6),
            "lcl_const": round(float(mean - L * sigma * np.sqrt(lam / (2 - lam))), 6),
            "violations": violations,
        },
        "summary": {
            "mean": round(float(mean), 6),
            "sigma": round(float(sigma), 6),
            "lambda": lam,
            "L": L,
            "steady_state_ucl": round(float(mean + L * sigma * np.sqrt(lam / (2 - lam))), 6),
            "steady_state_lcl": round(float(mean - L * sigma * np.sqrt(lam / (2 - lam))), 6),
        },
    }
