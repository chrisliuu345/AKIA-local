"""数据契约与校验 — 任务类型判定 / 特征选择 / 数据集体检。

供 prep / trees / automl 及 UI、Agent 工具复用，保证各入口判定一致。
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

TASK_REGRESSION = "regression"
TASK_CLASSIFICATION = "classification"
TASKS = (TASK_REGRESSION, TASK_CLASSIFICATION)

# 数值目标列判定为分类的唯一值上限（超过则视为连续回归目标）
_CLASSIFICATION_MAX_CLASSES = 10
MIN_ROWS = 20


class MLDataError(ValueError):
    """数据不满足建模条件（UI/Agent 直接展示 message）。"""


def detect_task_type(target: pd.Series, task: str | None = None) -> str:
    """判定任务类型；显式 task 优先。

    规则:
        - 文本 / 布尔 / 分类 dtype → classification
        - 数值型: 唯一值 ≤10 且全为整数 → classification（如 0/1 判定列）
        - 其余数值型 → regression
    """
    if task:
        key = str(task).strip().lower()
        alias = {"reg": TASK_REGRESSION, "回归": TASK_REGRESSION,
                 "cls": TASK_CLASSIFICATION, "分类": TASK_CLASSIFICATION}
        key = alias.get(key, key)
        if key not in TASKS:
            raise MLDataError(
                f"不支持的任务类型: {task}（可选 regression/classification）")
        return key

    if isinstance(target.dtype, pd.CategoricalDtype) or pd.api.types.is_bool_dtype(target):
        return TASK_CLASSIFICATION
    if not pd.api.types.is_numeric_dtype(target):
        return TASK_CLASSIFICATION

    values = target.dropna()
    unique = values.unique()
    is_integer = bool(np.all(np.equal(np.mod(values.to_numpy(dtype=float), 1), 0)))
    if is_integer and len(unique) <= _CLASSIFICATION_MAX_CLASSES:
        return TASK_CLASSIFICATION
    return TASK_REGRESSION


def resolve_features(df: pd.DataFrame, target: str,
                     features: list[str] | None = None) -> list[str]:
    """解析特征列：显式 features 优先，否则取全部列 - target。"""
    if target not in df.columns:
        raise MLDataError(f"目标列不存在: {target}")
    if features:
        missing = [c for c in features if c not in df.columns]
        if missing:
            raise MLDataError(f"特征列不存在: {', '.join(map(str, missing))}")
        cols = [c for c in features if c != target]
    else:
        cols = [c for c in df.columns if c != target]
    if not cols:
        raise MLDataError("至少需要一个特征列（当前只有目标列）")
    return list(dict.fromkeys(cols))


def validate_dataset(df: pd.DataFrame, target: str,
                     features: list[str] | None = None,
                     task: str | None = None,
                     min_rows: int = MIN_ROWS) -> dict[str, Any]:
    """数据集体检 — 返回任务类型、特征分组与行数统计；不满足条件抛 MLDataError。"""
    if df is None or len(df) == 0:
        raise MLDataError("数据表为空")
    if target not in df.columns:
        raise MLDataError(f"目标列不存在: {target}")

    feature_cols = resolve_features(df, target, features)
    data = df[[target] + feature_cols].dropna(subset=[target])
    dropped = int(len(df) - len(data))

    if len(data) < min_rows:
        raise MLDataError(
            f"有效样本不足: {len(data)} 行（需要 ≥{min_rows} 行，"
            f"目标列缺失已剔除 {dropped} 行）")

    resolved_task = detect_task_type(data[target], task)
    if resolved_task == TASK_CLASSIFICATION:
        classes = data[target].astype(str).unique()
        if len(classes) < 2:
            raise MLDataError(
                f"分类任务至少需要 2 个类别（当前 {len(classes)} 个）")

    numeric_cols, categorical_cols = [], []
    for col in feature_cols:
        series = data[col]
        if pd.api.types.is_numeric_dtype(series) or pd.api.types.is_bool_dtype(series):
            numeric_cols.append(col)
        else:
            categorical_cols.append(col)

    if not numeric_cols and not categorical_cols:
        raise MLDataError("没有可用特征列")

    return {
        "task": resolved_task,
        "target": target,
        "features": feature_cols,
        "numeric_features": numeric_cols,
        "categorical_features": categorical_cols,
        "n_rows": int(len(data)),
        "n_dropped_target_na": dropped,
        "n_numeric": len(numeric_cols),
        "n_categorical": len(categorical_cols),
        "missing_cells": int(data[feature_cols].isna().sum().sum()),
        "data": data,
    }


def base_result(analysis_type: str, **payload: Any) -> dict[str, Any]:
    """统一结果契约 — 所有 ML 引擎返回 analysis_type 前缀 "ml."。"""
    return {"analysis_type": f"ml.{analysis_type}", **payload}
