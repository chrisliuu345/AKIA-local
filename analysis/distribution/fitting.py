"""
通用分布拟合分析 — MLE 参数估计 + 拟合优度检验

支持分布：Normal, Lognormal, Exponential, Gamma, Weibull
拟合优度：Anderson-Darling, Kolmogorov-Smirnov, Chi-Square
"""

from typing import Any
import numpy as np
import pandas as pd
from scipy import stats


SUPPORTED_DISTRIBUTIONS = ["normal", "lognormal", "exponential", "gamma", "weibull"]


def fit_distribution(
    data: pd.Series,
    distribution: str = "normal",
) -> dict[str, Any]:
    """
    拟合指定分布并返回参数估计

    Args:
        data: 数据列
        distribution: 分布名称

    Returns:
        拟合结果字典
    """
    clean = data.dropna().astype(float)
    n = len(clean)

    if n < 5:
        raise ValueError(f"数据量不足: {n}，至少需要 5 个观测值")

    if distribution not in SUPPORTED_DISTRIBUTIONS:
        raise ValueError(f"不支持的分布: {distribution}")

    if distribution == "normal":
        result = _fit_normal(clean)
    elif distribution == "lognormal":
        result = _fit_lognormal(clean)
    elif distribution == "exponential":
        result = _fit_exponential(clean)
    elif distribution == "gamma":
        result = _fit_gamma(clean)
    elif distribution == "weibull":
        result = _fit_weibull(clean)

    result["distribution"] = distribution
    result["sample_size"] = n
    result["data_stats"] = {
        "mean": round(float(np.mean(clean)), 6),
        "std": round(float(np.std(clean, ddof=1)), 6),
        "min": round(float(np.min(clean)), 6),
        "max": round(float(np.max(clean)), 6),
    }

    return result


def goodness_of_fit(
    data: pd.Series,
    distribution: str = "normal",
    tests: list[str] | None = None,
) -> dict[str, Any]:
    """
    拟合优度检验

    Args:
        data: 数据列
        distribution: 分布名称
        tests: 检验方法列表，默认 ["ad", "ks", "chi2"]

    Returns:
        检验结果字典
    """
    clean = data.dropna().astype(float)
    n = len(clean)

    if tests is None:
        tests = ["ad", "ks", "chi2"]

    fit_result = fit_distribution(clean, distribution)
    params = fit_result.get("params", {})

    results = {
        "distribution": distribution,
        "sample_size": n,
        "tests": {},
    }

    dist = _get_scipy_dist(distribution, params)

    if dist is None:
        results["error"] = "无法获取分布对象"
        return results

    if "ad" in tests:
        ad_result = _anderson_darling_test(clean, dist)
        results["tests"]["anderson_darling"] = ad_result

    if "ks" in tests:
        ks_result = _kolmogorov_smirnov_test(clean, dist)
        results["tests"]["kolmogorov_smirnov"] = ks_result

    if "chi2" in tests:
        chi2_result = _chi_square_test(clean, dist)
        results["tests"]["chi_square"] = chi2_result

    return results


def compare_distributions(
    data: pd.Series,
    distributions: list[str] | None = None,
) -> dict[str, Any]:
    """
    比较多个分布的拟合效果

    Args:
        data: 数据列
        distributions: 分布列表，默认全部

    Returns:
        比较结果字典
    """
    if distributions is None:
        distributions = SUPPORTED_DISTRIBUTIONS

    clean = data.dropna().astype(float)
    comparisons = []

    for dist_name in distributions:
        try:
            fit_result = fit_distribution(clean, dist_name)
            gof_result = goodness_of_fit(clean, dist_name, tests=["ad", "ks"])

            n = len(clean)
            log_likelihood = _compute_log_likelihood(clean, dist_name, fit_result.get("params", {}))
            k = len(fit_result.get("params", {}))
            aic = 2 * k - 2 * log_likelihood
            bic = k * np.log(n) - 2 * log_likelihood

            comparisons.append({
                "distribution": dist_name,
                "params": fit_result.get("params", {}),
                "log_likelihood": round(float(log_likelihood), 4),
                "aic": round(float(aic), 4),
                "bic": round(float(bic), 4),
                "ad_statistic": gof_result.get("tests", {}).get("anderson_darling", {}).get("statistic"),
                "ks_p_value": gof_result.get("tests", {}).get("kolmogorov_smirnov", {}).get("p_value"),
            })
        except Exception as e:  # noqa: BLE001 - 单个分布拟合失败：记入 comparisons 供用户查看
            comparisons.append({
                "distribution": dist_name,
                "error": str(e),
            })

    valid_comparisons = [c for c in comparisons if "aic" in c]
    valid_comparisons.sort(key=lambda x: x["aic"])

    return {
        "sample_size": len(clean),
        "comparisons": comparisons,
        "best_fit": valid_comparisons[0] if valid_comparisons else None,
    }


def _fit_normal(data: np.ndarray) -> dict[str, Any]:
    """正态分布拟合"""
    mu, sigma = stats.norm.fit(data)
    return {
        "params": {"mu": round(float(mu), 6), "sigma": round(float(sigma), 6)},
        "param_names": ["mu", "sigma"],
    }


def _fit_lognormal(data: np.ndarray) -> dict[str, Any]:
    """对数正态分布拟合"""
    if np.any(data <= 0):
        shift = abs(np.min(data)) + 0.001
        data = data + shift
    else:
        shift = 0.0

    shape, loc, scale = stats.lognorm.fit(data, floc=0)
    return {
        "params": {
            "shape": round(float(shape), 6),
            "loc": round(float(loc), 6),
            "scale": round(float(scale), 6),
            "shift": round(float(shift), 6),
        },
        "param_names": ["shape", "loc", "scale", "shift"],
    }


def _fit_exponential(data: np.ndarray) -> dict[str, Any]:
    """指数分布拟合"""
    if np.any(data < 0):
        shift = abs(np.min(data))
        data = data + shift
    else:
        shift = 0.0

    loc, scale = stats.expon.fit(data, floc=0)
    return {
        "params": {
            "loc": round(float(loc), 6),
            "scale": round(float(scale), 6),
            "shift": round(float(shift), 6),
        },
        "param_names": ["loc", "scale", "shift"],
    }


def _fit_gamma(data: np.ndarray) -> dict[str, Any]:
    """Gamma 分布拟合"""
    if np.any(data <= 0):
        shift = abs(np.min(data)) + 0.001
        data = data + shift
    else:
        shift = 0.0

    shape, loc, scale = stats.gamma.fit(data, floc=0)
    return {
        "params": {
            "a": round(float(shape), 6),
            "loc": round(float(loc), 6),
            "scale": round(float(scale), 6),
            "shift": round(float(shift), 6),
        },
        "param_names": ["a", "loc", "scale", "shift"],
    }


def _fit_weibull(data: np.ndarray) -> dict[str, Any]:
    """Weibull 分布拟合"""
    if np.any(data <= 0):
        shift = abs(np.min(data)) + 0.001
        data = data + shift
    else:
        shift = 0.0

    c, loc, scale = stats.weibull_min.fit(data, floc=0)
    return {
        "params": {
            "c": round(float(c), 6),
            "loc": round(float(loc), 6),
            "scale": round(float(scale), 6),
            "shift": round(float(shift), 6),
        },
        "param_names": ["c", "loc", "scale", "shift"],
    }


def _get_scipy_dist(distribution: str, params: dict[str, float]):
    """获取 scipy 分布对象"""
    if distribution == "normal":
        return stats.norm(loc=params.get("mu", 0), scale=params.get("sigma", 1))
    if distribution == "lognormal":
        return stats.lognorm(
            s=params.get("shape", 1),
            loc=params.get("loc", 0),
            scale=params.get("scale", 1),
        )
    if distribution == "exponential":
        return stats.expon(loc=params.get("loc", 0), scale=params.get("scale", 1))
    if distribution == "gamma":
        return stats.gamma(
            a=params.get("a", 1),
            loc=params.get("loc", 0),
            scale=params.get("scale", 1),
        )
    if distribution == "weibull":
        return stats.weibull_min(
            c=params.get("c", 1),
            loc=params.get("loc", 0),
            scale=params.get("scale", 1),
        )
    return None


def _anderson_darling_test(data: np.ndarray, dist) -> dict[str, Any]:
    """Anderson-Darling 检验"""
    try:
        result = stats.anderson(data, dist="norm")
        return {
            "statistic": round(float(result.statistic), 4),
            "critical_values": {
                f"{level}%": round(float(cv), 4)
                for level, cv in zip([15, 10, 5, 2.5, 1], result.critical_values, strict=True)
            },
            "is_normal": result.statistic < result.critical_values[2],
        }
    except Exception:  # noqa: BLE001 - Anderson-Darling 不可用：退回经验 CDF 路径
        sorted_data = np.sort(data)
        n = len(sorted_data)
        cdf_values = dist.cdf(sorted_data)
        cdf_values = np.clip(cdf_values, 1e-10, 1 - 1e-10)
        i = np.arange(1, n + 1)
        ad = -n - np.mean((2 * i - 1) * (np.log(cdf_values) + np.log(1 - cdf_values[::-1])))
        return {
            "statistic": round(float(ad), 4),
            "critical_values": {},
            "interpretation": "AD 统计量越小表示拟合越好",
        }


def _kolmogorov_smirnov_test(data: np.ndarray, dist) -> dict[str, Any]:
    """Kolmogorov-Smirnov 检验"""
    result = stats.kstest(data, dist.cdf)
    return {
        "statistic": round(float(result.statistic), 6),
        "p_value": round(float(result.pvalue), 6),
        "is_rejected": result.pvalue < 0.05,
        "interpretation": "不拒绝原假设（拟合良好）" if result.pvalue >= 0.05 else "拒绝原假设（拟合不佳）",
    }


def _chi_square_test(data: np.ndarray, dist, bins: int = 10) -> dict[str, Any]:
    """Chi-Square 拟合优度检验"""
    n = len(data)
    observed, bin_edges = np.histogram(data, bins=bins)
    expected = dist.cdf(bin_edges[1:]) - dist.cdf(bin_edges[:-1])
    expected = expected * n

    while np.any(expected < 5) and len(expected) > 2:
        min_idx = np.argmin(expected)
        if min_idx == 0:
            observed = np.array([observed[0] + observed[1]] + list(observed[2:]))
            expected = np.array([expected[0] + expected[1]] + list(expected[2:]))
        elif min_idx == len(expected) - 1:
            observed = np.array(list(observed[:-2]) + [observed[-2] + observed[-1]])
            expected = np.array(list(expected[:-2]) + [expected[-2] + expected[-1]])
        else:
            if expected[min_idx - 1] < expected[min_idx + 1]:
                observed = np.array(list(observed[:min_idx-1]) + [observed[min_idx-1] + observed[min_idx]] + list(observed[min_idx+1:]))
                expected = np.array(list(expected[:min_idx-1]) + [expected[min_idx-1] + expected[min_idx]] + list(expected[min_idx+1:]))
            else:
                observed = np.array(list(observed[:min_idx]) + [observed[min_idx] + observed[min_idx+1]] + list(observed[min_idx+2:]))
                expected = np.array(list(expected[:min_idx]) + [expected[min_idx] + expected[min_idx+1]] + list(expected[min_idx+2:]))

    expected_safe = np.where(expected == 0, 1e-10, expected)
    chi2 = np.sum((observed - expected) ** 2 / expected_safe)
    df = len(observed) - 1
    p_value = 1 - stats.chi2.cdf(chi2, df)

    return {
        "statistic": round(float(chi2), 4),
        "df": df,
        "p_value": round(float(p_value), 6),
        "bins_used": len(observed),
        "is_rejected": p_value < 0.05,
        "interpretation": "不拒绝原假设（拟合良好）" if p_value >= 0.05 else "拒绝原假设（拟合不佳）",
    }


def _compute_log_likelihood(data: np.ndarray, distribution: str, params: dict[str, float]) -> float:
    """计算对数似然值"""
    dist = _get_scipy_dist(distribution, params)
    if dist is None:
        return 0.0

    try:
        log_pdf = dist.logpdf(data)
        log_pdf = np.where(np.isfinite(log_pdf), log_pdf, -1e10)
        return float(np.sum(log_pdf))
    except Exception:  # noqa: BLE001 - 对数似然数值失败：按 0 处理（仅用于排序）
        return 0.0
