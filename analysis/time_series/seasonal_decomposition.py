"""
季节性分解 — 经典分解（加法/乘法）+ STL 分解

提供:
  analyze() — 完整季节性分解
"""

from typing import Any

import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import seasonal_decompose, STL

from ._utils import detect_period


def analyze(
    data: pd.Series,
    model: str = "additive",
    period: int | None = None,
    method: str = "classical",
) -> dict[str, Any]:
    """
    季节性分解

    Args:
        data: 时间序列数据
        model: "additive"（加法）或 "multiplicative"（乘法）
        period: 季节周期（None 则自动检测）
        method: "classical"（经典分解）或 "stl"（STL 鲁棒分解）

    Returns:
        分解结果字典，含趋势、季节、残差分量
    """
    clean = data.dropna().astype(float)
    n = len(clean)

    if n < 4:
        return {
            "chart_type": "Seasonal Decomposition",
            "analysis_type": "time_series.seasonal_decomposition",
            "error": f"数据点不足: {n}（最少需要 4 个）",
        }

    if period is None:
        period = detect_period(clean)
        if period is None or period < 2 or period >= n // 2:
            period = min(12, n // 2)
            if period < 2:
                return {
                    "chart_type": "Seasonal Decomposition",
                    "analysis_type": "time_series.seasonal_decomposition",
                    "error": f"无法自动检测季节周期（数据长度 {n} 不足）",
                }

    if model == "multiplicative" and clean.min() <= 0:
        return {
            "chart_type": "Seasonal Decomposition",
            "analysis_type": "time_series.seasonal_decomposition",
            "error": "乘法模型要求数据全部为正值",
        }

    try:
        if method == "stl":
            decomposition = STL(clean, period=period, robust=True).fit()
        else:
            decomposition = seasonal_decompose(
                clean, model=model, period=period, extrapolate_trend="period"
            )
    except Exception as e:  # noqa: BLE001 - 分解失败：返回结构化错误
        return {
            "chart_type": "Seasonal Decomposition",
            "analysis_type": "time_series.seasonal_decomposition",
            "error": f"分解失败: {e!s}",
        }

    trend = decomposition.trend
    seasonal = decomposition.seasonal
    residual = decomposition.resid

    total_var = float(np.nanvar(clean))
    trend_var = float(np.nanvar(trend)) if total_var > 0 else 0.0
    seasonal_var = float(np.nanvar(seasonal)) if total_var > 0 else 0.0
    residual_var = float(np.nanvar(residual)) if total_var > 0 else 0.0

    return {
        "chart_type": "Seasonal Decomposition",
        "analysis_type": "time_series.seasonal_decomposition",
        "summary": {
            "sample_size": n,
            "period": period,
            "model": model,
            "method": method,
            "trend_strength": round(1.0 - residual_var / (trend_var + residual_var), 4) if (trend_var + residual_var) > 0 else 0.0,
            "seasonal_strength": round(1.0 - residual_var / (seasonal_var + residual_var), 4) if (seasonal_var + residual_var) > 0 else 0.0,
        },
        "trend": _to_list(trend),
        "seasonal": _to_list(seasonal),
        "residual": _to_list(residual),
    }


def _to_list(series: pd.Series) -> list:
    """将 Series 转为 JSON 安全的 list"""
    return [round(float(v), 6) if not np.isnan(v) else None for v in series]
