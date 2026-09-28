"""
预测框架 — 统一预测接口 + 多模型 AIC/BIC 排名对比

提供:
  compare_models()  — 多模型对比排名
  predict()         — 统一预测（调用各子模块）
"""

from typing import Any

import pandas as pd

from . import arima, exponential_smoothing
from ._utils import clean_series


def compare_models(
    data: pd.Series,
    models: list[str] | None = None,
    forecast_steps: int = 12,
    seasonal_periods: int | None = None,
    seasonal: str = "additive",
) -> dict[str, Any]:
    """
    多模型对比，按 AIC/BIC 排名

    Args:
        data: 时间序列数据
        models: 要对比的模型列表。默认 ["arima", "holt_winters", "double_exp"]
        forecast_steps: 预测步数
        seasonal_periods: 季节周期（Holt-Winters 需要）
        seasonal: "additive" 或 "multiplicative"（Holt-Winters 季节类型）

    Returns:
        模型对比结果字典
    """
    if models is None:
        models = ["arima", "holt_winters", "double_exp"]

    clean = clean_series(data)
    n = len(clean)

    if n < 10:
        return {
            "chart_type": "Model Comparison",
            "analysis_type": "time_series.model_comparison",
            "error": f"数据点不足: {n}（最少需要 10 个）",
        }

    comparisons = []

    for model_name in models:
        result = _run_model(model_name, clean, forecast_steps, seasonal_periods, seasonal=seasonal)
        if result is not None:
            comparisons.append(result)

    if not comparisons:
        return {
            "chart_type": "Model Comparison",
            "analysis_type": "time_series.model_comparison",
            "error": "所有模型均拟合失败",
        }

    comparisons.sort(key=lambda x: x.get("aic") or float("inf"))

    best = comparisons[0]

    return {
        "chart_type": "Model Comparison",
        "analysis_type": "time_series.model_comparison",
        "summary": {
            "sample_size": n,
            "models_compared": len(comparisons),
            "best_model": best["model"],
            "best_aic": best.get("aic"),
            "best_bic": best.get("bic"),
        },
        "comparisons": comparisons,
        "best_forecast": best.get("forecast", []),
        "best_confidence_lower": best.get("confidence_lower", []),
        "best_confidence_upper": best.get("confidence_upper", []),
    }


def predict(
    data: pd.Series,
    model: str = "arima",
    forecast_steps: int = 12,
    order: tuple | None = None,
    seasonal_periods: int | None = None,
) -> dict[str, Any]:
    """
    统一预测接口

    Args:
        data: 时间序列数据
        model: "arima" | "holt_winters" | "double_exp" | "single_exp"
        forecast_steps: 预测步数
        order: ARIMA 阶数 (p,d,q)，仅 arima 模型有效
        seasonal_periods: 季节周期，仅 holt_winters 有效

    Returns:
        预测结果字典
    """
    result = _run_model(model, data, forecast_steps, seasonal_periods, order=order)
    if result is None:
        return {
            "chart_type": "Forecast",
            "analysis_type": "time_series.forecast",
            "error": f"模型 {model} 拟合失败",
        }
    result["chart_type"] = "Forecast"
    result["analysis_type"] = "time_series.forecast"
    return result


def _run_model(
    model_name: str,
    data: pd.Series,
    forecast_steps: int,
    seasonal_periods: int | None = None,
    order: tuple | None = None,
    seasonal: str = "additive",
) -> dict | None:
    """内部：运行单个模型并返回标准化结果"""
    try:
        if model_name == "arima":
            r = arima.analyze(
                data, order=order, auto_select=(order is None),
                max_p=3, max_d=1, max_q=3, forecast_steps=forecast_steps,
            )
            if "error" in r:
                return None
            return {
                "model": f"ARIMA{tuple(r['summary']['order'])}",
                "aic": r["summary"]["aic"],
                "bic": r["summary"]["bic"],
                "forecast": r["forecast"],
                "confidence_lower": r["confidence_lower"],
                "confidence_upper": r["confidence_upper"],
                "fitted_values": r["fitted_values"],
            }
        if model_name == "holt_winters":
            sp = seasonal_periods or 12
            label = "Additive" if seasonal == "additive" else "Multiplicative"
            r = exponential_smoothing.analyze(
                data, method="holt_winters", seasonal=seasonal,
                seasonal_periods=sp, forecast_steps=forecast_steps,
            )
            if "error" in r:
                return None
            return {
                "model": f"Holt-Winters({label})",
                "aic": r["summary"]["aic"],
                "bic": r["summary"]["bic"],
                "forecast": r["forecast"],
                "confidence_lower": r["confidence_lower"],
                "confidence_upper": r["confidence_upper"],
                "fitted_values": r["fitted_values"],
            }
        if model_name == "double_exp":
            r = exponential_smoothing.analyze(
                data, method="double", forecast_steps=forecast_steps,
            )
            if "error" in r:
                return None
            return {
                "model": "Holt Linear",
                "aic": r["summary"]["aic"],
                "bic": r["summary"]["bic"],
                "forecast": r["forecast"],
                "confidence_lower": r["confidence_lower"],
                "confidence_upper": r["confidence_upper"],
                "fitted_values": r["fitted_values"],
            }
        if model_name == "single_exp":
            r = exponential_smoothing.analyze(
                data, method="single", forecast_steps=forecast_steps,
            )
            if "error" in r:
                return None
            return {
                "model": "Single Exponential",
                "aic": r["summary"]["aic"],
                "bic": r["summary"]["bic"],
                "forecast": r["forecast"],
                "confidence_lower": r["confidence_lower"],
                "confidence_upper": r["confidence_upper"],
                "fitted_values": r["fitted_values"],
            }
        return None
    except Exception as e:  # noqa: BLE001 - 单模型失败：记录 warning 并跳过
        import logging
        logging.getLogger(__name__).warning("Model %s failed: %s", model_name, e)
        return None
