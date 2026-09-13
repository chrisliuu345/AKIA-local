"""v4.0.0 P3 — AutoML 多模型 CV 排名与推荐。"""

import numpy as np
import pandas as pd
import pytest

from analysis.ml import automl
from analysis.ml.common import MLDataError


def _regression_frame(n=220, seed=17):
    rng = np.random.default_rng(seed)
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)
    return pd.DataFrame({
        "温度": x1,
        "压力": x2,
        "产线": rng.choice(["L1", "L2"], n),
        "强度": 3 * x1 + np.sin(x2 * 2) + rng.normal(0, 0.4, n),
    })


def _classification_frame(n=220, seed=19):
    rng = np.random.default_rng(seed)
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)
    score = x1 + x2 + rng.normal(0, 0.6, n)
    return pd.DataFrame({
        "尺寸": x1,
        "湿度": x2,
        "判定": np.where(score > 0, "PASS", "FAIL"),
    })


FAST_PARAMS = {"forest": {"n_estimators": 40}, "boosting": {"max_iter": 50}}


class TestAvailableModels:

    def test_regression_includes_mars(self):
        assert "mars" in automl.available_models("regression")

    def test_classification_excludes_mars(self):
        models = automl.available_models("classification")
        assert "mars" not in models
        assert {"linear", "tree", "forest", "boosting"} <= set(models)

    def test_unknown_model_rejected(self):
        with pytest.raises(MLDataError, match="不可用模型"):
            automl.analyze(_regression_frame(), "强度", models=["xgboost"],
                           cv=3)

    def test_mars_rejected_for_classification(self):
        with pytest.raises(MLDataError, match="不可用模型"):
            automl.analyze(_classification_frame(), "判定", models=["mars"],
                           cv=3)


class TestAutoMLAnalyze:

    def test_regression_leaderboard_and_ranking(self):
        out = automl.analyze(_regression_frame(), "强度", cv=3,
                             model_params=FAST_PARAMS, random_state=7)
        assert out["analysis_type"] == "ml.automl"
        assert out["ranking_metric"] == "r2_mean"
        assert len(out["leaderboard"]) == 5
        ranks = [item["rank"] for item in out["leaderboard"]]
        assert ranks == [1, 2, 3, 4, 5]
        scores = [item["cv"]["r2_mean"] for item in out["leaderboard"]]
        assert scores == sorted(scores, reverse=True)
        assert out["best_model"] == out["leaderboard"][0]["model"]
        assert "推荐" in out["summary_text"]
        assert out["total_seconds"] > 0

    def test_regression_reproducible(self):
        a = automl.analyze(_regression_frame(), "强度", cv=3,
                           model_params=FAST_PARAMS, random_state=7)
        b = automl.analyze(_regression_frame(), "强度", cv=3,
                           model_params=FAST_PARAMS, random_state=7)
        assert a["best_model"] == b["best_model"]
        assert [i["cv"]["r2_mean"] for i in a["leaderboard"]] == pytest.approx(
            [i["cv"]["r2_mean"] for i in b["leaderboard"]])

    def test_classification_leaderboard(self):
        out = automl.analyze(_classification_frame(), "判定", cv=3,
                             model_params=FAST_PARAMS, random_state=7)
        assert out["ranking_metric"] == "accuracy_mean"
        assert len(out["leaderboard"]) == 4
        assert out["best_model"] != "mars"
        assert out["predictions"]
        assert {"actual", "predicted", "probability"} <= set(out["predictions"][0])
        assert out["best_pipeline"] is not None
        sample = _classification_frame().drop(columns=["判定"]).head(3)
        assert len(out["best_pipeline"].predict(sample)) == 3

    def test_manual_subset_matches_leaderboard_order(self):
        """AutoML 排名与人工单模型 CV 结果一致（同一折、同 seed）。"""
        from analysis.ml import evaluate, prep
        from sklearn.pipeline import Pipeline

        df = _regression_frame()
        out = automl.analyze(df, "强度", models=["linear", "tree"], cv=3,
                             random_state=11)
        prepared = prep.prepare_data(df, "强度", random_state=11)
        X = pd.concat([prepared["X_train"], prepared["X_test"]])
        y = pd.concat([prepared["y_train"], prepared["y_test"]])
        manual = {}
        for name in ("linear", "tree"):
            pipe = Pipeline([("prep", prepared["preprocessor"]),
                             ("model", automl.make_estimator(name, "regression"))])
            manual[name] = evaluate.cross_validation(
                pipe, X, y, "regression", cv=3, random_state=11)["summary"]["r2_mean"]
        expected = max(manual, key=lambda k: manual[k])
        assert out["best_model"] == expected
        assert out["leaderboard"][0]["cv"]["r2_mean"] == pytest.approx(
            manual[expected])

    def test_time_budget_skips_remaining_models(self):
        out = automl.analyze(_regression_frame(), "强度",
                             models=["linear", "forest", "tree"], cv=3,
                             model_params=FAST_PARAMS, time_budget_s=0.0,
                             random_state=7)
        assert len(out["leaderboard"]) == 1
        assert len(out["skipped"]) == 2
        assert "时间预算" in out["summary_text"]
