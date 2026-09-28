"""
C控制图 (缺陷数控制图)
"""

from typing import Any
import numpy as np
import pandas as pd

from ._validation import clean_series, require_min_subgroups, require_non_negative


def analyze(defects: pd.Series) -> dict[str, Any]:
    c = clean_series(defects)
    n = len(c)
    require_min_subgroups(n)
    require_non_negative(c, "缺陷数")

    c_bar = c.mean()

    c_ucl = c_bar + 3 * np.sqrt(c_bar)
    c_lcl = max(c_bar - 3 * np.sqrt(c_bar), 0)
    c_cl = c_bar

    violations = []
    for i in range(n):
        if c[i] > c_ucl or c[i] < c_lcl:
            violations.append({
                "point": i + 1,
                "value": round(float(c[i]), 6),
                "ucl": round(float(c_ucl), 6),
                "lcl": round(float(c_lcl), 6),
            })

    return {
        "chart_type": "C-Chart",
        "num_subgroups": n,
        "data": c.tolist(),
        "cl": round(float(c_cl), 6),
        "ucl": round(float(c_ucl), 6),
        "lcl": round(float(c_lcl), 6),
        "violations": violations,
        "summary": {
            "c_bar": round(float(c_bar), 6),
            "total_defects": int(c.sum()),
        },
    }
