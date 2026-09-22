"""SPC 已知值 — MEWMA（v4.2.0 P2-1）

来源:
- Lowry, Woodall, Champ & Rigdon (1992), Technometrics 34(1):46-53
- Montgomery《Introduction to Statistical Quality Control》ch.11（多元 EWMA）

覆盖:
1. 递推式与手算值一致（r = 0.5）
2. Σ_Z = r/(2−r)·Σ ⇒ T²_1 = r(2−r)·(x₁−μ₀)ᵀΣ⁻¹(x₁−μ₀)（闭式）
3. r = 1 退化为 Hotelling 个体观测 T² 图（与 hotelling.py 逐点一致）
4. 在控数据平均 T² ≈ p；均值漂移可稳定检出（固定种子蒙特卡洛）
"""

import numpy as np
import pandas as pd
import pytest

from analysis.spc.hotelling import analyze as hotelling_analyze
from analysis.spc.mewma import analyze as mewma_analyze
from tests.known_values import KnownValueCase, assert_allclose, assert_close

_RECURSION_CASE = KnownValueCase.with_preset(
    "lowry1992-mewma-recursion", "Lowry et al. (1992) / Montgomery ch.11",
    preset="rounded_6dp",
    reference="4 点 (0,0)(1,1)(2,0)(3,1)，r=0.5：Z=(-0.75,-0.25)(-0.625,0.125)(-0.0625,-0.1875)(0.71875,0.15625)",
    notes="Z_i = r(x_i−μ₀) + (1−r)Z_{i−1}, Z_0=0，μ₀ 为样本均值 (1.5, 0.5)",
)

_SCALE_CASE = KnownValueCase.with_preset(
    "lowry1992-sigma-z-scaling", "Lowry et al. (1992)",
    preset="rounded_6dp",
    reference="精确形式下 T²_1 = (x₁−μ₀)ᵀΣ⁻¹(x₁−μ₀)（r 相消）",
    notes="Σ_Z(1) = r²Σ ⇒ T²_1 = Z_1ᵀ(r²Σ)⁻¹Z_1 = (x₁−μ₀)ᵀΣ⁻¹(x₁−μ₀)",
)

_MC_CASE = KnownValueCase(
    case_id="mewma-in-control-mean-t2",
    source="蒙特卡洛（固定种子，p=2）",
    reference="在控多元正态数据稳态段平均 T² ≈ p = 2",
    rel_tol=0.03, abs_tol=0.06,
    notes="400 组 × 60 点，r=0.1，取每条第 21 点之后的稳态段均值",
)

DATA = pd.DataFrame({
    "x": [0.0, 1.0, 2.0, 3.0],
    "y": [0.0, 1.0, 0.0, 1.0],
})


class TestMewmaRecursion:
    def test_recursion_matches_hand_calculation(self):
        result = mewma_analyze(DATA, ["x", "y"], lambda_=0.5)
        expected_z = [
            [-0.75, -0.25],
            [-0.625, 0.125],
            [-0.0625, -0.1875],
            [0.71875, 0.15625],
        ]
        assert_allclose(result["mewma_chart"]["z_values"], expected_z,
                        _RECURSION_CASE, context="Z 递推手算")
        assert_close(result["summary"]["steady_state_factor"], 1 / 3,
                     _RECURSION_CASE, context="r/(2−r)")
        assert_close(result["summary"]["first_sample_factor"], 0.75,
                     _RECURSION_CASE, context="r(2−r)")
        assert result["mewma_chart"]["cl"] == 0.0


class TestMewmaClosedForm:
    def test_first_sample_t2_closed_form(self):
        result = mewma_analyze(DATA, ["x", "y"], lambda_=0.5)
        X = DATA[["x", "y"]].to_numpy(dtype=float)
        mu0 = X.mean(axis=0)
        sigma = np.cov(X, rowvar=False, ddof=1)
        deviation = X[0] - mu0
        expected = float(deviation @ np.linalg.inv(sigma) @ deviation)
        assert_close(result["mewma_chart"]["data"][0], expected,
                     _SCALE_CASE, context="T²_1 闭式（精确 Σ_Z(i)）")

    def test_steady_state_mode_shrinks_early_points(self):
        """稳态 Σ_Z 会把早期点 T² 压小（Montgomery 查表形式的行为）。"""
        exact = mewma_analyze(DATA, ["x", "y"], lambda_=0.5, variance="exact")
        steady = mewma_analyze(DATA, ["x", "y"], lambda_=0.5,
                               variance="steady_state")
        assert steady["mewma_chart"]["data"][0] < exact["mewma_chart"]["data"][0]
        assert steady["summary"]["variance"] == "steady_state"
        assert exact["summary"]["variance"] == "exact"

    def test_limits_follow_montgomery_individual_formula(self):
        from scipy import stats

        m, p, alpha = len(DATA), 2, 0.0027
        result = mewma_analyze(DATA, ["x", "y"], lambda_=0.5, alpha=alpha)
        f_crit = stats.f.ppf(1 - alpha, p, m - p)
        expected_ucl = p * (m - 1) * (m + 1) / (m * (m - p)) * f_crit
        assert_close(result["mewma_chart"]["ucl"], expected_ucl,
                     _SCALE_CASE, context="UCL（个体观测 F 形式）")

        chi2_result = mewma_analyze(DATA, ["x", "y"], lambda_=0.5,
                                    alpha=alpha, ucl_method="chi2")
        assert_close(chi2_result["mewma_chart"]["ucl"],
                     float(stats.chi2.ppf(1 - alpha, p)),
                     _SCALE_CASE, context="UCL（χ² 形式）")


class TestMewmaReducesToHotelling:
    """r = 1 时 MEWMA 即 Hotelling 个体观测 T² 图（Montgomery ch.11）。"""

    DATA5 = pd.DataFrame({
        "x": [-2.0, -1.0, 0.0, 1.0, 2.0],
        "y": [1.0, -2.0, 0.0, 2.0, -1.0],
    })

    def test_t2_series_and_ucl_match_hotelling(self):
        hotelling = hotelling_analyze(self.DATA5, ["x", "y"])
        mewma = mewma_analyze(self.DATA5, ["x", "y"], lambda_=1.0)

        assert_allclose(mewma["mewma_chart"]["data"],
                        hotelling["t2_chart"]["data"],
                        _SCALE_CASE, context="r=1 → T² 序列")
        assert_close(mewma["mewma_chart"]["ucl"],
                     float(np.atleast_1d(hotelling["t2_chart"]["ucl"])[0]),
                     _SCALE_CASE, context="r=1 → UCL")


class TestMewmaBehaviour:
    """行为验证 — 按控制图规范以「Phase I 基线 → Phase II 监控」口径进行。"""

    def test_in_control_mean_t2_matches_p_with_known_parameters(self):
        rng = np.random.default_rng(20260922)
        mean_vector = [0.0, 0.0]
        cov = [[1.0, 0.0], [0.0, 1.0]]
        means = []
        for _ in range(400):
            sample = pd.DataFrame(rng.normal(size=(60, 2)), columns=["x", "y"])
            result = mewma_analyze(sample, ["x", "y"], lambda_=0.1,
                                   mean_vector=mean_vector, cov_matrix=cov)
            means.append(float(np.mean(result["mewma_chart"]["data"][20:])))
        assert_close(float(np.mean(means)), 2.0, _MC_CASE, context="平均 T²")

    def test_phase1_estimated_parameters_keep_mean_t2(self):
        """Phase I（500 点）估计参数后，Phase II 在控平均 T² 仍 ≈ p。"""
        rng = np.random.default_rng(4242)
        means = []
        for _ in range(200):
            phase1 = rng.normal(size=(500, 2))
            mu0 = phase1.mean(axis=0)
            sigma = np.cov(phase1, rowvar=False, ddof=1)
            phase2 = pd.DataFrame(rng.normal(size=(60, 2)), columns=["x", "y"])
            result = mewma_analyze(phase2, ["x", "y"], lambda_=0.1,
                                   mean_vector=mu0.tolist(),
                                   cov_matrix=sigma.tolist())
            means.append(float(np.mean(result["mewma_chart"]["data"][20:])))
        assert_close(float(np.mean(means)), 2.0, _MC_CASE,
                     context="Phase I 估计参数的平均 T²")

    def test_false_alarm_rate_matches_alpha(self):
        """F 限（m_phase1=500）在控越限率应贴近 α=0.0027。"""
        from scipy import stats

        rng = np.random.default_rng(31)
        alpha = 0.0027
        p, m_phase1 = 2, 500
        ucl = p * (m_phase1 - 1) * (m_phase1 + 1) / (m_phase1 * (m_phase1 - p)) * \
            float(stats.f.ppf(1 - alpha, p, m_phase1 - p))
        exceed = total = 0
        for _ in range(300):
            phase1 = rng.normal(size=(m_phase1, p))
            result = mewma_analyze(
                pd.DataFrame(rng.normal(size=(60, p)), columns=["x", "y"]),
                ["x", "y"], lambda_=0.1,
                mean_vector=phase1.mean(axis=0).tolist(),
                cov_matrix=np.cov(phase1, rowvar=False, ddof=1).tolist(),
                baseline_size=m_phase1)
            # 模块输出 UCL 保留 6 位小数
            assert result["mewma_chart"]["ucl"] == pytest.approx(ucl, abs=5e-7)
            exceed += len(result["mewma_chart"]["violations"])
            total += result["num_samples"]
        rate = exceed / total
        assert alpha / 3 < rate < alpha * 3, f"越限率 {rate:.5f} 偏离 α={alpha}"

    def test_mean_shift_is_detected(self):
        rng = np.random.default_rng(11)
        detected = 0
        for _ in range(50):
            phase1 = rng.normal(size=(500, 2))
            sample = rng.normal(size=(60, 2))
            sample[30:] += np.array([1.5, 0.0])
            result = mewma_analyze(
                pd.DataFrame(sample, columns=["x", "y"]), ["x", "y"], lambda_=0.1,
                mean_vector=phase1.mean(axis=0).tolist(),
                cov_matrix=np.cov(phase1, rowvar=False, ddof=1).tolist())
            if result["mewma_chart"]["violations"]:
                detected += 1
        assert detected == 50, f"均值漂移检出率不足: {detected}/50"

    def test_validation_errors(self):
        with pytest.raises(ValueError):
            mewma_analyze(DATA, ["x"], lambda_=0.5)
        with pytest.raises(ValueError):
            mewma_analyze(DATA, ["x", "y"], lambda_=0.0)
        with pytest.raises(ValueError):
            mewma_analyze(DATA, ["x", "y"], lambda_=1.5)
        with pytest.raises(ValueError):
            mewma_analyze(DATA, ["x", "y"], ucl_method="bogus")
