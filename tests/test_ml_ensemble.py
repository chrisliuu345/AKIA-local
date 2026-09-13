"""v4.0.0 P2 — 随机森林与梯度提升（OOB / 重要性 / backend 降级）。"""

import numpy as np
import pandas as pd
import pytest

from analysis.ml import boosting, forest
from analysis.ml.common import MLDataError


def _regression_frame(n=220, seed=21):
    rng = np.random.default_rng(seed)
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)
    return pd.DataFrame({
        "压力": x1,
        "温度": x2,
        "产线": rng.choice(["L1", "L2", "L3"], n),
        "屈服强度": 4 * x1 - 2 * x2 + np.sin(x1 * 2) + rng.normal(0, 0.5, n),
    })


def _classification_frame(n=240, seed=23):
    rng = np.random.default_rng(seed)
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)
    score = 1.5 * x1 + x2 + rng.normal(0, 0.6, n)
    return pd.DataFrame({
        "尺寸": x1,
        "湿度": x2,
        "班次": rng.choice(["早", "晚"], n),
        "判定": np.where(score > 0, "PASS", "FAIL"),
    })


class TestRandomForest:

    def test_regression_with_oob_and_importances(self):
        out = forest.analyze(_regression_frame(), "屈服强度",
                             features=["压力", "温度", "产线"],
                             n_estimators=60, random_state=5)
        assert out["analysis_type"] == "ml.forest"
        assert out["metrics"]["test"]["r2"] > 0.8
        assert out["oob_score"] is not None and out["oob_score"] > 0.5
        assert len(out["importances"]) == len(out["encoded_features"])
        assert sum(i["importance"] for i in out["importances"]) == pytest.approx(1.0)
        assert len(out["permutation_importance"]) == 3
        assert {i["feature"] for i in out["permutation_importance"]} == \
            {"压力", "温度", "产线"}
        assert out["cv"]["folds"] == 5
        assert "随机森林" in out["summary_text"]

    def test_classification_probability_and_auc(self):
        out = forest.analyze(_classification_frame(), "判定",
                             n_estimators=60, random_state=5)
        assert out["metrics"]["test"]["accuracy"] > 0.8
        assert out["roc"] is not None and out["roc"]["auc"] > 0.8
        assert {"actual", "predicted", "probability"} <= set(out["predictions"][0])

    def test_deterministic_with_same_seed(self):
        a = forest.analyze(_regression_frame(), "屈服强度", n_estimators=40,
                           random_state=3)
        b = forest.analyze(_regression_frame(), "屈服强度", n_estimators=40,
                           random_state=3)
        assert a["metrics"]["test"]["r2"] == pytest.approx(b["metrics"]["test"]["r2"])

    def test_empty_frame(self):
        with pytest.raises(MLDataError, match="数据表为空"):
            forest.analyze(pd.DataFrame(), "屈服强度")


class TestBoosting:

    def test_sklearn_regression(self):
        out = boosting.analyze(_regression_frame(), "屈服强度",
                               features=["压力", "温度", "产线"],
                               max_iter=80, random_state=5)
        assert out["analysis_type"] == "ml.boosting"
        assert out["backend"] == "sklearn"
        assert out["model"] == "HistGradientBoosting"
        assert out["metrics"]["test"]["r2"] > 0.8
        assert out["importances"], "置换重要性不应为空"
        assert out["params"]["max_iter"] == 80

    def test_sklearn_classification(self):
        out = boosting.analyze(_classification_frame(), "判定",
                               max_iter=80, random_state=5)
        assert out["metrics"]["test"]["accuracy"] > 0.8
        assert out["roc"] is not None and out["roc"]["auc"] > 0.8

    def test_auto_backend_falls_back_without_xgboost(self):
        out = boosting.analyze(_regression_frame(), "屈服强度",
                               backend="auto", max_iter=40, random_state=5)
        assert out["backend"] == "sklearn"

    def test_xgboost_backend_error_when_missing(self):
        if boosting.xgboost_available():
            pytest.skip("本环境已安装 xgboost，跳过缺失降级用例")
        with pytest.raises(MLDataError, match="未安装 XGBoost"):
            boosting.analyze(_regression_frame(), "屈服强度", backend="xgboost")

    def test_invalid_backend(self):
        with pytest.raises(MLDataError, match="不支持的 backend"):
            boosting.analyze(_regression_frame(), "屈服强度", backend="lightgbm")
