"""
非正态过程能力分析 — Box-Cox变换 + Johnson变换 + 百分位法
"""

from typing import Dict, Any, Optional
import warnings
import numpy as np
import pandas as pd
from scipy import stats
from analysis.capability._utils import get_capability_grade
from analysis.capability.johnson_transform import (
    johnson_transform,
    transform_value as johnson_transform_value,
)


def analyze(
    data: pd.Series,
    usl: Optional[float] = None,
    lsl: Optional[float] = None,
    method: str = "box_cox",
) -> Dict[str, Any]:
    """非正态过程能力分析

    Args:
        data: 数据序列
        usl: 上规格限
        lsl: 下规格限
        method: 变换方法
            - "box_cox": Box-Cox变换
            - "johnson": Johnson变换
            - "percentile": 百分位法（不依赖变换）

    Returns:
        Dict包含能力指数和统计量
    """
    clean = data.dropna().values.astype(float)
    n = len(clean)
    if n < 5:
        raise ValueError(f"数据量不足: {n}")

    if method == "percentile":
        return _analyze_percentile(clean, usl, lsl)

    if np.std(clean) == 0:
        result = {
            "chart_type": "Non-Normal Capability",
            "method": method,
            "transform_param": None,
            "summary": {
                "sample_size": n,
                "original_mean": round(float(np.mean(clean)), 6),
                "original_std": 0.0,
                "skewness": 0.0,
                "kurtosis": 0.0,
                "transformed_mean": round(float(np.mean(clean)), 6),
                "transformed_std": 0.0,
            },
            "error": "数据为常数（标准差=0），无法进行非正态能力分析",
        }
        return result

    shift = 0.0
    lam: Optional[float] = None
    johnson_params = None
    johnson_type = None
    
    if method == "box_cox":
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if np.any(clean <= 0):
                shift = abs(clean.min()) + 0.001
                transformed, lam = stats.boxcox(clean + shift)
            else:
                transformed, lam = stats.boxcox(clean)
    elif method == "johnson":
        result_johnson = johnson_transform(clean, method="auto")
        transformed = result_johnson["transformed"]
        johnson_params = result_johnson.get("params", {})
        johnson_type = result_johnson.get("type")
        lam = None
    else:
        transformed, lam = _johnson_transform(clean)

    mean_t = float(np.mean(transformed))
    std_t = float(np.std(transformed, ddof=1))
    mean_orig = float(np.mean(clean))
    std_orig = float(np.std(clean, ddof=1))

    result = {
        "chart_type": "Non-Normal Capability",
        "method": method,
        "transform_param": round(float(lam), 6) if lam is not None else None,
        "johnson_type": johnson_type,
        "johnson_params": johnson_params,
        "summary": {
            "sample_size": n,
            "original_mean": round(mean_orig, 6),
            "original_std": round(std_orig, 6),
            "skewness": round(float(stats.skew(clean)), 6),
            "kurtosis": round(float(stats.kurtosis(clean)), 6),
            "transformed_mean": round(mean_t, 6),
            "transformed_std": round(std_t, 6),
        },
    }

    has_usl = usl is not None
    has_lsl = lsl is not None
    if not (has_usl or has_lsl):
        return result

    usl_t = _transform_value(float(usl), method, lam, shift, mean_orig, std_orig,
                              johnson_params, johnson_type) if has_usl else None
    lsl_t = _transform_value(float(lsl), method, lam, shift, mean_orig, std_orig,
                              johnson_params, johnson_type) if has_lsl else None

    if has_usl and has_lsl:
        if std_t > 0:
            pp = (usl_t - lsl_t) / (6 * std_t)
            ppk = min((usl_t - mean_t) / (3 * std_t), (mean_t - lsl_t) / (3 * std_t))
            ppm = stats.norm.cdf((lsl_t - mean_t) / std_t) * 1e6 + stats.norm.sf((usl_t - mean_t) / std_t) * 1e6
        else:
            pp, ppk, ppm = None, None, None
    elif has_usl:
        if std_t > 0:
            pp = (usl_t - mean_t) / (3 * std_t)
            ppm = stats.norm.sf((usl_t - mean_t) / std_t) * 1e6
        else:
            pp, ppm = None, None
        ppk = pp
    else:
        if std_t > 0:
            pp = (mean_t - lsl_t) / (3 * std_t)
            ppm = stats.norm.cdf((lsl_t - mean_t) / std_t) * 1e6
        else:
            pp, ppm = None, None
        ppk = pp

    capability = {
        "pp": round(float(pp), 4) if pp is not None else None,
        "ppk": round(float(ppk), 4) if ppk is not None else None,
        "ppm_total": round(float(ppm), 2) if ppm is not None else None,
        "grade": get_capability_grade(ppk) if ppk is not None else "N/A",
        "sigma_level": round(float(min(ppk * 3, 6)), 2) if ppk is not None else None,
    }
    if has_usl:
        capability["usl"] = float(usl)
        capability["ppu"] = round(float(pp), 4) if pp is not None else None
    if has_lsl:
        capability["lsl"] = float(lsl)
        capability["ppl"] = round(float(pp), 4)
    result["capability"] = capability

    return result


def _analyze_percentile(
    data: np.ndarray,
    usl: Optional[float] = None,
    lsl: Optional[float] = None,
) -> Dict[str, Any]:
    """百分位法能力分析

    不依赖分布假设，直接使用经验分布函数计算能力指数。

    基于公式:
    - Pp = (USL - LSL) / (6 * σ_percentile)
    - Ppk = min((USL - P50) / (3 * σ_percentile), (P50 - LSL) / (3 * σ_percentile))
    - σ_percentile = (P99.865 - P0.135) / 6  (基于正态分布的百分位数)

    或使用更稳健的:
    - σ_percentile = IQR / 1.35  (四分位距法)
    """
    n = len(data)
    mean = float(np.mean(data))
    std = float(np.std(data, ddof=1))

    p50 = float(np.percentile(data, 50))
    p0135 = float(np.percentile(data, 0.135))
    p99865 = float(np.percentile(data, 99.865))
    q25 = float(np.percentile(data, 25))
    q75 = float(np.percentile(data, 75))

    sigma_percentile_1 = (p99865 - p0135) / 6

    iqr = q75 - q25
    sigma_percentile_2 = iqr / 1.35

    sigma_percentile = sigma_percentile_1 if sigma_percentile_1 > 0 else sigma_percentile_2

    result = {
        "chart_type": "Non-Normal Capability",
        "method": "percentile",
        "transform_param": None,
        "summary": {
            "sample_size": n,
            "original_mean": round(mean, 6),
            "original_std": round(std, 6),
            "skewness": round(float(stats.skew(data)), 6),
            "kurtosis": round(float(stats.kurtosis(data)), 6),
            "percentiles": {
                "p0_135": round(p0135, 6),
                "p25": round(q25, 6),
                "p50": round(p50, 6),
                "p75": round(q75, 6),
                "p99_865": round(p99865, 6),
            },
            "iqr": round(iqr, 6),
            "sigma_percentile": round(sigma_percentile, 6),
        },
    }

    has_usl = usl is not None
    has_lsl = lsl is not None

    if not (has_usl or has_lsl):
        return result

    capability = {}

    if has_usl and has_lsl:
        if sigma_percentile > 0:
            pp = (usl - lsl) / (6 * sigma_percentile)
            ppk = min((usl - p50) / (3 * sigma_percentile), (p50 - lsl) / (3 * sigma_percentile))

            p_above_usl = np.mean(data > usl)
            p_below_lsl = np.mean(data < lsl)
            ppm = (p_above_usl + p_below_lsl) * 1e6
        else:
            pp, ppk, ppm = None, None, None

        capability["pp"] = round(float(pp), 4) if pp is not None else None
        capability["ppk"] = round(float(ppk), 4) if ppk is not None else None
        capability["ppm_total"] = round(float(ppm), 2) if ppm is not None else None
        capability["usl"] = float(usl)
        capability["lsl"] = float(lsl)
    elif has_usl:
        if sigma_percentile > 0:
            pp = (usl - p50) / (3 * sigma_percentile)
            p_above_usl = np.mean(data > usl)
            ppm = p_above_usl * 1e6
        else:
            pp, ppm = None, None

        capability["pp"] = round(float(pp), 4) if pp is not None else None
        capability["ppk"] = capability["pp"]
        capability["ppm_total"] = round(float(ppm), 2) if ppm is not None else None
        capability["usl"] = float(usl)
    else:
        if sigma_percentile > 0:
            pp = (p50 - lsl) / (3 * sigma_percentile)
            p_below_lsl = np.mean(data < lsl)
            ppm = p_below_lsl * 1e6
        else:
            pp, ppm = None, None

        capability["pp"] = round(float(pp), 4) if pp is not None else None
        capability["ppk"] = capability["pp"]
        capability["ppm_total"] = round(float(ppm), 2) if ppm is not None else None
        capability["lsl"] = float(lsl)

    capability["grade"] = get_capability_grade(capability.get("ppk")) if capability.get("ppk") is not None else "N/A"
    capability["sigma_level"] = round(float(min(capability["ppk"] * 3, 6)), 2) if capability.get("ppk") is not None else None

    result["capability"] = capability
    return result


def _johnson_transform(data: np.ndarray) -> tuple:
    """z-score 标准化(Johnson 变换的近似实现)"""
    std = np.std(data, ddof=1)
    if std <= 0:
        return np.zeros_like(data), None
    return (data - np.mean(data)) / std, None


def _transform_value(value: float, method: str, lam: Optional[float],
                     shift: float, mean: float, std: float,
                     johnson_params: Optional[Dict] = None,
                     johnson_type: Optional[str] = None) -> float:
    """把原始尺度下的规格限变换到变换后尺度, 与数据变换口径完全一致"""
    if method == "johnson" and johnson_params and johnson_type:
        return johnson_transform_value(value, johnson_params, johnson_type)
    x = value + shift
    if x <= 0:
        return -1e9
    if lam == 0:
        return float(np.log(x))
    return float((x ** lam - 1) / lam)


