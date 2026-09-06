"""计量型抽样检验测试"""

import numpy as np
from core.sampling_engine import SamplingEngine


class TestMeasurementSampling:
    """计量型抽样方案测试"""

    def test_basic_measurement_sampling(self):
        result = SamplingEngine.measurement_sampling(
            lot_size=100,
            aql=1.0,
            usl=10.5,
            lsl=9.5,
        )

        assert result["method"] == "Measurement Sampling (GB/T 6378)"
        assert result["lot_size"] == 100
        assert result["sample_size"] > 0
        assert result["k_factor"] > 0
        assert result["usl"] == 10.5
        assert result["lsl"] == 9.5

    def test_measurement_sampling_different_aqls(self):
        result_01 = SamplingEngine.measurement_sampling(lot_size=100, aql=0.10)
        result_10 = SamplingEngine.measurement_sampling(lot_size=100, aql=1.0)
        result_65 = SamplingEngine.measurement_sampling(lot_size=100, aql=6.5)

        # 更严格的AQL应该有更大的k值
        assert result_01["k_factor"] > result_10["k_factor"] > result_65["k_factor"]

    def test_measurement_sampling_different_lot_sizes(self):
        result_50 = SamplingEngine.measurement_sampling(lot_size=50, aql=1.0)
        result_100 = SamplingEngine.measurement_sampling(lot_size=100, aql=1.0)
        result_500 = SamplingEngine.measurement_sampling(lot_size=500, aql=1.0)

        # 更大的批量应该有更大的样本量
        assert result_50["sample_size"] <= result_100["sample_size"] <= result_500["sample_size"]

    def test_measurement_sampling_usl_only(self):
        result = SamplingEngine.measurement_sampling(
            lot_size=100,
            aql=1.0,
            usl=10.5,
        )

        assert result["usl"] == 10.5
        assert result["lsl"] is None
        assert result["accept_upper"] is not None
        assert result["accept_lower"] is None

    def test_measurement_sampling_lsl_only(self):
        result = SamplingEngine.measurement_sampling(
            lot_size=100,
            aql=1.0,
            lsl=9.5,
        )

        assert result["usl"] is None
        assert result["lsl"] == 9.5
        assert result["accept_upper"] is None
        assert result["accept_lower"] is not None


class TestMeasurementDecision:
    """计量型抽样判定测试"""

    def test_accept_good_quality(self):
        np.random.seed(42)
        sample = np.random.normal(10.0, 0.1, 25)
        k_factor = 1.5

        result = SamplingEngine.measurement_decision(
            sample_data=sample,
            k_factor=k_factor,
            usl=10.5,
            lsl=9.5,
        )

        assert result["decision"] == "accept"
        assert result["sample_size"] == 25

    def test_reject_poor_quality(self):
        np.random.seed(42)
        sample = np.random.normal(10.5, 0.3, 25)  # 偏心且变异大
        k_factor = 1.5

        result = SamplingEngine.measurement_decision(
            sample_data=sample,
            k_factor=k_factor,
            usl=10.5,
            lsl=9.5,
        )

        assert result["decision"] == "reject"

    def test_decision_usl_only(self):
        np.random.seed(42)
        sample = np.random.normal(10.0, 0.2, 25)
        k_factor = 1.5

        result = SamplingEngine.measurement_decision(
            sample_data=sample,
            k_factor=k_factor,
            usl=10.5,
        )

        assert result["decision"] in ["accept", "reject"]
        assert result["usl"] == 10.5
        assert result["lsl"] is None

    def test_decision_lsl_only(self):
        np.random.seed(42)
        sample = np.random.normal(10.0, 0.2, 25)
        k_factor = 1.5

        result = SamplingEngine.measurement_decision(
            sample_data=sample,
            k_factor=k_factor,
            lsl=9.5,
        )

        assert result["decision"] in ["accept", "reject"]
        assert result["usl"] is None
        assert result["lsl"] == 9.5

    def test_insufficient_data(self):
        sample = np.array([10.0])
        result = SamplingEngine.measurement_decision(
            sample_data=sample,
            k_factor=1.5,
            usl=10.5,
            lsl=9.5,
        )

        assert result["decision"] == "error"
        assert "error" in result

    def test_zero_std(self):
        sample = np.full(25, 10.0)
        result = SamplingEngine.measurement_decision(
            sample_data=sample,
            k_factor=1.5,
            usl=10.5,
            lsl=9.5,
        )

        assert result["decision"] == "error"
        assert result["s"] == 0.0
