"""
生存分析 — Kaplan-Meier / Log-rank 检验 / Cox 比例风险回归

基于 lifelines 库封装，提供:
  kaplan_meier()    — Kaplan-Meier 生存曲线 + 置信区间
  logrank_test()    — Log-rank 两组比较检验
  cox_regression()  — Cox 比例风险回归
"""

from typing import Any

import numpy as np
import pandas as pd
from lifelines import KaplanMeierFitter, CoxPHFitter
from lifelines.statistics import logrank_test as _logrank_test

from analysis._sanitize import sanitize_pairs


def kaplan_meier(
    durations: pd.Series,
    event_observed: pd.Series,
    group_col: pd.Series | None = None,
    confidence_level: float = 0.95,
    label: str | None = None,
) -> dict[str, Any]:
    """
    Kaplan-Meier 生存分析

    Args:
        durations: 生存时间（删失时间也算）
        event_observed: 事件指示（1=失效, 0=删失）
        group_col: 分组列（可选，用于多组比较）
        confidence_level: 置信水平
        label: 组标签

    Returns:
        KM 分析结果字典
    """
    T, E = sanitize_pairs(durations, event_observed)
    E = E.astype(int)

    if len(T) < 2:
        return {
            "chart_type": "Kaplan-Meier",
            "analysis_type": "reliability.survival.km",
            "error": f"数据点不足: {len(T)}（至少需要 2 个）",
        }

    kmf = KaplanMeierFitter()
    kmf.fit(T, event_observed=E, label=label or "All")

    sf = kmf.survival_function_
    timeline = sf.index.tolist()
    sf_values = sf.iloc[:, 0].tolist()

    ci = kmf.confidence_interval_survival_function_
    ci_lower = ci.iloc[:, 0].tolist() if ci is not None else []
    ci_upper = ci.iloc[:, 1].tolist() if ci is not None else []

    et = kmf.event_table
    event_table = {
        "at_risk": et["at_risk"].tolist(),
        "observed": et["observed"].tolist(),
        "censored": et["censored"].tolist(),
        "entrance": et["entrance"].tolist(),
    }

    median_survival = float(kmf.median_survival_time_) if np.isfinite(kmf.median_survival_time_) else None

    return {
        "chart_type": "Kaplan-Meier",
        "analysis_type": "reliability.survival.km",
        "summary": {
            "n_subjects": int(len(T)),
            "n_events": int(E.sum()),
            "n_censored": int((1 - E).sum()),
            "median_survival": median_survival,
            "confidence_level": confidence_level,
        },
        "timeline": timeline,
        "survival_function": [round(float(v), 6) for v in sf_values],
        "confidence_lower": [round(float(v), 6) for v in ci_lower],
        "confidence_upper": [round(float(v), 6) for v in ci_upper],
        "event_table": event_table,
    }


def kaplan_meier_compare(
    durations_A: pd.Series,
    event_observed_A: pd.Series,
    durations_B: pd.Series,
    event_observed_B: pd.Series,
    label_A: str = "Group A",
    label_B: str = "Group B",
    confidence_level: float = 0.95,
) -> dict[str, Any]:
    """
    双组 Kaplan-Meier 生存分析 + Log-rank 检验

    Returns:
        两组 KM 结果 + Log-rank p 值
    """
    kmf_a = KaplanMeierFitter()
    T_A = durations_A.dropna().astype(float)
    E_A = event_observed_A.loc[T_A.index].astype(int)
    kmf_a.fit(T_A, event_observed=E_A, label=label_A)

    kmf_b = KaplanMeierFitter()
    T_B = durations_B.dropna().astype(float)
    E_B = event_observed_B.loc[T_B.index].astype(int)
    kmf_b.fit(T_B, event_observed=E_B, label=label_B)

    lr = _logrank_test(T_A, T_B, event_observed_A=E_A, event_observed_B=E_B)

    def _extract(kmf, name):
        sf = kmf.survival_function_
        ci = kmf.confidence_interval_survival_function_
        n_subjects = int(kmf.event_table["at_risk"].iloc[0])
        return {
            "label": name,
            "n_subjects": n_subjects,
            "n_events": int(kmf.event_table["observed"].sum()),
            "median_survival": float(kmf.median_survival_time_) if np.isfinite(kmf.median_survival_time_) else None,
            "timeline": sf.index.tolist(),
            "survival_function": [round(float(v), 6) for v in sf.iloc[:, 0].tolist()],
            "confidence_lower": [round(float(v), 6) for v in ci.iloc[:, 0].tolist()] if ci is not None else [],
            "confidence_upper": [round(float(v), 6) for v in ci.iloc[:, 1].tolist()] if ci is not None else [],
        }

    return {
        "chart_type": "Kaplan-Meier",
        "analysis_type": "reliability.survival.km_compare",
        "summary": {
            "logrank_statistic": round(float(lr.test_statistic), 6),
            "logrank_p_value": round(float(lr.p_value), 6),
            "is_significant": bool(lr.p_value < (1 - confidence_level)),
        },
        "group_a": _extract(kmf_a, label_A),
        "group_b": _extract(kmf_b, label_B),
    }


def logrank_test(
    durations_A: pd.Series,
    event_observed_A: pd.Series,
    durations_B: pd.Series,
    event_observed_B: pd.Series,
) -> dict[str, Any]:
    """
    Log-rank 检验（两组比较）

    Returns:
        检验结果字典
    """
    T_A, E_A = sanitize_pairs(durations_A, event_observed_A)
    E_A = E_A.astype(int)
    T_B, E_B = sanitize_pairs(durations_B, event_observed_B)
    E_B = E_B.astype(int)

    if len(T_A) < 2 or len(T_B) < 2:
        return {
            "analysis_type": "reliability.survival.logrank",
            "error": "每组至少需要 2 个数据点",
        }

    result = _logrank_test(T_A, T_B, event_observed_A=E_A, event_observed_B=E_B)

    return {
        "analysis_type": "reliability.survival.logrank",
        "summary": {
            "test_statistic": round(float(result.test_statistic), 6),
            "p_value": round(float(result.p_value), 6),
            "is_significant": bool(result.p_value < 0.05),
            "n_group_a": int(len(T_A)),
            "n_group_b": int(len(T_B)),
        },
    }


def cox_regression(
    df: pd.DataFrame,
    duration_col: str,
    event_col: str,
    covariates: list[str] | None = None,
    penalizer: float = 0.0,
    confidence_level: float = 0.95,
) -> dict[str, Any]:
    """
    Cox 比例风险回归

    Args:
        df: 数据框（必须包含 duration_col, event_col, 以及协变量列）
        duration_col: 生存时间列名
        event_col: 事件指示列名
        covariates: 协变量列名列表（None 则使用所有其他列）
        penalizer: L2 惩罚系数
        confidence_level: 置信水平

    Returns:
        Cox 回归结果字典
    """
    required = [duration_col, event_col]
    if covariates:
        required.extend(covariates)
    missing = [c for c in required if c not in df.columns]
    if missing:
        return {
            "analysis_type": "reliability.survival.cox",
            "error": f"缺少列: {missing}",
        }

    clean = df[required].dropna()
    if len(clean) < 10:
        return {
            "analysis_type": "reliability.survival.cox",
            "error": f"有效数据不足: {len(clean)}（至少需要 10 行）",
        }

    alpha = 1 - confidence_level
    cph = CoxPHFitter(penalizer=penalizer, alpha=alpha)

    try:
        cph.fit(clean, duration_col=duration_col, event_col=event_col, show_progress=False)
    except Exception as e:  # noqa: BLE001 - Cox 拟合失败：返回结构化错误（lifelines 异常类型不定）
        return {
            "analysis_type": "reliability.survival.cox",
            "error": f"Cox 回归拟合失败: {e!s}",
        }

    coefficients = {}
    for var in cph.params_.index:
        coef = float(cph.params_[var])
        hr = float(cph.hazard_ratios_[var])
        se = float(cph.standard_errors_[var])
        p = float(cph.summary.loc[var, "p"])
        ci_low = float(cph.summary.loc[var, f"coef lower {int(confidence_level*100)}%"])
        ci_high = float(cph.summary.loc[var, f"coef upper {int(confidence_level*100)}%"])
        coefficients[var] = {
            "coef": round(coef, 6),
            "hazard_ratio": round(hr, 6),
            "std_err": round(se, 6),
            "p_value": round(p, 6),
            "ci_lower": round(ci_low, 6),
            "ci_upper": round(ci_high, 6),
        }

    bs = cph.baseline_survival_
    baseline_survival = {
        "timeline": bs.index.tolist(),
        "survival": bs.iloc[:, 0].tolist(),
    }

    return {
        "analysis_type": "reliability.survival.cox",
        "summary": {
            "n_subjects": int(len(clean)),
            "n_events": int(clean[event_col].sum()),
            "concordance_index": round(float(cph.concordance_index_), 6),
            "log_likelihood": round(float(cph.log_likelihood_), 6),
            "AIC_partial": round(float(cph.AIC_partial_), 4),
            "log_likelihood_ratio_test_p": round(float(cph.log_likelihood_ratio_test().p_value), 6),
            "confidence_level": confidence_level,
        },
        "coefficients": coefficients,
        "baseline_survival": baseline_survival,
    }
