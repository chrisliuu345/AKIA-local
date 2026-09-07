"""
Taguchi Design — orthogonal arrays + S/N ratios + robust parameter design

References:
    Taguchi G, Konishi S (1987). Orthogonal Arrays and Linear Graphs.
    Montgomery D C (2017). Design and Analysis of Experiments, 9th ed.
    NIST Engineering Statistics Handbook, Section 5.5.6.

Supports: L4, L8, L9, L12, L16, L18, L27, L36 arrays
S/N ratios: larger-is-better, smaller-is-better, nominal-is-best (I/II)
"""
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from scipy import stats


_ARRAYS: Dict[str, dict] = {}


def _init_arrays():
    """Initialize all standard Taguchi orthogonal arrays."""
    _ARRAYS["L4"] = {"n": 4, "cols": 3, "levels": [2, 2, 2], "design": [
        [1,1,1],[1,2,2],[2,1,2],[2,2,1]]}

    _ARRAYS["L8"] = {"n": 8, "cols": 7, "levels": [2]*7, "design": [
        [1,1,1,1,1,1,1],[1,1,1,2,2,2,2],[1,2,2,1,1,2,2],
        [1,2,2,2,2,1,1],[2,1,2,1,2,1,2],[2,1,2,2,1,2,1],
        [2,2,1,1,2,2,1],[2,2,1,2,1,1,2]]}

    _ARRAYS["L9"] = {"n": 9, "cols": 4, "levels": [3, 3, 3, 3], "design": [
        [1,1,1,1],[1,2,2,2],[1,3,3,3],
        [2,1,2,3],[2,2,3,1],[2,3,1,2],
        [3,1,3,2],[3,2,1,3],[3,3,2,1]]}

    _ARRAYS["L12"] = {"n": 12, "cols": 11, "levels": [2]*11, "design": [
        [1,1,2,1,1,1,2,2,2,1,2],
        [2,1,1,2,1,1,1,2,2,2,1],
        [1,2,1,1,2,1,1,1,2,2,2],
        [2,1,2,1,1,2,1,1,1,2,2],
        [2,2,1,2,1,1,2,1,1,1,2],
        [2,2,2,1,2,1,1,2,1,1,1],
        [1,2,2,2,1,2,1,1,2,1,1],
        [1,1,2,2,2,1,2,1,1,2,1],
        [1,1,1,2,2,2,1,2,1,1,2],
        [2,1,1,1,2,2,2,1,2,1,1],
        [1,2,1,1,1,2,2,2,1,2,1],
        [2,2,2,2,2,2,2,2,2,2,2]]}

    _ARRAYS["L16"] = {"n": 16, "cols": 15, "levels": [2]*15, "design": [
        [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
        [1,1,1,1,1,1,1,2,2,2,2,2,2,2,2],
        [1,1,1,2,2,2,2,1,1,1,1,2,2,2,2],
        [1,1,1,2,2,2,2,2,2,2,2,1,1,1,1],
        [1,2,2,1,1,2,2,1,1,2,2,1,1,2,2],
        [1,2,2,1,1,2,2,2,2,1,1,2,2,1,1],
        [1,2,2,2,2,1,1,1,1,2,2,2,2,1,1],
        [1,2,2,2,2,1,1,2,2,1,1,1,1,2,2],
        [2,1,2,1,2,1,2,1,2,1,2,1,2,1,2],
        [2,1,2,1,2,1,2,2,1,2,1,2,1,2,1],
        [2,1,2,2,1,2,1,1,2,1,2,2,1,2,1],
        [2,1,2,2,1,2,1,2,1,2,1,1,2,1,2],
        [2,2,1,1,2,2,1,1,2,2,1,1,2,2,1],
        [2,2,1,1,2,2,1,2,1,1,2,2,1,1,2],
        [2,2,1,2,1,1,2,1,2,2,1,2,1,1,2],
        [2,2,1,2,1,1,2,2,1,1,2,1,2,2,1]]}

    _ARRAYS["L18"] = {"n": 18, "cols": 8, "levels": [2, 3, 3, 3, 3, 3, 3, 3], "design": [
        [1,1,1,1,1,1,1,1],
        [1,1,2,2,2,2,2,2],
        [1,1,3,3,3,3,3,3],
        [1,2,1,1,2,2,3,3],
        [1,2,2,2,3,3,1,1],
        [1,2,3,3,1,1,2,2],
        [1,3,1,2,1,3,2,3],
        [1,3,2,3,2,1,3,1],
        [1,3,3,1,3,2,1,2],
        [2,1,1,3,3,2,2,1],
        [2,1,2,1,1,3,3,2],
        [2,1,3,2,2,1,1,3],
        [2,2,1,2,3,1,3,2],
        [2,2,2,3,1,2,1,3],
        [2,2,3,1,2,3,2,1],
        [2,3,1,3,2,3,1,2],
        [2,3,2,1,3,1,2,3],
        [2,3,3,2,1,2,3,1]]}


    _ARRAYS["L36"] = {"n": 36, "cols": 23, "levels": [2]*11 + [3]*12,
        "design": None}

_init_arrays()


def _select_array(num_factors: int, factor_levels: List[int]) -> str:
    """Select smallest suitable orthogonal array."""
    all_2 = all(l == 2 for l in factor_levels)
    all_3 = all(l == 3 for l in factor_levels)

    if all_2:
        for name in ["L4", "L8", "L12", "L16"]:
            if _ARRAYS[name]["cols"] >= num_factors:
                return name
        raise ValueError("Too many 2-level factors (max 15)")
    elif all_3:
        if num_factors <= 4:
            return "L9"
        raise ValueError("Too many 3-level factors (max 4 for available arrays)")
    else:
        n2 = sum(1 for l in factor_levels if l == 2)
        n3 = sum(1 for l in factor_levels if l == 3)
        if n2 <= 1 and n3 <= 7:
            return "L18"
        raise ValueError("Cannot accommodate mixed levels: " + str(n2) + "x2 + " + str(n3) + "x3")


def _hadamard_sylvester(n: int) -> np.ndarray:
    """递归构造 n×n Sylvester-Hadamard (±1) 矩阵；n 必须为 2 的幂。"""
    if n == 1:
        return np.array([[1]], dtype=int)
    h = _hadamard_sylvester(n // 2)
    top = np.concatenate([h, h], axis=1)
    bottom = np.concatenate([h, -h], axis=1)
    return np.concatenate([top, bottom], axis=0)


def _build_plackett_burman(n: int) -> np.ndarray:
    """两水平 (±1) 正交阵列：Hadamard 去掉首列(全1) → n×(n-1) 子阵。

    供内噪因子双水平实验使用；n 为 2 的幂（调用方传入
    max(4, 2**ceil(log2(k+1)))），保证 n-1 ≥ 噪声因子数。
    """
    return _hadamard_sylvester(n)[:, 1:]


def generate_design(
    factors: List[str],
    factor_levels: Optional[List[int]] = None,
    array: Optional[str] = None,
    noise_factors: Optional[List[str]] = None,
    noise_levels: Optional[List[int]] = None,
    random_seed: Optional[int] = None,
) -> pd.DataFrame:
    """Generate Taguchi orthogonal array design.

    Parameters
    ----------
    factors : list of str
        Control factor names
    factor_levels : list of int, optional
        Number of levels per factor (default: all 2-level)
    array : str, optional
        Force a specific array (e.g. "L9"). If None, auto-select.
    noise_factors : list of str, optional
        Noise factor names (for inner/outer crossed array)
    noise_levels : list of int, optional
        Noise factor levels
    random_seed : int, optional
        Random seed for run order

    Returns
    -------
    pd.DataFrame with factor columns (level-encoded 1,2,3...) + RunOrder
    """
    k = len(factors)
    if k < 2:
        raise ValueError("At least 2 factors required")

    if factor_levels is None:
        factor_levels = [2] * k
    if len(factor_levels) != k:
        raise ValueError("factor_levels length must equal number of factors")

    if array is None:
        array = _select_array(k, factor_levels)
    if array not in _ARRAYS:
        raise ValueError("Unknown array: " + array + ". Available: " + str(list(_ARRAYS.keys())))

    arr_info = _ARRAYS[array]
    if arr_info["cols"] < k:
        raise ValueError(array + " has " + str(arr_info["cols"]) + " columns, but " + str(k) + " factors given")

    design = np.array(arr_info["design"], dtype=int)[:, :k]
    n_runs = arr_info["n"]

    data = {factors[i]: design[:, i] for i in range(k)}
    df = pd.DataFrame(data)

    rng = np.random.default_rng(random_seed)
    perm = rng.permutation(n_runs) + 1
    df["RunOrder"] = perm
    df["StdOrder"] = range(1, n_runs + 1)
    df["Array"] = array

    if noise_factors and noise_levels:
        n_noise = len(noise_factors)
        n_noise_levels = max(noise_levels) if noise_levels else 2
        if n_noise_levels == 2:
            noise_arr = _build_plackett_burman(max(4, 2 ** int(np.ceil(np.log2(n_noise + 1)))))
            noise_arr = ((noise_arr + 1) // 2 + 1).astype(int)
        else:
            noise_arr = np.array(_ARRAYS["L9"]["design"])[:, :n_noise] if n_noise <= 4 else np.ones((n_noise_levels ** n_noise, n_noise), dtype=int)
        noise_df = pd.DataFrame(noise_arr[:, :n_noise], columns=[nf + "_Noise" for nf in noise_factors])
        expanded = pd.merge(
            df.assign(_key=0),
            noise_df.assign(_key=0),
            on="_key"
        ).drop(columns=["_key"])
        return expanded

    return df


def compute_sn_ratio(values: np.ndarray, sn_type: str = "larger_is_better") -> float:
    """Compute signal-to-noise ratio.

    Parameters
    ----------
    values : array-like
        Response measurements for one run (one or more replicates)
    sn_type : str
        "larger_is_better", "smaller_is_better", "nominal_is_best", "nominal_is_best_ii"

    Returns
    -------
    float : S/N ratio in dB (always maximized)
    """
    v = np.asarray(values, dtype=float)
    v = v[v > 0]

    if len(v) == 0:
        return -np.inf

    n = len(v)

    if sn_type == "larger_is_better":
        msd = np.mean(1.0 / (v ** 2))
        return -10.0 * np.log10(msd)

    elif sn_type == "smaller_is_better":
        msd = np.mean(v ** 2)
        return -10.0 * np.log10(msd)

    elif sn_type == "nominal_is_best":
        y_bar = np.mean(v)
        if n > 1:
            s2 = np.var(v, ddof=1)
        else:
            s2 = 0.0
        if s2 > 1e-15:
            return 10.0 * np.log10((y_bar ** 2) / s2)
        return float("inf") if y_bar != 0 else 0.0

    elif sn_type == "nominal_is_best_ii":
        if n > 1:
            s2 = np.var(v, ddof=1)
        else:
            return 0.0
        if s2 > 1e-15:
            return -10.0 * np.log10(s2)
        return float("inf")

    else:
        raise ValueError("Unknown sn_type: " + sn_type)


def response_table(
    design_df: pd.DataFrame,
    sn_ratios: np.ndarray,
    factor_cols: List[str],
) -> Dict[str, Dict]:
    """Compute response table: level averages, delta, rank for each factor.

    Returns
    -------
    dict : {factor: {"level_averages": {level: avg}, "delta": float,
                     "best_level": int, "rank": int}}
    """
    result = {}
    for factor in factor_cols:
        levels = sorted(design_df[factor].unique())
        level_avgs = {}
        for level in levels:
            mask = design_df[factor].values == level
            level_avgs[int(level)] = round(float(np.mean(sn_ratios[mask])), 6)
        delta = max(level_avgs.values()) - min(level_avgs.values())
        best_level = max(level_avgs, key=level_avgs.get)
        result[factor] = {
            "level_averages": level_avgs,
            "delta": round(delta, 6),
            "best_level": best_level,
        }

    ranked = sorted(result.items(), key=lambda x: x[1]["delta"], reverse=True)
    for rank, (factor, _data) in enumerate(ranked, 1):
        result[factor]["rank"] = rank

    return result


def _anova_on_sn(
    design_df: pd.DataFrame,
    sn_ratios: np.ndarray,
    factor_cols: List[str],
) -> Dict[str, Any]:
    """Perform ANOVA on S/N ratios with optional pooling."""
    N = len(sn_ratios)
    grand_sum = float(np.sum(sn_ratios))
    grand_mean = grand_sum / N
    ss_total = float(np.sum((sn_ratios - grand_mean) ** 2))

    sources = []
    ss_list = []
    df_list = []

    for factor in factor_cols:
        levels = design_df[factor].unique()
        n_level = N // len(levels)
        t_sums = {}
        for level in levels:
            mask = design_df[factor].values == level
            t_sums[int(level)] = float(np.sum(sn_ratios[mask]))
        ss_f = sum(t ** 2 for t in t_sums.values()) / n_level - grand_sum ** 2 / N
        df_f = len(levels) - 1
        sources.append(factor)
        ss_list.append(round(ss_f, 6))
        df_list.append(df_f)

    ss_model = sum(ss_list)
    ss_error = max(ss_total - ss_model, 0.0)
    df_model = sum(df_list)
    df_error = max(N - 1 - df_model, 1)

    contributions = [s / ss_total * 100 if ss_total > 0 else 0.0 for s in ss_list]

    ms_error = ss_error / df_error if df_error > 0 else 1e-10
    f_values = []
    p_values = []
    for _i, (ss, df_f) in enumerate(zip(ss_list, df_list, strict=True)):
        ms_f = ss / df_f if df_f > 0 else 0.0
        f_val = ms_f / ms_error if ms_error > 1e-10 else 0.0
        p_val = 1.0 - stats.f.cdf(max(f_val, 0), df_f, df_error) if df_f > 0 and df_error > 0 else 1.0
        f_values.append(round(f_val, 4))
        p_values.append(round(p_val, 6))

    return {
        "source": sources + ["Error", "Total"],
        "ss": ss_list + [round(ss_error, 6), round(ss_total, 6)],
        "df": df_list + [df_error, N - 1],
        "ms": [round(s / d, 6) if d > 0 else 0.0 for s, d in zip(ss_list, df_list, strict=True)] +
              [round(ms_error, 6), 0.0],
        "f_value": f_values + [None, None],
        "p_value": p_values + [None, None],
        "contribution_pct": [round(c, 2) for c in contributions],
        "ss_total": round(ss_total, 6),
    }


def _optimal_combination(resp_table: Dict) -> Dict[str, Dict]:
    """Select best level for each factor (highest S/N average)."""
    optimal = {}
    for factor, data in resp_table.items():
        optimal[factor] = {
            "best_level": data["best_level"],
            "best_avg_sn": data["level_averages"][data["best_level"]],
            "rank": data["rank"],
        }
    return optimal


def _predicted_sn(resp_table: Dict, grand_mean_sn: float) -> float:
    """Predict S/N at optimal combination using additive model."""
    prediction = grand_mean_sn
    for _factor, data in resp_table.items():
        best_avg = data["level_averages"][data["best_level"]]
        prediction += best_avg - grand_mean_sn
    return round(prediction, 6)


def analyze(
    df: pd.DataFrame,
    response_col: str,
    factor_cols: List[str],
    sn_type: str = "larger_is_better",
) -> Dict[str, Any]:
    """Analyze Taguchi design data.

    Parameters
    ----------
    df : pd.DataFrame
        Design matrix with factor columns and response column
    response_col : str
        Column name for response data
    factor_cols : list of str
        Factor column names
    sn_type : str
        S/N ratio type

    Returns
    -------
    dict with response_table, anova, optimal, predicted_sn, contribution_pct
    """
    data = df[factor_cols + [response_col]].dropna()
    coerced = pd.to_numeric(data[response_col], errors="coerce")
    n_nan = coerced.isna().sum()
    if n_nan > 0:
        bad_vals = data[response_col][coerced.isna()].unique()[:5]
        raise ValueError(
            "列 '" + response_col + "' 包含非数值数据，无法进行DOE分析。"
            "示例: " + str(list(bad_vals)) + "。请确保选择的响应列为数值类型。"
        )
    response = data[response_col].values.astype(float)
    design = data[factor_cols]

    sn_ratios = np.array([compute_sn_ratio(np.array([r]), sn_type) for r in response])
    grand_mean_sn = float(np.mean(sn_ratios))

    resp_tab = response_table(design, sn_ratios, factor_cols)

    anova = _anova_on_sn(design, sn_ratios, factor_cols)

    optimal = _optimal_combination(resp_tab)

    pred_sn = _predicted_sn(resp_tab, grand_mean_sn)

    return {
        "chart_type": "Taguchi Analysis",
        "factors": factor_cols,
        "sn_type": sn_type,
        "observations": len(data),
        "grand_mean_sn": round(grand_mean_sn, 6),
        "response_table": resp_tab,
        "anova": anova,
        "optimal": optimal,
        "predicted_sn": pred_sn,
        "contribution_pct": dict(zip(factor_cols, anova["contribution_pct"], strict=True)),
    }
