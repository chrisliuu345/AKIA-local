"""数据准备与特征工程 — 缺失值 / 编码 / 分箱 / 标准化 + 防泄漏切分。

所有变换封装为 sklearn Pipeline：
    - 训练/测试切分在变换之前完成
    - CV 时 Pipeline 在折内拟合（调用方直接传 pipeline 给 cross_val_score）
    - 分类任务默认分层抽样，保持类别比例
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import KBinsDiscretizer, OneHotEncoder, StandardScaler

from analysis.ml.common import (
    TASK_CLASSIFICATION,
    base_result,
    validate_dataset,
)

DEFAULT_TEST_SIZE = 0.2
DEFAULT_RANDOM_STATE = 42


def build_preprocessor(
    numeric_features: List[str],
    categorical_features: Optional[List[str]] = None,
    scale: bool = True,
    bin_features: Optional[List[str]] = None,
    n_bins: int = 5,
) -> ColumnTransformer:
    """构建特征预处理 ColumnTransformer（数值 / 分箱 / 分类三分支）。"""
    categorical_features = categorical_features or []
    bin_features = [c for c in (bin_features or []) if c in numeric_features]
    plain_numeric = [c for c in numeric_features if c not in bin_features]

    numeric_steps: List[tuple] = [("imputer", SimpleImputer(strategy="median"))]
    if scale:
        numeric_steps.append(("scaler", StandardScaler()))

    transformers = []
    if plain_numeric:
        transformers.append(("num", Pipeline(numeric_steps), plain_numeric))
    if bin_features:
        transformers.append((
            "bin",
            Pipeline([
                ("imputer", SimpleImputer(strategy="median")),
                ("binner", KBinsDiscretizer(
                    n_bins=int(n_bins), encode="ordinal",
                    strategy="quantile", subsample=None)),
            ]),
            bin_features,
        ))
    if categorical_features:
        transformers.append((
            "cat",
            Pipeline([
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("encoder", OneHotEncoder(handle_unknown="ignore",
                                          sparse_output=False)),
            ]),
            categorical_features,
        ))

    if not transformers:
        raise ValueError("没有可用的特征列")
    return ColumnTransformer(transformers, remainder="drop",
                             verbose_feature_names_out=False)


def prepare_data(
    df: pd.DataFrame,
    target: str,
    features: Optional[List[str]] = None,
    task: Optional[str] = None,
    test_size: float = DEFAULT_TEST_SIZE,
    random_state: int = DEFAULT_RANDOM_STATE,
    scale: bool = True,
    bin_features: Optional[List[str]] = None,
    n_bins: int = 5,
    stratify: bool = True,
) -> Dict[str, Any]:
    """体检 + 切分 + 构建预处理流水线（未拟合，由模型 Pipeline 统一拟合）。

    返回:
        task / X_train / X_test / y_train / y_test / pipeline /
        feature_names / numeric_features / categorical_features / summary
    """
    if not 0.0 < float(test_size) < 1.0:
        raise ValueError(f"test_size 必须在 (0,1) 内: {test_size}")

    info = validate_dataset(df, target, features, task)
    data = info["data"]
    X = data[info["features"]]
    y = data[target]

    strat = y if (stratify and info["task"] == TASK_CLASSIFICATION
                  and y.value_counts().min() >= 2) else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=float(test_size), random_state=int(random_state),
        stratify=strat)

    preprocessor = build_preprocessor(
        info["numeric_features"], info["categorical_features"],
        scale=scale, bin_features=bin_features, n_bins=n_bins)
    pipeline = Pipeline([("prep", preprocessor)])

    summary = {
        "n_samples": info["n_rows"],
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "n_dropped_target_na": info["n_dropped_target_na"],
        "n_numeric": info["n_numeric"],
        "n_categorical": info["n_categorical"],
        "missing_cells": info["missing_cells"],
        "stratified": strat is not None,
        "scaled": bool(scale),
        "binned_features": list(bin_features or []),
    }
    return base_result(
        "prep",
        task=info["task"],
        feature_names=list(info["features"]),
        numeric_features=list(info["numeric_features"]),
        categorical_features=list(info["categorical_features"]),
        X_train=X_train, X_test=X_test, y_train=y_train, y_test=y_test,
        pipeline=pipeline, preprocessor=preprocessor,
        summary=summary,
    )


def describe_dataset(
    df: pd.DataFrame,
    target: Optional[str] = None,
    features: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """数据体检（不建模）— 供 UI 预检与 Agent 工具使用。"""
    if target is None:
        raise ValueError("必须提供目标列")
    info = validate_dataset(df, target, features)
    columns = []
    for col in info["features"]:
        series = info["data"][col]
        columns.append({
            "name": str(col),
            "kind": "numeric" if col in info["numeric_features"] else "categorical",
            "missing": int(series.isna().sum()),
            "unique": int(series.nunique(dropna=True)),
        })
    target_series = info["data"][target]
    return base_result(
        "prep_summary",
        task=info["task"],
        target=target,
        n_rows=info["n_rows"],
        columns=columns,
        class_counts=({str(k): int(v) for k, v in
                       target_series.value_counts().items()}
                      if info["task"] == TASK_CLASSIFICATION else {}),
    )
