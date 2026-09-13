"""v4.0.0 P3 — MARS 多元自适应回归样条（纯 numpy）。"""

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LinearRegression

from analysis.ml import mars, prep
from analysis.ml.common import MLDataError


def _friedman1(n=320, seed=7):
    """Friedman #1 合成集 — 含强交互项 x1·x2 与非线性项 x3²。"""
    rng = np.random.default_rng(seed)
    X = rng.uniform(0, 1, size=(n, 4))
    y = (10 * np.sin(np.pi * X[:, 0] * X[:, 1])
         + 20 * (X[:, 2] - 0.5) ** 2 + 10 * X[:, 3]
         + rng.normal(0, 1.0, n))
    df = pd.DataFrame(X, columns=["温度", "压力", "速度", "时间"])
    df["产出"] = y
    return df


class TestMARSRegressor:

    def test_fit_predict_shapes(self):
        rng = np.random.default_rng(1)
        X = rng.normal(size=(120, 3))
        y = 2 * X[:, 0] + np.maximum(X[:, 1], 0) + rng.normal(0, 0.2, 120)
        model = mars.MARSRegressor(max_terms=10, feature_names=["a", "b", "c"])
        model.fit(X, y)
        pred = model.predict(X)
        assert pred.shape == (120,)
        assert model.r2_ > 0.5
        assert model.n_terms_ <= 10
        assert all(isinstance(label, str) for label in model.term_labels())

    def test_constant_feature_ignored(self):
        rng = np.random.default_rng(2)
        X = np.column_stack([np.ones(80), rng.normal(size=80)])
        y = 3 * X[:, 1] + rng.normal(0, 0.1, 80)
        model = mars.MARSRegressor(max_terms=6).fit(X, y)
        assert np.isfinite(model.predict(X)).all()


class TestMARSAnalyze:

    def test_beats_linear_on_friedman1(self):
        df = _friedman1()
        out = mars.analyze(df, "产出", max_terms=21, n_knots=3,
                           cv=3, random_state=42)
        assert out["analysis_type"] == "ml.mars"
        assert out["task"] == "regression"
        assert out["n_terms"] >= 1
        assert out["metrics"]["test"]["r2"] > 0.5
        assert "MARS" in out["summary_text"]

        prepared = prep.prepare_data(df, "产出", test_size=0.2,
                                     random_state=42)
        linear = LinearRegression().fit(prepared["X_train"], prepared["y_train"])
        linear_pred = linear.predict(prepared["X_test"])
        linear_rmse = float(np.sqrt(np.mean(
            (np.asarray(prepared["y_test"]) - linear_pred) ** 2)))
        assert out["metrics"]["test"]["rmse"] < linear_rmse

    def test_interaction_term_detected(self):
        df = _friedman1(n=260, seed=11)
        out = mars.analyze(df, "产出", max_terms=16, n_knots=3,
                           cv=3, random_state=5)
        assert any("×" in term for term in out["terms"]), out["terms"]

    def test_feature_importance_sorted(self):
        df = _friedman1(n=220, seed=3)
        out = mars.analyze(df, "产出", max_terms=12, n_knots=2,
                           cv=3, random_state=5)
        assert out["importances"]
        values = [item["importance"] for item in out["importances"]]
        assert values == sorted(values, reverse=True)
        assert sum(values) == pytest.approx(1.0, abs=1e-6)

    def test_max_terms_respected(self):
        df = _friedman1(n=200, seed=9)
        out = mars.analyze(df, "产出", max_terms=5, n_knots=2,
                           cv=3, random_state=5)
        assert out["n_terms"] <= 5

    def test_classification_rejected(self):
        df = _friedman1(n=120)
        df["判定"] = np.where(df["产出"] > df["产出"].median(), "OK", "NG")
        with pytest.raises(MLDataError, match="仅支持回归"):
            mars.analyze(df, "判定")

    def test_empty_frame(self):
        with pytest.raises(MLDataError, match="数据表为空"):
            mars.analyze(pd.DataFrame(), "产出")
