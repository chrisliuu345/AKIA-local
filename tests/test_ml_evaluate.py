"""v4.0.0 P1 — 模型评估层（指标 / CV / 学习曲线 / ROC / 残差）。"""

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LinearRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)

from analysis.ml import evaluate
from analysis.ml.common import TASK_CLASSIFICATION, TASK_REGRESSION, MLDataError


@pytest.fixture
def regression_data():
    rng = np.random.default_rng(3)
    X = pd.DataFrame({"x1": rng.normal(size=120), "x2": rng.normal(size=120)})
    y = pd.Series(2 * X["x1"] - 1.5 * X["x2"] + rng.normal(0, 0.2, 120))
    return X, y


@pytest.fixture
def classification_data():
    rng = np.random.default_rng(5)
    X = pd.DataFrame({"x1": rng.normal(size=150), "x2": rng.normal(size=150)})
    y = pd.Series(np.where(X["x1"] + X["x2"] > 0, "OK", "NG"))
    return X, y


class TestRegressionMetrics:

    def test_matches_sklearn(self):
        rng = np.random.default_rng(1)
        y_true = rng.normal(size=40)
        y_pred = y_true + rng.normal(0, 0.5, 40)
        out = evaluate.regression_metrics(y_true, y_pred, n_features=3)
        assert out["r2"] == pytest.approx(r2_score(y_true, y_pred))
        assert out["rmse"] == pytest.approx(np.sqrt(mean_squared_error(y_true, y_pred)))
        assert out["mae"] == pytest.approx(mean_absolute_error(y_true, y_pred))
        expected_adj = 1 - (1 - out["r2"]) * (len(y_true) - 1) / (len(y_true) - 3 - 1)
        assert out["adj_r2"] == pytest.approx(expected_adj)

    def test_mape_skips_zero_targets(self):
        out = evaluate.regression_metrics([0, 10], [1, 11], n_features=1)
        assert out["mape_pct"] == pytest.approx(10.0)
        assert evaluate.regression_metrics([0, 0], [1, 2])["mape_pct"] is None


class TestClassificationMetrics:

    def test_matches_sklearn(self):
        y_true = ["OK", "NG", "OK", "OK", "NG"]
        y_pred = ["OK", "OK", "OK", "NG", "NG"]
        scores = np.array([[0.9, 0.1], [0.4, 0.6], [0.8, 0.2],
                           [0.45, 0.55], [0.2, 0.8]])
        out = evaluate.classification_metrics(y_true, y_pred, y_score=scores)
        assert out["accuracy"] == pytest.approx(accuracy_score(y_true, y_pred))
        assert out["f1_weighted"] == pytest.approx(
            f1_score(y_true, y_pred, average="weighted"))
        assert out["confusion_matrix"] == confusion_matrix(
            y_true, y_pred, labels=out["labels"]).tolist()
        assert out["labels"] == ["NG", "OK"]
        assert out["auc"] is not None and 0.0 <= out["auc"] <= 1.0

    def test_separable_scores_auc_high(self):
        y_true = ["NG"] * 20 + ["OK"] * 20
        scores = np.array([[0.8, 0.2]] * 20 + [[0.1, 0.9]] * 20)
        out = evaluate.classification_metrics(
            y_true, ["NG"] * 20 + ["OK"] * 20, y_score=scores)
        assert out["auc"] == pytest.approx(1.0)
        assert out["auc_kind"] == "binary"

    def test_multiclass_auc_ovr(self):
        labels = np.array(["A", "B", "C"] * 20)
        scores = np.full((60, 3), 0.1)
        scores[np.arange(60), [0, 1, 2] * 20] = 0.8
        out = evaluate.classification_metrics(labels, labels, y_score=scores)
        assert out["auc_kind"] == "ovr_weighted"
        assert out["auc"] == pytest.approx(1.0)

    def test_unknown_task_rejected(self):
        with pytest.raises(MLDataError, match="未知任务类型"):
            evaluate.compute_metrics("clustering", [1], [1])


class TestCrossValidation:

    def test_regression_cv_folds_and_summary(self, regression_data):
        from sklearn.pipeline import Pipeline
        X, y = regression_data
        pipe = Pipeline([("model", LinearRegression())])
        out = evaluate.cross_validation(pipe, X, y, TASK_REGRESSION, cv=5)
        assert out["summary"]["folds"] == 5
        assert len(out["scores"]["r2"]) == 5
        assert out["summary"]["r2_mean"] > 0.8
        assert out["summary"]["rmse_mean"] < 1.0

    def test_classification_cv_reduces_folds_for_small_classes(self, classification_data):
        from sklearn.pipeline import Pipeline
        from sklearn.tree import DecisionTreeClassifier
        X, y = classification_data
        pipe = Pipeline([("model", DecisionTreeClassifier(random_state=1))])
        out = evaluate.cross_validation(pipe, X, y, TASK_CLASSIFICATION, cv=20)
        assert out["summary"]["folds"] == min(20, int(y.value_counts().min()))
        assert 0.0 <= out["summary"]["accuracy_mean"] <= 1.0

    def test_learning_curve_shapes(self, regression_data):
        from sklearn.pipeline import Pipeline
        X, y = regression_data
        pipe = Pipeline([("model", LinearRegression())])
        out = evaluate.learning_curve_data(pipe, X, y, TASK_REGRESSION,
                                           cv=3, train_sizes=4)
        assert len(out["train_sizes"]) == 4
        assert len(out["train_mean"]) == len(out["valid_mean"]) == 4


class TestRocAndResiduals:

    def test_roc_binary_and_multiclass_none(self):
        y_true = ["NG"] * 10 + ["OK"] * 10
        scores = np.linspace(0.05, 0.95, 20)
        out = evaluate.roc_curve_data(y_true, scores)
        assert out["positive_label"] == "OK"
        assert len(out["fpr"]) == len(out["tpr"]) == len(out["thresholds"])
        assert 0.0 <= out["auc"] <= 1.0
        assert evaluate.roc_curve_data(["A", "B", "C"], [0.1, 0.2, 0.3]) is None

    def test_residual_diagnostics(self):
        y_true = np.array([10, 12, 14, 16, 18], dtype=float)
        out = evaluate.residual_diagnostics(y_true, y_true)
        assert out["mean"] == pytest.approx(0.0)
        assert out["std"] == pytest.approx(0.0)
        assert out["outliers_3sigma"] == 0

        biased = evaluate.residual_diagnostics(y_true, y_true + 2)
        assert biased["mean"] == pytest.approx(-2.0)
