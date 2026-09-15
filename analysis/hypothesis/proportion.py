"""
卡方检验与比例检验 — 拟合优度/独立性/2比例检验
"""

from typing import Any
import numpy as np
import pandas as pd
from scipy import stats


def chi_square_gof(
    observed: pd.Series,
    expected: pd.Series | None = None,
    probabilities: list[float] | None = None,
) -> dict[str, Any]:
    """
    卡方拟合优度检验

    Args:
        observed: 观测频数
        expected: 期望频数（可选）
        probabilities: 期望比例（可选，用于均匀分布等情况）

    Returns:
        检验结果字典
    """
    obs = observed.dropna().astype(float).values
    n = len(obs)

    if n < 2:
        raise ValueError(f"类别数不足: {n}，至少需要 2 个类别")

    total = obs.sum()
    if total <= 0:
        raise ValueError("观测频数总和必须大于 0")

    if expected is not None:
        exp = expected.dropna().astype(float).values
        if len(exp) != n:
            raise ValueError("观测和期望频数长度不一致")
    elif probabilities is not None:
        probs = np.array(probabilities)
        if len(probs) != n:
            raise ValueError("概率长度与观测频数不一致")
        if abs(probs.sum() - 1.0) > 0.01:
            raise ValueError("概率之和必须为 1")
        exp = probs * total
    else:
        exp = np.full(n, total / n)

    exp_safe = np.where(exp == 0, 1e-10, exp)
    chi2 = np.sum((obs - exp) ** 2 / exp_safe)
    df = n - 1
    p_value = 1 - stats.chi2.cdf(chi2, df)

    return {
        "test_type": "Chi-Square Goodness of Fit",
        "hypothesis": "H0: 分布与期望一致",
        "categories": n,
        "total_count": round(float(total), 2),
        "chi2_statistic": round(float(chi2), 4),
        "df": df,
        "p_value": round(float(p_value), 6),
        "is_significant": p_value < 0.05,
        "observed": obs.tolist(),
        "expected": exp.tolist(),
        "residuals": ((obs - exp) / np.sqrt(exp_safe)).tolist(),
    }


def chi_square_independence(
    data: pd.DataFrame,
    col1: str,
    col2: str,
) -> dict[str, Any]:
    """
    卡方独立性检验

    Args:
        data: 数据框
        col1: 第一个分类变量列名
        col2: 第二个分类变量列名

    Returns:
        检验结果字典
    """
    df = data[[col1, col2]].dropna()

    if df.empty:
        raise ValueError("无有效数据")

    contingency = pd.crosstab(df[col1], df[col2])
    chi2, p_value, dof, expected = stats.chi2_contingency(contingency)

    n = contingency.sum().sum()
    min_dim = min(contingency.shape) - 1
    cramers_v = np.sqrt(chi2 / (n * min_dim)) if min_dim > 0 and n > 0 else 0

    return {
        "test_type": "Chi-Square Test of Independence",
        "hypothesis": f"H0: {col1} 与 {col2} 独立",
        "contingency_table": contingency.values.tolist(),
        "row_labels": contingency.index.tolist(),
        "col_labels": contingency.columns.tolist(),
        "chi2_statistic": round(float(chi2), 4),
        "df": dof,
        "p_value": round(float(p_value), 6),
        "cramers_v": round(float(cramers_v), 4),
        "is_significant": p_value < 0.05,
        "expected_freq": expected.tolist(),
    }


def two_proportion_test(
    successes1: int,
    n1: int,
    successes2: int,
    n2: int,
    alternative: str = "two-sided",
) -> dict[str, Any]:
    """
    双样本比例检验

    Args:
        successes1: 样本1成功数
        n1: 样本1总数
        successes2: 样本2成功数
        n2: 样本2总数
        alternative: "two-sided", "greater", "less"

    Returns:
        检验结果字典
    """
    if n1 <= 0 or n2 <= 0:
        raise ValueError("样本量必须大于 0")
    if successes1 < 0 or successes2 < 0:
        raise ValueError("成功数不能为负")
    if successes1 > n1 or successes2 > n2:
        raise ValueError("成功数不能超过样本量")

    p1 = successes1 / n1
    p2 = successes2 / n2

    p_pool = (successes1 + successes2) / (n1 + n2)

    se = np.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2))

    if se > 0:
        z_stat = (p1 - p2) / se
    else:
        z_stat = 0.0

    if alternative == "two-sided":
        p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))
    elif alternative == "greater":
        p_value = 1 - stats.norm.cdf(z_stat)
    else:
        p_value = stats.norm.cdf(z_stat)

    se_diff = np.sqrt(p1*(1-p1)/n1 + p2*(1-p2)/n2)
    ci = (p1 - p2 - 1.96 * se_diff, p1 - p2 + 1.96 * se_diff)

    return {
        "test_type": "Two-Proportion Z-Test",
        "hypothesis": "H0: p1 - p2 = 0",
        "alternative": alternative,
        "group1": {
            "successes": successes1,
            "total": n1,
            "proportion": round(float(p1), 6),
        },
        "group2": {
            "successes": successes2,
            "total": n2,
            "proportion": round(float(p2), 6),
        },
        "difference": round(float(p1 - p2), 6),
        "pooled_proportion": round(float(p_pool), 6),
        "z_statistic": round(float(z_stat), 4),
        "p_value": round(float(p_value), 6),
        "ci_95": (round(float(ci[0]), 6), round(float(ci[1]), 6)),
        "is_significant": p_value < 0.05,
    }
