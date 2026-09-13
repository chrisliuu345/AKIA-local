"""v4.0.0 P2 — 模型解释（SHAP 优先 / 原生与置换重要性降级）。"""

import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import Pipeline

from analysis.ml import explain, prep


def _frame(n=260, seed=31):
    rng = np.random.default_rng(seed)
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)
    x3 = rng.normal(size=n)
    return pd.DataFrame({
        "温度": x1,
        "压力": x2,
        "湿度": x3,
        "设备": rng.choice(["A", "B"], n),
        "强度": 3 * x1 + 2 * x2 + 0.2 * x3 + rng.normal(0, 0.3, n),
    })


def _fitted_pipeline(df, estimator):
    prepared = prep.prepare_data(df, "强度", features=["温度", "压力", "湿度", "设备"],
                                 random_state=4)
    pipe = Pipeline([("prep", prepared["preprocessor"]), ("model", estimator)])
    pipe.fit(prepared["X_train"], prepared["y_train"])
    return pipe, prepared["X_train"], prepared["y_train"]


class TestExplainModel:

    def test_shap_path_for_tree_model(self):
        if not explain.shap_available():
            pytest.skip("未安装 shap")
        df = _frame()
        pipe, X, _y = _fitted_pipeline(df, RandomForestRegressor(
            n_estimators=40, random_state=1))
        out = explain.explain_model(pipe, X, max_rows=120)
        assert out["analysis_type"] == "ml.explain"
        assert out["method"] == "shap"
        assert out["n_rows_used"] <= 120
        assert out["importances"] and "温度" in out["importances"][0]["feature"]
        assert out["base_value"] is not None

    def test_native_fallback_when_shap_disabled(self):
        df = _frame()
        pipe, X, _y = _fitted_pipeline(df, RandomForestRegressor(
            n_estimators=40, random_state=1))
        out = explain.explain_model(pipe, X, use_shap=False)
        assert out["method"] == "native"
        assert out["importances"]

    def test_linear_coefficients_used_as_native(self):
        df = _frame()
        pipe, X, _y = _fitted_pipeline(df, LinearRegression())
        out = explain.explain_model(pipe, X, use_shap=False)
        assert out["method"] == "native"
        top = out["importances"][0]["feature"]
        assert top.startswith(("温度", "压力"))

    def test_permutation_fallback_for_unknown_model(self):
        df = _frame()
        pipe, X, y = _fitted_pipeline(df, KNeighborsRegressor(n_neighbors=5))
        out = explain.explain_model(pipe, X, y=y, use_shap=False)
        assert out["method"] == "permutation"
        assert out["importances"]

    def test_empty_features_rejected(self):
        df = _frame()
        pipe, _X, _y = _fitted_pipeline(df, LinearRegression())
        with pytest.raises(ValueError, match="非空特征数据"):
            explain.explain_model(pipe, pd.DataFrame())


class TestExplainSample:

    def test_single_row_contributions(self):
        df = _frame()
        pipe, X, _y = _fitted_pipeline(df, RandomForestRegressor(
            n_estimators=40, random_state=1))
        out = explain.explain_sample(pipe, X.iloc[0], max_features=5)
        assert out["analysis_type"] == "ml.explain_sample"
        assert 0 < len(out["contributions"]) <= 5
        assert all(np.isfinite(c["value"]) for c in out["contributions"])
        assert out["method"] in {"shap", "native", "permutation", "none"}

    def test_dataframe_row_accepted(self):
        df = _frame()
        pipe, X, _y = _fitted_pipeline(df, LinearRegression())
        out = explain.explain_sample(pipe, X.iloc[:1], max_features=3)
        assert len(out["contributions"]) <= 3
