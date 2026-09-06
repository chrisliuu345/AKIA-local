"""可靠性框图 (RBD) + Crow-AMSAA 单元测试"""

import numpy as np
import pytest

from analysis.reliability.rbd import (
    calculate_system_reliability, system_mtbf,
)
from analysis.reliability.mtbf import crow_amsaa


class TestRBD:

    def test_series_system(self):
        components = [
            {"name": "A", "reliability": 0.95},
            {"name": "B", "reliability": 0.90},
            {"name": "C", "reliability": 0.85},
        ]
        result = calculate_system_reliability(components, structure="series")
        assert result["summary"]["system_reliability"] == pytest.approx(0.95 * 0.90 * 0.85, abs=1e-6)
        assert result["summary"]["structure"] == "series"

    def test_parallel_system(self):
        components = [
            {"name": "A", "reliability": 0.90},
            {"name": "B", "reliability": 0.80},
        ]
        result = calculate_system_reliability(components, structure="parallel")
        expected = 1 - (1 - 0.90) * (1 - 0.80)
        assert result["summary"]["system_reliability"] == pytest.approx(expected, abs=1e-6)

    def test_mixed_system(self):
        components = [
            {"name": "A", "reliability": 0.95},
            {"name": "B", "reliability": 0.90},
            {"name": "C", "reliability": 0.85},
        ]
        # A 和 B 并联，再与 C 串联
        result = calculate_system_reliability(
            components, structure="mixed", parallel_groups=[[0, 1], [2]]
        )
        r_parallel = 1 - (1 - 0.95) * (1 - 0.90)
        expected = r_parallel * 0.85
        assert result["summary"]["system_reliability"] == pytest.approx(expected, abs=1e-6)

    def test_k_out_of_n(self):
        components = [
            {"name": "A", "reliability": 0.90},
            {"name": "B", "reliability": 0.85},
            {"name": "C", "reliability": 0.80},
        ]
        result = calculate_system_reliability(
            components, structure="k_out_of_n", k_out_of_n={"k": 2, "n": 3}
        )
        # 2/3 表决: P(≥2 正常)
        r = 0.90 * 0.85 * 0.80  # 全部正常
        r += 0.90 * 0.85 * 0.20  # A,B 正常, C 失效
        r += 0.90 * 0.15 * 0.80  # A,C 正常, B 失效
        r += 0.10 * 0.85 * 0.80  # B,C 正常, A 失效
        assert result["summary"]["system_reliability"] == pytest.approx(r, abs=1e-4)

    def test_weakest_component(self):
        components = [
            {"name": "A", "reliability": 0.99},
            {"name": "B", "reliability": 0.70},
            {"name": "C", "reliability": 0.95},
        ]
        result = calculate_system_reliability(components, structure="series")
        assert result["weakest_component"]["name"] == "B"
        assert result["weakest_component"]["reliability"] == 0.70

    def test_empty_components(self):
        result = calculate_system_reliability([], structure="series")
        assert "error" in result

    def test_missing_reliability(self):
        result = calculate_system_reliability([{"name": "A"}], structure="series")
        assert "error" in result


class TestSystemMTBF:

    def test_series_mtbf(self):
        components = [
            {"name": "A", "mtbf": 1000},
            {"name": "B", "mtbf": 2000},
        ]
        result = system_mtbf(components, structure="series")
        # Series: MTBF = 1/(1/1000 + 1/2000) = 666.67
        assert result["summary"]["system_mtbf"] == pytest.approx(666.67, abs=1)

    def test_parallel_mtbf(self):
        components = [
            {"name": "A", "mtbf": 1000},
            {"name": "B", "mtbf": 1000},
        ]
        result = system_mtbf(components, structure="parallel")
        # Parallel with equal MTBFs: MTBF > max(MTBFs)
        assert result["summary"]["system_mtbf"] > 1000


class TestCrowAMSAA:

    def test_basic_crow_amsaa(self):
        np.random.seed(42)
        # Simulate improving system (β < 1)
        times = np.sort(np.random.exponential(50, 20)) * np.linspace(1, 0.5, 20)
        result = crow_amsaa(times.tolist())
        assert result["analysis_type"] == "reliability.mtbf.crow_amsaa"
        assert result["summary"]["n_failures"] == 20
        assert result["summary"]["beta"] > 0
        assert result["summary"]["alpha"] > 0
        assert result["summary"]["trend"] in ("improving", "stable", "degrading")

    def test_crow_amsaa_degrading(self):
        # β > 1 = degrading
        times = [10, 15, 18, 20, 21, 22, 22.5, 23, 23.2, 23.5]
        result = crow_amsaa(times)
        assert result["summary"]["trend"] == "degrading"

    def test_crow_amsaa_insufficient(self):
        result = crow_amsaa([10, 20])
        assert "error" in result

    def test_crow_amsaa_confidence(self):
        np.random.seed(42)
        times = np.sort(np.random.exponential(100, 30))
        result = crow_amsaa(times, confidence_level=0.95)
        ci = result["summary"]
        assert ci["beta_ci_low"] < ci["beta"]
        assert ci["beta_ci_high"] > ci["beta"]
