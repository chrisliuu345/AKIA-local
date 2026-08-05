"""
因子设计 — 全因子/2^k因子设计
"""

from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
from scipy import stats


def generate_design(factors: List[str], replicates: int = 1) -> pd.DataFrame:
    k = len(factors)
    n_runs = 2 ** k * replicates

    levels = []
    for i in range(k):
        col = []
        block_size = 2 ** (k - i - 1)
        for _ in range(2 ** i):
            col.extend([-1] * block_size)
            col.extend([1] * block_size)
        levels.append(col * replicates)

    design = {}
    for i, factor_name in enumerate(factors):
        design[factor_name] = levels[i]
    design["RunOrder"] = range(1, n_runs + 1)
    design["StdOrder"] = list(range(1, 2 ** k + 1)) * replicates

    return pd.DataFrame(design)


def analyze_factorial(
    df: pd.DataFrame,
    response_col: str,
    factor_cols: List[str],
) -> Dict[str, Any]:
    data = df.copy()
    data = data.dropna(subset=[response_col] + factor_cols)
    response = data[response_col].astype(float).values

    effects = {}
    for factor in factor_cols:
        col = data[factor].astype(float).values
        high_mask = col == 1
        low_mask = col == -1
        effect_val = float(np.mean(response[high_mask]) - np.mean(response[low_mask]))
        effects[factor] = round(effect_val, 6)

    grand_mean = float(np.mean(response))

    ss_total = float(np.sum((response - grand_mean) ** 2))
    df_total = len(response) - 1

    ss_factors = {}
    df_factors = {}
    ms_factors = {}
    f_factors = {}
    p_factors = {}

    ss_model = 0
    df_model = 0

    for factor in factor_cols:
        col = data[factor].astype(float).values
        high_mask = col == 1
        low_mask = col == -1
        effect_val = effects[factor]
        ss_f = int(np.sum(high_mask)) * (effect_val / 2) ** 2 + int(np.sum(low_mask)) * (-effect_val / 2) ** 2
        ss_factors[factor] = round(float(ss_f), 4)
        df_factors[factor] = 1
        ss_model += ss_f
        df_model += 1

    ss_error = ss_total - ss_model
    df_error = df_total - df_model
    ms_e = ss_error / df_error if df_error > 0 else 0

    for factor in factor_cols:
        ms_f = ss_factors[factor] / df_factors[factor]
        f_val = ms_f / ms_e if ms_e > 0 else 0
        p_val = 1 - stats.f.cdf(f_val, df_factors[factor], df_error)
        ms_factors[factor] = round(float(ms_f), 4)
        f_factors[factor] = round(float(f_val), 4)
        p_factors[factor] = round(float(p_val), 6)

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
