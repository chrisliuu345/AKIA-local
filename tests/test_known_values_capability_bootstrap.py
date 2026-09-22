"""能力指数 Bootstrap 置信区间已知值测试（v4.2.0 P2-5）

命题: 非正态能力的 Pp/Ppk 抽样分布无闭式解，Bootstrap 区间应
1. 同一 seed 完全可复现（报告复核 / 重跑 diff 前提）
2. 覆盖率接近名义置信水平（蒙特卡洛检验，正态过程已知真值 Ppk = 1）
3. 样本量越大区间越窄（一致估计）
"""

import numpy as np
import pandas as pd
import pytest

from analysis.capability.non_normal_cap import bootstrap_capability_ci
from tests.known_values import KnownValueCase, assert_close

_COVERAGE_CASE = KnownValueCase(
    case_id="bootstrap-cpk-95ci-coverage",
    source="蒙特卡洛（固定种子，N(0,1)，USL=3 / LSL=-3 ⇒ 真值 Ppk=1，n=1500）",
    reference="95% 百分位 Bootstrap 区间覆盖率 ≥ 85%（名义 95%）",
    rel_tol=1e-9, abs_tol=0.12,
    notes=("百分位法需要大样本（σ_p 由极值决定）：实测 n=120 覆盖率 25%、"
           "n=500 67%、n=1500 94%、n=3000 95%"),
)


class TestBootstrapReproducibility:
    def test_same_seed_is_identical(self):
        rng = np.random.default_rng(0)
        data = pd.Series(rng.lognormal(mean=0.0, sigma=0.5, size=200))
        first = bootstrap_capability_ci(data, usl=6.0, lsl=0.0, seed=1234)
        second = bootstrap_capability_ci(data, usl=6.0, lsl=0.0, seed=1234)
        assert first["ci"] == second["ci"]
        assert first["point"] == second["point"]

    def test_different_seed_stays_close(self):
        rng = np.random.default_rng(1)
        data = pd.Series(rng.lognormal(mean=0.0, sigma=0.5, size=300))
        a = bootstrap_capability_ci(data, usl=6.0, lsl=0.0, n_boot=400, seed=1)
        b = bootstrap_capability_ci(data, usl=6.0, lsl=0.0, n_boot=400, seed=2)
        assert a["ci"]["ppk"][0] == pytest.approx(b["ci"]["ppk"][0], abs=0.02)
        assert a["ci"]["ppk"][1] == pytest.approx(b["ci"]["ppk"][1], abs=0.02)


class TestBootstrapCoverage:
    def test_normal_process_cpk_coverage(self):
        rng = np.random.default_rng(20260922)
        covered = 0
        total = 200
        for _ in range(total):
            sample = pd.Series(rng.normal(loc=0.0, scale=1.0, size=1500))
            result = bootstrap_capability_ci(sample, usl=3.0, lsl=-3.0,
                                            n_boot=200, seed=7)
            low, high = result["ci"]["ppk"]
            if low <= 1.0 <= high:
                covered += 1
        rate = covered / total
        assert_close(rate, 0.95, _COVERAGE_CASE, context="Ppk 95% 区间覆盖率")
        assert rate >= 0.85, f"覆盖率过低: {rate:.3f}"


class TestAccuracyWarning:
    def test_small_sample_percentile_warns(self):
        rng = np.random.default_rng(21)
        result = bootstrap_capability_ci(pd.Series(rng.normal(size=120)),
                                         usl=3.0, lsl=-3.0, n_boot=100)
        assert "n=120" in result["accuracy_warning"]
        assert "box_cox" in result["accuracy_warning"]

    def test_large_sample_has_no_warning(self):
        rng = np.random.default_rng(22)
        result = bootstrap_capability_ci(pd.Series(rng.normal(size=1500)),
                                         usl=3.0, lsl=-3.0, n_boot=100)
        assert result["accuracy_warning"] == ""

    def test_box_cox_mode_has_no_small_sample_warning(self):
        rng = np.random.default_rng(23)
        result = bootstrap_capability_ci(pd.Series(rng.normal(size=120) + 5.0),
                                         usl=9.0, lsl=1.0, method="box_cox",
                                         n_boot=100)
        assert result["accuracy_warning"] == ""


class TestBootstrapProperties:
    def test_interval_narrows_with_sample_size(self):
        rng = np.random.default_rng(3)
        small = pd.Series(rng.lognormal(0.0, 0.6, size=80))
        large = pd.Series(rng.lognormal(0.0, 0.6, size=2000))
        ci_small = bootstrap_capability_ci(small, usl=8.0, lsl=0.0,
                                           n_boot=400, seed=5)["ci"]["ppk"]
        ci_large = bootstrap_capability_ci(large, usl=8.0, lsl=0.0,
                                           n_boot=400, seed=5)["ci"]["ppk"]
        assert (ci_large[1] - ci_large[0]) < (ci_small[1] - ci_small[0])

    def test_ci_bounds_are_ordered_and_point_inside(self):
        rng = np.random.default_rng(4)
        data = pd.Series(rng.lognormal(0.0, 0.7, size=250))
        result = bootstrap_capability_ci(data, usl=8.0, lsl=0.0, seed=9)
        for key in ("pp", "ppk", "ppm_total"):
            low, high = result["ci"][key]
            assert low <= high
        assert result["ci"]["ppk"][0] <= result["point"]["ppk"] <= result["ci"]["ppk"][1]
        assert 0.0 <= result["ci"]["ppm_total"][0]
        assert result["ci"]["ppm_total"][1] <= 1e6

    def test_box_cox_mode_refits_transform(self):
        rng = np.random.default_rng(6)
        data = pd.Series(rng.lognormal(0.0, 0.5, size=150))
        result = bootstrap_capability_ci(data, usl=6.0, lsl=0.0,
                                         method="box_cox", n_boot=100, seed=3)
        assert result["method"] == "box_cox"
        assert result["ci"]["ppk"][0] <= result["ci"]["ppk"][1]
        assert result["point"]["ppk"] is not None

    def test_one_sided_spec_supported(self):
        rng = np.random.default_rng(8)
        data = pd.Series(rng.lognormal(0.0, 0.5, size=150))
        result = bootstrap_capability_ci(data, usl=6.0, seed=2)
        assert result["ci"]["ppk"] is not None
        assert result["ci"]["pp"][0] <= result["ci"]["pp"][1]

    def test_validation_errors(self):
        data = pd.Series(np.random.default_rng(9).normal(size=50))
        with pytest.raises(ValueError):
            bootstrap_capability_ci(data)
        with pytest.raises(ValueError):
            bootstrap_capability_ci(data, usl=3.0, n_boot=10)
        with pytest.raises(ValueError):
            bootstrap_capability_ci(data, usl=3.0, method="johnson")
        with pytest.raises(ValueError):
            bootstrap_capability_ci(data, usl=3.0, confidence=1.5)
