"""
EMP (Empirical Measurement Process) 方法量具研究

参考: Wheeler DJ (2006) "EMP III: Evaluating the Measurement Process"
      MSA 4th Edition Chapter IV

支持:
- EMP Crossed 量具研究
- 判异准则（Wheeler 8 条）
- 分辨力分级（1级/2级/3级/4级）
- 研究变异比 (Study Variation Ratio)
- 可区分类别数 (ndc)
"""

from typing import Any
import numpy as np
import pandas as pd
from config import settings as _cfg


def analyze_crossed(
    df: pd.DataFrame,
    measurement_col: str,
    part_col: str,
    operator_col: str,
    tolerance: float | None = None,
) -> dict[str, Any]:
    """
    EMP Crossed 量具研究

    Args:
        df: 数据框
        measurement_col: 测量值列
        part_col: 零件列
        operator_col: 评注者列
        tolerance: 公差范围（可选）

    Returns:
        分析结果字典
    """
    data = df.copy()
    data[measurement_col] = pd.to_numeric(data[measurement_col], errors="coerce")
    data = data.dropna(subset=[measurement_col, part_col, operator_col])

    parts = data[part_col].unique()
    operators = data[operator_col].unique()
    p, o = len(parts), len(operators)

    if p < 2 or o < 2:
        raise ValueError(f"需要至少2个零件和2个操作员，当前零件={p}, 操作员={o}")

    repeats = data.groupby([part_col, operator_col]).size()
    r = int(repeats.mode().iloc[0])

    float(data[measurement_col].mean())

    part_means = data.groupby(part_col)[measurement_col].mean()
    op_means = data.groupby(operator_col)[measurement_col].mean()

    r_bar = _avg_range(data, measurement_col, part_col, operator_col)
    d2 = _cfg.CONTROL_CHART_CONSTANTS.get(r, {}).get("d2", 1.128 * (r ** 0.3))

    ev = r_bar / d2

    r_op = float(op_means.max() - op_means.min())
    d2_star_op = _cfg.MSA_D2_STAR.get(o, _cfg.CONTROL_CHART_CONSTANTS.get(o, {}).get("d2", 1.128))
    av = np.sqrt(max((r_op / d2_star_op) ** 2 - ev ** 2 / (p * r), 0))

    grr = np.sqrt(ev ** 2 + av ** 2)
    r_part = float(part_means.max() - part_means.min())
    d2_star_part = _cfg.MSA_D2_STAR.get(p, _cfg.CONTROL_CHART_CONSTANTS.get(p, {}).get("d2", 1.128))
    pv = r_part / d2_star_part

    tv = np.sqrt(grr ** 2 + pv ** 2)

    grr_pct_tv = (grr / tv * 100) if tv > 0 else 0
    grr_pct_tol = (grr / tolerance * 100) if tolerance else None
    ndc = int(1.41 * (pv / grr)) if grr > 0 else 0
    ev_pct = (ev / tv * 100) if tv > 0 else 0
    av_pct = (av / tv * 100) if tv > 0 else 0
    pv_pct = (pv / tv * 100) if tv > 0 else 0

    study_var_ratio = (6 * grr / tv) if tv > 0 else 0
    discrimination_grade = _discrimination_grade(ndc)
    wheeler_criteria = _wheeler_criteria(ev, av, grr, pv, tv, ndc, grr_pct_tv)

    interaction_data = _calculate_interaction(data, measurement_col, part_col, operator_col)

    return {
        "chart_type": "EMP Crossed",
        "method": "EMP",
        "design": {
            "parts": p,
            "operators": o,
            "replicates": r,
            "total_measurements": len(data),
        },
        "variance_components": {
            "ev": round(float(ev), 6),
            "av": round(float(av), 6),
            "grr": round(float(grr), 6),
            "pv": round(float(pv), 6),
            "tv": round(float(tv), 6),
        },
        "percentages": {
            "ev_pct": round(float(ev_pct), 2),
            "av_pct": round(float(av_pct), 2),
            "grr_pct_tv": round(float(grr_pct_tv), 2),
            "grr_pct_tol": round(float(grr_pct_tol), 2) if grr_pct_tol is not None else None,
            "pv_pct": round(float(pv_pct), 2),
        },
        "ndc": ndc,
        "study_variation_ratio": round(float(study_var_ratio), 4),
        "discrimination_grade": discrimination_grade,
        "wheeler_criteria": wheeler_criteria,
        "interaction": interaction_data,
        "acceptance": _emp_acceptance(grr_pct_tv, ndc, discrimination_grade),
    }


def analyze_nested(
    df: pd.DataFrame,
    measurement_col: str,
    part_col: str,
    operator_col: str,
    tolerance: float | None = None,
) -> dict[str, Any]:
    """
    EMP Nested 量具研究（每个零件由不同操作员测量）

    Args:
        df: 数据框
        measurement_col: 测量值列
        part_col: 零件列
        operator_col: 评注者列
        tolerance: 公差范围（可选）

    Returns:
        分析结果字典
    """
    data = df.copy()
    data[measurement_col] = pd.to_numeric(data[measurement_col], errors="coerce")
    data = data.dropna(subset=[measurement_col, part_col, operator_col])

    parts = data[part_col].unique()
    operators = data[operator_col].unique()
    p, o = len(parts), len(operators)

    if p < 2 or o < 2:
        raise ValueError(f"需要至少2个零件和2个操作员，当前零件={p}, 操作员={o}")

    repeats = data.groupby([part_col, operator_col]).size()
    r = int(repeats.mode().iloc[0])

    float(data[measurement_col].mean())

    part_means = data.groupby(part_col)[measurement_col].mean()
    op_means = data.groupby(operator_col)[measurement_col].mean()

    r_bar = _avg_range(data, measurement_col, part_col, operator_col)
    d2 = _cfg.CONTROL_CHART_CONSTANTS.get(r, {}).get("d2", 1.128 * (r ** 0.3))

    ev = r_bar / d2

    r_op = float(op_means.max() - op_means.min())
    d2_star_op = _cfg.MSA_D2_STAR.get(o, _cfg.CONTROL_CHART_CONSTANTS.get(o, {}).get("d2", 1.128))
    av = np.sqrt(max((r_op / d2_star_op) ** 2 - ev ** 2 / (p * r), 0))

    grr = np.sqrt(ev ** 2 + av ** 2)
    r_part = float(part_means.max() - part_means.min())
    d2_star_part = _cfg.MSA_D2_STAR.get(p, _cfg.CONTROL_CHART_CONSTANTS.get(p, {}).get("d2", 1.128))
    pv = r_part / d2_star_part

    tv = np.sqrt(grr ** 2 + pv ** 2)

    grr_pct_tv = (grr / tv * 100) if tv > 0 else 0
    grr_pct_tol = (grr / tolerance * 100) if tolerance else None
    ndc = int(1.41 * (pv / grr)) if grr > 0 else 0
    ev_pct = (ev / tv * 100) if tv > 0 else 0
    av_pct = (av / tv * 100) if tv > 0 else 0
    pv_pct = (pv / tv * 100) if tv > 0 else 0

    study_var_ratio = (6 * grr / tv) if tv > 0 else 0
    discrimination_grade = _discrimination_grade(ndc)
    wheeler_criteria = _wheeler_criteria(ev, av, grr, pv, tv, ndc, grr_pct_tv)

    return {
        "chart_type": "EMP Nested",
        "method": "EMP",
        "design": {
            "parts": p,
            "operators": o,
            "replicates": r,
            "total_measurements": len(data),
        },
        "variance_components": {
            "ev": round(float(ev), 6),
            "av": round(float(av), 6),
            "grr": round(float(grr), 6),
            "pv": round(float(pv), 6),
            "tv": round(float(tv), 6),
        },
        "percentages": {
            "ev_pct": round(float(ev_pct), 2),
            "av_pct": round(float(av_pct), 2),
            "grr_pct_tv": round(float(grr_pct_tv), 2),
            "grr_pct_tol": round(float(grr_pct_tol), 2) if grr_pct_tol is not None else None,
            "pv_pct": round(float(pv_pct), 2),
        },
        "ndc": ndc,
        "study_variation_ratio": round(float(study_var_ratio), 4),
        "discrimination_grade": discrimination_grade,
        "wheeler_criteria": wheeler_criteria,
        "acceptance": _emp_acceptance(grr_pct_tv, ndc, discrimination_grade),
    }


def _discrimination_grade(ndc: int) -> dict[str, Any]:
    """
    分辨力分级

    Grade 1: ndc < 2 (unacceptable)
    Grade 2: ndc = 2-3 (marginal)
    Grade 3: ndc = 4-5 (acceptable)
    Grade 4: ndc >= 6 (excellent)
    """
    if ndc < 2:
        grade = 1
        level = "unacceptable"
        description = "不可接受 — 无法区分零件差异"
    elif ndc <= 3:
        grade = 2
        level = "marginal"
        description = "边缘 — 可区分少数类别"
    elif ndc <= 5:
        grade = 3
        level = "acceptable"
        description = "可接受 — 可区分足够类别"
    else:
        grade = 4
        level = "excellent"
        description = "优秀 — 可区分大量类别"

    return {
        "grade": grade,
        "level": level,
        "description": description,
        "ndc": ndc,
    }


def _wheeler_criteria(
    ev: float,
    av: float,
    grr: float,
    pv: float,
    tv: float,
    ndc: int,
    grr_pct: float,
) -> list[dict[str, Any]]:
    """
    Wheeler 判异准则（8 条）

    1. 测量系统必须一致（无特殊原因变异）
    2. 测量系统必须有能力（ndc >= 5）
    3. 测量系统必须可重复
    4. 测量系统必须可再现
    5. 测量系统必须准确（无偏倚）
    6. 测量系统必须线性
    7. 测量系统必须稳定
    8. 测量系统必须适合目的
    """
    criteria = [
        {
            "id": 1,
            "name": "一致性",
            "description": "测量系统必须一致（无特殊原因变异）",
            "status": "pass" if ndc >= 5 else "fail",
            "detail": f"ndc = {ndc}" + (" ≥ 5" if ndc >= 5 else " < 5"),
        },
        {
            "id": 2,
            "name": "能力",
            "description": "测量系统必须有能力（ndc >= 5）",
            "status": "pass" if ndc >= 5 else "fail",
            "detail": f"ndc = {ndc}" + (" ≥ 5" if ndc >= 5 else " < 5"),
        },
        {
            "id": 3,
            "name": "可重复性",
            "description": "测量系统必须可重复",
            "status": "pass" if (ev / tv < 0.3 if tv > 0 else False) else "fail",
            "detail": f"EV/TV = {ev/tv*100:.1f}%" if tv > 0 else "EV/TV = N/A" + (" < 30%" if (ev / tv < 0.3 if tv > 0 else False) else " ≥ 30%"),
        },
        {
            "id": 4,
            "name": "可再现性",
            "description": "测量系统必须可再现",
            "status": "pass" if (av / tv < 0.3 if tv > 0 else False) else "fail",
            "detail": f"AV/TV = {av/tv*100:.1f}%" if tv > 0 else "AV/TV = N/A" + (" < 30%" if (av / tv < 0.3 if tv > 0 else False) else " ≥ 30%"),
        },
        {
            "id": 5,
            "name": "准确性",
            "description": "测量系统必须准确（无偏倚）",
            "status": "pass" if grr_pct < 30 else "fail",
            "detail": f"GRR% = {grr_pct:.1f}%" + (" < 30%" if grr_pct < 30 else " ≥ 30%"),
        },
        {
            "id": 6,
            "name": "线性",
            "description": "测量系统必须线性",
            "status": "pass" if grr_pct < 30 else "fail",
            "detail": "需偏倚/线性研究验证" if grr_pct < 30 else "GRR% 过高",
        },
        {
            "id": 7,
            "name": "稳定性",
            "description": "测量系统必须稳定",
            "status": "pass" if grr_pct < 30 else "fail",
            "detail": "需控制图监控" if grr_pct < 30 else "GRR% 过高",
        },
        {
            "id": 8,
            "name": "适合目的",
            "description": "测量系统必须适合目的",
            "status": "pass" if grr_pct < 30 and ndc >= 5 else "fail",
            "detail": f"GRR% = {grr_pct:.1f}%, ndc = {ndc}",
        },
    ]

    return criteria


def _calculate_interaction(
    df: pd.DataFrame,
    measurement_col: str,
    part_col: str,
    operator_col: str,
) -> dict[str, Any]:
    """
    计算交互效应数据（零件 × 操作员）
    """
    pivot = df.pivot_table(
        values=measurement_col,
        index=part_col,
        columns=operator_col,
        aggfunc="mean",
    )

    operators = pivot.columns.tolist()
    parts = pivot.index.tolist()

    interaction_data = []
    for op in operators:
        op_means = pivot[op].values
        overall_means = pivot.mean(axis=1).values
        interaction = op_means - overall_means
        interaction_data.append({
            "operator": str(op),
            "parts": parts,
            "means": [round(float(x), 4) for x in op_means],
            "interaction": [round(float(x), 4) for x in interaction],
        })

    return {
        "operators": operators,
        "parts": parts,
        "data": interaction_data,
    }


def _emp_acceptance(
    grr_pct: float,
    ndc: int,
    discrimination_grade: dict[str, Any],
) -> dict[str, Any]:
    """
    EMP 接收准则

    基于 GRR% 和 ndc 综合判断
    """
    grade = discrimination_grade["grade"]

    if grr_pct < 10 and ndc >= 10:
        level = "excellent"
        description = "优秀 — 测量系统完全可接受"
    elif grr_pct < 30 and ndc >= 5:
        level = "acceptable"
        description = "可接受 — 测量系统可用于过程控制"
    elif grr_pct < 55 and ndc >= 3:
        level = "marginal"
        description = "边缘 — 测量系统可能需要改进"
    else:
        level = "unacceptable"
        description = "不可接受 — 测量系统需要改进"

    return {
        "level": level,
        "description": description,
        "grr_pct": round(float(grr_pct), 2),
        "ndc": ndc,
        "grade": grade,
    }


def _avg_range(
    df: pd.DataFrame,
    measurement_col: str,
    part_col: str,
    operator_col: str,
) -> float:
    """计算平均极差"""
    grouped = df.groupby([part_col, operator_col])[measurement_col]
    ranges = grouped.max() - grouped.min()
    return float(ranges.mean())
