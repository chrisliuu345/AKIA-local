"""
因子设计 — 全因子/2^k因子设计
"""

from typing import Dict, Any, List
import numpy as np
import pandas as pd
from scipy import stats


def generate_design(factors: List[str], replicates: int = 1) -> pd.DataFrame:
    k = len(factors)
    n_runs = 2 ** k * replicates

    # Vectorized factorial design generation
    idx = np.arange(2 ** k)
    design_matrix = 2 * ((idx[:, np.newaxis] >> np.arange(k)[::-1]) & 1).astype(int) - 1
    if replicates > 1:
        design_matrix = np.tile(design_matrix, (replicates, 1))

    design = {factors[i]: design_matrix[:, i].tolist() for i in range(k)}
    design["RunOrder"] = range(1, n_runs + 1)
    design["StdOrder"] = list(range(1, 2 ** k + 1)) * replicates

    return pd.DataFrame(design)


def analyze_factorial(
    df: pd.DataFrame,
    response_col: str,
    factor_cols: List[str],
) -> Dict[str, Any]:
    data = df
    data = data.dropna(subset=[response_col] + factor_cols)
    response = data[response_col].astype(float).values

    # Build design matrix from factor columns
    design = data[factor_cols].astype(float).values

    # Vectorized effects computation (W35 fix: 支持非±1编码，按>0/<0分组)
    design_f = design
    high_mask = design_f > 0
    low_mask = design_f < 0
    n_high = high_mask.sum(axis=0)
    n_low = low_mask.sum(axis=0)
    sum_high = (response[:, np.newaxis] * high_mask).sum(axis=0)
    sum_low = (response[:, np.newaxis] * low_mask).sum(axis=0)
    valid = (n_high > 0) & (n_low > 0)
    effects_arr = np.where(valid, sum_high / n_high - sum_low / n_low, 0.0)

    effects = {factor: round(float(effects_arr[i]), 6) for i, factor in enumerate(factor_cols)}

    grand_mean = float(np.mean(response))

    ss_total = float(np.sum((response - grand_mean) ** 2))
    df_total = len(response) - 1

    # Vectorized SS computation (W35 fix: 支持非±1编码)
    ss_arr = np.where(valid, n_high * (effects_arr / 2) ** 2 + n_low * (-effects_arr / 2) ** 2, 0.0)
    ss_factors = {factor: round(float(ss_arr[i]), 4) for i, factor in enumerate(factor_cols)}
    df_factors = {factor: 1 for factor in factor_cols}
    ss_model = float(np.sum(ss_arr))
    df_model = int(valid.sum())

    ss_error = ss_total - ss_model
    df_error = df_total - df_model
    ms_e = ss_error / df_error if df_error > 0 else 0

    # Vectorized MS, F, p-value computation
    ms_arr = ss_arr  # df=1 for each factor, so ms = ss
    f_arr = np.where(ms_e > 0, ms_arr / ms_e, 0.0)
    p_arr = 1 - stats.f.cdf(f_arr, 1, df_error)

    ms_factors = {factor: round(float(ms_arr[i]), 4) for i, factor in enumerate(factor_cols)}
    f_factors = {factor: round(float(f_arr[i]), 4) for i, factor in enumerate(factor_cols)}
    p_factors = {factor: round(float(p_arr[i]), 6) for i, factor in enumerate(factor_cols)}

    significant = [f for f in factor_cols if p_factors[f] < 0.05]

    pareto_data = []
    for factor in factor_cols:
        pareto_data.append({
            "factor": factor,
            "effect": abs(effects[factor]),
            "t_value": round(float(np.sqrt(f_factors[factor])), 4) if f_factors[factor] is not None else 0,
        })
    pareto_data.sort(key=lambda x: x["effect"], reverse=True)

    return {
        "chart_type": "Factorial DOE Analysis",
        "factors": factor_cols,
        "response": response_col,
        "observations": len(data),
        "grand_mean": round(grand_mean, 6),
        "effects": effects,
        "anova": {
            "source": factor_cols + ["Error", "Total"],
            "ss": [
                ss_factors.get(f, 0) for f in factor_cols
            ] + [round(float(ss_error), 4), round(float(ss_total), 4)],
            "df": [1] * len(factor_cols) + [int(df_error), int(df_total)],
            "ms": [
                ms_factors.get(f, 0) for f in factor_cols
            ] + [round(float(ms_e), 4), 0],
            "f": [
                f_factors.get(f, 0) for f in factor_cols
            ] + [None, None],
            "p_value": [
                p_factors.get(f, 0) for f in factor_cols
            ] + [None, None],
        },
        "significant_factors": significant,
        "pareto_data": pareto_data,
        "model_r_squared": round(float(1 - ss_error / ss_total if ss_total > 0 else 0), 4),
    }
