"""数值鲁棒性契约测试（v4.2.0 P3-2）

契约：退化/病态输入必须「不崩溃」，且只允许两种出口——
1. 结构化 ``error`` 字段（可读消息，供 UI 提示）；
2. 明确异常（消息可读，说明缺什么）。
禁止：返回 NaN 污染的结果、无限大但被当作真实结果的能力指数、静默错值。

覆盖: 规格限倒置 / 波动相对公差可忽略 / 常量与含缺测控制图 /
      极大数值尺度 / 秩亏协方差 / 子组退化 / 单类别分类 / 零方差 DOE / 单操作员 MSA
"""

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from analysis.capability import non_normal_cap, normal_cap
from analysis.doe.factorial import analyze_factorial
from analysis.ml import automl
from analysis.ml.common import MLDataError
from analysis.msa import gage_rr
from analysis.spc import imr, xbar_r
from analysis.spc.change_point import detect
from analysis.spc.gen_var import analyze as genvar_analyze
from analysis.spc.mewma import analyze as mewma_analyze
from analysis.time_series import exponential_smoothing


class TestSpecLimits:
    def test_inverted_limits_return_error(self):
        data = pd.Series(np.random.default_rng(0).normal(0, 1, 60))
        for module in (normal_cap, non_normal_cap):
            result = module.analyze(data, usl=1.0, lsl=2.0)
            assert "上规格限" in result["error"]
            assert "capability" not in result, "规格限非法时不得输出能力指数"

    def test_equal_limits_return_error(self):
        data = pd.Series(np.random.default_rng(1).normal(0, 1, 60))
        result = normal_cap.analyze(data, usl=1.0, lsl=1.0)
        assert "上规格限" in result["error"]

    def test_degenerate_spread_returns_error(self):
        """σ≈0（数值噪声级）时 Cp 可达 1e12 并被评 A+，必须拦截。"""
        noisy_constant = pd.Series([1.0 + 1e-13 * i for i in range(40)])
        for module in (normal_cap, non_normal_cap):
            result = module.analyze(noisy_constant, usl=2.0, lsl=0.0)
            assert "可忽略" in result["error"]
            assert "capability" not in result

    def test_normal_variation_still_analysed(self):
        """回归守卫：正常波动不能被误判为退化。"""
        data = pd.Series(np.random.default_rng(2).normal(0, 0.5, 200))
        result = normal_cap.analyze(data, usl=3.0, lsl=-3.0)
        assert "error" not in result
        assert result["capability"]["cp"] > 0


class TestControlChartDegeneracies:
    def test_constant_series_collapses_limits(self):
        result = imr.analyze(pd.Series([5.0] * 30))
        assert result["summary"]["x_bar"] == 5.0
        assert result["summary"]["sigma_hat"] == 0.0
        assert result["i_chart"]["ucl"] == result["i_chart"]["lcl"] == 5.0
        # 零变异本身即判异（Nelson 规则 7/8 系列"波动过小"），故允许有规则级告警，
        # 但不得出现 "above_ucl" 这类越限误报
        rules = {v.get("rule") for v in result["i_chart"]["violations"]}
        assert "above_ucl" not in rules
        assert all(isinstance(r, int) for r in rules), f"非规则级告警: {rules}"

    def test_missing_values_keep_gap_and_finite_summary(self):
        series = pd.Series([1.0, np.nan, 2.0, 3.0, np.nan, 5.0, 6.0])
        result = imr.analyze(series)
        assert np.isnan(result["i_chart"]["data"][1]), "缺测点应保留为空隙"
        assert np.isfinite(result["summary"]["x_bar"])
        assert np.isfinite(result["summary"]["sigma_hat"])
        assert result["summary"]["sigma_hat"] > 0

    def test_huge_scale_values_stay_finite(self):
        values = pd.Series(np.linspace(1e12, 1e12 + 10.0, 40))
        result = imr.analyze(values)
        assert np.isfinite(result["i_chart"]["ucl"])
        assert result["i_chart"]["ucl"] > result["i_chart"]["cl"]
        assert np.isfinite(result["mr_chart"]["ucl"])

    def test_equal_subgroups_do_not_crash(self):
        result = xbar_r.analyze(pd.Series([1.0] * 30), subgroup_size=3)
        assert result["num_subgroups"] == 10
        assert all(np.isfinite([result["r_chart"]["ucl"]])
                   if isinstance(result.get("r_chart"), dict) else [True])


class TestMultivariateDegeneracies:
    COLLINEAR = pd.DataFrame({"a": np.arange(20.0), "b": np.arange(20.0) * 2})

    def test_mewma_collinear_columns_use_ridge(self):
        result = mewma_analyze(self.COLLINEAR, ["a", "b"])
        assert all(np.isfinite(result["mewma_chart"]["data"]))

    def test_mewma_too_few_rows_raises_clear_error(self):
        frame = pd.DataFrame({"a": [1.0, 2.0], "b": [2.0, 3.0]})
        with pytest.raises(ValueError, match="数据量不足"):
            mewma_analyze(frame, ["a", "b"])

    def test_genvar_singular_subgroup_returns_zero_determinant(self):
        frame = pd.DataFrame({
            "g": [1] * 5 + [2] * 5,
            "a": [1.0] * 10,
            "b": [1.0] * 10,
        })
        result = genvar_analyze(frame, ["a", "b"], subgroup_size=5)
        assert result["genvar_chart"]["data"] == [0.0, 0.0]
        assert result["genvar_chart"]["violations"] == []

    def test_genvar_subgroup_too_small_raises(self):
        frame = pd.DataFrame({"a": [1.0, 2.0, 3.0, 4.0], "b": [1.0, 4.0, 9.0, 16.0]})
        with pytest.raises(ValueError):
            genvar_analyze(frame, ["a", "b"], subgroup_size=2)

    def test_changepoint_all_missing_raises(self):
        with pytest.raises(ValueError, match="序列为空"):
            detect(np.full(20, np.nan))


class TestStudyDegeneracies:
    def test_gage_rr_single_operator_raises(self):
        frame = pd.DataFrame({
            "part": [1, 2, 3, 1, 2, 3],
            "op": ["A"] * 6,
            "meas": [1.0, 2.0, 3.0, 1.1, 2.1, 3.1],
        })
        with pytest.raises(ValueError, match="操作员"):
            gage_rr.analyze_crossed(frame, "meas", "part", "op")

    def test_gage_rr_zero_variation_returns_zeros(self):
        frame = pd.DataFrame({
            "part": [1, 2, 3] * 4,
            "op": ["A", "B"] * 6,
            "meas": [1.0] * 12,
        })
        result = gage_rr.analyze_crossed(frame, "meas", "part", "op")
        assert result["design"]["operators"] == 2
        components = result["variance_components"]
        assert all(value == 0.0 for value in components.values())
        # 未提供公差时 grr_pct_tol 为 None（语义正确），仅校验其余百分比
        numeric = [v for v in result["percentages"].values() if v is not None]
        assert all(np.isfinite(numeric))
        assert result["ndc"] == 0

    def test_doe_zero_variance_response_returns_grand_mean(self):
        frame = pd.DataFrame({
            "A": [-1, 1, -1, 1],
            "B": [-1, -1, 1, 1],
            "y": [5.0, 5.0, 5.0, 5.0],
        })
        result = analyze_factorial(frame, "y", ["A", "B"])
        assert result["grand_mean"] == 5.0
        assert all(np.isfinite([result["grand_mean"]]))

    def test_automl_single_class_raises_clear_error(self):
        frame = pd.DataFrame({
            "a": np.arange(40.0),
            "b": np.arange(40.0) * 2,
            "y": [0] * 40,
        })
        with pytest.raises(MLDataError, match="至少需要 2 个类别"):
            automl.analyze(frame, "y", features=["a", "b"], task="classification")

    def test_exponential_smoothing_constant_series(self):
        result = exponential_smoothing.analyze(pd.Series([3.0] * 40))
        assert "error" not in result or result.get("error") is None
        forecast = result.get("forecast") or []
        assert all(np.isfinite(forecast))


class TestNumericalHygiene:
    """结果里不应出现"未标注的 NaN 污染"。"""

    def test_capability_indices_finite_for_normal_data(self):
        data = pd.Series(np.random.default_rng(3).normal(10, 1, 300))
        result = normal_cap.analyze(data, usl=13, lsl=7)
        cap = result["capability"]
        for key in ("cp", "cpk", "pp", "ppk", "ppm_total"):
            assert np.isfinite(cap[key]), f"{key} 非有限值"
        assert 0 < cap["cpk"] < 10

    def test_cpk_matches_closed_form(self):
        """Cp/Cpk 闭式核对（已知值口径的最小回归守卫）。"""
        data = pd.Series([9.0, 10.0, 11.0, 10.0, 10.0])
        result = normal_cap.analyze(data, usl=13.0, lsl=7.0)
        mean = float(np.mean(data))
        std = float(np.std(data, ddof=1))
        expected_cpk = min((13.0 - mean) / (3 * std), (mean - 7.0) / (3 * std))
        assert result["capability"]["ppk"] == pytest.approx(expected_cpk, abs=1e-4)
        # 引擎输出保留 6 位小数
        assert result["summary"]["std_overall"] == pytest.approx(std, abs=1e-6)

    def test_mewma_t2_never_negative(self):
        rng = np.random.default_rng(4)
        frame = pd.DataFrame(rng.normal(size=(80, 2)), columns=["x", "y"])
        result = mewma_analyze(frame, ["x", "y"])
        assert min(result["mewma_chart"]["data"]) >= 0.0
        assert all(np.isfinite(result["mewma_chart"]["data"]))

    def test_boxcox_shift_handles_non_positive_values(self):
        """非正态能力：数据含 0/负值时 Box-Cox 走平移分支，结果仍有限。"""
        rng = np.random.default_rng(5)
        data = pd.Series(rng.normal(0.0, 1.0, 200))
        result = non_normal_cap.analyze(data, usl=4.0, lsl=-4.0, method="box_cox")
        assert "error" not in result
        assert np.isfinite(result["capability"]["ppk"])
        assert result["summary"]["skewness"] == pytest.approx(
            float(stats.skew(data.to_numpy())), abs=1e-6)


class TestNonFiniteInputs:
    """2026-09-28 质量审查：缺失值与非有限值（±inf）必须先净化再进算法。

    旧实现只做 ``dropna()``，±inf 会穿透并在 scipy/statsmodels/matplotlib 内部
    抛底层报错（如 "autodetected range ... is not finite"、"cannot convert float
    NaN to integer"），用户无法判断是数据问题还是软件问题。
    """

    @staticmethod
    def _series_with_bad_values() -> pd.Series:
        rng = np.random.default_rng(17)
        values = pd.Series(rng.normal(10.0, 1.0, 120))
        values[[5, 60]] = np.inf
        values[[3, 40, 99]] = np.nan
        return values

    def test_sanitize_series_drops_non_finite(self):
        from analysis._sanitize import sanitize_series

        cleaned = sanitize_series(self._series_with_bad_values())
        assert len(cleaned) == 120 - 5
        assert np.isfinite(cleaned.to_numpy()).all()
        assert list(cleaned.index) == list(range(len(cleaned)))

    def test_time_series_modules_accept_non_finite(self):
        from analysis.spc import residual_chart
        from analysis.time_series import acf_pacf, arima, exponential_smoothing, seasonal_decomposition

        series = self._series_with_bad_values()
        fitted = arima.analyze(series, order=(1, 0, 0), auto_select=False)
        assert "error" not in fitted
        for module in (exponential_smoothing, seasonal_decomposition):
            result = module.analyze(series)
            assert "error" not in result, result.get("error")
        assert acf_pacf.compute_acf(series)["acf_values"]
        assert "error" not in residual_chart.analyze(series, order=(1, 0, 0), auto_select=False)

    def test_count_charts_accept_missing_and_infinite(self):
        from analysis.spc import c_chart, np_chart, p_chart, u_chart

        counts = pd.Series([10, 12, np.nan, 8, np.inf, 9, 10, 12, 7, 9, 11, 8])
        samples = pd.Series([100] * 12, dtype=float)
        assert c_chart.analyze(counts)["num_subgroups"] == 10
        assert np_chart.analyze(counts, 100)["num_subgroups"] == 10
        assert p_chart.analyze(counts, samples)["num_subgroups"] == 10
        assert u_chart.analyze(counts, samples / 20)["num_subgroups"] == 10

    def test_count_chart_reports_negative_values(self):
        from analysis.spc import c_chart

        with pytest.raises(ValueError, match="非负数"):
            c_chart.analyze(pd.Series([1, -2, 3, 4]))

    def test_capability_modules_accept_non_finite(self):
        from analysis.capability import non_normal_cap, sixpack

        series = self._series_with_bad_values()
        assert "error" not in sixpack.analyze(series, usl=12.0, lsl=8.0)
        assert "error" not in non_normal_cap.analyze(series, usl=12.0, lsl=8.0)

    def test_hypothesis_and_reliability_accept_non_finite(self):
        from analysis.hypothesis import t_tests, variance_tests
        from analysis.reliability import survival

        series = self._series_with_bad_values()
        assert "error" not in t_tests.one_sample(series, 10.0)
        assert "error" not in variance_tests.variance_tests(series, series * 1.05)
        events = pd.Series([1] * len(series))
        assert "error" not in survival.kaplan_meier(series, events)
