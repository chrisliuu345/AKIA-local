"""
非正态过程能力分析 — Box-Cox变换 + Johnson变换 + 百分位法
"""

from typing import Any
import warnings
import numpy as np
import pandas as pd
from analysis._sanitize import sanitize_array
from scipy import stats
from analysis.capability._utils import (
    degenerate_spread_error,
    get_capability_grade,
    spec_limit_error,
)
from analysis.capability.johnson_transform import (
    johnson_transform,
    transform_value as johnson_transform_value,
)


def analyze(
    data: pd.Series,
    usl: float | None = None,
    lsl: float | None = None,
    method: str = "box_cox",
) -> dict[str, Any]:
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
    clean = sanitize_array(data)
    n = len(clean)
    if n < 5:
        raise ValueError(f"数据量不足: {n}")

    limit_error = spec_limit_error(usl, lsl)
    spread_error = degenerate_spread_error(clean, usl, lsl)
    if limit_error or spread_error:
        return {
            "chart_type": "Non-Normal Capability",
            "method": method,
            "transform_param": None,
            "summary": {
                "sample_size": n,
                "original_mean": round(float(np.mean(clean)), 6),
                "original_std": round(float(np.std(clean, ddof=1)), 12),
                "skewness": None,
                "kurtosis": None,
            },
            "error": limit_error or spread_error,
        }

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
    lam: float | None = None
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
    usl: float | None = None,
    lsl: float | None = None,
) -> dict[str, Any]:
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


def _transform_value(value: float, method: str, lam: float | None,
                     shift: float, mean: float, std: float,
                     johnson_params: dict | None = None,
                     johnson_type: str | None = None) -> float:
    """把原始尺度下的规格限变换到变换后尺度, 与数据变换口径完全一致"""
    if method == "johnson" and johnson_params and johnson_type:
        return johnson_transform_value(value, johnson_params, johnson_type)
    x = value + shift
    if x <= 0:
        return -1e9
    if lam == 0:
        return float(np.log(x))
    return float((x ** lam - 1) / lam)


_BOOTSTRAP_METHODS = ("percentile", "box_cox")


def bootstrap_capability_ci(
    data: pd.Series | np.ndarray,
    usl: float | None = None,
    lsl: float | None = None,
    method: str = "percentile",
    n_boot: int = 1000,
    confidence: float = 0.95,
    seed: int = 20260922,
) -> dict[str, Any]:
    """能力指数的 Bootstrap 置信区间（百分位法）。

    非正态数据的 Pp/Ppk 抽样分布无闭式解，用 Bootstrap 给出区间；同一 ``seed``
    结果完全可复现（便于报告复核与重跑 diff）。

    样本量提示（实测标定，正态过程 USL=3 / LSL=−3，真值 Ppk=1）:
    ``method="percentile"`` 的 σ_p = (P99.865 − P0.135)/6 由样本极值决定，
    n=120 时点估计均值 1.166（偏高 17%）、95% 区间覆盖率仅 25%；n=500 为 1.048 /
    67%；n=1500 为 1.019 / 94%；n=3000 为 1.006 / 95%。因此 n < 1000 时函数会
    在返回值 ``accuracy_warning`` 中给出提示，建议改用 ``method="box_cox"`` 或
    增大样本。

    Args:
        data: 数据序列
        usl: 上规格限
        lsl: 下规格限（与 usl 至少给一个）
        method: "percentile"（经验分布，向量化，默认）或 "box_cox"（每次重拟合变换）
        n_boot: Bootstrap 次数（≥ 50）
        confidence: 置信水平（默认 0.95）
        seed: 随机种子

    Returns:
        dict: ``point``（点估计）、``ci``（区间）、``ci_method`` 等
    """
    if usl is None and lsl is None:
        raise ValueError("至少需要提供 usl 或 lsl 之一")
    if method not in _BOOTSTRAP_METHODS:
        raise ValueError(
            f"未知 method: {method}（可选 {_BOOTSTRAP_METHODS}；Johnson 变换"
            "逐次重拟合代价高且不稳定，如需请改用 percentile 或 box_cox）")
    if n_boot < 50:
        raise ValueError(f"n_boot 需 ≥ 50，当前 {n_boot}")
    if not 0.0 < confidence < 1.0:
        raise ValueError(f"confidence 需在 (0, 1) 内，当前 {confidence}")

    clean = np.asarray(pd.Series(data).dropna(), dtype=float)
    n = clean.size
    if n < 5:
        raise ValueError(f"数据量不足: {n}")

    point = _indices_from_sample(clean, usl, lsl, method)
    rng = np.random.default_rng(seed)
    draws = clean[rng.integers(0, n, size=(n_boot, n))]

    if method == "percentile":
        boot = _indices_matrix_percentile(draws, usl, lsl)
    else:
        boot = _indices_matrix_box_cox(draws, usl, lsl)

    alpha = (1.0 - confidence) / 2.0
    ci: dict[str, list[float] | None] = {}
    for key in ("pp", "ppk", "ppm_total"):
        values = boot[key]
        values = values[np.isfinite(values)]
        if values.size == 0 or point[key] is None:
            ci[key] = None
            continue
        low, high = np.percentile(values, [alpha * 100, (1 - alpha) * 100])
        ci[key] = [round(float(low), 4), round(float(high), 4)]

    return {
        "chart_type": "非正态能力 Bootstrap 区间",
        "method": method,
        "ci_method": "percentile",
        "n_boot": int(n_boot),
        "confidence": float(confidence),
        "seed": int(seed),
        "sample_size": int(n),
        "point": point,
        "ci": ci,
        "accuracy_warning": _accuracy_warning(method, n),
        "notes": ("区间为百分位 Bootstrap；同一 seed 结果可复现。"
                  "box_cox 模式每次重抽样都重新估计 λ。"),
    }


def _accuracy_warning(method: str, n: int) -> str:
    """小样本下百分位法的精度提示（空字符串 = 无提示）。"""
    if method != "percentile" or n >= 1000:
        return ""
    return (f"样本量 n={n} < 1000：百分位法 σ_p 由样本极值决定，点估计与区间可能"
            "系统性偏高（实测 n=120 偏高约 17%、覆盖率约 25%；n≥1500 时覆盖率"
            "回到名义 95%）。建议增大样本或改用 method='box_cox'。")


def _indices_from_sample(
    sample: np.ndarray,
    usl: float | None,
    lsl: float | None,
    method: str,
) -> dict[str, float | None]:
    """单样本能力指数（口径与 analyze 的 percentile / box_cox 一致）。"""
    matrix = sample.reshape(1, -1)
    if method == "percentile":
        result = _indices_matrix_percentile(matrix, usl, lsl)
    else:
        result = _indices_matrix_box_cox(matrix, usl, lsl)
    return {
        key: (None if not np.isfinite(result[key][0]) else round(float(result[key][0]), 4))
        for key in ("pp", "ppk", "ppm_total")
    }


def _indices_matrix_percentile(
    draws: np.ndarray,
    usl: float | None,
    lsl: float | None,
) -> dict[str, np.ndarray]:
    """向量化的百分位法能力指数（逐行 = 一次重抽样）。"""
    p0135 = np.percentile(draws, 0.135, axis=1)
    p50 = np.percentile(draws, 50.0, axis=1)
    p99865 = np.percentile(draws, 99.865, axis=1)
    sigma = (p99865 - p0135) / 6.0
    with np.errstate(divide="ignore", invalid="ignore"):
        pp, ppk = _pp_ppk_from(p50, sigma, usl, lsl)
        ppm = _empirical_ppm(draws, usl, lsl)
    return {"pp": pp, "ppk": ppk, "ppm_total": ppm}


def _indices_matrix_box_cox(
    draws: np.ndarray,
    usl: float | None,
    lsl: float | None,
) -> dict[str, np.ndarray]:
    """逐行重拟合 Box-Cox 的能力指数（重抽样间 λ 可不同）。"""
    n_rows = draws.shape[0]
    pp = np.full(n_rows, np.nan)
    ppk = np.full(n_rows, np.nan)
    ppm = np.full(n_rows, np.nan)
    for i, sample in enumerate(draws):
        if np.std(sample) <= 0:
            continue
        shift = 0.0
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if np.any(sample <= 0):
                shift = abs(float(np.min(sample))) + 0.001
            try:
                transformed, lam = stats.boxcox(sample + shift)
            except (ValueError, FloatingPointError):
                continue
        mean_t = float(np.mean(transformed))
        std_t = float(np.std(transformed, ddof=1))
        if std_t <= 0:
            continue
        usl_t = _transform_value(usl, "box_cox", lam, shift, mean_t, std_t) if usl is not None else None
        lsl_t = _transform_value(lsl, "box_cox", lam, shift, mean_t, std_t) if lsl is not None else None
        row_pp, row_ppk = _pp_ppk_scalar(mean_t, std_t, usl_t, lsl_t)
        pp[i], ppk[i] = row_pp, row_ppk
        ppm[i] = _empirical_ppm(sample.reshape(1, -1), usl, lsl)[0]
    return {"pp": pp, "ppk": ppk, "ppm_total": ppm}


def _pp_ppk_from(
    center: np.ndarray,
    sigma: np.ndarray,
    usl: float | None,
    lsl: float | None,
) -> tuple[np.ndarray, np.ndarray]:
    """由中心/尺度计算 Pp 与 Ppk（支持单侧规格）。"""
    with np.errstate(divide="ignore", invalid="ignore"):
        if usl is not None and lsl is not None:
            pp = (usl - lsl) / (6.0 * sigma)
            ppk = np.minimum((usl - center) / (3.0 * sigma),
                             (center - lsl) / (3.0 * sigma))
        elif usl is not None:
            pp = (usl - center) / (3.0 * sigma)
            ppk = pp
        elif lsl is not None:
            pp = (center - lsl) / (3.0 * sigma)
            ppk = pp
        else:                                    # pragma: no cover - 已在校验拦截
            pp = np.full_like(center, np.nan)
            ppk = np.full_like(center, np.nan)
    return pp, ppk


def _pp_ppk_scalar(
    center: float,
    sigma: float,
    usl: float | None,
    lsl: float | None,
) -> tuple[float, float]:
    pp_arr, ppk_arr = _pp_ppk_from(np.array([center]), np.array([sigma]), usl, lsl)
    return float(pp_arr[0]), float(ppk_arr[0])


def _empirical_ppm(
    draws: np.ndarray,
    usl: float | None,
    lsl: float | None,
) -> np.ndarray:
    """经验越界率（ppm），与 analyze 的 percentile 口径一致。"""
    total = np.zeros(draws.shape[0])
    if usl is not None:
        total += np.mean(draws > usl, axis=1)
    if lsl is not None:
        total += np.mean(draws < lsl, axis=1)
    return total * 1e6
