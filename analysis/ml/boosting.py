"""梯度提升 — sklearn HistGradientBoosting 主实现 + 可选 XGBoost 适配。

不新增硬依赖：未安装 xgboost 时 backend="auto" 自动使用 sklearn；
显式 backend="xgboost" 且未安装时抛出可读错误（UI/Agent 展示安装指引）。
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import (HistGradientBoostingClassifier,
                              HistGradientBoostingRegressor)
from sklearn.pipeline import Pipeline

from analysis.ml import evaluate, prep
from analysis.ml.common import TASK_CLASSIFICATION, MLDataError, base_result

DEFAULT_MAX_ITER = 200
DEFAULT_LEARNING_RATE = 0.1


def xgboost_available() -> bool:
    try:
        import xgboost  # noqa: F401
        return True
    except Exception:  # noqa: BLE001 - 可选依赖
        return False


def make_estimator(task: str, backend: str = "auto",
                   max_iter: int = DEFAULT_MAX_ITER,
                   learning_rate: float = DEFAULT_LEARNING_RATE,
                   max_depth: int | None = None,
                   min_samples_leaf: int = 20,
                   l2_regularization: float = 0.0,
                   random_state: int = 42):
    """构建提升模型；backend: auto / sklearn / xgboost。"""
    backend = (backend or "auto").lower()
    if backend not in ("auto", "sklearn", "xgboost"):
        raise MLDataError(f"不支持的 backend: {backend}（可选 auto/sklearn/xgboost）")
    if backend in ("auto", "xgboost") and not xgboost_available():
        if backend == "xgboost":
            raise MLDataError(
                "未安装 XGBoost（可选依赖）。请执行 pip install xgboost，"
                "或改用 backend=sklearn / auto 使用内置 HistGradientBoosting")
        backend = "sklearn"

    params = dict(learning_rate=float(learning_rate),
                  max_iter=int(max_iter),
                  max_depth=max_depth,
                  min_samples_leaf=int(min_samples_leaf),
                  l2_regularization=float(l2_regularization),
                  random_state=int(random_state))
    if backend == "xgboost":
        import xgboost as xgb
        xgb_params = dict(n_estimators=int(max_iter),
                          learning_rate=float(learning_rate),
                          max_depth=int(max_depth) if max_depth else 6,
                          reg_lambda=float(l2_regularization),
                          random_state=int(random_state), verbosity=0)
        return (xgb.XGBClassifier(**xgb_params)
                if task == TASK_CLASSIFICATION else xgb.XGBRegressor(**xgb_params))
    return (HistGradientBoostingClassifier(**params)
            if task == TASK_CLASSIFICATION else HistGradientBoostingRegressor(**params))


def analyze(
    df: pd.DataFrame,
    target: str,
    features: list[str] | None = None,
    task: str | None = None,
    backend: str = "auto",
    max_iter: int = DEFAULT_MAX_ITER,
    learning_rate: float = DEFAULT_LEARNING_RATE,
    max_depth: int | None = None,
    min_samples_leaf: int = 20,
    l2_regularization: float = 0.0,
    test_size: float = prep.DEFAULT_TEST_SIZE,
    cv: int = 5,
    random_state: int = 42,
    scale: bool = False,
    bin_features: list[str] | None = None,
    n_bins: int = 5,
    max_preview: int = 200,
) -> dict[str, Any]:
    """梯度提升完整流程：切分 → 拟合 → 指标/CV/重要性。"""
    if df is None or len(df) == 0:
        raise MLDataError("数据表为空")

    prepared = prep.prepare_data(
        df, target, features=features, task=task, test_size=test_size,
        random_state=random_state, scale=scale, bin_features=bin_features,
        n_bins=n_bins)
    resolved_task = prepared["task"]
    X_train, X_test = prepared["X_train"], prepared["X_test"]
    y_train, y_test = prepared["y_train"], prepared["y_test"]

    estimator = make_estimator(resolved_task, backend=backend,
                               max_iter=max_iter, learning_rate=learning_rate,
                               max_depth=max_depth,
                               min_samples_leaf=min_samples_leaf,
                               l2_regularization=l2_regularization,
                               random_state=random_state)
    pipeline = Pipeline([("prep", prepared["preprocessor"]), ("model", estimator)])
    pipeline.fit(X_train, y_train)

    names = [str(n) for n in pipeline.named_steps["prep"].get_feature_names_out()]
    train_pred = pipeline.predict(X_train)
    test_pred = pipeline.predict(X_test)
    y_prob_test = (pipeline.predict_proba(X_test)
                   if resolved_task == TASK_CLASSIFICATION else None)

    metrics = {
        "train": evaluate.compute_metrics(resolved_task, y_train, train_pred,
                                          n_features=len(names)),
        "test": evaluate.compute_metrics(resolved_task, y_test, test_pred,
                                         y_score=y_prob_test, n_features=len(names)),
    }
    X_full = pd.concat([X_train, X_test])
    y_full = pd.concat([y_train, y_test])
    cv_result = evaluate.cross_validation(pipeline, X_full, y_full,
                                          resolved_task, cv=cv,
                                          random_state=random_state)

    from analysis.ml.forest import _permutation_importance
    permutation = _permutation_importance(pipeline, X_test, y_test,
                                          resolved_task, 3, int(random_state))

    roc = (evaluate.roc_curve_data(y_test, y_prob_test)
           if resolved_task == TASK_CLASSIFICATION and y_prob_test is not None
           else None)
    residuals = (evaluate.residual_diagnostics(y_test, test_pred)
                 if resolved_task != TASK_CLASSIFICATION else None)

    preview = pd.DataFrame({"actual": np.asarray(y_test),
                            "predicted": np.asarray(test_pred)})
    if y_prob_test is not None and y_prob_test.ndim == 2 and y_prob_test.shape[1] == 2:
        preview["probability"] = y_prob_test[:, 1]

    used_backend = ("xgboost" if estimator.__class__.__module__.startswith("xgboost")
                    else "sklearn")
    return base_result(
        "boosting",
        task=resolved_task,
        target=target,
        features=list(prepared["feature_names"]),
        encoded_features=names,
        model="HistGradientBoosting" if used_backend == "sklearn" else "XGBoost",
        backend=used_backend,
        params={"max_iter": int(max_iter), "learning_rate": float(learning_rate),
                "max_depth": max_depth, "min_samples_leaf": int(min_samples_leaf),
                "l2_regularization": float(l2_regularization)},
        metrics=metrics,
        cv=cv_result["summary"],
        cv_scores=cv_result["scores"],
        importances=permutation,
        roc=roc,
        residuals=residuals,
        predictions=preview.head(int(max_preview)).to_dict(orient="records"),
        summary_text=_summary_text(resolved_task, metrics, cv_result, used_backend),
        prep_summary=prepared["summary"],
    )


def _summary_text(task: str, metrics: dict[str, Any], cv_result: dict[str, Any],
                  backend: str) -> str:
    kind = "分类" if task == TASK_CLASSIFICATION else "回归"
    cv = cv_result["summary"]
    name = "HistGradientBoosting" if backend == "sklearn" else "XGBoost"
    if task == TASK_CLASSIFICATION:
        test = metrics["test"]
        return (f"{name} {kind}（测试集）: 准确率={test['accuracy']:.3f}，"
                f"F1={test['f1_weighted']:.3f}；{cv['folds']} 折 CV 准确率="
                f"{cv['accuracy_mean']:.3f}±{cv['accuracy_std']:.3f}")
    test = metrics["test"]
    return (f"{name} {kind}（测试集）: R²={test['r2']:.3f}，"
            f"RMSE={test['rmse']:.4g}；{cv['folds']} 折 CV R²="
            f"{cv['r2_mean']:.3f}±{cv['r2_std']:.3f}")
