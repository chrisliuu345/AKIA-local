"""Cpm 田口能力指数测试"""
import pytest
import numpy as np
import pandas as pd
from analysis.capability.normal_cap import analyze
from analysis.capability._utils import get_capability_grade


class TestCpm:
    """Cpm 计算测试"""

    def test_cpm_basic(self):
        """基本 Cpm 计算"""
        data = pd.Series([4.5, 4.8, 5.0, 5.2, 5.5])
        result = analyze(data, usl=10, lsl=0, target=5)

        assert "cpm" in result["capability"]
        assert result["capability"]["target"] == 5.0
        # Cpm 应该大于或等于 Cpk（数据围绕目标）
        assert result["capability"]["cpm"] >= result["capability"]["cpk"]

    def test_cpm_without_target(self):
        """无目标值时 Cpm 应为 None"""
        data = pd.Series([4.5, 4.8, 5.0, 5.2, 5.5])
        result = analyze(data, usl=10, lsl=0)

        assert result["capability"]["cpm"] is None

    def test_cpm_off_target(self):
        """数据偏离目标时 Cpm 应减小"""
        data = pd.Series([7.0, 7.2, 7.5, 7.8, 8.0])  # 偏离目标 T=5
        result = analyze(data, usl=10, lsl=0, target=5)

        assert result["capability"]["cpm"] < result["capability"]["cp"]

    def test_cpm_constant_on_target(self):
        """常数数据且在目标值上"""
        data = pd.Series([5.0, 5.0, 5.0, 5.0, 5.0])
        result = analyze(data, usl=10, lsl=0, target=5)

        # σ_T=0 时 Cpm 应为 inf
        assert result["capability"]["cpm"] == "inf"

    def test_cpm_known_value(self):
        """Cpm 已知值验证"""
        data = pd.Series([4.8, 5.0, 5.2, 4.9, 5.1, 5.0, 5.1, 4.9, 5.0, 5.1])
        result = analyze(data, usl=10, lsl=0, target=5)

        # 手动计算验证
        sigma_t = np.sqrt(np.sum((data - 5) ** 2) / (len(data) - 1))
        expected_cpm = (10 - 0) / (6 * sigma_t)

        assert abs(result["capability"]["cpm"] - round(expected_cpm, 4)) < 0.001

    def test_cpm_with_subgroup(self):
        """带子组的 Cpm 计算"""
        data = pd.Series([4.5, 4.8, 5.0, 5.2, 5.5, 4.6, 4.9, 5.1, 5.3, 5.4])
        result = analyze(data, usl=10, lsl=0, target=5, subgroup_size=5)

        assert "cpm" in result["capability"]
        assert result["capability"]["target"] == 5.0


class TestGetCapabilityGrade:
    """评级函数测试"""

    def test_grade_a_plus(self):
        assert get_capability_grade(1.67) == "A+ (特优)"
        assert get_capability_grade(2.0) == "A+ (特优)"

    def test_grade_a(self):
        assert get_capability_grade(1.33) == "A (优)"
        assert get_capability_grade(1.5) == "A (优)"

    def test_grade_b(self):
        assert get_capability_grade(1.0) == "B (良好)"
        assert get_capability_grade(1.2) == "B (良好)"

    def test_grade_c(self):
        assert get_capability_grade(0.67) == "C (一般)"
        assert get_capability_grade(0.8) == "C (一般)"

    def test_grade_d(self):
        assert get_capability_grade(0.5) == "D (差)"
        assert get_capability_grade(0.0) == "D (差)"


class TestNormalCapability:
    """正态能力分析回归测试"""

    def test_basic_capability(self):
        """基本能力分析"""
        data = pd.Series([4.5, 4.8, 5.0, 5.2, 5.5, 4.6, 4.9, 5.1, 5.3, 5.4])
        result = analyze(data, usl=6, lsl=4)

        assert "capability" in result
        assert "cp" in result["capability"]
        assert "cpk" in result["capability"]
        assert "pp" in result["capability"]
        assert "ppk" in result["capability"]

    def test_capability_with_target(self):
        """带目标值的能力分析"""
        data = pd.Series([4.5, 4.8, 5.0, 5.2, 5.5, 4.6, 4.9, 5.1, 5.3, 5.4])
        result = analyze(data, usl=6, lsl=4, target=5)

        assert result["capability"]["target"] == 5.0
        assert "cpm" in result["capability"]

    def test_capability_without_spec(self):
        """无规格限的能力分析"""
        data = pd.Series([4.5, 4.8, 5.0, 5.2, 5.5])
        result = analyze(data)

        assert result["capability"]["usl"] is None
        assert result["capability"]["lsl"] is None
