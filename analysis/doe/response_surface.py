"""
响应曲面设计 — CCD (Central Composite Design) / Box-Behnken
"""

from typing import Any
import numpy as np
import pandas as pd


def generate_ccd(factors: list[str], alpha: str = "rotatable", center_points: int = 3) -> pd.DataFrame:
    k = len(factors)
    factorial_runs = 2 ** k

    if alpha == "rotatable":
        a = 2 ** (k / 4)
    elif alpha == "orthogonal":
        a = np.sqrt((np.sqrt(factorial_runs * (factorial_runs + 2 * k + center_points)) - factorial_runs) / 2)
    else:
        a = float(alpha)

    factorial_design = _get_factorial_points(k)
    axial_points = _get_axial_points(k, a)
    center = np.zeros((center_points, k))

    design_matrix = np.vstack([factorial_design, axial_points, center])
    n_runs = len(design_matrix)

    result = {}
    for i, factor_name in enumerate(factors):
        result[factor_name] = design_matrix[:, i]

    result["Block"] = (
        ["Factorial"] * len(factorial_design) +
        ["Axial"] * len(axial_points) +
        ["Center"] * center_points
    )
    result["RunOrder"] = range(1, n_runs + 1)
    return pd.DataFrame(result)


def analyze_response_surface(
    df: pd.DataFrame,
    response_col: str,
    factor_cols: list[str],
) -> dict[str, Any]:
    data = df.dropna(subset=[response_col] + factor_cols)
    for col in [response_col] + factor_cols:
        coerced = pd.to_numeric(data[col], errors="coerce")
        n_nan = coerced.isna().sum()
        if n_nan > 0:
            bad_vals = data[col][coerced.isna()].unique()[:5]
            raise ValueError(
                "列 '" + col + "' 包含非数值数据，无法进行DOE分析。"
                "示例: " + str(list(bad_vals)) + "。请确保选择的响应列和因子列均为数值类型。"
            )

    response = data[response_col].astype(float).values
    k = len(factor_cols)
    design = data[factor_cols].astype(float).values

    n = len(data)

    X_list = [np.ones(n), design]
    for i in range(k):
        X_list.append(design[:, i] ** 2)
    for i in range(k):
        for j in range(i + 1, k):
            X_list.append(design[:, i] * design[:, j])
    X = np.column_stack(X_list)

    try:
        coeffs, residuals, _rank, _sv = np.linalg.lstsq(X, response, rcond=None)
    except np.linalg.LinAlgError:
        coeffs = np.linalg.pinv(X) @ response
        residuals = response - X @ coeffs

    y_pred = X @ coeffs
    ss_res = np.sum((response - y_pred) ** 2)
    ss_total = np.sum((response - np.mean(response)) ** 2)
    r_squared = 1 - ss_res / ss_total if ss_total > 0 else 0

    coef_labels = ["intercept"] + factor_cols
    for i in range(k):
        coef_labels.append(f"{factor_cols[i]}^2")
    for i in range(k):
        for j in range(i + 1, k):
            coef_labels.append(f"{factor_cols[i]}*{factor_cols[j]}")

    coefficients = {}
    for label, coef in zip(coef_labels, coeffs, strict=True):
        coefficients[label] = round(float(coef), 6)

    return {
        "chart_type": "Response Surface Analysis",
        "factors": factor_cols,
        "observations": n,
        "coefficients": coefficients,
        "r_squared": round(float(r_squared), 4),
        "r_squared_adjusted": round(float(1 - (1 - r_squared) * (n - 1) / (n - len(coeffs))), 4),
        "residual_std": round(float(np.std(residuals, ddof=1)), 6),
        "num_parameters": len(coeffs),
    }


def _get_factorial_points(k: int) -> np.ndarray:
    idx = np.arange(2 ** k)
    points = 2 * ((idx[:, np.newaxis] >> np.arange(k)) & 1).astype(int) - 1
    return points


def _get_axial_points(k: int, alpha: float) -> np.ndarray:
    axial = np.zeros((2 * k, k))
    axial[np.arange(k), np.arange(k)] = alpha
    axial[k + np.arange(k), np.arange(k)] = -alpha
    return axial