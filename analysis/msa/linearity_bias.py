"""
偏倚和线性研究
"""

from typing import Any
import numpy as np
import pandas as pd
from analysis._sanitize import sanitize_array
from scipy import stats


def analyze_bias(data: pd.Series, reference: float) -> dict[str, Any]:
    clean = sanitize_array(data)
    n = len(clean)
    if n < 2:
        raise ValueError(f"数据量不足: {n}")

    bias_values = clean - reference
    mean_bias = float(np.mean(bias_values))
    std_bias = float(np.std(bias_values, ddof=1))

    se = std_bias / np.sqrt(n)
    t_stat = mean_bias / se if se > 0 else 0
    df = n - 1
    p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df))

    return {
        "chart_type": "Bias Study",
        "reference_value": float(reference),
        "measurements": n,
        "mean_bias": round(float(mean_bias), 6),
        "std_bias": round(float(std_bias), 6),
        "t_statistic": round(float(t_stat), 4),
        "p_value": round(float(p_value), 6),
        "is_significant": bool(p_value < 0.05),
        "interpretation": "偏倚显著" if p_value < 0.05 else "偏倚不显著",
        "bias_values": bias_values.tolist(),
    }


def analyze_linearity(
    df: pd.DataFrame,
    measurement_col: str,
    reference_col: str,
) -> dict[str, Any]:
    data = df.copy()
    data[measurement_col] = pd.to_numeric(data[measurement_col], errors="coerce")
    data[reference_col] = pd.to_numeric(data[reference_col], errors="coerce")
    data = data.dropna(subset=[measurement_col, reference_col])

    if len(data) < 5:
        raise ValueError("数据量不足: 需要至少 5 点")

    x = data[reference_col].values
    y = data[measurement_col].values - x

    slope, intercept, r_value, p_value, _std_err = stats.linregress(x, y)

    linearity = abs(slope) * (x.max() - x.min())

    return {
        "chart_type": "Linearity Study",
        "measurements": len(data),
        "linearity": round(float(linearity), 6),
        "slope": round(float(slope), 8),
        "intercept": round(float(intercept), 6),
        "r_squared": round(float(r_value ** 2), 6),
        "p_value": round(float(p_value), 6),
        "is_linear": p_value >= 0.05,
        "interpretation": "线性可接受" if p_value >= 0.05 else "存在显著线性偏差",
    }
