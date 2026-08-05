"""
P控制图 (不合格品率控制图)
"""

from typing import Dict, Any, List
import numpy as np
import pandas as pd


def analyze(defectives: pd.Series, sample_sizes: pd.Series) -> Dict[str, Any]:
    n = len(defectives)
    if n < 2:
        raise ValueError(f"数据量不足: 需要至少 2 个子组, 当前 {n}")

    d = defectives.values.astype(float)
    ss = sample_sizes.values.astype(float)

    p = d / ss
    p_bar = d.sum() / ss.sum()

    ucl_vals = []
    lcl_vals = []
    for i in range(n):
        se = np.sqrt(p_bar * (1 - p_bar) / ss[i])
        ucl_vals.append(p_bar + 3 * se)
        lcl_vals.append(max(p_bar - 3 * se, 0))

    violations = []
    for i in range(n):
        if p[i] > ucl_vals[i] or p[i] < lcl_vals[i]:
            violations.append({
                "point": i + 1,
                "value": round(float(p[i]), 6),
                "ucl": round(float(ucl_vals[i]), 6),
                "lcl": round(float(lcl_vals[i]), 6),
            })

    return {
        "chart_type": "P-Chart",
        "num_subgroups": n,
        "data": {
            "p_values": p.tolist(),
            "sample_sizes": ss.tolist(),
            "defectives": d.tolist(),
        },
        "cl": round(float(p_bar), 6),
        "ucl": [round(float(v), 6) for v in ucl_vals],
        "lcl": [round(float(v), 6) for v in lcl_vals],
        "violations": violations,
        "summary": {
            "p_bar": round(float(p_bar), 6),
            "total_inspected": int(d.sum()),
            "total_defectives": int(ss.sum()),
        },
    }
