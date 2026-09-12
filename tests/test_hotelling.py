"""Hotelling T² 测试"""
import pytest
import numpy as np
import pandas as pd
from analysis.spc.hotelling import analyze


class TestHotellingT2:
    """Hotelling T² 测试"""

    def test_basic_t2(self):
        """基本 T² 分析"""
        np.random.seed(42)
        data = pd.DataFrame({
            "X1": np.random.normal(0, 1, 50),
            "X2": np.random.normal(0, 1, 50),
        })
        result = analyze(data, ["X1", "X2"])

        assert result["chart_type"] == "Hotelling T²"
        assert result["num_variables"] == 2
        assert result["num_samples"] == 50
        assert "t2_chart" in result
        assert "data" in result["t2_chart"]
        assert "ucl" in result["t2_chart"]

    def test_correlated_data(self):
        """相关数据"""
        np.random.seed(42)
        mean = [0, 0]
        cov = [[1, 0.8], [0.8, 1]]
        data = pd.DataFrame(
            np.random.multivariate_normal(mean, cov, 50),
            columns=["X1", "X2"]
        )
        result = analyze(data, ["X1", "X2"])

        assert result["num_variables"] == 2
        assert "correlation_matrix" in result["summary"]
        # 相关系数应接近 0.8
        corr = result["summary"]["correlation_matrix"][0][1]
        assert abs(corr - 0.8) < 0.2

    def test_three_variables(self):
        """三个变量"""
        np.random.seed(42)
        data = pd.DataFrame({
            "X1": np.random.normal(0, 1, 40),
            "X2": np.random.normal(0, 1, 40),
            "X3": np.random.normal(0, 1, 40),
        })
        result = analyze(data, ["X1", "X2", "X3"])

        assert result["num_variables"] == 3
        assert len(result["summary"]["mean_vector"]) == 3

    def test_with_subgroups(self):
        """子组数据"""
        np.random.seed(42)
        data = pd.DataFrame({
            "X1": np.random.normal(0, 1, 60),
            "X2": np.random.normal(0, 1, 60),
            "Group": np.repeat([1, 2, 3, 4, 5, 6], 10),
        })
        result = analyze(data, ["X1", "X2"], subgroup_col="Group")

        assert result["num_variables"] == 2
        assert len(result["t2_chart"]["data"]) == 6

    def test_insufficient_variables(self):
        """变量不足"""
        data = pd.DataFrame({"X1": [1, 2, 3]})
        with pytest.raises(ValueError, match="至少 2 个变量"):
            analyze(data, ["X1"])

    def test_insufficient_data(self):
        """数据量不足"""
        data = pd.DataFrame({
            "X1": [1, 2],
            "X2": [3, 4],
        })
        with pytest.raises(ValueError, match="数据量不足"):
            analyze(data, ["X1", "X2"])

    def test_violations_detection(self):
        """违规点检测"""
        np.random.seed(42)
        # 创建包含异常值的数据
        data = pd.DataFrame({
            "X1": np.concatenate([np.random.normal(0, 1, 48), [5, -5]]),
            "X2": np.concatenate([np.random.normal(0, 1, 48), [5, -5]]),
        })
        result = analyze(data, ["X1", "X2"])

        # 应该检测到违规点
        assert len(result["t2_chart"]["violations"]) > 0

    def test_mean_vector(self):
        """均值向量"""
        np.random.seed(42)
        data = pd.DataFrame({
            "X1": np.random.normal(5, 1, 50),
            "X2": np.random.normal(10, 1, 50),
        })
        result = analyze(data, ["X1", "X2"])

        mean = result["summary"]["mean_vector"]
        assert abs(mean[0] - 5) < 0.5
        assert abs(mean[1] - 10) < 0.5

    def test_phase1(self):
        """Phase 1 分析"""
        np.random.seed(42)
        data = pd.DataFrame({
            "X1": np.random.normal(0, 1, 50),
            "X2": np.random.normal(0, 1, 50),
        })
        result = analyze(data, ["X1", "X2"], phase="phase1")

        assert result["phase"] == "phase1"

    def test_individual_observations_ucl_not_zero(self):
        """回归（v3.8.0）：无子组时旧实现 UCL=0、全部点误报越限"""
        np.random.seed(42)
        data = pd.DataFrame({
            "X1": np.random.normal(0, 1, 50),
            "X2": np.random.normal(0, 1, 50),
        })
        result = analyze(data, ["X1", "X2"])

        ucl = np.asarray(result["t2_chart"]["ucl"], dtype=float)
        assert np.all(np.isfinite(ucl)) and np.all(ucl > 0)
        assert result["t2_chart"]["violations"] == []

    def test_individual_ucl_matches_montgomery_formula(self):
        """个体观测 UCL = p(m-1)(m+1)/(m(m-p))·F(1-α; p, m-p)"""
        from scipy import stats

        np.random.seed(42)
        m, p, alpha = 50, 2, 0.0027
        data = pd.DataFrame({
            "X1": np.random.normal(0, 1, m),
            "X2": np.random.normal(0, 1, m),
        })
        result = analyze(data, ["X1", "X2"], alpha=alpha)

        expected = (p * (m - 1) * (m + 1) / (m * (m - p))
                    * stats.f.ppf(1 - alpha, p, m - p))
        ucl = np.asarray(result["t2_chart"]["ucl"], dtype=float)
        assert ucl.shape == (m,)
        assert np.allclose(ucl, expected)

    def test_subgroup_ucl_matches_tym_formula(self):
        """子组 UCL = p(m-1)(n_i-1)/(N-m-p+1)·F(1-α; p, N-m-p+1)"""
        from scipy import stats

        np.random.seed(42)
        m, ni, p, alpha = 6, 10, 2, 0.0027
        n = m * ni
        data = pd.DataFrame({
            "X1": np.random.normal(0, 1, n),
            "X2": np.random.normal(0, 1, n),
            "Group": np.repeat(range(m), ni),
        })
        result = analyze(data, ["X1", "X2"], subgroup_col="Group", alpha=alpha)

        df2 = n - m - p + 1
        expected = p * (m - 1) * (ni - 1) / df2 * stats.f.ppf(1 - alpha, p, df2)
        ucl = np.asarray(result["t2_chart"]["ucl"], dtype=float)
        assert len(ucl) == m
        assert np.allclose(ucl, expected)
        assert ucl[0] > 1.0    # 旧公式（约 2.0）在 α=0.0027 下过紧，属误报源

    def test_hotelling_test(self):
        """多元正态性检验"""
        np.random.seed(42)
        data = pd.DataFrame({
            "X1": np.random.normal(0, 1, 50),
            "X2": np.random.normal(0, 1, 50),
        })
        result = analyze(data, ["X1", "X2"])

        assert "hotelling_test" in result
        assert "skewness_statistic" in result["hotelling_test"]
        assert "kurtosis_statistic" in result["hotelling_test"]


class TestPChartVectorized:
    """P图向量化测试"""

    def test_basic_p_chart(self):
        """基本 P 图"""
        import pandas as pd
        from analysis.spc.p_chart import analyze

        defectives = pd.Series([10, 15, 12, 8, 14])
        sample_sizes = pd.Series([100, 120, 110, 90, 105])
        result = analyze(defectives, sample_sizes)

        assert result["chart_type"] == "P-Chart"
        assert len(result["data"]["p_values"]) == 5
        assert "ucl" in result
        assert "lcl" in result

    def test_p_chart_violations(self):
        """P 图违规检测"""
        import pandas as pd
        from analysis.spc.p_chart import analyze

        defectives = pd.Series([50, 10, 10, 10, 10])
        sample_sizes = pd.Series([100, 100, 100, 100, 100])
        result = analyze(defectives, sample_sizes)

        # 第一个点应该超出 UCL
        assert len(result["violations"]) > 0


class TestUChartVectorized:
    """U图向量化测试"""

    def test_basic_u_chart(self):
        """基本 U 图"""
        import pandas as pd
        from analysis.spc.u_chart import analyze

        defects = pd.Series([5, 8, 6, 4, 7])
        unit_sizes = pd.Series([10, 12, 11, 9, 10])
        result = analyze(defects, unit_sizes)

        assert result["chart_type"] == "U-Chart"
        assert len(result["data"]["u_values"]) == 5
        assert "ucl" in result
        assert "lcl" in result
