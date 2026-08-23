"""Johnson 变换测试"""
import pytest
import numpy as np
from analysis.capability.johnson_transform import (
    johnson_transform,
    inverse_transform,
    transform_value,
    JOHNSON_TYPES,
)


class TestJohnsonTransform:
    """Johnson 变换测试"""

    def test_auto_select(self):
        """自动选择变换类型"""
        np.random.seed(42)
        data = np.random.lognormal(0, 0.5, 100)
        result = johnson_transform(data, method="auto")

        assert result["type"] in JOHNSON_TYPES
        assert "transformed" in result
        assert "params" in result

    def test_su_transform(self):
        """SU 变换"""
        np.random.seed(42)
        data = np.random.normal(0, 1, 100)
        result = johnson_transform(data, method="SU")

        assert result["type"] == "SU"
        assert "gamma" in result["params"]
        assert "delta" in result["params"]
        assert "xi" in result["params"]
        assert "lambda" in result["params"]

    def test_sb_transform(self):
        """SB 变换"""
        np.random.seed(42)
        data = np.random.beta(2, 5, 100) * 10
        result = johnson_transform(data, method="SB")

        assert result["type"] == "SB"
        assert "gamma" in result["params"]
        assert "delta" in result["params"]

    def test_sl_transform(self):
        """SL 变换"""
        np.random.seed(42)
        data = np.random.exponential(1, 100) + 1
        result = johnson_transform(data, method="SL")

        assert result["type"] == "SL"
        assert "gamma" in result["params"]
        assert "delta" in result["params"]

    def test_ln_transform(self):
        """LN 变换"""
        np.random.seed(42)
        data = np.random.lognormal(0, 0.5, 100)
        result = johnson_transform(data, method="LN")

        assert result["type"] == "LN"
        assert "gamma" in result["params"]
        assert "delta" in result["params"]

    def test_insufficient_data(self):
        """数据量不足"""
        data = np.array([1.0, 2.0, 3.0])
        with pytest.raises(ValueError, match="数据量不足"):
            johnson_transform(data)

    def test_constant_data(self):
        """常数数据"""
        data = np.array([5.0, 5.0, 5.0, 5.0, 5.0])
        result = johnson_transform(data)

        assert result["type"] == "constant"

    def test_unsupported_method(self):
        """不支持的变换方法"""
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        with pytest.raises(ValueError, match="不支持的变换类型"):
            johnson_transform(data, method="INVALID")


class TestInverseTransform:
    """逆变换测试"""

    def test_su_inverse(self):
        """SU 逆变换"""
        params = {"gamma": 0, "delta": 1, "xi": 0, "lambda": 1}
        data = np.array([0.0, 1.0, -1.0, 2.0, -2.0])
        transformed = np.array([transform_value(x, params, "SU") for x in data])
        inverse = inverse_transform(transformed, params, "SU")

        np.testing.assert_array_almost_equal(data, inverse, decimal=5)

    def test_sb_inverse(self):
        """SB 逆变换"""
        params = {"gamma": 0, "delta": 1, "xi": 0, "lambda": 10}
        data = np.array([2.0, 5.0, 8.0])
        transformed = np.array([transform_value(x, params, "SB") for x in data])
        inverse = inverse_transform(transformed, params, "SB")

        np.testing.assert_array_almost_equal(data, inverse, decimal=5)

    def test_sl_inverse(self):
        """SL 逆变换"""
        params = {"gamma": 0, "delta": 1, "xi": 0, "lambda": 1}
        data = np.array([1.0, 2.0, 3.0])
        transformed = np.array([transform_value(x, params, "SL") for x in data])
        inverse = inverse_transform(transformed, params, "SL")

        np.testing.assert_array_almost_equal(data, inverse, decimal=5)

    def test_ln_inverse(self):
        """LN 逆变换"""
        params = {"gamma": 0, "delta": 1, "xi": 0, "lambda": 1}
        data = np.array([1.0, 2.0, 3.0])
        transformed = np.array([transform_value(x, params, "LN") for x in data])
        inverse = inverse_transform(transformed, params, "LN")

        np.testing.assert_array_almost_equal(data, inverse, decimal=5)


class TestTransformValue:
    """单值变换测试"""

    def test_su_value(self):
        """SU 单值变换"""
        params = {"gamma": 0, "delta": 1, "xi": 0, "lambda": 1}
        result = transform_value(0.0, params, "SU")
        assert result == 0.0

    def test_sb_value(self):
        """SB 单值变换"""
        params = {"gamma": 0, "delta": 1, "xi": 0, "lambda": 10}
        result = transform_value(5.0, params, "SB")
        assert np.isfinite(result)

    def test_sl_value(self):
        """SL 单值变换"""
        params = {"gamma": 0, "delta": 1, "xi": 0, "lambda": 1}
        result = transform_value(1.0, params, "SL")
        assert result == 0.0

    def test_ln_value(self):
        """LN 单值变换"""
        params = {"gamma": 0, "delta": 1, "xi": 0, "lambda": 1}
        result = transform_value(1.0, params, "LN")
        assert result == 0.0

    def test_sb_boundary(self):
        """SB 边界值"""
        params = {"gamma": 0, "delta": 1, "xi": 0, "lambda": 10}
        # 超出范围的值
        result_low = transform_value(-1.0, params, "SB")
        result_high = transform_value(11.0, params, "SB")
        assert not np.isfinite(result_low)
        assert not np.isfinite(result_high)


class TestJohnsonTypes:
    """支持的 Johnson 类型"""

    def test_supported_types(self):
        """支持的类型列表"""
        assert "SU" in JOHNSON_TYPES
        assert "SB" in JOHNSON_TYPES
        assert "SL" in JOHNSON_TYPES
        assert "LN" in JOHNSON_TYPES


class TestNonNormalCapability:
    """非正态能力分析集成测试"""

    def test_johnson_method(self):
        """Johnson 方法"""
        import pandas as pd
        from analysis.capability.non_normal_cap import analyze
        np.random.seed(42)
        data = pd.Series(np.random.lognormal(0, 0.5, 100))
        result = analyze(data, usl=5.0, lsl=0.5, method="johnson")

        assert result["method"] == "johnson"
        assert result["johnson_type"] in JOHNSON_TYPES
        assert "johnson_params" in result
