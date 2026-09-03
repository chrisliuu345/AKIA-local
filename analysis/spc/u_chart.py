"""
U控制图 (单位缺陷数控制图) — 向量化实现
"""

from typing import Dict, Any
import numpy as np
import pandas as pd


def analyze(defects: pd.Series, unit_sizes: pd.Series) -> Dict[str, Any]:
    n = len(defects)
    if n < 2:
        raise ValueError(f"数据量不足: 需要至少 2 个子组, 当前 {n}")

    c = defects.values.astype(float)
    u_sizes = unit_sizes.values.astype(float)

    u = c / u_sizes
    u_bar = c.sum() / u_sizes.sum()

    se = np.sqrt(u_bar / u_sizes)
    ucl_vals = u_bar + 3 * se
    lcl_vals = np.maximum(u_bar - 3 * se, 0)

    violations_mask = (u > ucl_vals) | (u < lcl_vals)
    violations_idx = np.where(violations_mask)[0]

    violations = []
    for i in violations_idx:
        violations.append({
            "point": int(i + 1),
            "value": round(float(u[i]), 6),
            "ucl": round(float(ucl_vals[i]), 6),
            "lcl": round(float(lcl_vals[i]), 6),
        })

    return {
        "chart_type": "U-Chart",
        "num_subgroups": n,
        "data": {
            "u_values": u.tolist(),
            "unit_sizes": u_sizes.tolist(),
            "defects": c.tolist(),
        },
        "cl": round(float(u_bar), 6),
        "ucl": [round(float(v), 6) for v in ucl_vals],
        "lcl": [round(float(v), 6) for v in lcl_vals],
        "violations": violations,
        "summary": {
            "u_bar": round(float(u_bar), 6),
            "total_defects": int(c.sum()),
            "total_units": float(u_sizes.sum()),
        },
    }
