"""MARS — 多元自适应回归样条（纯 numpy 实现，无额外依赖）。

算法:
    1. 前向：以铰链函数 max(x_j - t, 0) / max(t - x_j, 0) 为基，
       逐步加入使残差平方和下降最多的项；支持两个铰链乘积的交互项
       （degree ≤ max_degree）
    2. 后向：按 GCV 逐项剪枝，直到 GCV 不再下降
    3. 最小二乘拟合最终基函数系数，输出可读项与特征重要性

仅支持回归任务（分类请使用 CART / 随机森林 / 梯度提升）。
"""

from __future__ import annotations

from typing import Any
from collections.abc import Sequence

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.pipeline import Pipeline

from analysis.ml import evaluate, prep
from analysis.ml.common import (
    TASK_REGRESSION,
    MLDataError,
    base_result,
    detect_task_type,
)

Atom = tuple[int, float, int]          # (feature_index, knot, side)
Term = tuple[Atom, ...]

DEFAULT_MAX_TERMS = 21
DEFAULT_MAX_DEGREE = 2
DEFAULT_N_KNOTS = 3
DEFAULT_INTERACTION_FEATURES = 5


def _hinge(X: np.ndarray, atoms: Sequence[Atom]) -> np.ndarray:
    """单个铰链原子（或原子组合）取值。"""
    out = np.ones(len(X))
    for j, knot, side in atoms:
        col = X[:, j] - knot
        out = out * np.maximum(side * col, 0.0)
    return out


def _design(X: np.ndarray, terms: Sequence[Term]) -> np.ndarray:
    columns = [np.ones(len(X))]
    columns.extend(_hinge(X, term) for term in terms)
    return np.column_stack(columns)


class MARSRegressor(RegressorMixin, BaseEstimator):
    """MARS 回归器（sklearn 兼容，可直接放入 Pipeline / CV）。"""

    def __init__(self, max_terms: int = DEFAULT_MAX_TERMS,
                 max_degree: int = DEFAULT_MAX_DEGREE,
                 n_knots: int = DEFAULT_N_KNOTS,
                 interaction_features: int = DEFAULT_INTERACTION_FEATURES,
                 pruning: bool = True,
                 min_improvement: float = 1e-6,
                 feature_names: Sequence[str] | None = None):
        self.max_terms = max_terms
        self.max_degree = max_degree
        self.n_knots = n_knots
        self.interaction_features = interaction_features
        self.pruning = pruning
        self.min_improvement = min_improvement
        self.feature_names = feature_names

    # -- 内部工具 -----------------------------------------------------

    def _name(self, j: int) -> str:
        if self.feature_names is not None and 0 <= j < len(self.feature_names):
            return str(self.feature_names[j])
        return f"x{j}"

    def _knots(self, X: np.ndarray) -> list[list[float]]:
        knots: list[list[float]] = []
        quantiles = np.linspace(0.1, 0.9, int(self.n_knots))
        for j in range(X.shape[1]):
            column = X[:, j]
            if np.std(column) <= 0:
                knots.append([])
                continue
            values = np.unique(np.quantile(column, quantiles))
            knots.append([float(v) for v in values])
        return knots

    def _candidate_terms(self, X: np.ndarray, terms: list[Term],
                         knots: list[list[float]]) -> list[Term]:
        candidates: list[Term] = []
        for j, feature_knots in enumerate(knots):
            for knot in feature_knots:
                candidates.append(((j, knot, 1),))
                candidates.append(((j, knot, -1),))

        if not terms or int(self.max_degree) < 2:
            return candidates

        # 交互项只取与 y 相关性最高的前 N 个特征，控制候选规模
        correlations = [abs(float(np.corrcoef(X[:, j], self._y)[0, 1]))
                        if np.std(X[:, j]) > 0 else 0.0
                        for j in range(X.shape[1])]
        top_features = set(np.argsort(correlations)[::-1][:int(self.interaction_features)])
        base_terms = [t for t in terms if len(t) < int(self.max_degree)]
        for term in base_terms:
            for j in sorted(top_features):
                for knot in knots[j]:
                    candidates.append(term + ((j, knot, 1),))
                    candidates.append(term + ((j, knot, -1),))
        # 去重（同一组原子顺序不同）
        seen, unique = set(), []
        for term in candidates:
            key = tuple(sorted(term))
            if key not in seen:
                seen.add(key)
                unique.append(term)
        return unique

    @staticmethod
    def _gcv(y: np.ndarray, matrix: np.ndarray) -> float:
        coef, *_ = np.linalg.lstsq(matrix, y, rcond=None)
        resid = y - matrix @ coef
        n = len(y)
        k = matrix.shape[1] + 1
        denom = (1.0 - k / n) ** 2
        if denom <= 1e-9:
            return float("inf")
        return float(np.sum(resid ** 2) / n / denom)

    # -- 拟合与预测 ---------------------------------------------------

    def fit(self, X, y):
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()
        self._y = y
        self.n_features_in_ = X.shape[1]
        knots = self._knots(X)
        terms: list[Term] = []

        for _ in range(max(0, int(self.max_terms) - 1)):
            candidates = self._candidate_terms(X, terms, knots)
            if not candidates:
                break
            design = _design(X, terms)
            coef, *_ = np.linalg.lstsq(design, y, rcond=None)
            resid = y - design @ coef
            Q, _ = np.linalg.qr(design)
            C = np.column_stack([_hinge(X, term) for term in candidates])
            C_perp = C - Q @ (Q.T @ C)
            denom = np.sum(C_perp ** 2, axis=0)
            numer = (resid @ C_perp) ** 2
            gains = np.where(denom > 1e-12, numer / np.maximum(denom, 1e-12), 0.0)
            best = int(np.argmax(gains))
            total_var = float(np.sum((y - y.mean()) ** 2))
            if gains[best] <= float(self.min_improvement) * max(total_var, 1e-12):
                break
            terms.append(candidates[best])
            if len(terms) >= int(self.max_terms) - 1:
                break

        if self.pruning and terms:
            current = self._gcv(y, _design(X, terms))
            improved = True
            while improved and len(terms) > 1:
                improved = False
                best_drop, best_gcv = None, current
                for idx in range(len(terms)):
                    candidate = terms[:idx] + terms[idx + 1:]
                    value = self._gcv(y, _design(X, candidate))
                    if value < best_gcv - 1e-12:
                        best_drop, best_gcv = idx, value
                if best_drop is not None:
                    terms.pop(best_drop)
                    current = best_gcv
                    improved = True

        self.terms_ = terms
        matrix = _design(X, terms)
        coef, *_ = np.linalg.lstsq(matrix, y, rcond=None)
        self.coefficients_ = [float(v) for v in coef]
        self.n_terms_ = len(terms)
        self._feature_importance(X, terms, coef)
        fitted = matrix @ coef
        self.rss_ = float(np.sum((y - fitted) ** 2))
        self.r2_ = float(1 - self.rss_ / max(np.sum((y - y.mean()) ** 2), 1e-12))
        return self

    def _feature_importance(self, X: np.ndarray, terms: Sequence[Term],
                            coef: np.ndarray) -> None:
        weights = np.zeros(X.shape[1])
        for idx, term in enumerate(terms):
            column = _hinge(X, term)
            weight = abs(float(coef[idx + 1])) * float(np.std(column))
            for j, _knot, _side in term:
                weights[j] += weight / len(term)
        total = float(np.sum(weights))
        self.feature_importance_ = (weights / total) if total > 0 else weights

    def predict(self, X):
        X = np.asarray(X, dtype=float)
        matrix = _design(X, getattr(self, "terms_", []))
        coef = np.asarray(getattr(self, "coefficients_", [0.0]), dtype=float)
        return matrix @ coef

    # -- 可读输出 -----------------------------------------------------

    def term_labels(self, max_terms: int | None = None) -> list[str]:
        labels = []
        for term in getattr(self, "terms_", []):
            parts = []
            for j, knot, side in term:
                if side >= 0:
                    parts.append(f"max({self._name(j)}-{knot:.3g},0)")
                else:
                    parts.append(f"max({knot:.3g}-{self._name(j)},0)")
            labels.append(" × ".join(parts))
        if max_terms is not None:
            labels = labels[:int(max_terms)]
        return labels


def analyze(
    df: pd.DataFrame,
    target: str,
    features: list[str] | None = None,
    task: str | None = None,
    max_terms: int = DEFAULT_MAX_TERMS,
    max_degree: int = DEFAULT_MAX_DEGREE,
    n_knots: int = DEFAULT_N_KNOTS,
    pruning: bool = True,
    test_size: float = prep.DEFAULT_TEST_SIZE,
    cv: int = 5,
    random_state: int = 42,
    bin_features: list[str] | None = None,
    n_bins: int = 5,
    max_preview: int = 200,
) -> dict[str, Any]:
    """MARS 完整流程（仅回归）：切分 → 前向/后向 → 指标/CV/可读项。"""
    if df is None or len(df) == 0:
        raise MLDataError("数据表为空")
    if target not in df.columns:
        raise MLDataError(f"目标列不存在: {target}")
    if detect_task_type(df[target], task) != TASK_REGRESSION:
        raise MLDataError("MARS 仅支持回归任务（分类请使用 CART/随机森林/梯度提升）")

    prepared = prep.prepare_data(
        df, target, features=features, task=TASK_REGRESSION,
        test_size=test_size, random_state=random_state, scale=False,
        bin_features=bin_features, n_bins=n_bins)
    if prepared["task"] != TASK_REGRESSION:
        raise MLDataError("MARS 仅支持回归任务（目标列被判定为分类）")

    X_train, X_test = prepared["X_train"], prepared["X_test"]
    y_train, y_test = prepared["y_train"], prepared["y_test"]
    preprocessor = prepared["preprocessor"]
    encoded_names = [str(n) for n in
                     preprocessor.fit(X_train).get_feature_names_out()]

    estimator = MARSRegressor(max_terms=max_terms, max_degree=max_degree,
                              n_knots=n_knots, pruning=pruning,
                              feature_names=encoded_names)
    pipeline = Pipeline([("prep", preprocessor), ("model", estimator)])
    pipeline.fit(X_train, y_train)

    train_pred = pipeline.predict(X_train)
    test_pred = pipeline.predict(X_test)
    metrics = {
        "train": evaluate.regression_metrics(y_train, train_pred,
                                             n_features=len(encoded_names)),
        "test": evaluate.regression_metrics(y_test, test_pred,
                                            n_features=len(encoded_names)),
    }
    X_full = pd.concat([X_train, X_test])
    y_full = pd.concat([y_train, y_test])
    cv_result = evaluate.cross_validation(pipeline, X_full, y_full,
                                          TASK_REGRESSION, cv=cv,
                                          random_state=random_state)

    importances = sorted(
        ({"feature": name, "importance": float(value)}
         for name, value in zip(encoded_names, estimator.feature_importance_,
                                strict=False)),
        key=lambda item: item["importance"], reverse=True)
    residuals = evaluate.residual_diagnostics(y_test, test_pred)
    preview = pd.DataFrame({"actual": np.asarray(y_test),
                            "predicted": np.asarray(test_pred)})

    test = metrics["test"]
    summary_text = (f"MARS 回归（测试集）: R²={test['r2']:.3f}，"
                    f"RMSE={test['rmse']:.4g}，项数={estimator.n_terms_}；"
                    f"{cv_result['summary']['folds']} 折 CV R²="
                    f"{cv_result['summary']['r2_mean']:.3f}"
                    f"±{cv_result['summary']['r2_std']:.3f}")
    return base_result(
        "mars",
        task=TASK_REGRESSION,
        target=target,
        features=list(prepared["feature_names"]),
        encoded_features=encoded_names,
        model="MARS",
        params={"max_terms": int(max_terms), "max_degree": int(max_degree),
                "n_knots": int(n_knots), "pruning": bool(pruning)},
        metrics=metrics,
        cv=cv_result["summary"],
        cv_scores=cv_result["scores"],
        importances=importances,
        terms=estimator.term_labels(max_terms=20),
        n_terms=estimator.n_terms_,
        residuals=residuals,
        predictions=preview.head(int(max_preview)).to_dict(orient="records"),
        summary_text=summary_text,
        prep_summary=prepared["summary"],
    )
