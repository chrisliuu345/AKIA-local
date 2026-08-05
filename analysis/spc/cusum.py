"""
CUSUM (累积和) 控制图分析 — 双侧 Tabular CUSUM
"""

from typing import Dict, Any, List
import numpy as np
import pandas as pd


def analyze(
    data: pd.Series,
    target: float = None,
    k: float = 0.5,
    h: float = 5.0,
) -> Dict[str, Any]:
    values = data.values.astype(float)
    n = len(values)
    if n < 2:
        raise ValueError(f"数据量不足: {n}")

    if target is None:
        target = float(np.mean(values))

    sigma = float(np.std(values, ddof=1)) if n > 1 else 1.0
    k_abs = k * sigma
    h_abs = h * sigma

    cplus = np.zeros(n)
    cminus = np.zeros(n)

    for i in range(n):
        dev = values[i] - target
        if i == 0:
            cplus[i] = max(0, dev - k_abs)
            cminus[i] = max(0, -dev - k_abs)
        else:
            cplus[i] = max(0, cplus[i - 1] + dev - k_abs)
            cminus[i] = max(0, cminus[i - 1] - dev - k_abs)

    violations = []
    for i in range(n):
        if cplus[i] > h_abs:
            violations.append({
                "point": i + 1, "rule": "CUSUM+",
                "desc": f"CUSUM+超出决策区间 ({cplus[i]:.3f} > {h_abs:.3f})",
                "value": round(float(cplus[i]), 6),
            })
        if cminus[i] > h_abs:
            violations.append({
                "point": i + 1, "rule": "CUSUM-",
                "desc": f"CUSUM-超出决策区间 ({cminus[i]:.3f} > {h_abs:.3f})",
                "value": round(float(cminus[i]), 6),
            })

    return {
        "chart_type": "CUSUM",
        "num_points": n,
        "cusum_chart": {
            "data": values.tolist(),
            "cusum_plus": cplus.tolist(),
            "cusum_minus": cminus.tolist(),
            "target": round(float(target), 6),
            "cl": 0.0,
            "ucl": round(float(h_abs), 6),
            "lcl": round(float(-h_abs), 6),
            "violations": violations,
        },
        "summary": {
            "target": round(float(target), 6),
            "k": k,
            "h": h,
            "sigma": round(float(sigma), 6),
            "k_absolute": round(float(k_abs), 6),
            "h_absolute": round(float(h_abs), 6),
        },
    }
