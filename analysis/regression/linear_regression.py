"""
线性回归分析 — 简单线性回归 / 多元回归
"""

from typing import Dict, Any, List
import numpy as np
import pandas as pd
from scipy import stats


def analyze(
    df: pd.DataFrame,
    response_col: str,
    factor_cols: List[str],
) -> Dict[str, Any]:
    data = df.dropna(subset=[response_col] + factor_cols).copy()
    for col in [response_col] + factor_cols:
        coerced = pd.to_numeric(data[col], errors="coerce")
        n_nan = coerced.isna().sum()
        if n_nan > 0:
            bad_vals = data[col][coerced.isna()].unique()[:5]
            raise ValueError(
                "列 '" + col + "' 包含非数值数据，无法进行回归分析。"
                "示例: " + str(list(bad_vals)) + "。请确保选择的响应列和因子列均为数值类型。"
            )
    n = len(data)
    y = data[response_col].astype(float).values
    k = len(factor_cols)
    X = np.column_stack([np.ones(n)] + [data[fc].astype(float).values for fc in factor_cols])

    try:
        coeffs, residuals, rank, sv = np.linalg.lstsq(X, y, rcond=None)
    except np.linalg.LinAlgError:
        coeffs = np.linalg.pinv(X) @ y
        y - X @ coeffs

    y_pred = X @ coeffs
    residuals_arr = y - y_pred
    ss_res = np.sum(residuals_arr ** 2)
    ss_total = np.sum((y - np.mean(y)) ** 2)
    r_squared = 1 - ss_res / ss_total if ss_total > 0 else 0.0
    adj_r_squared = 1 - (1 - r_squared) * (n - 1) / max(n - k - 1, 1)

    dof = max(n - k - 1, 1)
    sigma2 = ss_res / dof
    se = np.sqrt(sigma2 * np.diag(np.linalg.pinv(X.T @ X))) if n > k + 1 else np.full(k + 1, np.nan)

    t_values = [coeffs[i] / se[i] if se[i] > 0 else np.nan for i in range(k + 1)]
    p_values = [2 * stats.t.sf(abs(t), dof) if not np.isnan(t) else np.nan for t in t_values]

    coef_names = ["(Intercept)"] + factor_cols
    coefficient_table = []
    for i, name in enumerate(coef_names):
        coefficient_table.append({
            "term": name,
            "estimate": round(float(coeffs[i]), 6),
            "std_error": round(float(se[i]), 6),
            "t_value": round(float(t_values[i]), 6) if not np.isnan(t_values[i]) else None,
            "p_value": f"{p_values[i]:.6f}" if not np.isnan(p_values[i]) else "N/A",
        })

    ss_reg = ss_total - ss_res
    ms_reg = ss_reg / k if k > 0 else 0
    ms_res = sigma2
    f_stat = ms_reg / ms_res if ms_res > 0 else 0
    f_p_value = 1 - stats.f.cdf(f_stat, k, dof) if dof > 0 and k > 0 else 1.0

    anova_table = {
        "regression_ss": round(float(ss_reg), 4),
        "regression_df": k,
        "regression_ms": round(float(ms_reg), 4),
        "residual_ss": round(float(ss_res), 4),
        "residual_df": dof,
        "residual_ms": round(float(ms_res), 4),
        "f_statistic": round(float(f_stat), 4),
        "f_p_value": f"{f_p_value:.6f}",
    }

    return {
        "chart_type": "Regression",
        "analysis_type": "Regression",
        "response": response_col,
        "factors": factor_cols,
        "n": n,
        "r_squared": round(float(r_squared), 4),
        "r_squared_adjusted": round(float(adj_r_squared), 4),
        "residual_std": round(float(np.sqrt(sigma2)), 6),
        "coefficients": coefficient_table,
        "anova": anova_table,
        "fitted_values": y_pred.tolist(),
        "residuals": residuals_arr.tolist(),
        "actual_values": y.tolist(),
        "summary": {
            "observations": n,
            "parameters": k + 1,
            "response": response_col,
            "factors": factor_cols,
        },
    }
