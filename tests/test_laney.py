"""Laney P'/U' 控制图测试"""

import numpy as np
import pytest
from analysis.spc.laney import laney_p_prime, laney_u_prime


class TestLaneyPPrime:
    """Laney P' 图测试"""

    def test_basic_p_prime(self):
        defects = np.array([10, 15, 8, 12, 11, 14, 9, 13, 10, 12])
        sample_sizes = np.array([100, 120, 90, 110, 105, 115, 95, 108, 100, 112])
        result = laney_p_prime(defects, sample_sizes)
        
        assert result["chart_type"] == "Laney P'"
        assert result["n_subgroups"] == 10
        assert len(result["ucl"]) == 10
        assert len(result["lcl"]) == 10
        assert len(result["proportions"]) == 10
        assert result["center_line"] > 0
        assert result["sigma_z"] >= 1.0

    def test_overdispersed_data(self):
        np.random.seed(42)
        n = 20
        sample_sizes = np.full(n, 100)
        p_true = 0.1
        defects = np.random.binomial(100, p_true, n)
        defects[5] = 50  # 添加异常值
        defects[15] = 5
        
        result = laney_p_prime(defects, sample_sizes)
        
        assert result["n_violations"] >= 0
        assert result["sigma_z"] >= 1.0

    def test_different_sample_sizes(self):
        defects = np.array([5, 10, 15, 8, 12])
        sample_sizes = np.array([50, 100, 200, 75, 150])
        result = laney_p_prime(defects, sample_sizes)
        
        assert result["n_subgroups"] == 5
        assert len(result["ucl"]) == 5
        # UCL应该随样本大小变化
        assert result["ucl"][2] < result["ucl"][0]

    def test_laney_p_prime_constant_sample_sizes(self):
        defects = np.array([10, 12, 11, 13, 10, 12, 11, 12])
        sample_sizes = np.full(8, 100)
        result = laney_p_prime(defects, sample_sizes)
        
        assert result["n_subgroups"] == 8
        assert result["sigma_z"] >= 1.0

    def test_laney_p_prime_violations(self):
        defects = np.array([10, 10, 10, 50, 10, 10, 10, 10])
        sample_sizes = np.full(8, 100)
        result = laney_p_prime(defects, sample_sizes)
        
        assert 3 in result["violation_indices"]

    def test_laney_p_prime_insufficient_data(self):
        defects = np.array([10])
        sample_sizes = np.array([100])
        with pytest.raises(ValueError):
            laney_p_prime(defects, sample_sizes)

    def test_laney_p_prime_invalid_sample_sizes(self):
        defects = np.array([10, 15, 8])
        sample_sizes = np.array([100, 0, 90])
        with pytest.raises(ValueError):
            laney_p_prime(defects, sample_sizes)

    def test_laney_p_prime_negative_defects(self):
        defects = np.array([-1, 15, 8])
        sample_sizes = np.array([100, 120, 90])
        with pytest.raises(ValueError):
            laney_p_prime(defects, sample_sizes)

    def test_laney_p_prime_length_mismatch(self):
        defects = np.array([10, 15, 8])
        sample_sizes = np.array([100, 120])
        with pytest.raises(ValueError):
            laney_p_prime(defects, sample_sizes)


class TestLaneyUPrime:
    """Laney U' 图测试"""

    def test_basic_u_prime(self):
        defects = np.array([10, 15, 8, 12, 11, 14, 9, 13, 10, 12])
        sample_sizes = np.array([100, 120, 90, 110, 105, 115, 95, 108, 100, 112])
        result = laney_u_prime(defects, sample_sizes)
        
        assert result["chart_type"] == "Laney U'"
        assert result["n_subgroups"] == 10
        assert len(result["ucl"]) == 10
        assert len(result["lcl"]) == 10
        assert len(result["unit_defects"]) == 10
        assert result["center_line"] > 0
        assert result["sigma_z"] >= 1.0

    def test_overdispersed_u_data(self):
        np.random.seed(42)
        n = 20
        sample_sizes = np.full(n, 100)
        u_true = 0.1
        defects = np.random.binomial(100, u_true, n)
        defects[5] = 50
        defects[15] = 5
        
        result = laney_u_prime(defects, sample_sizes)
        
        assert result["n_violations"] >= 0
        assert result["sigma_z"] >= 1.0

    def test_different_sample_sizes_u(self):
        defects = np.array([5, 10, 15, 8, 12])
        sample_sizes = np.array([50, 100, 200, 75, 150])
        result = laney_u_prime(defects, sample_sizes)
        
        assert result["n_subgroups"] == 5
        assert len(result["ucl"]) == 5

    def test_laney_u_prime_constant_sample_sizes(self):
        defects = np.array([10, 12, 11, 13, 10, 12, 11, 12])
        sample_sizes = np.full(8, 100)
        result = laney_u_prime(defects, sample_sizes)
        
        assert result["n_subgroups"] == 8
        assert result["sigma_z"] >= 1.0

    def test_laney_u_prime_violations(self):
        defects = np.array([10, 10, 10, 50, 10, 10, 10, 10])
        sample_sizes = np.full(8, 100)
        result = laney_u_prime(defects, sample_sizes)
        
        assert 3 in result["violation_indices"]

    def test_laney_u_prime_insufficient_data(self):
        defects = np.array([10])
        sample_sizes = np.array([100])
        with pytest.raises(ValueError):
            laney_u_prime(defects, sample_sizes)

    def test_laney_u_prime_invalid_sample_sizes(self):
        defects = np.array([10, 15, 8])
        sample_sizes = np.array([100, 0, 90])
        with pytest.raises(ValueError):
            laney_u_prime(defects, sample_sizes)

    def test_laney_u_prime_negative_defects(self):
        defects = np.array([-1, 15, 8])
        sample_sizes = np.array([100, 120, 90])
        with pytest.raises(ValueError):
            laney_u_prime(defects, sample_sizes)


class TestLaneyComparison:
    """Laney P'/U' 与标准P/U图对比测试"""

    def test_laney_vs_standard_p_chart(self):
        import pandas as pd
        defects = np.array([10, 15, 8, 12, 11, 14, 9, 13, 10, 12])
        sample_sizes = np.array([100, 120, 90, 110, 105, 115, 95, 108, 100, 112])
        
        from analysis.spc.p_chart import analyze as p_analyze
        result_p = p_analyze(pd.Series(defects), pd.Series(sample_sizes))
        result_laney = laney_p_prime(defects, sample_sizes)
        
        # 中心线应该相同 (p_chart用"cl"，laney用"center_line")
        assert abs(result_p["cl"] - result_laney["center_line"]) < 1e-10
        
        # Laney的sigma_z >= 1，所以控制限应该更宽或相同
        assert result_laney["sigma_z"] >= 1.0

    def test_laney_vs_standard_u_chart(self):
        import pandas as pd
        defects = np.array([10, 15, 8, 12, 11, 14, 9, 13, 10, 12])
        sample_sizes = np.array([100, 120, 90, 110, 105, 115, 95, 108, 100, 112])
        
        from analysis.spc.u_chart import analyze as u_analyze
        result_u = u_analyze(pd.Series(defects), pd.Series(sample_sizes))
        result_laney = laney_u_prime(defects, sample_sizes)
        
        # 中心线应该相同
        assert abs(result_u["cl"] - result_laney["center_line"]) < 1e-10
