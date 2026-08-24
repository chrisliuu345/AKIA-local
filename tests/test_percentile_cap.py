"""百分位法能力分析测试"""

import numpy as np
import pandas as pd
import pytest
from analysis.capability.non_normal_cap import analyze


class TestPercentileCapability:
    """百分位法能力分析测试"""

    def test_basic_percentile(self):
        np.random.seed(42)
        data = pd.Series(np.random.normal(100, 5, 100))
        result = analyze(data, usl=115, lsl=85, method="percentile")

        assert result["chart_type"] == "Non-Normal Capability"
        assert result["method"] == "percentile"
        assert "summary" in result
        assert "capability" in result

    def test_percentile_with_usl_only(self):
        np.random.seed(42)
        data = pd.Series(np.random.normal(100, 5, 100))
        result = analyze(data, usl=115, method="percentile")

        assert result["chart_type"] == "Non-Normal Capability"
        assert "capability" in result
        assert "usl" in result["capability"]
        assert "lsl" not in result["capability"]

    def test_percentile_with_lsl_only(self):
        np.random.seed(42)
        data = pd.Series(np.random.normal(100, 5, 100))
        result = analyze(data, lsl=85, method="percentile")

        assert result["chart_type"] == "Non-Normal Capability"
        assert "capability" in result
        assert "lsl" in result["capability"]
        assert "usl" not in result["capability"]

    def test_percentile_no_specs(self):
        np.random.seed(42)
        data = pd.Series(np.random.normal(100, 5, 100))
        result = analyze(data, method="percentile")

        assert result["chart_type"] == "Non-Normal Capability"
        assert "summary" in result
        assert "capability" not in result

    def test_percentile_constant_data(self):
        data = pd.Series(np.full(50, 100.0))
        result = analyze(data, usl=115, lsl=85, method="percentile")

        # 常数数据应该有无限能力
        assert result["capability"]["pp"] is None or result["capability"]["pp"] == float('inf')

    def test_percentile_insufficient_data(self):
        data = pd.Series([100.0, 101.0])
        with pytest.raises(ValueError):
            analyze(data, usl=115, lsl=85, method="percentile")

    def test_percentile_summary_structure(self):
        np.random.seed(42)
        data = pd.Series(np.random.normal(100, 5, 50))
        result = analyze(data, usl=115, lsl=85, method="percentile")

        assert "sample_size" in result["summary"]
        assert "original_mean" in result["summary"]
        assert "original_std" in result["summary"]
        assert "skewness" in result["summary"]
        assert "kurtosis" in result["summary"]
        assert "percentiles" in result["summary"]
        assert "sigma_percentile" in result["summary"]

    def test_percentile_capability_structure(self):
        np.random.seed(42)
        data = pd.Series(np.random.normal(100, 5, 50))
        result = analyze(data, usl=115, lsl=85, method="percentile")

        assert "pp" in result["capability"]
        assert "ppk" in result["capability"]
        assert "ppm_total" in result["capability"]
        assert "grade" in result["capability"]
        assert "sigma_level" in result["capability"]

    def test_percentile_vs_box_cox(self):
        np.random.seed(42)
        data = pd.Series(np.random.normal(100, 5, 100))

        result_percentile = analyze(data, usl=115, lsl=85, method="percentile")
        result_boxcox = analyze(data, usl=115, lsl=85, method="box_cox")

        # 两种方法都应该产生有效的结果
        assert result_percentile["capability"]["pp"] is not None
        assert result_boxcox["capability"]["pp"] is not None

        # 对于正态数据，两种方法应该给出相似的结果
        assert abs(result_percentile["capability"]["pp"] - result_boxcox["capability"]["pp"]) < 0.5

    def test_percentile_non_normal_data(self):
        np.random.seed(42)
        # 生成对数正态数据（非正态）
        data = pd.Series(np.random.lognormal(4, 0.5, 100))
        result = analyze(data, usl=100, lsl=10, method="percentile")

        assert result["chart_type"] == "Non-Normal Capability"
        assert result["method"] == "percentile"
        assert "capability" in result

    def test_percentile_sigma_estimation(self):
        np.random.seed(42)
        data = pd.Series(np.random.normal(100, 5, 100))
        result = analyze(data, method="percentile")

        sigma = result["summary"]["sigma_percentile"]
        # 对于正态数据，sigma_percentile应该接近真实标准差5
        # 允许较大容差因为百分位法是近似估计
        assert 3 < sigma < 7
