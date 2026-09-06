"""
Power & Sample Size Analysis — 假设检验功效分析与样本量计算器

References:
    Montgomery D C (2017). Design and Analysis of Experiments, 9th ed.
    Minitab Power and Sample Size Documentation.
    Cohen J (1988). Statistical Power Analysis for the Behavioral Sciences, 2nd ed.

Supports:
    - 1-Sample t, 2-Sample t, Paired t
    - 1-Proportion, 2-Proportions
    - 1-Variance
    - One-Way ANOVA
"""
from typing import Dict, Any, Tuple
import math
import numpy as np
from scipy import stats


def _z(p: float) -> float:
    """Standard normal quantile (inverse CDF)."""
    return stats.norm.ppf(p)


def _t_quantile(p: float, df: int) -> float:
    """Student's t quantile."""
    return stats.t.ppf(p, df)


def power_one_sample_t(
    n: int,
    delta: float,
    sigma: float,
    alpha: float = 0.05,
) -> float:
    """Compute power for 1-sample t test.

    Parameters
    ----------
    n : int
        Sample size (per group).
    delta : float
        Mean difference to detect (|μ1 - μ0|).
    sigma : float
        Population standard deviation.
    alpha : float
        Significance level (two-sided).

    Returns
    -------
    float : Power (1 - β), in [0, 1].
    """
    if n < 2 or sigma <= 0 or delta == 0:
        return 0.0

    df = n - 1
    se = sigma / math.sqrt(n)
    ncp = delta / se
    t_crit = _t_quantile(1 - alpha / 2, df)
    power = 1 - (stats.nct.cdf(t_crit, df, ncp) - stats.nct.cdf(-t_crit, df, ncp))
    return float(max(0.0, min(1.0, power)))


def sample_size_one_sample_t(
    delta: float,
    sigma: float,
    power: float = 0.8,
    alpha: float = 0.05,
) -> int:
    """Compute required sample size for 1-sample t test.

    Uses iterative search with initial estimate from z-approximation.
    """
    if delta == 0 or sigma <= 0:
        return 0

    n_est = math.ceil(((sigma / delta) * (_z(1 - alpha / 2) + _z(power))) ** 2)
    n_est = max(n_est, 3)

    for n in range(max(3, n_est - 10), n_est + 50):
        pwr = power_one_sample_t(n, delta, sigma, alpha)
        if pwr >= power:
            return n

    lo, hi = max(3, n_est - 10), n_est + 100
    while lo < hi:
        mid = (lo + hi) // 2
        if power_one_sample_t(mid, delta, sigma, alpha) >= power:
            hi = mid
        else:
            lo = mid + 1
    return lo


def power_two_sample_t(
    n1: int,
    n2: int,
    delta: float,
    sigma: float,
    alpha: float = 0.05,
    ratio: float = 1.0,
) -> float:
    """Compute power for 2-sample t test (pooled variance).

    Parameters
    ----------
    n1, n2 : int
        Sample sizes for groups 1 and 2.
    delta : float
        Mean difference to detect (|μ1 - μ2|).
    sigma : float
        Pooled standard deviation.
    alpha : float
        Significance level (two-sided).
    ratio : float
        Allocation ratio (n2/n1), used if n2=0.

    Returns
    -------
    float : Power.
    """
    if n1 < 2 or sigma <= 0 or delta == 0:
        return 0.0

    if n2 == 0:
        n2 = max(2, int(n1 * ratio))

    df = n1 + n2 - 2
    se = sigma * math.sqrt(1 / n1 + 1 / n2)
    ncp = delta / se
    t_crit = _t_quantile(1 - alpha / 2, df)
    power = 1 - (stats.nct.cdf(t_crit, df, ncp) - stats.nct.cdf(-t_crit, df, ncp))
    return float(max(0.0, min(1.0, power)))


def sample_size_two_sample_t(
    delta: float,
    sigma: float,
    power: float = 0.8,
    alpha: float = 0.05,
    ratio: float = 1.0,
) -> int:
    """Compute required sample size per group for 2-sample t test.

    Returns n1; n2 = ratio * n1.
    """
    if delta == 0 or sigma <= 0:
        return 0

    n1_est = math.ceil(((sigma / delta) * (_z(1 - alpha / 2) + _z(power))) ** 2 * (1 + 1 / ratio))
    n1_est = max(n1_est, 3)

    for n1 in range(max(3, n1_est - 10), n1_est + 50):
        n2 = max(2, int(n1 * ratio))
        pwr = power_two_sample_t(n1, n2, delta, sigma, alpha, ratio)
        if pwr >= power:
            return n1

    lo, hi = max(3, n1_est - 10), n1_est + 100
    while lo < hi:
        mid = (lo + hi) // 2
        n2 = max(2, int(mid * ratio))
        if power_two_sample_t(mid, n2, delta, sigma, alpha, ratio) >= power:
            hi = mid
        else:
            lo = mid + 1
    return lo


def power_paired_t(
    n: int,
    delta: float,
    sigma_d: float,
    alpha: float = 0.05,
) -> float:
    """Compute power for paired t test.

    Parameters
    ----------
    n : int
        Number of pairs.
    delta : float
        Mean difference to detect.
    sigma_d : float
        Standard deviation of differences.
    alpha : float
        Significance level.
    """
    return power_one_sample_t(n, delta, sigma_d, alpha)


def sample_size_paired_t(
    delta: float,
    sigma_d: float,
    power: float = 0.8,
    alpha: float = 0.05,
) -> int:
    """Compute required number of pairs for paired t test."""
    return sample_size_one_sample_t(delta, sigma_d, power, alpha)


def power_one_proportion(
    n: int,
    p1: float,
    p0: float,
    alpha: float = 0.05,
) -> float:
    """Compute power for 1-proportion z test (two-sided).

    Parameters
    ----------
    n : int
        Sample size.
    p1 : float
        True proportion.
    p0 : float
        Null hypothesis proportion.
    alpha : float
        Significance level.
    """
    if n < 2 or p0 <= 0 or p0 >= 1 or p1 <= 0 or p1 >= 1:
        return 0.0

    se0 = math.sqrt(p0 * (1 - p0) / n)
    se1 = math.sqrt(p1 * (1 - p1) / n)

    if se0 == 0 or se1 == 0:
        return 0.0

    z_crit = _z(1 - alpha / 2)
    z_power = (abs(p1 - p0) - z_crit * se0) / se1
    power = _norm_cdf(z_power)
    return float(max(0.0, min(1.0, power)))


def _norm_cdf(x: float) -> float:
    """Standard normal CDF."""
    return float(stats.norm.cdf(x))


def sample_size_one_proportion(
    p1: float,
    p0: float,
    power: float = 0.8,
    alpha: float = 0.05,
) -> int:
    """Compute required sample size for 1-proportion z test."""
    if p0 <= 0 or p0 >= 1 or p1 <= 0 or p1 >= 1 or p1 == p0:
        return 0

    z_alpha = _z(1 - alpha / 2)
    z_beta = _z(power)
    se0 = math.sqrt(p0 * (1 - p0))
    se1 = math.sqrt(p1 * (1 - p1))

    n_est = math.ceil(((z_alpha * se0 + z_beta * se1) / abs(p1 - p0)) ** 2)
    n_est = max(n_est, 2)

    for n in range(max(2, n_est - 10), n_est + 50):
        pwr = power_one_proportion(n, p1, p0, alpha)
        if pwr >= power:
            return n

    return n_est


def power_two_proportions(
    n1: int,
    n2: int,
    p1: float,
    p2: float,
    alpha: float = 0.05,
) -> float:
    """Compute power for 2-proportions z test (two-sided).

    Parameters
    ----------
    n1, n2 : int
        Sample sizes.
    p1, p2 : float
        True proportions.
    alpha : float
        Significance level.
    """
    if n1 < 2 or n2 < 2:
        return 0.0
    if p1 <= 0 or p1 >= 1 or p2 <= 0 or p2 >= 1:
        return 0.0

    p_pool = (n1 * p1 + n2 * p2) / (n1 + n2)
    se_pool = math.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    se_diff = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)

    if se_pool == 0 or se_diff == 0:
        return 0.0

    z_crit = _z(1 - alpha / 2)
    z_power = (abs(p1 - p2) - z_crit * se_pool) / se_diff
    power = _norm_cdf(z_power)
    return float(max(0.0, min(1.0, power)))


def sample_size_two_proportions(
    p1: float,
    p2: float,
    power: float = 0.8,
    alpha: float = 0.05,
    ratio: float = 1.0,
) -> int:
    """Compute required sample size per group for 2-proportions test.

    Returns n1; n2 = ratio * n1.
    """
    if p1 <= 0 or p1 >= 1 or p2 <= 0 or p2 >= 1 or p1 == p2:
        return 0

    z_alpha = _z(1 - alpha / 2)
    z_beta = _z(power)
    p_pool = (p1 + ratio * p2) / (1 + ratio)
    se_pool = math.sqrt(p_pool * (1 - p_pool) * (1 + 1 / ratio))
    se_diff = math.sqrt(p1 * (1 - p1) + p2 * (1 - p2) / ratio)

    n1_est = math.ceil(((z_alpha * se_pool + z_beta * se_diff) / abs(p1 - p2)) ** 2)
    n1_est = max(n1_est, 2)

    for n1 in range(max(2, n1_est - 10), n1_est + 50):
        n2 = max(2, int(n1 * ratio))
        pwr = power_two_proportions(n1, n2, p1, p2, alpha)
        if pwr >= power:
            return n1

    return n1_est


def power_one_variance(
    n: int,
    sigma: float,
    sigma0: float,
    alpha: float = 0.05,
) -> float:
    """Compute power for 1-variance chi-square test (two-sided).

    Parameters
    ----------
    n : int
        Sample size.
    sigma : float
        True standard deviation.
    sigma0 : float
        Null hypothesis standard deviation.
    alpha : float
        Significance level.
    """
    if n < 2 or sigma <= 0 or sigma0 <= 0:
        return 0.0

    df = n - 1
    ratio = (sigma / sigma0) ** 2
    chi2_lower = stats.chi2.ppf(alpha / 2, df)
    chi2_upper = stats.chi2.ppf(1 - alpha / 2, df)
    power_lower = stats.chi2.cdf(chi2_lower / ratio, df)
    power_upper = 1 - stats.chi2.cdf(chi2_upper / ratio, df)
    power = power_lower + power_upper
    return float(max(0.0, min(1.0, power)))


def sample_size_one_variance(
    sigma: float,
    sigma0: float,
    power: float = 0.8,
    alpha: float = 0.05,
) -> int:
    """Compute required sample size for 1-variance test."""
    if sigma <= 0 or sigma0 <= 0 or sigma == sigma0:
        return 0

    ratio = (sigma / sigma0) ** 2

    df_est = max(3, int(2 * (_z(1 - alpha / 2) + _z(power)) ** 2 / (1 - 1 / ratio) ** 2))
    df_est = max(df_est, 3)

    for df in range(max(2, df_est - 10), df_est + 50):
        n = df + 1
        pwr = power_one_variance(n, sigma, sigma0, alpha)
        if pwr >= power:
            return n

    lo, hi = 3, df_est + 100
    while lo < hi:
        mid = (lo + hi) // 2
        if power_one_variance(mid, sigma, sigma0, alpha) >= power:
            hi = mid
        else:
            lo = mid + 1
    return lo


def power_one_way_anova(
    n_groups: int,
    n_per_group: int,
    f_squared: float,
    alpha: float = 0.05,
) -> float:
    """Compute power for one-way ANOVA F-test.

    Parameters
    ----------
    n_groups : int
        Number of groups (k).
    n_per_group : int
        Sample size per group.
    f_squared : float
        Effect size f² = σ²_between / σ²_within (Cohen's f²).
    alpha : float
        Significance level.

    Returns
    -------
    float : Power.
    """
    if n_groups < 2 or n_per_group < 2 or f_squared <= 0:
        return 0.0

    k = n_groups
    n = n_per_group
    N = k * n
    df1 = k - 1
    df2 = N - k

    lam = n * k * f_squared

    f_crit = stats.f.ppf(1 - alpha, df1, df2)

    power = 1 - stats.ncf.cdf(f_crit, df1, df2, lam)
    return float(max(0.0, min(1.0, power)))


def power_one_way_anova_delta(
    n_groups: int,
    n_per_group: int,
    delta: float,
    sigma: float,
    alpha: float = 0.05,
) -> float:
    """Compute power using mean difference δ and σ (converts to f²).

    Assumes equal group means equally spaced, so f² = δ² / (2 * σ²).
    """
    f_squared = (delta ** 2) / (2 * sigma ** 2) if sigma > 0 else 0
    return power_one_way_anova(n_groups, n_per_group, f_squared, alpha)


def sample_size_one_way_anova(
    n_groups: int,
    f_squared: float,
    power: float = 0.8,
    alpha: float = 0.05,
) -> int:
    """Compute required sample size per group for one-way ANOVA.

    Returns n_per_group.
    """
    if n_groups < 2 or f_squared <= 0:
        return 0

    k = n_groups
    z_alpha = _z(1 - alpha / 2)
    z_beta = _z(power)
    lam_est = (z_alpha + z_beta) ** 2 / f_squared
    n_est = max(2, math.ceil(lam_est / k + (k - 1) / 2))

    for n in range(max(2, n_est - 10), n_est + 50):
        pwr = power_one_way_anova(k, n, f_squared, alpha)
        if pwr >= power:
            return n

    lo, hi = 2, n_est + 100
    while lo < hi:
        mid = (lo + hi) // 2
        if power_one_way_anova(k, mid, f_squared, alpha) >= power:
            hi = mid
        else:
            lo = mid + 1
    return lo


def oc_curve(
    test_type: str,
    n_range: Tuple[int, int] = (5, 100),
    steps: int = 20,
    **kwargs,
) -> Dict[str, Any]:
    """Generate OC curve data (Power vs Sample Size).

    Parameters
    ----------
    test_type : str
        "1_sample_t", "2_sample_t", "1_proportion", "2_proportions",
        "1_variance", "1_way_anova"
    n_range : tuple
        (min_n, max_n) range.
    steps : int
        Number of points.
    **kwargs
        Additional parameters for the power function.

    Returns
    -------
    dict with "n_values" and "power_values" lists.
    """
    n_min, n_max = n_range
    n_values = [int(n) for n in np.linspace(n_min, n_max, steps)]
    power_values = []

    for n in n_values:
        try:
            if test_type == "1_sample_t":
                pwr = power_one_sample_t(n, kwargs.get("delta", 1.0), kwargs.get("sigma", 1.0), kwargs.get("alpha", 0.05))
            elif test_type == "2_sample_t":
                pwr = power_two_sample_t(n, n, kwargs.get("delta", 0.5), kwargs.get("sigma", 1.0), kwargs.get("alpha", 0.05))
            elif test_type == "paired_t":
                pwr = power_paired_t(n, kwargs.get("delta", 1.0), kwargs.get("sigma_d", 1.0), kwargs.get("alpha", 0.05))
            elif test_type == "1_proportion":
                pwr = power_one_proportion(n, kwargs.get("p1", 0.15), kwargs.get("p0", 0.10), kwargs.get("alpha", 0.05))
            elif test_type == "2_proportions":
                pwr = power_two_proportions(n, n, kwargs.get("p1", 0.3), kwargs.get("p2", 0.2), kwargs.get("alpha", 0.05))
            elif test_type == "1_variance":
                pwr = power_one_variance(n, kwargs.get("sigma", 1.5), kwargs.get("sigma0", 1.0), kwargs.get("alpha", 0.05))
            elif test_type == "1_way_anova":
                k = kwargs.get("n_groups", 3)
                pwr = power_one_way_anova(k, n, kwargs.get("f_squared", 0.25), kwargs.get("alpha", 0.05))
            else:
                pwr = 0.0
        except Exception:
            pwr = 0.0
        power_values.append(round(pwr, 4))

    return {"n_values": n_values, "power_values": power_values}


def cohens_d(delta: float, sigma: float) -> float:
    """Cohen's d effect size for means."""
    return abs(delta) / sigma if sigma > 0 else 0.0


def f_squared_from_eta2(eta2: float) -> float:
    """Convert η² to f²."""
    if eta2 <= 0 or eta2 >= 1:
        return 0.0
    return eta2 / (1 - eta2)


def eta2_from_f_squared(f2: float) -> float:
    """Convert f² to η²."""
    if f2 <= 0:
        return 0.0
    return f2 / (1 + f2)


POWER_FUNCTIONS = {
    "1_sample_t": power_one_sample_t,
    "2_sample_t": power_two_sample_t,
    "paired_t": power_paired_t,
    "1_proportion": power_one_proportion,
    "2_proportions": power_two_proportions,
    "1_variance": power_one_variance,
    "1_way_anova": power_one_way_anova,
}

SAMPLE_SIZE_FUNCTIONS = {
    "1_sample_t": sample_size_one_sample_t,
    "2_sample_t": sample_size_two_sample_t,
    "paired_t": sample_size_paired_t,
    "1_proportion": sample_size_one_proportion,
    "2_proportions": sample_size_two_proportions,
    "1_variance": sample_size_one_variance,
    "1_way_anova": sample_size_one_way_anova,
}

TEST_TYPE_LABELS = {
    "1_sample_t": "单样本 t 检验",
    "2_sample_t": "双样本 t 检验",
    "paired_t": "配对 t 检验",
    "1_proportion": "单比例检验",
    "2_proportions": "双比例检验",
    "1_variance": "单方差检验",
    "1_way_anova": "单因素 ANOVA",
}


def compute_power(test_type: str, n: int, **kwargs) -> float:
    """Generic power computation.

    Parameters
    ----------
    test_type : str
        One of POWER_FUNCTIONS keys.
    n : int
        Sample size (or n1 for 2-sample tests).
    **kwargs
        Test-specific parameters.
    """
    if test_type not in POWER_FUNCTIONS:
        raise ValueError(f"Unknown test type: {test_type}. Available: {list(POWER_FUNCTIONS.keys())}")
    return POWER_FUNCTIONS[test_type](n, **kwargs)


def compute_sample_size(test_type: str, power: float = 0.8, alpha: float = 0.05, **kwargs) -> int:
    """Generic sample size computation.

    Parameters
    ----------
    test_type : str
        One of SAMPLE_SIZE_FUNCTIONS keys.
    power : float
        Desired power.
    alpha : float
        Significance level.
    **kwargs
        Test-specific parameters.
    """
    if test_type not in SAMPLE_SIZE_FUNCTIONS:
        raise ValueError(f"Unknown test type: {test_type}. Available: {list(SAMPLE_SIZE_FUNCTIONS.keys())}")
    return SAMPLE_SIZE_FUNCTIONS[test_type](power=power, alpha=alpha, **kwargs)
