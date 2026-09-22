"""
指数平滑 — 单指数 / Holt 线性 / Holt-Winters（加法/乘法季节性）

提供:
  analyze() — 完整指数平滑分析 + 预测
"""

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats as sp_stats
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from ._utils import detect_period


def analyze(
    data: pd.Series,
    method: str = "holt_winters",
    seasonal: str = "additive",
    seasonal_periods: int | None = None,
    forecast_steps: int = 12,
    confidence_level: float = 0.95,
) -> dict[str, Any]:
    """
    指数平滑分析 + 预测

    Args:
        data: 时间序列数据
        method: "single"（单指数）| "double"（Holt 线性）| "holt_winters"
        seasonal: "additive" | "multiplicative" | "none"
        seasonal_periods: 季节周期（None 则自动检测）
        forecast_steps: 预测步数
        confidence_level: 置信水平

    Returns:
        拟合结果 + 预测值 + 置信区间 + AIC/BIC
    """
    clean = data.dropna().astype(float)
    n = len(clean)

    if n < 4:
        return {
            "chart_type": "Exponential Smoothing",
            "analysis_type": "time_series.exponential_smoothing",
            "error": f"数据点不足: {n}（最少需要 4 个）",
        }

    if method == "holt_winters" and seasonal != "none":
        if seasonal_periods is None:
            seasonal_periods = detect_period(clean)
            if seasonal_periods is None or seasonal_periods < 2 or seasonal_periods >= n // 2:
                seasonal_periods = min(12, n // 2)
                if seasonal_periods < 2:
                    return {
                        "chart_type": "Exponential Smoothing",
                        "analysis_type": "time_series.exponential_smoothing",
                        "error": f"无法检测季节周期（数据长度 {n} 不足）",
                    }

    trend_type = None
    use_seasonal = False
    seasonal_type = None

    if method == "single":
        trend_type = None
        use_seasonal = False
    elif method == "double":
        trend_type = "add"
        use_seasonal = False
    elif method == "holt_winters":
        trend_type = "add"
        use_seasonal = seasonal != "none"
        seasonal_type = seasonal if use_seasonal else None
    else:
        return {
            "chart_type": "Exponential Smoothing",
            "analysis_type": "time_series.exponential_smoothing",
            "error": f"未知方法: {method}",
        }

    try:
        model = ExponentialSmoothing(
            clean,
            trend=trend_type,
            seasonal=seasonal_type if use_seasonal else None,
            seasonal_periods=seasonal_periods if use_seasonal else None,
            initialization_method="estimated",
        )
        fit = model.fit(optimized=True, remove_bias=False)
    except Exception as e:  # noqa: BLE001 - 平滑拟合失败：返回结构化错误
        return {
            "chart_type": "Exponential Smoothing",
            "analysis_type": "time_series.exponential_smoothing",
            "error": f"模型拟合失败: {str(e)}",
        }

    fitted = fit.fittedvalues

    forecast_result = fit.forecast(steps=forecast_steps)

    residuals = clean - fitted
    residual_std = float(np.std(residuals, ddof=1))
    z = sp_stats.norm.ppf((1 + confidence_level) / 2)
    conf_half = z * residual_std * np.sqrt(np.arange(1, forecast_steps + 1))

    forecast_vals = forecast_result.values
    conf_lower = (forecast_vals - conf_half).tolist()
    conf_upper = (forecast_vals + conf_half).tolist()

    aic = float(fit.aic) if hasattr(fit, "aic") else None
    bic = float(fit.bic) if hasattr(fit, "bic") else None

    return {
        "chart_type": "Exponential Smoothing",
        "analysis_type": "time_series.exponential_smoothing",
        "summary": {
            "sample_size": n,
            "method": method,
            "seasonal": seasonal if use_seasonal else "none",
            "seasonal_periods": seasonal_periods if use_seasonal else None,
            "aic": round(aic, 4) if aic is not None else None,
            "bic": round(bic, 4) if bic is not None else None,
            "residual_std": round(residual_std, 6),
            "forecast_steps": forecast_steps,
        },
        "fitted_values": [round(float(v), 6) for v in fitted],
        "forecast": [round(float(v), 6) for v in forecast_vals],
        "confidence_lower": [round(float(v), 6) for v in conf_lower],
        "confidence_upper": [round(float(v), 6) for v in conf_upper],
    }
