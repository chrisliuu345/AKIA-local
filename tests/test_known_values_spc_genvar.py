"""SPC 已知值 — 广义方差 |S| 图（v4.2.0 P2-2）

来源: Montgomery《Introduction to Statistical Quality Control》ch.11
       b1 = Π(n−j)/(n−1)^p；b2 = Π(n−j)[Π(n−j+2) − Π(n−j)]/(n−1)^{2p}

覆盖:
1. p=2, n=10 的 b1/b2 手算闭式（b1 = 8/9，b2 = 2736/6561）
2. CL/UCL/LCL 与手算一致（n=10, p=2 时 LCL 下界截断为 0）
3. 方差放大的子组被检出
"""

import numpy as np
import pandas as pd
import pytest

from analysis.spc.gen_var import analyze as genvar_analyze
from analysis.spc.gen_var import generalized_variance_constants
from tests.known_values import KnownValueCase, assert_close

_CONST_CASE = KnownValueCase.with_preset(
    "montgomery-generalized-variance-constants", "Montgomery ch.11",
    preset="closed_form",
    reference="p=2, n=10 ⇒ b1 = 8/9 = 0.888…，b2 = 2736/6561 = 0.417…",
    notes="b1 = 9·8/9²; b2 = 72·(11·10 − 9·8)/9⁴",
)

_LIMIT_CASE = KnownValueCase.with_preset(
    "montgomery-generalized-variance-limits", "Montgomery ch.11",
    preset="rounded_6dp",
    reference="CL = b1·|S̄|，UCL = |S̄|(b1 + 3√b2)，LCL = max(0, |S̄|(b1 − 3√b2))",
)


def _make_data(scale_last: float = 1.0, seed: int = 5) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for g in range(10):
        scale = scale_last if g == 9 else 1.0
        block = rng.normal(size=(10, 2)) * scale
        for x, y in block:
            rows.append({"group": g, "x": x, "y": y})
    return pd.DataFrame(rows)


class TestGeneralizedVarianceConstants:
    def test_constants_match_hand_calculation(self):
        b1, b2 = generalized_variance_constants(n=10, p=2)
        assert_close(b1, 8 / 9, _CONST_CASE, context="b1")
        assert_close(b2, 2736 / 6561, _CONST_CASE, context="b2")

    def test_constants_require_enough_observations(self):
        with pytest.raises(ValueError):
            generalized_variance_constants(n=3, p=2)


class TestGeneralizedVarianceChart:
    def test_limits_match_hand_calculation(self):
        data = _make_data()
        result = genvar_analyze(data, ["x", "y"], subgroup_col="group")
        assert result["equal_subgroup_size"] is True
        assert result["subgroup_size"] == 10

        b1, b2 = 8 / 9, 2736 / 6561
        pooled_det = result["summary"]["pooled_det"]
        k = 3.0
        assert_close(result["genvar_chart"]["cl"], b1 * pooled_det,
                     _LIMIT_CASE, context="CL")
        assert_close(result["genvar_chart"]["ucl"],
                     pooled_det * (b1 + k * np.sqrt(b2)),
                     _LIMIT_CASE, context="UCL")
        assert result["genvar_chart"]["lcl"] == 0.0
        assert result["summary"]["b1"] == pytest.approx(b1, rel=1e-9)
        assert result["summary"]["b2"] == pytest.approx(b2, rel=1e-9)

    def test_uses_pooled_covariance_determinant(self):
        data = _make_data()
        result = genvar_analyze(data, ["x", "y"], subgroup_col="group")
        expected = []
        total_dof = 0
        pooled = np.zeros((2, 2))
        for _, group in data.groupby("group", sort=False):
            values = group[["x", "y"]].to_numpy(dtype=float)
            dof = len(values) - 1
            pooled += dof * np.cov(values, rowvar=False, ddof=1)
            total_dof += dof
            expected.append(abs(float(np.linalg.det(np.cov(values, rowvar=False, ddof=1)))))
        pooled /= total_dof
        assert_close(result["summary"]["pooled_det"], abs(float(np.linalg.det(pooled))),
                     _LIMIT_CASE, context="合并协方差行列式")
        assert result["genvar_chart"]["data"] == pytest.approx(expected, rel=1e-9, abs=1e-12)

    def test_equal_subgroup_size_mode(self):
        data = _make_data()
        flat = data[["x", "y"]]
        result = genvar_analyze(flat, ["x", "y"], subgroup_size=10)
        assert result["num_subgroups"] == 10
        assert result["genvar_chart"]["labels"][0] == "子组1"

    def test_variance_shift_detected(self):
        data = _make_data(scale_last=6.0)
        result = genvar_analyze(data, ["x", "y"], subgroup_col="group")
        rules = [v["rule"] for v in result["genvar_chart"]["violations"]]
        assert "above_ucl" in rules
        flagged = [v["label"] for v in result["genvar_chart"]["violations"]]
        assert "9" in flagged

    def test_validation_errors(self):
        data = _make_data()
        with pytest.raises(ValueError):
            genvar_analyze(data, ["x"], subgroup_col="group")
        with pytest.raises(ValueError):
            genvar_analyze(data, ["x", "y"])
        with pytest.raises(ValueError):
            genvar_analyze(data, ["x", "y"], subgroup_col="group", subgroup_size=10)
