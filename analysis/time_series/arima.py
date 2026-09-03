"""
ARIMA 建模 — 手动定阶 + 网格搜索自动选阶 + 残差诊断 + 预测

提供:
  analyze()       — 完整 ARIMA 分析（手动或自动）
  auto_select()   — 网格搜索自动选阶
"""

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.stats.stattools import durbin_watson


def analyze(
    data: pd.Series,
    order: Optional[Tuple[int, int, int]] = None,
    auto_select: bool = True,
    max_p: int = 5,
    max_d: int = 2,
    max_q: int = 5,
    forecast_steps: int = 12,
    confidence_level: float = 0.95,
) -> Dict[str, Any]:
    """
    ARIMA 建模 + 预测

    Args:
        data: 时间序列数据
        order: 手动指定 (p, d, q)。None 且 auto_select=True 时自动选阶
        auto_select: 是否自动选阶（网格搜索 AIC 最小）
        max_p: 自动选阶时 p 的最大值
        max_d: 自动选阶时 d 的最大值
        max_q: 自动选阶时 q 的最大值
        forecast_steps: 预测步数
        confidence_level: 置信水平

    Returns:
        ARIMA 分析结果字典
    """
    clean = data.dropna().astype(float)
    n = len(clean)

    if n < 10:
        return {
            "chart_type": "ARIMA",
            "analysis_type": "time_series.arima",
            "error": f"数据点不足: {n}（最少需要 10 个）",
        }

    candidates = []
    if order is None and auto_select:
        best_order, candidates = _auto_select(clean, max_p, max_d, max_q)
        if best_order is None:
            return {
                "chart_type": "ARIMA",
                "analysis_type": "time_series.arima",
                "error": "自动选阶失败：所有模型均不收敛",
            }
    elif order is not None:
        best_order = order
    else:
        return {
            "chart_type": "ARIMA",
            "analysis_type": "time_series.arima",
            "error": "未指定 order 且 auto_select=False",
        }

    try:
        model = ARIMA(clean, order=best_order)
        fit = model.fit()
    except Exception as e:
        return {
            "chart_type": "ARIMA",
            "analysis_type": "time_series.arima",
            "error": f"ARIMA{best_order} 拟合失败: {str(e)}",
        }

    fitted = fit.fittedvalues

    forecast_result = fit.get_forecast(steps=forecast_steps)
    forecast_vals = forecast_result.predicted_mean
    conf_int = forecast_result.conf_int(alpha=1 - confidence_level)

    residuals = clean - fitted
    resid_clean = residuals.dropna()

    lb_lags = min(10, len(resid_clean) // 5)
    lb_lags = max(1, lb_lags)
    lb_test = acorr_ljungbox(resid_clean, lags=[lb_lags], return_df=True)
    lb_stat = float(lb_test["lb_stat"].iloc[0])
    lb_pval = float(lb_test["lb_pvalue"].iloc[0])
    dw = float(durbin_watson(resid_clean))

    from statsmodels.tsa.stattools import acf as _acf, pacf as _pacf
    resid_lags = min(20, len(resid_clean) // 2 - 1)
    resid_lags = max(1, resid_lags)
    resid_acf = _acf(resid_clean, nlags=resid_lags, fft=True)
    resid_pacf = _pacf(resid_clean, nlags=resid_lags, method="yw")

    from scipy import stats as sp_stats
    sorted_resid = np.sort(resid_clean.values)
    n_resid = len(sorted_resid)
    theoretical = sp_stats.norm.ppf(np.arange(1, n_resid + 1) / (n_resid + 1))

    return {
        "chart_type": "ARIMA",
        "analysis_type": "time_series.arima",
        "summary": {
            "sample_size": n,
            "order": list(best_order),
            "aic": round(float(fit.aic), 4),
            "bic": round(float(fit.bic), 4),
            "log_likelihood": round(float(fit.llf), 4),
            "residual_std": round(float(resid_clean.std()), 6),
            "ljung_box_statistic": round(lb_stat, 6),
            "ljung_box_p_value": round(lb_pval, 6),
            "ljung_box_lags": lb_lags,
            "durbin_watson": round(dw, 6),
        },
        "fitted_values": [round(float(v), 6) for v in fitted],
        "forecast": [round(float(v), 6) for v in forecast_vals],
        "confidence_lower": [round(float(v), 6) for v in conf_int.iloc[:, 0]],
        "confidence_upper": [round(float(v), 6) for v in conf_int.iloc[:, 1]],
        "residual_diagnostics": {
            "acf_values": [round(float(v), 6) for v in resid_acf],
            "pacf_values": [round(float(v), 6) for v in resid_pacf],
            "qq_theoretical": [round(float(v), 6) for v in theoretical],
            "qq_sample": [round(float(v), 6) for v in sorted_resid],
        },
        "candidates": candidates[:10],
    }


def auto_select(
    data: pd.Series,
    max_p: int = 5,
    max_d: int = 2,
    max_q: int = 5,
) -> Tuple[Optional[Tuple[int, int, int]], List[Dict]]:
    """
    网格搜索自动选阶

    遍历 p∈[0..max_p], d∈[0..max_d], q∈[0..max_q]，
    选 AIC 最小的 (p, d, q) 组合。

    Returns:
        (best_order, candidates_list)
    """
    return _auto_select(data, max_p, max_d, max_q)


def _auto_select(
    data: pd.Series,
    max_p: int,
    max_d: int,
    max_q: int,
) -> Tuple[Optional[Tuple[int, int, int]], List[Dict]]:
    """内部网格搜索"""
    candidates = []
    n = len(data)

    for d in range(max_d + 1):
        for p in range(max_p + 1):
            for q in range(max_q + 1):
                if p == 0 and q == 0:
                    continue
                try:
                    model = ARIMA(data, order=(p, d, q))
                    fit = model.fit()
                    aic = float(fit.aic)
                    bic = float(fit.bic)
                    candidates.append({
                        "order": [p, d, q],
                        "aic": round(aic, 4),
                        "bic": round(bic, 4),
                        "log_likelihood": round(float(fit.llf), 4),
                    })
                except Exception:
                    continue

    if not candidates:
        return None, []

    candidates.sort(key=lambda x: x["aic"])
    best = candidates[0]
    return tuple(best["order"]), candidates
