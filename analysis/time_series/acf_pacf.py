"""
ACF/PACF 分析 — 平稳性检验 + 自相关/偏自相关 + Ljung-Box + Durbin-Watson

提供:
  analyze()         — 完整 ACF/PACF 分析（ADF + ACF + PACF + Ljung-Box + Durbin-Watson）
  check_stationarity() — ADF 平稳性检验
  compute_acf()     — 自相关函数
  compute_pacf()    — 偏自相关函数
"""

import pandas as pd
from typing import Any, Dict, Optional

from statsmodels.tsa.stattools import adfuller, acf, pacf
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.stats.stattools import durbin_watson


def check_stationarity(
    data: pd.Series,
    significance_level: float = 0.05,
) -> Dict[str, Any]:
    """
    ADF 平稳性检验

    Args:
        data: 时间序列数据
        significance_level: 显著性水平（默认 0.05）

    Returns:
        包含 ADF 统计量、p 值、是否平稳等信息的字典
    """
    clean = data.dropna().astype(float)
    if len(clean) < 6:
        return {
            "adf_statistic": None,
            "p_value": None,
            "is_stationary": None,
            "lags_used": None,
            "n_obs": len(clean),
            "critical_values": {},
            "error": "数据点不足（最少需要 6 个）",
        }

    result = adfuller(clean, autolag="AIC", result_object=True)
    adf_stat = result.statistic
    p_value = result.pvalue
    lags = result.lags
    nobs = result.nobs
    crit_vals = result.critical_values

    return {
        "adf_statistic": round(float(adf_stat), 6),
        "p_value": round(float(p_value), 6),
        "is_stationary": bool(p_value < significance_level),
        "lags_used": int(lags),
        "n_obs": int(nobs),
        "critical_values": {k: round(float(v), 6) for k, v in crit_vals.items()},
        "significance_level": significance_level,
    }


def compute_acf(
    data: pd.Series,
    lags: int = 40,
    alpha: float = 0.05,
) -> Dict[str, Any]:
    """
    计算自相关函数（ACF）

    Args:
        data: 时间序列数据
        lags: 最大滞后阶数
        alpha: 置信区间显著性水平

    Returns:
        ACF 值、置信区间边界
    """
    clean = data.dropna().astype(float)
    max_lags = min(lags, len(clean) // 2 - 1)
    if max_lags < 1:
        max_lags = 1

    acf_result = acf(clean, nlags=max_lags, alpha=alpha, result_object=True)
    acf_vals = acf_result.acf
    confint = acf_result.confint
    confidence_band = round(float(confint[0, 1] - acf_vals[0]), 6)

    return {
        "acf_values": [round(float(v), 6) for v in acf_vals],
        "confidence_band": confidence_band,
        "confidence_lower": [round(float(v), 6) for v in confint[:, 0]],
        "confidence_upper": [round(float(v), 6) for v in confint[:, 1]],
        "nlags": max_lags,
    }


def compute_pacf(
    data: pd.Series,
    lags: int = 40,
    alpha: float = 0.05,
) -> Dict[str, Any]:
    """
    计算偏自相关函数（PACF）

    Args:
        data: 时间序列数据
        lags: 最大滞后阶数
        alpha: 置信区间显著性水平

    Returns:
        PACF 值、置信区间边界
    """
    clean = data.dropna().astype(float)
    max_lags = min(lags, len(clean) // 2 - 1)
    if max_lags < 1:
        max_lags = 1

    pacf_result = pacf(clean, nlags=max_lags, alpha=alpha, method="yw", result_object=True)
    pacf_vals = pacf_result.pacf
    confint = pacf_result.confint
    confidence_band = round(float(confint[0, 1] - pacf_vals[0]), 6)

    return {
        "pacf_values": [round(float(v), 6) for v in pacf_vals],
        "confidence_band": confidence_band,
        "confidence_lower": [round(float(v), 6) for v in confint[:, 0]],
        "confidence_upper": [round(float(v), 6) for v in confint[:, 1]],
        "nlags": max_lags,
    }


def analyze(
    data: pd.Series,
    lags: int = 40,
    significance_level: float = 0.05,
    ljung_box_lags: Optional[int] = None,
) -> Dict[str, Any]:
    """
    完整 ACF/PACF 分析

    包含: ADF 平稳性检验、ACF、PACF、Ljung-Box 检验、Durbin-Watson 统计量

    Args:
        data: 时间序列数据
        lags: ACF/PACF 最大滞后阶数
        significance_level: 显著性水平
        ljung_box_lags: Ljung-Box 检验滞后阶数（默认 min(10, n//5)）

    Returns:
        完整分析结果字典
    """
    clean = data.dropna().astype(float)
    n = len(clean)

    if n < 6:
        return {
            "chart_type": "ACF/PACF",
            "analysis_type": "time_series.acf_pacf",
            "summary": {},
            "error": f"数据点不足: {n}（最少需要 6 个）",
        }

    stationarity = check_stationarity(clean, significance_level)
    acf_result = compute_acf(clean, lags)
    pacf_result = compute_pacf(clean, lags)

    lb_lags = ljung_box_lags or min(10, n // 5)
    lb_lags = max(1, min(lb_lags, n // 2 - 1))
    lb_test = acorr_ljungbox(clean, lags=[lb_lags], return_df=True)
    lb_stat = float(lb_test["lb_stat"].iloc[0])
    lb_pval = float(lb_test["lb_pvalue"].iloc[0])

    dw = float(durbin_watson(clean.values))

    return {
        "chart_type": "ACF/PACF",
        "analysis_type": "time_series.acf_pacf",
        "summary": {
            "sample_size": n,
            "adf_statistic": stationarity["adf_statistic"],
            "adf_p_value": stationarity["p_value"],
            "is_stationary": stationarity["is_stationary"],
            "ljung_box_statistic": round(lb_stat, 6),
            "ljung_box_p_value": round(lb_pval, 6),
            "ljung_box_lags": lb_lags,
            "durbin_watson": round(dw, 6),
            "critical_values": stationarity["critical_values"],
        },
        "acf": acf_result,
        "pacf": pacf_result,
    }
