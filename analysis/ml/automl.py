"""AutoML — 多模型交叉验证排名与推荐。

模型库: 线性/逻辑回归 · CART · 随机森林 · 梯度提升 · MARS（仅回归）
排名: 回归按 CV R²（次 RMSE）· 分类按 CV Accuracy（次 F1）
预算: time_budget_s 控制总时长，超时模型标记 skipped（至少运行第一个模型）
"""

from __future__ import annotations

import time
from typing import Any

import pandas as pd
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.pipeline import Pipeline

from analysis.ml import boosting, evaluate, forest, prep, trees
from analysis.ml.common import TASK_CLASSIFICATION, TASK_REGRESSION, MLDataError, base_result
from analysis.ml.mars import MARSRegressor

MODEL_LABELS = {
    "linear": "线性/逻辑回归",
    "tree": "CART 决策树",
    "forest": "随机森林",
    "boosting": "梯度提升",
    "mars": "MARS",
}


def available_models(task: str) -> list[str]:
    """按任务类型返回可用模型名（MARS 仅回归）。"""
    models = ["linear", "tree", "forest", "boosting"]
    if task == TASK_REGRESSION:
        models.append("mars")
    return models


def make_estimator(name: str, task: str, params: dict[str, Any] | None = None):
    """按名称构建估计器（供排序与单模型复跑复用）。"""
    params = dict(params or {})
    if name == "linear":
        if task == TASK_CLASSIFICATION:
            params.setdefault("max_iter", 1000)
            return LogisticRegression(**params)
        return LinearRegression(**params)
    if name == "tree":
        return trees.make_estimator(task, **params)
    if name == "forest":
        return forest.make_estimator(task, **params)
    if name == "boosting":
        return boosting.make_estimator(task, **params)
    if name == "mars":
        if task != TASK_REGRESSION:
            raise MLDataError("MARS 仅支持回归任务")
        return MARSRegressor(**params)
    raise MLDataError(
        f"未知模型: {name}（可选: {', '.join(available_models(task))}）")


def analyze(
    df: pd.DataFrame,
    target: str,
    features: list[str] | None = None,
    task: str | None = None,
    models: list[str] | None = None,
    model_params: dict[str, dict[str, Any]] | None = None,
    test_size: float = prep.DEFAULT_TEST_SIZE,
    cv: int = 5,
    random_state: int = 42,
    time_budget_s: float | None = None,
    max_preview: int = 200,
) -> dict[str, Any]:
    """AutoML 主流程 — 统一切分下比较各模型，返回 leaderboard 与推荐。"""
    if df is None or len(df) == 0:
        raise MLDataError("数据表为空")

    prepared = prep.prepare_data(df, target, features=features, task=task,
                                 test_size=test_size, random_state=random_state)
    resolved_task = prepared["task"]
    X_train, X_test = prepared["X_train"], prepared["X_test"]
    y_train, y_test = prepared["y_train"], prepared["y_test"]
    X_full = pd.concat([X_train, X_test])
    y_full = pd.concat([y_train, y_test])

    wanted = list(models) if models else available_models(resolved_task)
    unknown = [m for m in wanted if m not in available_models(resolved_task)]
    if unknown:
        raise MLDataError(
            f"不可用模型: {', '.join(unknown)}"
            f"（{resolved_task} 可选: {', '.join(available_models(resolved_task))}）")

    params_by_model = dict(model_params or {})
    leaderboard: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    pipelines: dict[str, Pipeline] = {}
    started = time.perf_counter()

    for index, name in enumerate(wanted):
        elapsed = time.perf_counter() - started
        if index > 0 and time_budget_s is not None and elapsed > float(time_budget_s):
            skipped.append({"model": name, "reason": "超出时间预算"})
            continue
        model_started = time.perf_counter()
        estimator = make_estimator(name, resolved_task,
                                   params_by_model.get(name))
        pipeline = Pipeline([("prep", prepared["preprocessor"]),
                             ("model", estimator)])
        cv_result = evaluate.cross_validation(pipeline, X_full, y_full,
                                              resolved_task, cv=cv,
                                              random_state=random_state)
        pipeline.fit(X_train, y_train)
        test_pred = pipeline.predict(X_test)
        y_score = (pipeline.predict_proba(X_test)
                   if resolved_task == TASK_CLASSIFICATION else None)
        test_metrics = evaluate.compute_metrics(resolved_task, y_test, test_pred,
                                                y_score=y_score)
        pipelines[name] = pipeline
        leaderboard.append({
            "model": name,
            "label": MODEL_LABELS.get(name, name),
            "cv": cv_result["summary"],
            "test": test_metrics,
            "duration_s": round(time.perf_counter() - model_started, 3),
        })

    ranking_key = ("r2_mean" if resolved_task == TASK_REGRESSION
                   else "accuracy_mean")
    leaderboard.sort(key=lambda item: item["cv"].get(ranking_key, float("-inf")),
                     reverse=True)
    for rank, item in enumerate(leaderboard, start=1):
        item["rank"] = rank

    best = leaderboard[0] if leaderboard else None
    recommendation = _recommendation(resolved_task, leaderboard, skipped)
    preview = []
    if best is not None:
        pipeline = pipelines[best["model"]]
        pred = pipeline.predict(X_test)
        frame = pd.DataFrame({"actual": y_test.to_numpy(),
                              "predicted": pred})
        if resolved_task == TASK_CLASSIFICATION:
            proba = pipeline.predict_proba(X_test)
            if proba.ndim == 2 and proba.shape[1] == 2:
                frame["probability"] = proba[:, 1]
        preview = frame.head(int(max_preview)).to_dict(orient="records")

    return base_result(
        "automl",
        task=resolved_task,
        target=target,
        features=list(prepared["feature_names"]),
        ranking_metric=ranking_key,
        leaderboard=leaderboard,
        skipped=skipped,
        best_model=best["model"] if best else None,
        best_label=best["label"] if best else None,
        best_pipeline=pipelines.get(best["model"]) if best else None,
        predictions=preview,
        total_seconds=round(time.perf_counter() - started, 3),
        summary_text=recommendation,
        prep_summary=prepared["summary"],
    )


def _recommendation(task: str, leaderboard: list[dict[str, Any]],
                    skipped: list[dict[str, str]]) -> str:
    if not leaderboard:
        return "未评估任何模型（时间预算过小）"
    metric = "R²" if task == TASK_REGRESSION else "准确率"
    key = "r2_mean" if task == TASK_REGRESSION else "accuracy_mean"
    best = leaderboard[0]
    text = (f"推荐 {best['label']}：CV {metric}={best['cv'][key]:.3f}"
            f"（测试集 {metric}="
            f"{best['test']['r2' if task == TASK_REGRESSION else 'accuracy']:.3f}）")
    if len(leaderboard) > 1:
        runner = leaderboard[1]
        text += (f"；次选 {runner['label']}（CV {metric}="
                 f"{runner['cv'][key]:.3f}）")
    if skipped:
        text += f"；{len(skipped)} 个模型因时间预算跳过"
    return text
