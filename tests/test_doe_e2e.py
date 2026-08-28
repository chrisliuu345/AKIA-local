"""
DOE 全流程 E2E 测试

验证各设计类型的完整工作流：设计生成 → 数据填充 → 分析 → 结果验证
"""
import pytest
import numpy as np
import pandas as pd
from analysis.doe import (
    plackett_burman, definitive_screening, fractional,
    taguchi, mixture, factorial, response_surface, box_behnken,
)


class TestPlackettBurmanE2E:
    """Plackett-Burman 筛选设计 E2E 测试"""

    def test_pb_full_workflow(self):
        """PB 设计完整流程: 生成 → 填充 → 分析"""
        # 1. 生成设计
        factors = ["Temperature", "Pressure", "Time", "Speed", "Concentration"]
        df = plackett_burman.generate_design(factors, n_runs=12)

        # 2. 填充响应（真实模型: y = 100 + 5*Temp + 3*Pressure + noise）
        np.random.seed(42)
        df["Yield"] = (
            100
            + 5.0 * df["Temperature"]
            + 3.0 * df["Pressure"]
            + np.random.normal(0, 1.0, len(df))
        )

        # 3. 分析
        result = plackett_burman.analyze(df, "Yield", factors)

        # 4. 验证
        assert result["chart_type"] == "Plackett-Burman Screening Design"
        assert result["observations"] == 12
        assert "effects" in result
        assert "anova" in result
        assert "pareto_data" in result

        # Temperature 应为最显著因子
        assert result["effects"]["Temperature"] > result["effects"]["Speed"]
        assert "Temperature" in result["significant_factors"]
        assert "Pressure" in result["significant_factors"]

        # R² 应合理
        assert 0.5 < result["model_r_squared"] < 1.0

    def test_pb_center_points(self):
        """PB 设计含中心点"""
        factors = ["A", "B", "C"]
        df = plackett_burman.generate_design(factors, n_runs=8, center_points=2)

        assert len(df) == 10  # 8 + 2
        center_rows = df[df["StdOrder"] == 0]
        assert len(center_rows) == 2


class TestDefinitiveScreeningE2E:
    """Definitive Screening Design E2E 测试"""

    def test_dsd_full_workflow(self):
        """DSD 设计完整流程"""
        # 1. 生成设计
        factors = ["A", "B", "C", "D"]
        df = definitive_screening.generate_design(factors, random_seed=42)

        # 2. 填充响应
        np.random.seed(42)
        df["Response"] = (
            10.0
            + 8.0 * df["A"]
            - 5.0 * df["B"]
            + np.random.normal(0, 0.5, len(df))
        )

        # 3. 分析
        result = definitive_screening.analyze(df, "Response", factors)

        # 4. 验证
        assert result["chart_type"] == "Definitive Screening Design"
        assert result["observations"] == 9
        assert "curvature" in result
        assert "effects" in result

        # A 和 B 应为显著因子
        assert "A" in result["significant_factors"]
        assert "B" in result["significant_factors"]

    def test_dsd_curvature_detection(self):
        """DSD 曲率检测"""
        factors = ["A", "B", "C", "D"]
        df = definitive_screening.generate_design(factors, random_seed=42)

        # 在中心行添加曲率
        df["Response"] = 10.0 + 2.0 * df["A"]
        center_mask = df["Block"] == "Center"
        df.loc[center_mask, "Response"] = 20.0  # 中心行响应更高

        result = definitive_screening.analyze(df, "Response", factors)
        assert result["curvature"] is not None
        assert result["curvature"] > 0  # 检测到正曲率


class TestFractionalFactorialE2E:
    """部分因子设计 E2E 测试"""

    def test_fractional_full_workflow(self):
        """部分因子设计完整流程"""
        # 1. 生成设计
        factors = ["A", "B", "C", "D", "E"]
        df = fractional.generate_design(factors, fraction="1/2", random_seed=42)

        # 2. 填充响应
        np.random.seed(42)
        df["Yield"] = (
            50
            + 3.0 * df["A"]
            - 2.0 * df["B"]
            + 1.5 * df["C"]
            + np.random.normal(0, 0.5, len(df))
        )

        # 3. 分析
        result = fractional.analyze(df, "Yield", factors)

        # 4. 验证
        assert result["chart_type"] == "Fractional Factorial Design"
        assert result["observations"] == 16  # 2^(5-1) = 16
        assert "effects" in result
        assert "alias_groups" in result
        assert "model_r_squared" in result

        # 主效应应被正确估计
        assert abs(result["effects"]["A"]) > abs(result["effects"]["E"])


class TestTaguchiE2E:
    """田口设计 E2E 测试"""

    def test_taguchi_l9_workflow(self):
        """L9 田口设计完整流程"""
        # 1. 生成设计
        factors = ["Temperature", "Time", "Pressure"]
        df = taguchi.generate_design(factors, array="L9", random_seed=42)

        # 2. 填充响应（望大特性）
        np.random.seed(42)
        df["Strength"] = (
            100
            + 10.0 * (df["Temperature"] - 1)
            + 5.0 * (df["Time"] - 1)
            + np.random.normal(0, 2.0, len(df))
        )

        # 3. 分析
        result = taguchi.analyze(df, "Strength", factors, sn_type="larger_is_better")

        # 4. 验证
        assert result["chart_type"] == "Taguchi Analysis"
        assert result["observations"] == 9
        assert "response_table" in result
        assert "anova" in result
        assert "optimal" in result
        assert "predicted_sn" in result

        # 验证响应表结构
        for factor in factors:
            assert factor in result["response_table"]
            assert "level_averages" in result["response_table"][factor]
            assert "delta" in result["response_table"][factor]
            assert "best_level" in result["response_table"][factor]

    def test_taguchi_sn_ratios(self):
        """SN 比计算"""
        # 望大特性
        sn_large = taguchi.compute_sn_ratio(np.array([10, 12, 11]), "larger_is_better")
        assert sn_large > 0

        # 望小特性
        sn_small = taguchi.compute_sn_ratio(np.array([0.1, 0.2, 0.15]), "smaller_is_better")
        assert sn_small > 0

        # 望目特性
        sn_nom = taguchi.compute_sn_ratio(np.array([10, 10, 10]), "nominal_is_best")
        assert sn_nom > 0


class TestMixtureE2E:
    """混合设计 E2E 测试"""

    def test_simplex_centroid_workflow(self):
        """Simplex Centroid 混合设计完整流程"""
        # 1. 生成设计
        components = ["Component_A", "Component_B", "Component_C"]
        df = mixture.simplex_centroid(components)

        # 2. 填充响应（Scheffé 二次模型）
        np.random.seed(42)
        df["Response"] = (
            80 * df["Component_A"]
            + 60 * df["Component_B"]
            + 70 * df["Component_C"]
            + 20 * df["Component_A"] * df["Component_B"]
            + np.random.normal(0, 1.0, len(df))
        )

        # 3. 分析
        result = mixture.analyze(df, "Response", components, model="quadratic")

        # 4. 验证
        assert result["chart_type"] == "Mixture Design Analysis"
        assert result["observations"] == 7  # 2^3 - 1 = 7
        assert "coefficients" in result
        assert "anova" in result
        assert "r_squared" in result

        # 验证系数结构
        assert "Component_A" in result["coefficients"]
        assert "Component_A*Component_B" in result["coefficients"]

    def test_simplex_lattice_workflow(self):
        """Simplex Lattice 混合设计"""
        components = ["X", "Y", "Z"]
        df = mixture.simplex_lattice(components, degree=2)

        # 验证设计点
        assert len(df) > 0
        # 所有行的比例之和应为 1
        for _, row in df.iterrows():
            assert abs(sum(row[c] for c in components) - 1.0) < 1e-10

    def test_extreme_vertices_workflow(self):
        """Extreme Vertices 混合设计"""
        components = ["A", "B", "C"]
        lower = [0.1, 0.2, 0.1]
        upper = [0.6, 0.5, 0.4]

        df = mixture.extreme_vertices(components, lower, upper)

        # 验证约束
        assert len(df) > 0
        for _, row in df.iterrows():
            total = sum(row[c] for c in components)
            assert abs(total - 1.0) < 1e-10
            for i, c in enumerate(components):
                assert lower[i] - 1e-10 <= row[c] <= upper[i] + 1e-10


class TestFullFactorialE2E:
    """全因子设计 E2E 测试"""

    def test_2k_factorial_workflow(self):
        """2^k 全因子设计完整流程"""
        # 1. 生成设计
        factors = ["A", "B"]
        df = factorial.generate_design(factors, replicates=2)

        # 2. 填充响应
        np.random.seed(42)
        df["Yield"] = (
            50
            + 5.0 * df["A"]
            + 3.0 * df["B"]
            + 2.0 * df["A"] * df["B"]
            + np.random.normal(0, 0.5, len(df))
        )

        # 3. 分析
        result = factorial.analyze_factorial(df, "Yield", factors)

        # 4. 验证
        assert result["chart_type"] == "Factorial DOE Analysis"
        assert "effects" in result
        assert "anova" in result

        # 主效应应被正确估计
        assert abs(result["effects"]["A"]) > abs(result["effects"]["B"])


class TestResponseSurfaceE2E:
    """响应曲面设计 E2E 测试"""

    def test_ccd_workflow(self):
        """CCD 响应曲面设计完整流程"""
        # 使用内置 CCD 设计
        factors = ["X1", "X2", "X3"]
        df = response_surface.generate_ccd(factors, center_points=3)

        # 填充响应
        np.random.seed(42)
        df["Response"] = (
            100
            + 10 * df["X1"]
            - 5 * df["X2"]
            + 3 * df["X1"] ** 2
            + np.random.normal(0, 1.0, len(df))
        )

        # 分析
        result = response_surface.analyze_response_surface(df, "Response", factors)

        # 验证
        assert "r_squared" in result
        assert "coefficients" in result


class TestBoxBehnkenE2E:
    """Box-Behnken 设计 E2E 测试"""

    def test_box_behnken_workflow(self):
        """Box-Behnken 设计完整流程"""
        factors = ["X1", "X2", "X3"]
        df = box_behnken.generate_bbd(factors, center_points=3)

        # 填充响应
        np.random.seed(42)
        df["Response"] = (
            50
            + 5 * df["X1"]
            - 3 * df["X2"]
            + 2 * df["X1"] * df["X2"]
            + np.random.normal(0, 0.5, len(df))
        )

        # 分析
        result = box_behnken.analyze_box_behnken(df, "Response", factors)

        # 验证
        assert "r_squared" in result
        assert "coefficients" in result


class TestCrossDesignComparison:
    """跨设计类型一致性测试"""

    def test_same_data_different_designs(self):
        """相同数据用不同设计类型分析，效应方向应一致"""
        # 生成全因子设计
        factors = ["A", "B"]
        df_full = factorial.generate_design(factors)
        np.random.seed(42)
        df_full["Y"] = 10 + 2 * df_full["A"] + 1 * df_full["B"]

        # 用全因子分析
        result_full = factorial.analyze_factorial(df_full, "Y", factors)

        # PB 设计 (N=4)
        df_pb = plackett_burman.generate_design(factors, n_runs=4)
        df_pb["Y"] = 10 + 2 * df_pb["A"] + 1 * df_pb["B"]
        result_pb = plackett_burman.analyze(df_pb, "Y", factors)

        # 效应方向应一致（符号相同）
        assert result_full["effects"]["A"] > 0
        assert result_pb["effects"]["A"] > 0
        assert result_full["effects"]["B"] > 0
        assert result_pb["effects"]["B"] > 0
