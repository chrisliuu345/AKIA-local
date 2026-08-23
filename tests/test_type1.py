"""Type 1 量具研究测试"""
import pytest
import numpy as np
import pandas as pd
from analysis.msa.type1_study import analyze


class TestType1Study:
    """Type 1 量具研究测试"""

    def test_basic_type1(self):
        """基本 Type 1 研究"""
        data = pd.Series([9.9, 10.0, 10.1, 9.95, 10.05, 10.0, 10.1, 9.9, 10.0, 10.1])
        result = analyze(data, reference=10.0, tolerance=0.5)

        assert result["chart_type"] == "Type 1 Gage Study"
        assert "capability" in result
        assert "cg" in result["capability"]
        assert "cgk" in result["capability"]

    def test_type1_with_usl_lsl(self):
        """使用 USL/LSL"""
        data = pd.Series([9.9, 10.0, 10.1, 9.95, 10.05])
        result = analyze(data, reference=10.0, usl=10.5, lsl=9.5)

        assert result["capability"]["usl"] == 10.5
        assert result["capability"]["lsl"] == 9.5

    def test_type1_good_gage(self):
        """高质量量具"""
        data = pd.Series([10.0, 10.01, 9.99, 10.0, 10.01, 9.99, 10.0, 10.01])
        result = analyze(data, reference=10.0, tolerance=0.5)

        assert result["capability"]["cg"] > 1.33
        assert result["capability"]["cgk"] > 1.33
        assert result["acceptance"]["level"] == "acceptable"

    def test_type1_poor_gage(self):
        """低质量量具"""
        data = pd.Series([9.5, 10.5, 9.0, 11.0, 9.5, 10.5, 9.0, 11.0])
        result = analyze(data, reference=10.0, tolerance=0.5)

        assert result["capability"]["cg"] < 1.33
        assert result["acceptance"]["level"] == "unacceptable"

    def test_type1_with_bias(self):
        """有偏倚的量具"""
        data = pd.Series([10.2, 10.3, 10.1, 10.25, 10.15, 10.2, 10.3, 10.1])
        result = analyze(data, reference=10.0, tolerance=0.5)

        assert result["bias_test"]["mean_bias"] > 0
        assert result["capability"]["bias"] > 0

    def test_type1_no_bias_test(self):
        """跳过偏倚检验"""
        data = pd.Series([9.9, 10.0, 10.1, 9.95, 10.05])
        result = analyze(data, reference=10.0, tolerance=0.5, bias_test=False)

        assert "bias_test" not in result

    def test_type1_insufficient_data(self):
        """数据量不足"""
        data = pd.Series([9.9, 10.0, 10.1])
        with pytest.raises(ValueError, match="数据量不足"):
            analyze(data, reference=10.0, tolerance=0.5)

    def test_type1_constant_data(self):
        """常数数据"""
        data = pd.Series([10.0, 10.0, 10.0, 10.0, 10.0])
        result = analyze(data, reference=10.0, tolerance=0.5)

        assert result["capability"]["cg"] == "inf"
        assert result["capability"]["cgk"] == "inf"

    def test_type1_bias_test_result(self):
        """偏倚检验结果"""
        data = pd.Series([10.0, 10.01, 9.99, 10.0, 10.01, 9.99, 10.0, 10.01])
        result = analyze(data, reference=10.0, tolerance=0.5)

        assert "bias_test" in result
        assert "mean_bias" in result["bias_test"]
        assert "p_value" in result["bias_test"]
        assert "is_significant" in result["bias_test"]

    def test_type1_acceptance_criteria(self):
        """判定标准测试"""
        # 可接受的量具
        data_good = pd.Series([10.0, 10.01, 9.99, 10.0, 10.01, 9.99, 10.0, 10.01])
        result_good = analyze(data_good, reference=10.0, tolerance=0.5)
        assert result_good["acceptance"]["level"] == "acceptable"

        # 不可接受的量具
        data_bad = pd.Series([9.0, 11.0, 8.5, 11.5, 9.0, 11.0, 8.5, 11.5])
        result_bad = analyze(data_bad, reference=10.0, tolerance=0.5)
        assert result_bad["acceptance"]["level"] == "unacceptable"
