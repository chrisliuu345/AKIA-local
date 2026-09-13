"""统一训练入口 — 供 UI / Agent 工具复用的最小拟合流程。

返回拟合后的 Pipeline 与训练/测试指标、CV，用于：
    - 模型持久化（.qamodel）
    - 新数据预测
    - 解释与学习曲线（需要保留 Pipeline）
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd
from sklearn.pipeline import Pipeline

from analysis.ml import automl, evaluate, prep
from analysis.ml.common import TASK_REGRESSION, base_result

DEFAULT_MODEL = "forest"
DEFAULT_PARAMS: Dict[str, Dict[str, Any]] = {
    "forest": {"n_estimators": 120},
    "boosting": {"max_iter": 150},
}

_ALIASES = {
    "cart": "tree", "dt": "tree", "decision_tree": "tree",
    "rf": "forest", "random_forest": "forest",
    "gbdt": "boosting", "hist": "boosting", "hgb": "boosting",
    "linear": "linear", "logistic": "linear", "regression": "linear",
    "mars": "mars", "tree": "tree", "forest": "forest",
    "boosting": "boosting",
}


def normalize_model(name: Optional[str]) -> str:
    key = str(name or DEFAULT_MODEL).strip().lower()
    resolved = _ALIASES.get(key)
    if resolved is None:
        raise ValueError(
            f"未知模型: {name}（可选: {', '.join(_ALIASES)}）")
    return resolved


def fit_pipeline(
    df: pd.DataFrame,
    target: str,
    features: Optional[List[str]] = None,
    task: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    params: Optional[Dict[str, Any]] = None,
    test_size: float = prep.DEFAULT_TEST_SIZE,
    cv: int = 5,
    random_state: int = 42,
    scale: bool = False,
) -> Dict[str, Any]:
    """切分 → 拟合 → 指标 + CV；返回可直接持久化/预测的 Pipeline。"""
    name = normalize_model(model)
    prepared = prep.prepare_data(df, target, features=features, task=task,
                                 test_size=test_size, random_state=random_state,
                                 scale=scale)
    resolved_task = prepared["task"]
    merged = dict(DEFAULT_PARAMS.get(name, {}))
    merged.update(params or {})
    estimator = automl.make_estimator(name, resolved_task, merged)
    pipeline = Pipeline([("prep", prepared["preprocessor"]), ("model", estimator)])
    pipeline.fit(prepared["X_train"], prepared["y_train"])

    names = [str(n) for n in pipeline.named_steps["prep"].get_feature_names_out()]
    y_score = (pipeline.predict_proba(prepared["X_test"])
               if resolved_task != TASK_REGRESSION else None)
    metrics = {
        "train": evaluate.compute_metrics(
            resolved_task, prepared["y_train"],
            pipeline.predict(prepared["X_train"]), n_features=len(names)),
        "test": evaluate.compute_metrics(
            resolved_task, prepared["y_test"], pipeline.predict(prepared["X_test"]),
            y_score=y_score, n_features=len(names)),
    }
    X_full = pd.concat([prepared["X_train"], prepared["X_test"]])
    y_full = pd.concat([prepared["y_train"], prepared["y_test"]])
    cv_result = evaluate.cross_validation(pipeline, X_full, y_full,
                                          resolved_task, cv=cv,
                                          random_state=random_state)
    return base_result(
        "train",
        model=name,
        params=merged,
        task=resolved_task,
        target=target,
        features=list(prepared["feature_names"]),
        encoded_features=names,
        pipeline=pipeline,
        X_train=prepared["X_train"], X_test=prepared["X_test"],
        y_train=prepared["y_train"], y_test=prepared["y_test"],
        metrics=metrics,
        cv=cv_result["summary"],
        cv_scores=cv_result["scores"],
        prep_summary=prepared["summary"],
    )
