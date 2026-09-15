"""
属性一致性分析 (Attribute Agreement Analysis)

支持:
- Cohen's Kappa (2 评注者)
- Fleiss's Kappa (多评注者)
- 有效 Kappa (Kappa / Kappa_max)
- 偏差矩阵 (评注者 × 标准)
"""

from typing import Any
import numpy as np
import pandas as pd


def analyze(
    df: pd.DataFrame,
    result_col: str,
    standard_col: str,
    operator_col: str = "",
    part_col: str = "",
    method: str = "auto",
) -> dict[str, Any]:
    """
    属性一致性分析

    Args:
        df: 数据框
        result_col: 评注结果列
        standard_col: 标准（真值）列
        operator_col: 评注者列（可选）
        part_col: 零件列（可选）
        method: 方法选择
            - "auto": 自动选择（2评注者用Cohen，多评注者用Fleiss）
            - "cohen": Cohen's Kappa
            - "fleiss": Fleiss's Kappa

    Returns:
        分析结果字典
    """
    data = df.copy()
    data = data.dropna(subset=[result_col, standard_col])

    n = len(data)
    if n < 10:
        raise ValueError(f"数据量不足: {n}")

    agreement = (data[result_col].astype(str) == data[standard_col].astype(str)).sum()
    agreement_rate = agreement / n

    categories = sorted(set(data[standard_col].astype(str)))
    k = len(categories)

    if operator_col and operator_col in data.columns:
        operators = data[operator_col].unique()
        n_operators = len(operators)
    else:
        operators = []
        n_operators = 0

    if method == "auto":
        if n_operators == 2:
            method = "cohen"
        elif n_operators > 2:
            method = "fleiss"
        else:
            method = "cohen"

    if method == "fleiss" and n_operators >= 3:
        kappa = fleiss_kappa(data, result_col, standard_col, operator_col)
        kappa_max = _kappa_max(data, result_col, standard_col, categories)
    else:
        kappa = _calculate_cohen_kappa(data, result_col, standard_col, categories)
        kappa_max = _kappa_max(data, result_col, standard_col, categories)

    effective_kappa_val = kappa / kappa_max if kappa_max > 0 else 0.0

    op_agreements = {}
    if operator_col and operator_col in data.columns:
        for op in operators:
            op_data = data[data[operator_col] == op]
            op_agree = (op_data[result_col].astype(str) == op_data[standard_col].astype(str)).sum()
            op_agreements[str(op)] = {
                "total": len(op_data),
                "agreement": int(op_agree),
                "rate": round(float(op_agree / len(op_data) * 100), 2),
            }

    bias_mat = _calculate_bias_matrix(data, result_col, standard_col, operator_col, categories, operators)

    return {
        "chart_type": "Attribute Agreement",
        "method": method,
        "total_assessments": n,
        "agreement_count": int(agreement),
        "agreement_rate": round(float(agreement_rate * 100), 2),
        "kappa": round(float(kappa), 4),
        "kappa_interpretation": _kappa_interpretation(kappa),
        "kappa_max": round(float(kappa_max), 4),
        "effective_kappa": round(float(effective_kappa_val), 4),
        "effective_kappa_interpretation": _kappa_interpretation(effective_kappa_val),
        "n_categories": k,
        "n_operators": n_operators,
        "operator_agreements": op_agreements,
        "bias_matrix": bias_mat,
        "is_acceptable": bool(agreement_rate >= 0.9 and kappa >= 0.7),
    }


def fleiss_kappa(
    df: pd.DataFrame,
    result_col: str,
    standard_col: str,
    operator_col: str,
    part_col: str = "",
) -> float:
    """
    Fleiss's Kappa (多评注者)

    参考: Fleiss (1971) "Measuring nominal scale agreement among many raters"
    """
    data = df.copy()
    data[result_col] = data[result_col].astype(str)
    data[standard_col] = data[standard_col].astype(str)

    if part_col and part_col in data.columns:
        subjects = data[part_col].unique()
    else:
        subjects = data[standard_col].unique()

    categories = sorted(set(data[standard_col].astype(str)))
    k = len(categories)
    N = len(subjects)

    if N < 2 or k < 2:
        return 0.0

    n_raters = len(data[operator_col].unique()) if operator_col in data.columns else 0
    if n_raters < 2:
        return 0.0

    matrix = np.zeros((N, k), dtype=int)
    for i, subj in enumerate(subjects):
        if part_col and part_col in data.columns:
            subj_data = data[data[part_col] == subj]
        else:
            subj_data = data[data[standard_col] == subj]

        for j, cat in enumerate(categories):
            matrix[i, j] = (subj_data[result_col] == cat).sum()

    n = n_raters
    P_i = (matrix * (matrix - 1)).sum(axis=1) / (n * (n - 1))
    P_bar = P_i.mean()

    p_j = matrix.sum(axis=0) / (N * n)
    P_e = (p_j ** 2).sum()

    if abs(1 - P_e) < 1e-10:
        if abs(P_bar - 1) < 1e-10:
            return 1.0
        return -1.0

    return (P_bar - P_e) / (1 - P_e)


def _kappa_max(
    df: pd.DataFrame,
    result_col: str,
    standard_col: str,
    categories: list[str],
) -> float:
    """
    计算 Kappa_max (最大可能 Kappa)

    Kappa_max = max(1 - Pe) / (1 - Pe_min)
    限制在 [0, 1] 范围内
    """
    n = len(df)
    if n == 0:
        return 1.0

    pe = 0.0
    for cat in categories:
        p_a = (df[result_col].astype(str) == cat).sum() / n
        p_b = (df[standard_col].astype(str) == cat).sum() / n
        pe += p_a * p_b

    p_j = []
    for cat in categories:
        p_j.append((df[result_col].astype(str) == cat).sum() / n)

    pe_min = 0.0
    for p in p_j:
        pe_min += p * p

    if abs(1 - pe_min) < 1e-10:
        return 1.0

    kappa_max = (1 - pe) / (1 - pe_min)
    return min(max(kappa_max, 0.0), 1.0)


def _calculate_bias_matrix(
    df: pd.DataFrame,
    result_col: str,
    standard_col: str,
    operator_col: str,
    categories: list[str],
    operators: np.ndarray,
) -> dict[str, Any]:
    """
    计算偏差矩阵 (评注者 × 标准)

    返回每个评注者对每个标准类别的判断偏差
    """
    if not operator_col or not operators.any():
        return {"matrix": {}, "summary": {}}

    matrix = {}
    for op in operators:
        op_data = df[df[operator_col] == op]
        op_row = {}
        for cat in categories:
            count = (op_data[result_col] == cat).sum()
            total = len(op_data)
            op_row[cat] = {
                "count": int(count),
                "pct": round(float(count / total * 100), 2) if total > 0 else 0,
            }
        matrix[str(op)] = op_row

    summary = {}
    for cat in categories:
        cat_data = df[df[standard_col] == cat]
        over_count = 0
        under_count = 0
        correct_count = 0
        for op in operators:
            op_cat_data = cat_data[cat_data[operator_col] == op]
            if len(op_cat_data) == 0:
                continue
            result_dist = op_cat_data[result_col].value_counts()
            for r_cat, cnt in result_dist.items():
                cat_idx = categories.index(r_cat) if r_cat in categories else -1
                std_idx = categories.index(cat) if cat in categories else -1
                if cat_idx > std_idx:
                    over_count += cnt
                elif cat_idx < std_idx:
                    under_count += cnt
                else:
                    correct_count += cnt

        total = len(cat_data)
        summary[cat] = {
            "over_count": int(over_count),
            "under_count": int(under_count),
            "correct_count": int(correct_count),
            "total": int(total),
        }

    return {"matrix": matrix, "summary": summary}


def _calculate_cohen_kappa(df: pd.DataFrame, result_col: str, standard_col: str,
                           categories: list[str]) -> float:
    """Cohen's Kappa (2 评注者)"""
    n = len(df)
    observed = 0
    for cat in categories:
        both = ((df[result_col].astype(str) == cat) & (df[standard_col].astype(str) == cat)).sum()
        observed += both

    po = observed / n if n > 0 else 0

    pe = 0.0
    for cat in categories:
        p_a = (df[result_col].astype(str) == cat).sum() / n
        p_b = (df[standard_col].astype(str) == cat).sum() / n
        pe += p_a * p_b

    if abs(1 - pe) < 1e-10:
        if abs(po - 1) < 1e-10:
            return 1.0
        return -1.0

    return (po - pe) / (1 - pe)


def _kappa_interpretation(kappa: float) -> str:
    if kappa < 0:
        return "一致性极差"
    elif kappa < 0.2:
        return "轻微一致"
    elif kappa < 0.4:
        return "一般一致"
    elif kappa < 0.6:
        return "中等一致"
    elif kappa < 0.8:
        return "高度一致"
    else:
        return "几乎完全一致"
