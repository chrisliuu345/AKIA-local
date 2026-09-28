"""
Type 1 量具研究 — Cg/Cgk + 偏倚t检验

参考: MSA 4th Edition Chapter III
"""

from typing import Any
import numpy as np
import pandas as pd
from analysis._sanitize import sanitize_array
from scipy import stats


def analyze(
    data: pd.Series,
    reference: float,
    usl: float | None = None,
    lsl: float | None = None,
    tolerance: float | None = None,
    study_variation: float = 6.0,
    bias_test: bool = True,
) -> dict[str, Any]:
    """
    Type 1 量具研究

    Args:
        data: 测量数据
        reference: 参考值（真值）
        usl: 上规格限
        lsl: 下规格限
        tolerance: 公差范围（USL - LSL）
        study_variation: 研究变异乘数（默认6）
        bias_test: 是否执行偏倚检验

    Returns:
        分析结果字典
    """
    clean = sanitize_array(data)
    n = len(clean)

    if n < 5:
        raise ValueError(f"数据量不足: 需要至少 5 个观测值，当前 {n}")

    mean = float(np.mean(clean))
    std = float(np.std(clean, ddof=1))

    if tolerance is not None and usl is None and lsl is None:
        usl = reference + tolerance / 2
        lsl = reference - tolerance / 2

    result = {
        "chart_type": "Type 1 Gage Study",
        "summary": {
            "sample_size": n,
            "mean": round(mean, 6),
            "std": round(std, 6),
            "reference": float(reference),
        },
    }

    if usl is not None and lsl is not None:
        usl, lsl = float(usl), float(lsl)
        tolerance_val = usl - lsl

        if std > 0:
            cg = tolerance_val / (study_variation * std)
            cgk = min((usl - mean) / (study_variation / 2 * std),
                      (mean - lsl) / (study_variation / 2 * std))
        else:
            cg = float("inf")
            cgk = float("inf")

        bias = mean - reference
        bias_pct = (abs(bias) / (tolerance_val / 2) * 100) if tolerance_val > 0 else 0

        result["capability"] = {
            "usl": usl,
            "lsl": lsl,
            "tolerance": round(tolerance_val, 6),
            "cg": round(float(cg), 4) if cg != float("inf") else "inf",
            "cgk": round(float(cgk), 4) if cgk != float("inf") else "inf",
            "bias": round(float(bias), 6),
            "bias_pct": round(float(bias_pct), 2),
            "is_capable": (cg == float("inf") or cg >= 1.33) and (cgk == float("inf") or cgk >= 1.33),
        }

    if bias_test:
        bias_values = clean - reference
        mean_bias = float(np.mean(bias_values))
        std_bias = float(np.std(bias_values, ddof=1))

        if std_bias > 0:
            se = std_bias / np.sqrt(n)
            t_stat = mean_bias / se
            df = n - 1
            p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df))
        else:
            t_stat = 0.0
            p_value = 1.0

        result["bias_test"] = {
            "mean_bias": round(float(mean_bias), 6),
            "std_bias": round(float(std_bias), 6),
            "t_statistic": round(float(t_stat), 4),
            "p_value": round(float(p_value), 6),
            "is_significant": bool(p_value < 0.05),
            "interpretation": "偏倚显著" if p_value < 0.05 else "偏倚不显著",
        }

    if "capability" in result:
        result["acceptance"] = _type1_acceptance(
            result["capability"].get("cg"),
            result["capability"].get("cgk"),
            result.get("bias_test", {}).get("is_significant", False),
        )

    return result


def _type1_acceptance(cg, cgk, bias_significant: bool) -> dict[str, Any]:
    """Type 1 量具研究判定"""
    cg_ok = cg == "inf" or (isinstance(cg, (int, float)) and cg >= 1.33)
    cgk_ok = cgk == "inf" or (isinstance(cgk, (int, float)) and cgk >= 1.33)

    if cg_ok and cgk_ok and not bias_significant:
        level = "acceptable"
        message = "量具可接受（重复性好，偏倚不显著）"
    elif cg_ok and cgk_ok and bias_significant:
        level = "marginal"
        message = "量具条件接受（重复性好，但偏倚显著）"
    elif cg_ok and not cgk_ok:
        level = "marginal"
        message = "量具条件接受（重复性好，但偏倚较大）"
    else:
        level = "unacceptable"
        message = "量具不可接受（重复性不足）"

    return {"level": level, "message": message}
