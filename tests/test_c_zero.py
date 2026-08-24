"""C=0 抽样方案测试"""

import numpy as np
import pytest
from core.sampling_engine import SamplingEngine


class TestCZeroSampling:
    """C=0 抽样方案测试"""

    def test_basic_c_zero(self):
        result = SamplingEngine.c_zero_sampling(lot_size=100, aql=0.10)

        assert result["method"] == "C=0 Sampling Plan"
        assert result["lot_size"] == 100
        assert result["sample_size"] > 0
        assert result["accept_number"] == 0
        assert result["reject_number"] == 1
        assert result["aql"] == 0.10

    def test_c_zero_different_lot_sizes(self):
        result_50 = SamplingEngine.c_zero_sampling(lot_size=50, aql=0.10)
        result_100 = SamplingEngine.c_zero_sampling(lot_size=100, aql=0.10)
        result_500 = SamplingEngine.c_zero_sampling(lot_size=500, aql=0.10)

        # 更大的批量应该有更大的样本量
        assert result_50["sample_size"] <= result_100["sample_size"] <= result_500["sample_size"]

    def test_c_zero_different_aqls(self):
        result_01 = SamplingEngine.c_zero_sampling(lot_size=100, aql=0.05)
        result_10 = SamplingEngine.c_zero_sampling(lot_size=100, aql=0.10)

        # 两者都应该有效
        assert result_01["sample_size"] > 0
        assert result_10["sample_size"] > 0

    def test_c_zero_description(self):
        result = SamplingEngine.c_zero_sampling(lot_size=100, aql=0.10)

        assert "description" in result
        assert "100" in result["description"]
        assert str(result["sample_size"]) in result["description"]


class TestCZeroDecision:
    """C=0 抽样判定测试"""

    def test_accept_zero_defects(self):
        results = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        result = SamplingEngine.c_zero_decision(results)

        assert result["decision"] == "accept"
        assert result["defects"] == 0
        assert result["sample_size"] == 10
        assert result["defect_rate"] == 0.0

    def test_reject_with_defects(self):
        results = [0, 0, 1, 0, 0, 0, 0, 0, 0, 0]
        result = SamplingEngine.c_zero_decision(results)

        assert result["decision"] == "reject"
        assert result["defects"] == 1
        assert result["sample_size"] == 10
        assert result["defect_rate"] == 10.0

    def test_reject_multiple_defects(self):
        results = [0, 0, 1, 0, 1, 0, 0, 0, 1, 0]
        result = SamplingEngine.c_zero_decision(results)

        assert result["decision"] == "reject"
        assert result["defects"] == 3
        assert result["defect_rate"] == 30.0

    def test_decision_description(self):
        results = [0, 0, 0, 0, 0]
        result = SamplingEngine.c_zero_decision(results)

        assert "description" in result
        assert "5" in result["description"]
        assert "0" in result["description"]
        assert "接收" in result["description"]

    def test_reject_description(self):
        results = [0, 1, 0, 0, 0]
        result = SamplingEngine.c_zero_decision(results)

        assert "拒收" in result["description"]
        assert "1" in result["description"]

    def test_empty_results(self):
        results = []
        result = SamplingEngine.c_zero_decision(results)

        assert result["decision"] == "accept"
        assert result["defects"] == 0
        assert result["sample_size"] == 0
        assert result["defect_rate"] == 0.0
