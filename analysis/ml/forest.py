"""随机森林 — Bagging + 特征随机 / OOB 误差 / 特征重要性与置换重要性。"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.pipeline import Pipeline

from analysis.ml import evaluate, prep
from analysis.ml.common import TASK_CLASSIFICATION, MLDataError, base_result

DEFAULT_N_ESTIMATORS = 200
DEFAULT_PERMUTATION_REPEATS = 3
DEFAULT_MAX_PREVIEW = 200


def make_estimator(task: str, n_estimators: int = DEFAULT_N_ESTIMATORS,
                   max_depth: int | None = None, min_samples_leaf: int = 1,
                   max_features: str = "sqrt", oob_score: bool = True,
                   random_state: int = 42):
    """按任务类型构建随机森林估计器（默认启用 OOB）。"""
    params = {"n_estimators": int(n_estimators), "max_depth": max_depth,
                  "min_samples_leaf": int(min_samples_leaf),
                  "max_features": max_features, "oob_score": bool(oob_score),
                  "n_jobs": -1, "random_state": int(random_state)}
    if task == TASK_CLASSIFICATION:
        return RandomForestClassifier(**params)
    return RandomForestRegressor(**params)


def analyze(
    df: pd.DataFrame,
    target: str,
    features: list[str] | None = None,
    task: str | None = None,
    n_estimators: int = DEFAULT_N_ESTIMATORS,
    max_depth: int | None = None,
    min_samples_leaf: int = 1,
    max_features: str = "sqrt",
    oob_score: bool = True,
    permutation_repeats: int = DEFAULT_PERMUTATION_REPEATS,
    test_size: float = prep.DEFAULT_TEST_SIZE,
    cv: int = 5,
    random_state: int = 42,
    scale: bool = False,
    bin_features: list[str] | None = None,
    n_bins: int = 5,
    max_preview: int = DEFAULT_MAX_PREVIEW,
) -> dict[str, Any]:
    """随机森林完整流程：切分 → 拟合 → 指标/CV/OOB/重要性/置换重要性。"""
    if df is None or len(df) == 0:
        raise MLDataError("数据表为空")

    prepared = prep.prepare_data(
        df, target, features=features, task=task, test_size=test_size,
        random_state=random_state, scale=scale, bin_features=bin_features,
        n_bins=n_bins)
    resolved_task = prepared["task"]
    X_train, X_test = prepared["X_train"], prepared["X_test"]
    y_train, y_test = prepared["y_train"], prepared["y_test"]

    estimator = make_estimator(resolved_task, n_estimators=n_estimators,
                               max_depth=max_depth,
                               min_samples_leaf=min_samples_leaf,
                               max_features=max_features,
                               oob_score=oob_score,
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

    model = pipeline.named_steps["model"]
    importances = sorted(
        ({"feature": k, "importance": float(v)}
         for k, v in zip(names, model.feature_importances_, strict=False)),
        key=lambda item: item["importance"], reverse=True)

    permutation = _permutation_importance(
        pipeline, X_test, y_test, resolved_task, int(permutation_repeats),
        int(random_state))

    oob = None
    if oob_score and getattr(model, "oob_score_", None) is not None:
        oob = float(model.oob_score_)

    roc = (evaluate.roc_curve_data(y_test, y_prob_test)
           if resolved_task == TASK_CLASSIFICATION and y_prob_test is not None
           else None)
    residuals = (evaluate.residual_diagnostics(y_test, test_pred)
                 if resolved_task != TASK_CLASSIFICATION else None)

    preview = pd.DataFrame({"actual": np.asarray(y_test),
                            "predicted": np.asarray(test_pred)})
    if y_prob_test is not None and y_prob_test.ndim == 2 and y_prob_test.shape[1] == 2:
        preview["probability"] = y_prob_test[:, 1]

    return base_result(
        "forest",
        task=resolved_task,
        target=target,
        features=list(prepared["feature_names"]),
        encoded_features=names,
        model="RandomForest",
        params={"n_estimators": int(n_estimators), "max_depth": max_depth,
                "min_samples_leaf": int(min_samples_leaf),
                "max_features": max_features, "oob_score": bool(oob_score)},
        metrics=metrics,
        cv=cv_result["summary"],
        cv_scores=cv_result["scores"],
        oob_score=oob,
        importances=importances,
        permutation_importance=permutation,
        roc=roc,
        residuals=residuals,
        predictions=preview.head(int(max_preview)).to_dict(orient="records"),
        summary_text=_summary_text(resolved_task, metrics, cv_result, oob),
        prep_summary=prepared["summary"],
    )


def _permutation_importance(pipeline, X_test, y_test, task: str,
                            repeats: int, random_state: int) -> list[dict[str, Any]]:
    """置换重要性（基于原始特征列，可读性优于编码后列名）。"""
    if repeats <= 0 or len(X_test) < 2:
        return []
    try:
        scoring = "r2" if task != TASK_CLASSIFICATION else "accuracy"
        result = permutation_importance(
            pipeline, X_test, y_test, n_repeats=int(repeats),
            scoring=scoring, random_state=int(random_state), n_jobs=1)
        pairs = zip(list(X_test.columns), result.importances_mean, strict=False)
        return [{"feature": str(k), "importance": float(v)}
                for k, v in sorted(pairs, key=lambda kv: kv[1], reverse=True)]
    except Exception:  # noqa: BLE001 - 置换重要性失败不影响主结果
        return []


def _summary_text(task: str, metrics: dict[str, Any], cv_result: dict[str, Any],
                  oob: float | None) -> str:
    kind = "分类" if task == TASK_CLASSIFICATION else "回归"
    cv = cv_result["summary"]
    oob_text = ""
    if oob is not None:
        oob_text = f"，OOB={f'{oob:.3f}'}" if task == TASK_CLASSIFICATION \
            else f"，OOB R²={oob:.3f}"
    if task == TASK_CLASSIFICATION:
        test = metrics["test"]
        return (f"随机森林 {kind}（测试集）: 准确率={test['accuracy']:.3f}，"
                f"F1={test['f1_weighted']:.3f}{oob_text}；"
                f"{cv['folds']} 折 CV 准确率="
                f"{cv['accuracy_mean']:.3f}±{cv['accuracy_std']:.3f}")
    test = metrics["test"]
    return (f"随机森林 {kind}（测试集）: R²={test['r2']:.3f}，"
            f"RMSE={test['rmse']:.4g}{oob_text}；"
            f"{cv['folds']} 折 CV R²={cv['r2_mean']:.3f}±{cv['r2_std']:.3f}")
