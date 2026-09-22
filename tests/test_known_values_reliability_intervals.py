"""可靠性区间已知值 — Weibull CI / ALT 外推区间 / KM CI（v4.2.0 P2-6）

来源:
- Fisher 信息矩阵参数 CI（Weibull 2P MLE）↔ lifelines WeibullAFTFitter 交叉验证
- Draper & Smith《Applied Regression Analysis》ch.1：均值置信区间 vs 单样本预测区间
- Kaplan-Meier 生存函数 CI（指数 Greenwood 形式，lifelines 实现）

覆盖:
1. 我方 Weibull CI 与 lifelines 一致（点估计 0.5%、区间端点 2% 内）
2. Weibull CI 覆盖率 ≈ 名义 95%（Type I 删失蒙特卡洛）
3. ALT 平均寿命 CI 覆盖率 ≈ 95%（修正后；旧实现用 ±1.96·se 忽略杠杆项）
4. KM CI 不变式：区间包含估计值、随样本量收窄
"""

import numpy as np
import pandas as pd
import pytest

from analysis.reliability.alt import ALTEngine
from analysis.reliability.survival import kaplan_meier
from analysis.reliability.weibull import WeibullAnalyzer
from tests.known_values import KnownValueCase, assert_close

_LIFELINES_CASE = KnownValueCase(
    case_id="weibull-ci-vs-lifelines",
    source="lifelines WeibullAFTFitter（同数据集交叉验证）",
    reference="β / η 点估计相差 ≤0.5%；95% CI 端点相差 ≤2%",
    rel_tol=0.02, abs_tol=1e-6,
    notes="两实现均用 log 尺度正态近似，端点应高度一致（实测差异 <1%）",
)

_WEIBULL_COVERAGE_CASE = KnownValueCase(
    case_id="weibull-ci-95-coverage",
    source="蒙特卡洛（固定种子，Weibull β=2、η=100，Type I 删失 150h）",
    reference="95% CI 覆盖率 ≥ 85%（名义 95%）",
    rel_tol=1e-9, abs_tol=0.12,
    notes="150 点 × 30% 截尾 × 150 次；实测 β=0.940、η=0.945",
)

_ALT_COVERAGE_CASE = KnownValueCase(
    case_id="alt-arrhenius-mean-life-ci-coverage",
    source="蒙特卡洛（固定种子，Arrhenius Ea=0.7eV，3 应力 × 5 样本）",
    reference="使用条件（25℃）平均寿命 95% CI 覆盖率 ≥ 88%（名义 95%）",
    rel_tol=1e-9, abs_tol=0.10,
    notes="寿命对数标准差 0.3；实测覆盖率 0.950",
)


class TestWeibullCiCrossValidation:
    def test_matches_lifelines(self):
        lifelines = pytest.importorskip("lifelines")
        from lifelines import WeibullAFTFitter

        rng = np.random.default_rng(5)
        n = 200
        true_times = rng.weibull(2.0, n) * 100.0
        censored = (rng.random(n) >= 0.25).astype(int)
        observed = np.where(censored == 1, true_times,
                            np.minimum(true_times, 140.0))

        result = WeibullAnalyzer().analyze(observed.tolist(),
                                           censored=censored.tolist())["result"]
        frame = pd.DataFrame({"T": observed, "E": censored})
        aft = WeibullAFTFitter().fit(frame, "T", "E")
        summary = aft.summary

        shape = float(np.exp(summary.loc[("rho_", "Intercept"), "coef"]))
        scale = float(np.exp(summary.loc[("lambda_", "Intercept"), "coef"]))
        shape_ci = np.exp([float(summary.loc[("rho_", "Intercept"), "coef lower 95%"]),
                           float(summary.loc[("rho_", "Intercept"), "coef upper 95%"])])
        scale_ci = np.exp([float(summary.loc[("lambda_", "Intercept"), "coef lower 95%"]),
                           float(summary.loc[("lambda_", "Intercept"), "coef upper 95%"])])

        assert result.beta == pytest.approx(shape, rel=0.005)
        assert result.eta == pytest.approx(scale, rel=0.005)
        ci = result.confidence_intervals
        assert_close(ci["beta"]["ci_lower"], shape_ci[0], _LIFELINES_CASE, context="β 下限")
        assert_close(ci["beta"]["ci_upper"], shape_ci[1], _LIFELINES_CASE, context="β 上限")
        assert_close(ci["eta"]["ci_lower"], scale_ci[0], _LIFELINES_CASE, context="η 下限")
        assert_close(ci["eta"]["ci_upper"], scale_ci[1], _LIFELINES_CASE, context="η 上限")
        assert lifelines is not None

    def test_ci_brackets_estimate_and_orders(self):
        rng = np.random.default_rng(7)
        observed = rng.weibull(2.0, 80) * 50.0
        result = WeibullAnalyzer().analyze(observed.tolist())["result"]
        for key, estimate in (("beta", result.beta), ("eta", result.eta)):
            ci = result.confidence_intervals[key]
            assert ci["ci_lower"] < estimate < ci["ci_upper"]


class TestWeibullCiCoverage:
    def test_coverage_of_true_parameters(self):
        rng = np.random.default_rng(11)
        engine = WeibullAnalyzer()
        reps = 150
        censor_time = 150.0
        covered_beta = covered_eta = 0
        for _ in range(reps):
            times = rng.weibull(2.0, 150) * 100.0
            observed = np.minimum(times, censor_time)
            censored = (times <= censor_time).astype(int)
            result = engine.analyze(observed.tolist(), censored=censored.tolist())["result"]
            ci = result.confidence_intervals
            covered_beta += int(ci["beta"]["ci_lower"] <= 2.0 <= ci["beta"]["ci_upper"])
            covered_eta += int(ci["eta"]["ci_lower"] <= 100.0 <= ci["eta"]["ci_upper"])

        rate_beta = covered_beta / reps
        rate_eta = covered_eta / reps
        assert_close(rate_beta, 0.95, _WEIBULL_COVERAGE_CASE, context="β 覆盖率")
        assert_close(rate_eta, 0.95, _WEIBULL_COVERAGE_CASE, context="η 覆盖率")
        assert rate_beta >= 0.85 and rate_eta >= 0.85


class TestAltIntervals:
    STRESS = np.array([358.15, 378.15, 398.15])       # 85 / 105 / 125 °C
    EA_TRUE = 0.7
    A_TRUE = 1e-6
    K_BOLTZMANN = 8.617333262145e-5

    def _true_use_life(self) -> float:
        return self.A_TRUE * np.exp(self.EA_TRUE / (self.K_BOLTZMANN * 298.15))

    def test_arrhenius_mean_life_ci_coverage(self):
        rng = np.random.default_rng(17)
        reps = 200
        covered = 0
        for _ in range(reps):
            true_life = self.A_TRUE * np.exp(
                self.EA_TRUE / (self.K_BOLTZMANN * self.STRESS))
            life = (true_life[:, None]
                    * np.exp(rng.normal(0, 0.3, size=(3, 5)))).ravel()
            result = ALTEngine.arrhenius_life(np.repeat(self.STRESS, 5), life,
                                              use_temp=25)
            covered += int(result["life_95ci_low"]
                           <= self._true_use_life()
                           <= result["life_95ci_high"])
        rate = covered / reps
        assert_close(rate, 0.95, _ALT_COVERAGE_CASE, context="平均寿命 CI 覆盖率")
        assert rate >= 0.88, f"覆盖率过低: {rate:.3f}"

    def test_prediction_interval_contains_confidence_interval(self):
        rng = np.random.default_rng(19)
        true_life = self.A_TRUE * np.exp(
            self.EA_TRUE / (self.K_BOLTZMANN * self.STRESS))
        life = (true_life[:, None] * np.exp(rng.normal(0, 0.3, size=(3, 5)))).ravel()
        result = ALTEngine.arrhenius_life(np.repeat(self.STRESS, 5), life, use_temp=25)

        assert result["life_95ci_low"] < result["life_at_use"] < result["life_95ci_high"]
        assert (result["life_pred_95ci_low"] <= result["life_95ci_low"]
                and result["life_pred_95ci_high"] >= result["life_95ci_high"])
        assert result["se_log_life"] > 0

    def test_inverse_power_law_and_eyring_intervals_ordered(self):
        rng = np.random.default_rng(23)
        stress = np.array([1.0, 1.5, 2.0])
        life = (1000.0 * stress[:, None] ** (-2.0)
                * np.exp(rng.normal(0, 0.2, size=(3, 4)))).ravel()
        power = ALTEngine.inverse_power_law(np.repeat(stress, 4), life, use_stress=0.8)
        assert power["life_95ci_low"] < power["life_at_use"] < power["life_95ci_high"]
        assert power["life_pred_95ci_low"] <= power["life_95ci_low"]

        temps = np.array([358.15, 378.15, 398.15])
        eyring_life = (1e5 / temps[:, None]
                       * np.exp(8000 / temps[:, None])
                       * np.exp(rng.normal(0, 0.2, size=(3, 4)))).ravel()
        eyring = ALTEngine.eyring(np.repeat(temps, 4), eyring_life, use_temp=25)
        assert eyring["life_95ci_low"] < eyring["life_at_use"] < eyring["life_95ci_high"]
        assert eyring["life_pred_95ci_low"] <= eyring["life_95ci_low"]


class TestKaplanMeierCiInvariants:
    def test_ci_brackets_survival_estimate(self):
        rng = np.random.default_rng(29)
        durations = pd.Series(rng.weibull(1.5, 120) * 200.0)
        events = pd.Series((rng.random(120) < 0.7).astype(int))
        result = kaplan_meier(durations, events, confidence_level=0.95)

        survival = result["survival_function"]
        lower = result["confidence_lower"]
        upper = result["confidence_upper"]
        assert len(lower) == len(survival) == len(upper)
        for estimate, lo, hi in zip(survival, lower, upper, strict=True):
            assert 0.0 <= lo <= estimate + 1e-9
            assert estimate - 1e-9 <= hi <= 1.0 + 1e-9

    def test_ci_narrows_with_sample_size(self):
        rng = np.random.default_rng(31)
        small = kaplan_meier(pd.Series(rng.weibull(1.5, 60) * 200.0),
                             pd.Series(np.ones(60)), confidence_level=0.95)
        large = kaplan_meier(pd.Series(rng.weibull(1.5, 1200) * 200.0),
                             pd.Series(np.ones(1200)), confidence_level=0.95)
        width_small = np.mean(np.array(small["confidence_upper"])
                              - np.array(small["confidence_lower"]))
        width_large = np.mean(np.array(large["confidence_upper"])
                              - np.array(large["confidence_lower"]))
        assert width_large < width_small
