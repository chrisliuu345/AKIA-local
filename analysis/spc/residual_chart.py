"""自相关残差控制图 — 先白化再监控（ARIMA 残差 + I-MR）

动机: 自相关数据直接上 I-MR / XBar 图会系统性误报——相邻点不独立时
σ̂ = MR̄/d2 低估真实波动、且 Nelson 规则的"随机性"前提被破坏。

做法:
1. 用 ARIMA 拟合序列（默认自动选阶），得到拟合值 f_t；
2. 残差 e_t = y_t − f_t（去掉差分导致的头部 NaN）；
3. 对 e_t 施加 I-MR 图 + Nelson 8 规则 —— 残差近似白噪声，误报率回到名义水平。

同时输出白化前后对照指标（lag-1 自相关、越限点数），便于报告量化改善。
"""

from typing import Any

import numpy as np
import pandas as pd

from analysis.spc import imr
from analysis.time_series import arima


def analyze(
    data: pd.Series,
    order: tuple[int, int, int] | None = None,
    auto_select: bool = True,
    alpha_arima: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    残差控制图分析

    Args:
        data: 时间序列（等间隔）
        order: 手动指定 ARIMA (p, d, q)；None 且 auto_select=True 时自动选阶
        auto_select: 是否自动选阶
        alpha_arima: 透传给 analysis.time_series.arima.analyze 的额外参数

    Returns:
        分析结果字典；ARIMA 失败时降级为原始序列 I-MR（``fallback`` 说明原因）
    """
    clean = pd.Series(data).dropna().astype(float).reset_index(drop=True)
    if len(clean) < 10:
        raise ValueError(f"数据量不足: {len(clean)}，需要至少 10 点")

    raw_chart = imr.analyze(clean)
    kwargs = dict(alpha_arima or {})
    kwargs.setdefault("forecast_steps", 1)
    fitted = arima.analyze(clean, order=order, auto_select=auto_select, **kwargs)

    fallback = ""
    if "error" in fitted:
        fallback = str(fitted["error"])
        residuals = None
    else:
        predicted = pd.Series(fitted["fitted_values"], index=clean.index[:len(fitted["fitted_values"])])
        residuals = (clean - predicted).dropna()
        if len(residuals) < 10:
            fallback = f"残差有效点不足: {len(residuals)}（ARIMA 差分或收敛问题）"
            residuals = None
        elif float(residuals.std()) <= 1e-12:
            fallback = "残差近似为常量（序列无可建模变异）"
            residuals = None

    if residuals is None:
        return {
            "chart_type": "残差控制图",
            "analysis_type": "spc.residual_chart",
            "fallback": True,
            "fallback_reason": fallback,
            "residual_chart": raw_chart,
            "diagnostics": {
                "raw_chart_type": raw_chart["chart_type"],
                "raw_lag1_autocorr": _lag1_autocorr(clean.to_numpy()),
                "raw_violations": _count_points(raw_chart),
            },
        }

    residual_chart = imr.analyze(residuals.reset_index(drop=True))
    order_used = (fitted.get("summary", {}) or {}).get("order")

    return {
        "chart_type": "残差控制图",
        "analysis_type": "spc.residual_chart",
        "fallback": False,
        "residual_chart": residual_chart,
        "diagnostics": {
            "arima_order": list(order_used) if order_used else None,
            "num_residuals": int(len(residuals)),
            "raw_lag1_autocorr": _lag1_autocorr(clean.to_numpy()),
            "residual_lag1_autocorr": _lag1_autocorr(residuals.to_numpy()),
            "raw_violations": _count_points(raw_chart),
            "residual_violations": _count_points(residual_chart),
            "ljung_box_p_value": (fitted.get("summary", {}) or {}).get("ljung_box_p_value"),
            "durbin_watson": (fitted.get("summary", {}) or {}).get("durbin_watson"),
            "improvement": _improvement(raw_chart, residual_chart),
        },
    }


def _lag1_autocorr(values: np.ndarray) -> float:
    """lag-1 自相关（去均值、逐样本标准化）。"""
    arr = np.asarray(values, dtype=float)
    if arr.size < 3:
        return 0.0
    arr = arr - arr.mean()
    denom = float(arr @ arr)
    if denom == 0.0:
        return 0.0
    return float(arr[:-1] @ arr[1:] / denom)


def _count_points(chart: dict) -> int:
    """统计 I-MR 结果中 I 图与 MR 图的越限点总数。"""
    total = 0
    for key in ("i_chart", "mr_chart"):
        section = chart.get(key, {})
        total += len(section.get("violations", []) or [])
    return total


def _improvement(raw_chart: dict, residual_chart: dict) -> dict[str, Any]:
    """白化前后对照：越限点减少量与比值。"""
    raw_count = _count_points(raw_chart)
    res_count = _count_points(residual_chart)
    return {
        "violations_before": raw_count,
        "violations_after": res_count,
        "violations_reduced": raw_count - res_count,
        "ratio": (round(res_count / raw_count, 6) if raw_count else None),
    }
