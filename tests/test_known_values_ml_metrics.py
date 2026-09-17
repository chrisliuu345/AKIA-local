"""ML 评估指标已知值 — 回归与分类（v4.2.0 P1）。

来源: 指标定义（sklearn 用户指南）+ 手算闭式值。
本文件同时回归 v4.2.0 P1 预检发现的缺陷：数值类别 0/1 的混淆矩阵此前全 0。
"""

import numpy as np

from analysis.ml import evaluate
from tests.known_values import KnownValueCase, assert_allclose, assert_close

_REG_CASE = KnownValueCase.with_preset(
    "handcalc-regression-metrics", "指标定义（手算）", preset="closed_form",
    reference="y=[1,2,3], ŷ=[1,2,4]：SSE=1, SST=2",
)

_CLS_CASE = KnownValueCase.with_preset(
    "handcalc-classification-metrics", "指标定义（手算）", preset="closed_form",
    reference="y=[1,1,0,0], ŷ=[1,1,0,1]：accuracy=3/4",
    notes="数值标签场景，验证混淆矩阵标签类型一致性（P1 缺陷修复）",
)


class TestRegressionMetricsKnownValues:
    def test_exact_metrics(self):
        out = evaluate.regression_metrics([1, 2, 3], [1, 2, 4], n_features=1)
        assert_close(out["r2"], 0.5, _REG_CASE, context="R² = 1 − 1/2")
        assert_close(out["adj_r2"], 0.0, _REG_CASE, context="adj-R² = 0")
        assert_close(out["rmse"], np.sqrt(1.0 / 3.0), _REG_CASE, context="RMSE")
        assert_close(out["mae"], 1.0 / 3.0, _REG_CASE, context="MAE")
        assert_close(out["mape_pct"], 100.0 / 9.0, _REG_CASE, context="MAPE")


class TestClassificationMetricsKnownValues:
    def test_exact_metrics_and_confusion_matrix(self):
        out = evaluate.classification_metrics([1, 1, 0, 0], [1, 1, 0, 1])

        assert_close(out["accuracy"], 0.75, _CLS_CASE, context="accuracy = 3/4")
        assert_close(out["precision_weighted"], 5.0 / 6.0, _CLS_CASE,
                     context="weighted precision = (2/3 + 1)/2")
        assert_close(out["recall_weighted"], 0.75, _CLS_CASE,
                     context="weighted recall = (1 + 1/2)/2")
        assert_close(out["f1_weighted"], 11.0 / 15.0, _CLS_CASE,
                     context="weighted F1 = (0.8 + 2/3)/2")
        assert out["labels"] == ["0", "1"]
        assert_allclose(
            out["confusion_matrix"],
            [[1, 1], [0, 2]],
            _CLS_CASE,
            context="数值标签混淆矩阵（修复前为全 0）",
        )
