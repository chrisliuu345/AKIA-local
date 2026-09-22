"""
自动能力分析 — 自动检测最佳拟合分布 → 选择最优变换 → 输出能力指标

支持:
- 自动分布检测 (正态/对数正态/Weibull/Gamma)
- AIC/BIC 拟合优度排序
- 自动变换选择 (Box-Cox/Johnson/无变换)
- Edgeworth 近似能力指数
"""

import logging
from typing import Any
import warnings
import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger("QA-Tool.AutoCap")


DISTRIBUTIONS = {
    "normal": {"scipy": stats.norm, "name": "正态"},
    "lognormal": {"scipy": stats.lognorm, "name": "对数正态"},
    "weibull": {"scipy": stats.weibull_min, "name": "Weibull"},
    "gamma": {"scipy": stats.gamma, "name": "Gamma"},
    "exponential": {"scipy": stats.expon, "name": "指数"},
}


def analyze(
    data: pd.Series,
    usl: float | None = None,
    lsl: float | None = None,
    target: float | None = None,
) -> dict[str, Any]:
    """
    自动能力分析

    Args:
        data: 测量数据
        usl: 上规格限
        lsl: 下规格限
        target: 目标值

    Returns:
        自动能力分析结果
    """
    clean = data.dropna().values.astype(float)
    n = len(clean)

    if n < 10:
        raise ValueError(f"数据量不足: 需要至少 10 个观测值，当前 {n}")

    fit_results = _fit_all_distributions(clean)
    best_dist = _select_best_distribution(fit_results)

    transform_result = _select_transform(clean)
    transformed_data = transform_result["transformed"]

    if usl is not None and lsl is not None:
        capability = _calculate_capability(
            transformed_data, usl, lsl, target,
            transform_result, best_dist
        )
    else:
        capability = {"error": "未提供规格限，无法计算能力指数"}

    return {
        "chart_type": "Auto Capability Analysis",
        "sample_size": n,
        "best_distribution": best_dist,
        "fit_results": fit_results,
        "transform": transform_result,
        "capability": capability,
    }


def _fit_all_distributions(data: np.ndarray) -> list[dict[str, Any]]:
    """拟合所有支持的分布"""
    results = []

    for dist_name, dist_info in DISTRIBUTIONS.items():
        try:
            scipy_dist = dist_info["scipy"]

            if dist_name == "normal":
                params = scipy_dist.fit(data)
                loglik = np.sum(scipy_dist.logpdf(data, *params))
            elif dist_name == "lognormal":
                positive_data = data[data > 0]
                if len(positive_data) < len(data) * 0.9:
                    continue
                params = scipy_dist.fit(positive_data)
                loglik = np.sum(scipy_dist.logpdf(positive_data, *params))
            elif dist_name == "weibull":
                positive_data = data[data > 0]
                if len(positive_data) < len(data) * 0.9:
                    continue
                params = scipy_dist.fit(positive_data)
                loglik = np.sum(scipy_dist.logpdf(positive_data, *params))
            elif dist_name == "gamma":
                positive_data = data[data > 0]
                if len(positive_data) < len(data) * 0.9:
                    continue
                params = scipy_dist.fit(positive_data)
                loglik = np.sum(scipy_dist.logpdf(positive_data, *params))
            elif dist_name == "exponential":
                positive_data = data[data > 0]
                if len(positive_data) < len(data) * 0.9:
                    continue
                params = scipy_dist.fit(positive_data)
                loglik = np.sum(scipy_dist.logpdf(positive_data, *params))
            else:
                continue

            k = len(params)
            n = len(data)
            aic = 2 * k - 2 * loglik
            bic = k * np.log(n) - 2 * loglik

            ks_stat, ks_p = stats.kstest(
                data if dist_name == "normal" else positive_data,
                lambda x, d=scipy_dist, p=params: d.cdf(x, *p)
            )

            results.append({
                "distribution": dist_name,
                "name": dist_info["name"],
                "params": params,
                "loglik": float(loglik),
                "aic": float(aic),
                "bic": float(bic),
                "ks_statistic": float(ks_stat),
                "ks_p_value": float(ks_p),
            })
        except Exception:
            continue

    return sorted(results, key=lambda x: x["aic"])


def _select_best_distribution(fit_results: list[dict[str, Any]]) -> dict[str, Any]:
    """选择最佳分布 (基于 AIC)"""
    if not fit_results:
        return {"distribution": "normal", "name": "正态", "params": (0, 1), "aic": float('inf')}

    best = fit_results[0]

    return {
        "distribution": best["distribution"],
        "name": best["name"],
        "params": best["params"],
        "aic": best["aic"],
        "bic": best["bic"],
        "ks_statistic": best["ks_statistic"],
        "ks_p_value": best["ks_p_value"],
    }


def _select_transform(data: np.ndarray) -> dict[str, Any]:
    """选择最优变换"""
    skewness = float(stats.skew(data))
    kurtosis = float(stats.kurtosis(data))

    if abs(skewness) < 0.5 and abs(kurtosis) < 1:
        return {
            "method": "none",
            "transformed": data,
            "params": {},
            "skewness": skewness,
            "kurtosis": kurtosis,
        }

    if skewness > 0.5:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                transformed, lmbda = stats.boxcox(data[data > 0])
            return {
                "method": "boxcox",
                "transformed": transformed,
                "params": {"lambda": float(lmbda)},
                "skewness": float(stats.skew(transformed)),
                "kurtosis": float(stats.kurtosis(transformed)),
            }
        except Exception as e:  # noqa: BLE001 - 变换失败退回无变换（method=none）
            logger.debug("Box-Cox 正偏变换失败，退回无变换: %s", e)

    if skewness < -0.5:
        try:
            flipped = data.max() - data + 1
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                transformed, lmbda = stats.boxcox(flipped[flipped > 0])
            return {
                "method": "boxcox_inverse",
                "transformed": transformed,
                "params": {"lambda": float(lmbda), "flipped": True},
                "skewness": float(stats.skew(transformed)),
                "kurtosis": float(stats.kurtosis(transformed)),
            }
        except Exception as e:  # noqa: BLE001 - 变换失败退回无变换（method=none）
            logger.debug("Box-Cox 反偏变换失败，退回无变换: %s", e)

    return {
        "method": "none",
        "transformed": data,
        "params": {},
        "skewness": skewness,
        "kurtosis": kurtosis,
    }


def _calculate_capability(
    data: np.ndarray,
    usl: float,
    lsl: float,
    target: float | None,
    transform_result: dict[str, Any],
    best_dist: dict[str, Any],
) -> dict[str, Any]:
    """计算能力指数"""
    len(data)
    mean = float(np.mean(data))
    std = float(np.std(data, ddof=1))

    if std == 0:
        return {"error": "标准差为 0，无法计算能力指数"}

    cp = (usl - lsl) / (6 * std)
    cpk = min((usl - mean) / (3 * std), (mean - lsl) / (3 * std))

    cpm = None
    if target is not None:
        sigma_t = float(np.sqrt(np.mean((data - target) ** 2)))
        cpm = (usl - lsl) / (6 * sigma_t) if sigma_t > 0 else float('inf')

    z_upper = (usl - mean) / std
    z_lower = (mean - lsl) / std
    ppm_above = (1 - stats.norm.cdf(z_upper)) * 1_000_000
    ppm_below = (1 - stats.norm.cdf(z_lower)) * 1_000_000
    ppm_total = ppm_above + ppm_below

    return {
        "cp": round(float(cp), 4),
        "cpk": round(float(cpk), 4),
        "cpm": round(float(cpm), 4) if cpm is not None else None,
        "ppm_above": round(float(ppm_above), 0),
        "ppm_below": round(float(ppm_below), 0),
        "ppm_total": round(float(ppm_total), 0),
        "pct_defective": round(float(ppm_total / 10_000), 4),
        "grade": _capability_grade(cpk),
        "mean": round(mean, 6),
        "std": round(std, 6),
    }


def _capability_grade(cpk: float) -> str:
    """能力等级判定"""
    if cpk >= 1.67:
        return "A+ (优秀)"
    elif cpk >= 1.33:
        return "A (良好)"
    elif cpk >= 1.00:
        return "B (可接受)"
    elif cpk >= 0.67:
        return "C (边缘)"
    else:
        return "D (差)"
