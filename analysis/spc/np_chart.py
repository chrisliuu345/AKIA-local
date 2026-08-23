"""
NP控制图 (不合格品数控制图)
"""

from typing import Dict, Any
import numpy as np
import pandas as pd


def analyze(defectives: pd.Series, sample_size: int) -> Dict[str, Any]:
    n = len(defectives)
    if n < 2:
        raise ValueError(f"数据量不足: 需要至少 2 个子组, 当前 {n}")

    d = defectives.values.astype(float)

    p_bar = d.sum() / (n * sample_size)
    np_bar = d.mean()

    se = np.sqrt(d.mean() * (1 - p_bar))
    np_ucl = np_bar + 3 * se
    np_lcl = max(np_bar - 3 * se, 0)
    np_cl = np_bar

    violations = []
    for i in range(n):
        if d[i] > np_ucl or d[i] < np_lcl:
            violations.append({
                "point": i + 1,
                "value": round(float(d[i]), 6),
                "ucl": round(float(np_ucl), 6),
                "lcl": round(float(np_lcl), 6),
            })

    return {
        "chart_type": "NP-Chart",
        "sample_size": sample_size,
        "num_subgroups": n,
        "data": d.tolist(),
        "cl": round(float(np_cl), 6),
        "ucl": round(float(np_ucl), 6),
        "lcl": round(float(np_lcl), 6),
        "violations": violations,
        "summary": {
            "np_bar": round(float(np_bar), 6),
            "p_bar": round(float(p_bar), 6),
            "total_defectives": int(d.sum()),
        },
    }
