"""
DOE分析引擎 — 效应Pareto、交互作用、残差诊断
"""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from scipy import stats


def analyze(
    df: pd.DataFrame,
    response_col: str,
    factor_cols: List[str],
) -> Dict[str, Any]:
    data = df.copy()
    data = data.dropna(subset=[response_col] + factor_cols)

    response = data[response_col].astype(float).values
    design = data[factor_cols].astype(float).values

    n, k = len(data), len(factor_cols)
    grand_mean = float(np.mean(response))

    main_effects = {}
    interaction_effects = {}
    pareto_items = []

    for i, f1 in enumerate(factor_cols):
        high = response[design[:, i] > 0]
        low = response[design[:, i] < 0]
        if len(high) > 0 and len(low) > 0:
            effect = float(np.mean(high) - np.mean(low))
            main_effects[f1] = round(effect, 6)
            pareto_items.append({"term": f1, "effect": abs(effect), "type": "main"})

    for i in range(k):
        for j in range(i + 1, k):
            label = f"{factor_cols[i]}*{factor_cols[j]}"
            interaction = design[:, i] * design[:, j]
            high = response[interaction > 0]
            low = response[interaction < 0]
            if len(high) > 0 and len(low) > 0:
                effect = float(np.mean(high) - np.mean(low))
                interaction_effects[label] = round(effect, 6)
                pareto_items.append({"term": label, "effect": abs(effect), "type": "interaction"})

    pareto_items.sort(key=lambda x: x["effect"], reverse=True)

    residuals = _compute_residuals(response, design, main_effects, interaction_effects, factor_cols)
    resid_std = float(np.std(residuals, ddof=1))
    y_pred = response - residuals
    r_squared = 1 - np.sum(residuals ** 2) / np.sum((response - grand_mean) ** 2) if np.sum((response - grand_mean) ** 2) > 0 else 0

    sw_stat, sw_p = stats.shapiro(residuals) if len(residuals) <= 5000 else (0, 0)

    return {
        "chart_type": "DOE Analysis",
        "factors": factor_cols,
        "observations": n,
        "grand_mean": round(grand_mean, 6),
        "main_effects": main_effects,
        "interaction_effects": interaction_effects,
        "pareto": pareto_items,
        "r_squared": round(float(r_squared), 4),
        "residual_std": round(resid_std, 6),
        "residual_normality_p": round(float(sw_p), 6),
        "residuals_normal": sw_p > 0.05,
        "residuals": residuals.tolist(),
        "predicted": y_pred.tolist(),
    }


def _compute_residuals(
    response: np.ndarray,
    design: np.ndarray,
    main_effects: Dict[str, float],
    interaction_effects: Dict[str, float],
    factor_cols: List[str],
) -> np.ndarray:
    k = len(factor_cols)
    y_pred = np.full(len(response), np.mean(response))

    for i, f in enumerate(factor_cols):
        y_pred += (main_effects.get(f, 0) / 2) * design[:, i]

    idx = 0
    for i in range(k):
        for j in range(i + 1, k):
            label = f"{factor_cols[i]}*{factor_cols[j]}"
            y_pred += (interaction_effects.get(label, 0) / 2) * (design[:, i] * design[:, j])
            idx += 1

    return response - y_pred
