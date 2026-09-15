"""CART 分类回归树 — 构建 / 预剪枝 / 后剪枝（ccp_alpha）/ 规则导出。

实现基于 sklearn 决策树内核，输出统一契约（analysis_type="ml.tree"），
并提供：
    - auto_ccp_alpha(): 用代价复杂度剪枝路径 + 交叉验证自动选 alpha
    - export_rules(): 把拟合后的树导出为文字规则（供 UI/报告/Agent 展示）
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor, export_text

from analysis.ml import evaluate, prep
from analysis.ml.common import TASK_CLASSIFICATION, MLDataError, base_result

DEFAULT_MAX_RULES = 12
DEFAULT_MAX_PREVIEW = 200


def make_estimator(task: str, max_depth: int | None = None,
                   min_samples_leaf: int = 1, ccp_alpha: float = 0.0,
                   random_state: int = 42):
    """按任务类型构建决策树估计器。"""
    params = dict(max_depth=max_depth, min_samples_leaf=int(min_samples_leaf),
                  ccp_alpha=float(ccp_alpha), random_state=int(random_state))
    if task == TASK_CLASSIFICATION:
        return DecisionTreeClassifier(**params)
    return DecisionTreeRegressor(**params)


def auto_ccp_alpha(preprocessor, X_train: pd.DataFrame, y_train: pd.Series,
                   task: str, cv: int = 5, random_state: int = 42,
                   max_candidates: int = 8) -> float:
    """在训练集上按代价复杂度路径 + 交叉验证选后剪枝 alpha（0 表示不剪枝）。"""
    try:
        Xt = preprocessor.fit_transform(X_train)
        base = make_estimator(task, random_state=random_state)
        path = base.cost_complexity_pruning_path(Xt, y_train)
        positive = np.asarray(path.ccp_alphas)[np.asarray(path.ccp_alphas) > 0]
        if positive.size == 0:
            return 0.0
        candidates = np.unique(np.quantile(
            positive, np.linspace(0.0, 1.0, int(max_candidates))))

        scoring = "accuracy" if task == TASK_CLASSIFICATION else "r2"
        splitter = evaluate._cv_splitter(task, cv, random_state, y_train)
        best_alpha, best_score = 0.0, -np.inf
        for alpha in candidates:
            est = make_estimator(task, ccp_alpha=float(alpha),
                                 random_state=random_state)
            scores = cross_val_score(est, Xt, y_train, cv=splitter,
                                     scoring=scoring)
            mean = float(np.mean(scores))
            if mean > best_score + 1e-9:
                best_alpha, best_score = float(alpha), mean
        baseline = float(np.mean(cross_val_score(
            make_estimator(task, random_state=random_state), Xt, y_train,
            cv=splitter, scoring=scoring)))
        return best_alpha if best_score > baseline + 1e-9 else 0.0
    except Exception:  # noqa: BLE001 - 剪枝选择失败时退回不剪枝
        return 0.0


def export_rules(pipeline: Pipeline, max_rules: int = DEFAULT_MAX_RULES) -> list[str]:
    """导出树规则文本（限制行数，供展示）。"""
    try:
        model = pipeline.named_steps["model"]
        names = list(pipeline.named_steps["prep"].get_feature_names_out())
        lines = export_text(model, feature_names=[str(n) for n in names]).splitlines()
        return [line.rstrip() for line in lines[:int(max_rules)]]
    except Exception:  # noqa: BLE001 - 规则导出失败不影响主结果
        return []


def analyze(
    df: pd.DataFrame,
    target: str,
    features: list[str] | None = None,
    task: str | None = None,
    max_depth: int | None = None,
    min_samples_leaf: int = 1,
    ccp_alpha: float = 0.0,
    auto_prune: bool = False,
    test_size: float = prep.DEFAULT_TEST_SIZE,
    cv: int = 5,
    random_state: int = 42,
    scale: bool = False,
    bin_features: list[str] | None = None,
    n_bins: int = 5,
    max_rules: int = DEFAULT_MAX_RULES,
    max_preview: int = DEFAULT_MAX_PREVIEW,
) -> dict[str, Any]:
    """CART 完整流程：切分 →（可选）自动剪枝 → 拟合 → 指标/CV/规则/重要性。"""
    if df is None or len(df) == 0:
        raise MLDataError("数据表为空")

    prepared = prep.prepare_data(
        df, target, features=features, task=task, test_size=test_size,
        random_state=random_state, scale=scale, bin_features=bin_features,
        n_bins=n_bins)
    resolved_task = prepared["task"]
    X_train, X_test = prepared["X_train"], prepared["X_test"]
    y_train, y_test = prepared["y_train"], prepared["y_test"]

    if auto_prune and float(ccp_alpha) == 0.0:
        ccp_alpha = auto_ccp_alpha(prepared["preprocessor"], X_train, y_train,
                                   resolved_task, cv=cv,
                                   random_state=random_state)

    estimator = make_estimator(resolved_task, max_depth=max_depth,
                               min_samples_leaf=min_samples_leaf,
                               ccp_alpha=ccp_alpha, random_state=random_state)
    pipeline = Pipeline([("prep", prepared["preprocessor"]), ("model", estimator)])
    pipeline.fit(X_train, y_train)

    names = [str(n) for n in pipeline.named_steps["prep"].get_feature_names_out()]
    train_pred = pipeline.predict(X_train)
    test_pred = pipeline.predict(X_test)
    y_prob_test = (pipeline.predict_proba(X_test)
                   if resolved_task == TASK_CLASSIFICATION else None)
    y_prob_train = (pipeline.predict_proba(X_train)
                    if resolved_task == TASK_CLASSIFICATION else None)

    metrics = {
        "train": evaluate.compute_metrics(resolved_task, y_train, train_pred,
                                          y_score=y_prob_train, n_features=len(names)),
        "test": evaluate.compute_metrics(resolved_task, y_test, test_pred,
                                         y_score=y_prob_test, n_features=len(names)),
    }

    X_full = pd.concat([X_train, X_test])
    y_full = pd.concat([y_train, y_test])
    cv_result = evaluate.cross_validation(pipeline, X_full, y_full,
                                          resolved_task, cv=cv,
                                          random_state=random_state)

    model = pipeline.named_steps["model"]
    importances = []
    if hasattr(model, "feature_importances_"):
        pairs = sorted(zip(names, (float(v) for v in model.feature_importances_),
                           strict=False),
                       key=lambda kv: kv[1], reverse=True)
        importances = [{"feature": k, "importance": v} for k, v in pairs]

    roc = (evaluate.roc_curve_data(y_test, y_prob_test)
           if resolved_task == TASK_CLASSIFICATION and y_prob_test is not None
           else None)
    residuals = (evaluate.residual_diagnostics(y_test, test_pred)
                 if resolved_task != TASK_CLASSIFICATION else None)

    preview = pd.DataFrame({"actual": np.asarray(y_test),
                            "predicted": np.asarray(test_pred)})
    if y_prob_test is not None and y_prob_test.ndim == 2 and y_prob_test.shape[1] == 2:
        preview["probability"] = y_prob_test[:, 1]
    preview = preview.head(int(max_preview))

    summary_text = _summary_text(resolved_task, metrics, cv_result, ccp_alpha)
    return base_result(
        "tree",
        task=resolved_task,
        target=target,
        features=list(prepared["feature_names"]),
        encoded_features=names,
        model="CART",
        params={
            "max_depth": max_depth,
            "min_samples_leaf": int(min_samples_leaf),
            "ccp_alpha": float(ccp_alpha),
            "auto_prune": bool(auto_prune),
        },
        metrics=metrics,
        cv=cv_result["summary"],
        cv_scores=cv_result["scores"],
        importances=importances,
        rules=export_rules(pipeline, max_rules=max_rules),
        roc=roc,
        residuals=residuals,
        predictions=preview.to_dict(orient="records"),
        summary_text=summary_text,
        prep_summary=prepared["summary"],
    )


def _summary_text(task: str, metrics: dict[str, Any], cv_result: dict[str, Any],
                  ccp_alpha: float) -> str:
    kind = "分类" if task == TASK_CLASSIFICATION else "回归"
    cv_sum = cv_result["summary"]
    prune = f"，后剪枝 α={ccp_alpha:.4g}" if ccp_alpha else ""
    if task == TASK_CLASSIFICATION:
        test = metrics["test"]
        return (f"CART {kind}（测试集）: 准确率={test['accuracy']:.3f}，"
                f"F1={test['f1_weighted']:.3f}"
                + (f"，AUC={test['auc']:.3f}" if test.get("auc") else "")
                + f"；{cv_sum['folds']} 折 CV 准确率="
                  f"{cv_sum['accuracy_mean']:.3f}±{cv_sum['accuracy_std']:.3f}{prune}")
    test = metrics["test"]
    return (f"CART {kind}（测试集）: R²={test['r2']:.3f}，"
            f"RMSE={test['rmse']:.4g}，MAE={test['mae']:.4g}；"
            f"{cv_sum['folds']} 折 CV R²="
            f"{cv_sum['r2_mean']:.3f}±{cv_sum['r2_std']:.3f}{prune}")
