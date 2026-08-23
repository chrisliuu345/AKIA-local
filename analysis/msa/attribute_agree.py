"""
属性一致性分析 (Attribute Agreement Analysis)
"""

from typing import Dict, Any, List
import pandas as pd


def analyze(
    df: pd.DataFrame,
    result_col: str,
    standard_col: str,
    operator_col: str = "",
    part_col: str = "",
) -> Dict[str, Any]:
    data = df.copy()
    data = data.dropna(subset=[result_col, standard_col])

    n = len(data)
    if n < 10:
        raise ValueError(f"数据量不足: {n}")

    agreement = (data[result_col].astype(str) == data[standard_col].astype(str)).sum()
    agreement_rate = agreement / n

    if operator_col and operator_col in data.columns:
        operators = data[operator_col].unique()
        op_agreements = {}
        for op in operators:
            op_data = data[data[operator_col] == op]
            op_agree = (op_data[result_col].astype(str) == op_data[standard_col].astype(str)).sum()
            op_agreements[str(op)] = {
                "total": len(op_data),
                "agreement": int(op_agree),
                "rate": round(float(op_agree / len(op_data) * 100), 2),
            }
    else:
        op_agreements = {}

    categories = sorted(set(data[standard_col].astype(str)))
    kappa = _calculate_kappa(data, result_col, standard_col, categories)

    return {
        "chart_type": "Attribute Agreement",
        "total_assessments": n,
        "agreement_count": int(agreement),
        "agreement_rate": round(float(agreement_rate * 100), 2),
        "kappa": round(float(kappa), 4),
        "kappa_interpretation": _kappa_interpretation(kappa),
        "operator_agreements": op_agreements,
        "is_acceptable": agreement_rate >= 0.9 and kappa >= 0.7,
    }


def _calculate_kappa(df: pd.DataFrame, result_col: str, standard_col: str,
                     categories: List[str]) -> float:
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
        return 1.0

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
