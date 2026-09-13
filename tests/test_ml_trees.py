"""v4.0.0 P1 — CART 分类回归树（剪枝 / 规则 / 重要性 / 端到端）。"""

import numpy as np
import pandas as pd
import pytest

from analysis.ml import trees
from analysis.ml.common import MLDataError


def _regression_frame(n=200, seed=11):
    rng = np.random.default_rng(seed)
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)
    df = pd.DataFrame({
        "直径": x1,
        "温度": x2,
        "设备": rng.choice(["A", "B", "C"], n),
        "强度": 3 * x1 + 2 * x2 + rng.normal(0, 0.4, n),
    })
    df.loc[df.index[:4], "温度"] = np.nan          # 缺失值应被流水线处理
    return df


def _classification_frame(n=240, seed=13):
    rng = np.random.default_rng(seed)
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)
    score = x1 + x2 + rng.normal(0, 0.5, n)
    return pd.DataFrame({
        "测量值": x1,
        "环境温度": x2,
        "产线": rng.choice(["L1", "L2"], n),
        "判定": np.where(score > 0, "OK", "NG"),
    })


class TestRegressionTree:

    def test_end_to_end_regression(self):
        out = trees.analyze(_regression_frame(), "强度",
                            features=["直径", "温度", "设备"], random_state=7)
        assert out["analysis_type"] == "ml.tree"
        assert out["task"] == "regression"
        assert out["metrics"]["test"]["r2"] > 0.8
        assert out["metrics"]["test"]["rmse"] < 1.5
        assert out["cv"]["folds"] == 5
        assert out["cv"]["r2_mean"] > 0.75
        assert out["residuals"] is not None
        assert "CART" in out["summary_text"]

    def test_importances_and_rules(self):
        out = trees.analyze(_regression_frame(), "强度", random_state=7)
        assert len(out["importances"]) == len(out["encoded_features"])
        total = sum(item["importance"] for item in out["importances"])
        assert total == pytest.approx(1.0, abs=1e-6)
        # 直径/温度 是真实驱动变量，重要性应排前列
        top = {item["feature"] for item in out["importances"][:2]}
        assert top & {"直径", "温度"}
        assert out["rules"], "规则导出不应为空"
        assert any("直径" in line or "温度" in line for line in out["rules"])

    def test_deterministic_with_same_seed(self):
        a = trees.analyze(_regression_frame(), "强度", random_state=5)
        b = trees.analyze(_regression_frame(), "强度", random_state=5)
        assert a["metrics"]["test"]["r2"] == pytest.approx(b["metrics"]["test"]["r2"])

    def test_auto_prune_runs(self):
        out = trees.analyze(_regression_frame(), "强度", auto_prune=True,
                            random_state=9)
        assert out["params"]["auto_prune"] is True
        assert out["params"]["ccp_alpha"] >= 0.0
        assert out["metrics"]["test"]["r2"] > 0.5

    def test_max_depth_limits_tree(self):
        out = trees.analyze(_regression_frame(), "强度", max_depth=2,
                            random_state=3)
        assert out["params"]["max_depth"] == 2
        assert len(out["rules"]) <= trees.DEFAULT_MAX_RULES


class TestClassificationTree:

    def test_end_to_end_classification(self):
        out = trees.analyze(_classification_frame(), "判定",
                            features=["测量值", "环境温度", "产线"],
                            random_state=7)
        assert out["task"] == "classification"
        assert out["metrics"]["test"]["accuracy"] >= 0.8
        assert out["metrics"]["test"]["f1_weighted"] >= 0.8
        assert out["roc"] is not None and out["roc"]["auc"] >= 0.8
        assert out["residuals"] is None
        cm = np.asarray(out["metrics"]["test"]["confusion_matrix"])
        assert cm.sum() == len(out["predictions"])
        assert any("accuracy_mean" in k for k in out["cv"])

    def test_predictions_include_probability(self):
        out = trees.analyze(_classification_frame(), "判定", random_state=7)
        assert {"actual", "predicted", "probability"} <= set(out["predictions"][0])
        proba = [row["probability"] for row in out["predictions"]]
        assert all(0.0 <= p <= 1.0 for p in proba)

    def test_missing_and_categorical_handled(self):
        df = _classification_frame()
        df.loc[df.index[:5], "环境温度"] = np.nan
        df.loc[df.index[:3], "产线"] = np.nan
        out = trees.analyze(df, "判定", random_state=7)
        assert out["metrics"]["test"]["accuracy"] > 0.7
        assert out["prep_summary"]["missing_cells"] > 0


class TestErrors:

    def test_too_few_rows(self):
        df = _regression_frame(n=15)
        with pytest.raises(MLDataError, match="有效样本不足"):
            trees.analyze(df, "强度")

    def test_empty_frame(self):
        with pytest.raises(MLDataError, match="数据表为空"):
            trees.analyze(pd.DataFrame(), "强度")
