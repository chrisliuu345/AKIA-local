"""
组间/组内过程能力分析
"""

from typing import Any
import numpy as np
import pandas as pd
from analysis.capability._utils import get_capability_grade


def analyze(
    data: pd.DataFrame,
    measurement_col: str,
    subgroup_col: str,
    usl: float | None = None,
    lsl: float | None = None,
) -> dict[str, Any]:
    df = data.dropna(subset=[measurement_col, subgroup_col]).copy()
    df[measurement_col] = pd.to_numeric(df[measurement_col], errors="coerce")
    df[measurement_col] = df[measurement_col].replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=[measurement_col])

    if df.empty:
        raise ValueError("无有效数据")

    groups = df.groupby(subgroup_col)[measurement_col]
    subgroup_means = groups.mean()
    subgroup_counts = groups.count()
    valid_subgroups = subgroup_counts[subgroup_counts >= 2]
    if len(valid_subgroups) < 2:
        raise ValueError(f"有效子组不足（需要至少2个n≥2的子组，当前{len(valid_subgroups)}个）")
    subgroup_stds = groups.std(ddof=1).loc[valid_subgroups.index]
    subgroup_means = subgroup_means.loc[valid_subgroups.index]

    overall_mean = float(df[measurement_col].mean())
    overall_std = float(df[measurement_col].std(ddof=1))

    within_std = np.sqrt(np.mean(subgroup_stds ** 2))
    between_std = _estimate_between_sigma(subgroup_means, within_std, groups.count())

    total_std = float(np.sqrt(within_std ** 2 + between_std ** 2))

    result = {
        "chart_type": "Between/Within Capability",
        "summary": {
            "sample_size": len(df),
            "num_subgroups": len(subgroup_means),
            "overall_mean": round(overall_mean, 6),
            "overall_std": round(overall_std, 6),
            "within_std": round(float(within_std), 6),
            "between_std": round(float(between_std), 6),
            "total_std": round(total_std, 6),
        },
    }

    if usl is not None and lsl is not None:
        cp = (float(usl) - float(lsl)) / (6 * total_std) if total_std > 0 else float("inf")
        cpk = min(
            (float(usl) - overall_mean) / (3 * total_std),
            (overall_mean - float(lsl)) / (3 * total_std),
        ) if total_std > 0 else 0

        result["capability"] = {
            "usl": float(usl),
            "lsl": float(lsl),
            "cp": round(float(cp), 4),
            "cpk": round(float(cpk), 4),
            "grade": get_capability_grade(cpk),
        }

    return result


def _estimate_between_sigma(means: pd.Series, within_std: float, counts: pd.Series) -> float:
    n = len(means)
    if n < 2:
        return 0.0

    mean_of_means = float(means.mean())
    ss_between = np.sum(counts.values * (means.values - mean_of_means) ** 2)
    grand_n = counts.sum()
    k = len(counts)

    ms_between = ss_between / (k - 1)
    variance_between = max((ms_between - within_std ** 2) / (grand_n / k), 0)

    return float(np.sqrt(variance_between))

