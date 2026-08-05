"""ALT + 非参数检验 单元测试"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest, numpy as np

from analysis.reliability.alt import ALTEngine
from analysis.hypothesis.nonparametric import mann_whitney, wilcoxon_signed_rank, kruskal_wallis


class TestALT:
    def test_arrhenius(self):
        T = np.array([373, 393, 413, 433], dtype=float)  # K
        life = np.array([5000, 2000, 800, 300], dtype=float)
        r = ALTEngine.arrhenius_life(T, life, use_temp=25, activation_energy=0.7)
        assert r["r_squared"] > 0.9
        assert r["acceleration_factor"] > 1
        assert r["life_at_use"] > r["life_95ci_low"]

    def test_inverse_power(self):
        V = np.array([200, 250, 300, 350], dtype=float)
        life = np.array([10000, 5000, 2000, 1000], dtype=float)
        r = ALTEngine.inverse_power_law(V, life, use_stress=120)
        assert r["r_squared"] > 0.8
        assert r["acceleration_factor"] > 1


class TestNonparametric:
    def test_mann_whitney_sig(self):
        a = np.random.normal(10, 1, 30)
        b = np.random.normal(12, 1, 30)
        r = mann_whitney(a, b)
        assert r["p_value"] < 0.05
        assert r["significant"]

    def test_mann_whitney_ns(self):
        a = np.random.normal(10, 1, 30)
        b = np.random.normal(10.1, 1, 30)
        r = mann_whitney(a, b)
        assert "u_statistic" in r

    def test_wilcoxon_paired_sig(self):
        a = np.random.normal(10, 1, 30)
        b = a + 2 + np.random.normal(0, 0.5, 30)
        r = wilcoxon_signed_rank(a, b)
        assert r["p_value"] < 0.01

    def test_wilcoxon_one_sample(self):
        a = np.random.normal(5, 1, 20)
        r = wilcoxon_signed_rank(a)
        assert r["n"] == 20

    def test_kruskal_wallis(self):
        a = np.random.normal(10, 1, 20)
        b = np.random.normal(12, 1, 20)
        c = np.random.normal(14, 1, 20)
        r = kruskal_wallis(a, b, c)
        assert r["p_value"] < 0.01

    def test_kruskal_ns(self):
        a = np.random.normal(10, 1, 20)
        b = np.random.normal(10, 1, 20)
        r = kruskal_wallis(a, b)
        assert r["n_groups"] == 2

    def test_small_sample(self):
        r = mann_whitney(np.array([1, 2]), np.array([3]))
        assert "error" in r


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
