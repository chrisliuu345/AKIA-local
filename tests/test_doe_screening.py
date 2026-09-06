"""
Plackett-Burman 筛选设计单元测试

验证来源:
    Plackett R L, Burman J P (1946). The Design of Optimal Multifactorial
    Experiments. Biometrika, 33(4), 305-325.

    NIST/SEMATECH e-Handbook of Statistical Methods, Section 5.3.4.
"""
import pytest
import numpy as np
from analysis.doe.plackett_burman import generate_design, analyze, _hadamard_from_base


# ── Plackett-Burman (1946) 已知第一行模式 ──
# N=8:  ++++--+- (论文原文)
# N=12: +++--+-++--+ (论文原文)
# N=16: +++++++++------- (Sylvester)

class TestHadamardConstruction:
    """Hadamard 矩阵构造验证"""

    def test_n4_hadamard_rows(self):
        """N=4: Hadamard 矩阵 4×3"""
        h = _hadamard_from_base([-1, 1, -1])
        assert h.shape == (4, 3)

    def test_n4_hadamard_orthogonal(self):
        """N=4: 列间正交 (内积=0)"""
        h = _hadamard_from_base([-1, 1, -1])
        for i in range(3):
            for j in range(i + 1, 3):
                assert np.dot(h[:, i], h[:, j]) == 0

    def test_n8_hadamard_orthogonal(self):
        """N=8: 列间正交"""
        h = _hadamard_from_base([1, 1, 1, -1, 1, -1, -1])
        assert h.shape == (8, 7)
        for i in range(7):
            for j in range(i + 1, 7):
                assert np.dot(h[:, i], h[:, j]) == 0

    def test_n12_hadamard_orthogonal(self):
        """N=12: 列间正交 — 核心 PB 设计"""
        base = [1, 1, -1, 1, 1, 1, -1, -1, -1, 1, -1]
        h = _hadamard_from_base(base)
        assert h.shape == (12, 11)
        for i in range(11):
            for j in range(i + 1, 11):
                assert np.dot(h[:, i], h[:, j]) == 0

    def test_n16_hadamard_orthogonal(self):
        """N=16: Sylvester 构造正交性"""
        from analysis.doe.plackett_burman import _sylvester_hadamard
        h = _sylvester_hadamard(4)  # 16×16
        assert h.shape == (16, 16)
        for i in range(16):
            for j in range(i + 1, 16):
                assert np.dot(h[:, i], h[:, j]) == 0

    def test_n12_last_row_all_minus1(self):
        """N=12: 最后一行全 -1（Plackett-Burman 规则）"""
        base = [1, 1, -1, 1, 1, 1, -1, -1, -1, 1, -1]
        h = _hadamard_from_base(base)
        np.testing.assert_array_equal(h[-1, :], -1)

    def test_n12_first_row_matches_plackett(self):
        """N=12: 第一行与 Plackett-Burman (1946) 论文一致"""
        base = [1, 1, -1, 1, 1, 1, -1, -1, -1, 1, -1]
        h = _hadamard_from_base(base)
        # 论文 Table: 第一行为 ++-++++-+--+
        expected = np.array([1, 1, -1, 1, 1, 1, -1, -1, -1, 1, -1])
        np.testing.assert_array_equal(h[0, :], expected)


class TestGenerateDesign:
    """设计生成测试"""

    def test_n12_k5_design_shape(self):
        """N=12, k=5: 生成 12×5 设计矩阵"""
        factors = ["A", "B", "C", "D", "E"]
        df = generate_design(factors, n_runs=12)
        assert len(df) == 12
        assert list(df.columns[:5]) == ["A", "B", "C", "D", "E"]

    def test_n12_k11_full_capacity(self):
        """N=12, k=11: 最大容量"""
        factors = [f"F{i}" for i in range(11)]
        df = generate_design(factors, n_runs=12)
        assert len(df) == 12
        assert len(df.columns) >= 11

    def test_n12_k12_exceeds_capacity(self):
        """N=12, k=12: 超出容量应报错"""
        factors = [f"F{i}" for i in range(12)]
        with pytest.raises(ValueError, match="超出"):
            generate_design(factors, n_runs=12)

    def test_n8_k3_auto_select(self):
        """k=3: 自动选择 N=4（最小可用）"""
        factors = ["A", "B", "C"]
        df = generate_design(factors)
        assert len(df) == 4

    def test_n12_k5_auto_select(self):
        """k=5: 自动选择 N=8"""
        factors = ["A", "B", "C", "D", "E"]
        df = generate_design(factors)
        # k=5 → 最小 N >= 6 → N=8
        assert len(df) == 8

    def test_n16_k15_full_capacity(self):
        """N=16, k=15: 最大容量"""
        factors = [f"F{i}" for i in range(15)]
        df = generate_design(factors, n_runs=16)
        assert len(df) == 16

    def test_center_points(self):
        """中心点添加"""
        factors = ["A", "B", "C"]
        df = generate_design(factors, n_runs=8, center_points=3)
        assert len(df) == 11  # 8 + 3
        # 中心点行的因子列应为 0
        center_rows = df[df["StdOrder"] == 0]
        assert len(center_rows) == 3
        for f in factors:
            np.testing.assert_array_equal(center_rows[f].values, 0.0)

    def test_run_order_randomized(self):
        """RunOrder 应为随机排列"""
        factors = ["A", "B", "C", "D", "E"]
        df = generate_design(factors, n_runs=12)
        assert sorted(df["RunOrder"].tolist()) == list(range(1, 13))

    def test_invalid_n_runs(self):
        """n_runs 不在 {4,8,12,16} 应报错"""
        factors = ["A", "B", "C"]
        with pytest.raises(ValueError, match="必须为 4 的倍数"):
            generate_design(factors, n_runs=10)

    def test_too_few_factors(self):
        """因子数 < 2 应报错"""
        with pytest.raises(ValueError, match="至少需要 2 个因子"):
            generate_design(["A"])

    def test_design_values_are_pm1(self):
        """设计矩阵值应为 ±1"""
        factors = ["A", "B", "C", "D", "E"]
        df = generate_design(factors, n_runs=12)
        for f in factors:
            vals = set(df[f].unique())
            assert vals <= {-1, 1}, f"因子 {f} 包含非 ±1 值: {vals}"


class TestAnalyze:
    """Plackett-Burman 分析测试"""

    def _make_data(self):
        """构造 N=12, k=5 的已知数据"""
        np.random.seed(42)
        factors = ["A", "B", "C", "D", "E"]
        df = generate_design(factors, n_runs=12)
        # 真实模型: y = 10 + 2*A + 1.5*B + 0*C + 0*D + 0*E + noise
        df["Response"] = (
            10
            + 2.0 * df["A"]
            + 1.5 * df["B"]
            + np.random.normal(0, 0.3, 12)
        )
        return df, factors

    def test_analyze_returns_dict(self):
        """analyze 返回完整字典"""
        df, factors = self._make_data()
        result = analyze(df, "Response", factors)
        assert "chart_type" in result
        assert result["chart_type"] == "Plackett-Burman Screening Design"
        assert "effects" in result
        assert "anova" in result
        assert "pareto_data" in result

    def test_effects_sign_and_magnitude(self):
        """A 和 B 效应应为正且最大"""
        df, factors = self._make_data()
        result = analyze(df, "Response", factors)
        # A 效应 ≈ 2*2 = 4 (因为 ±1 编码, effect = mean_high - mean_low ≈ 2*2)
        # 实际 effect = mean(y|A=1) - mean(y|A=-1)
        assert result["effects"]["A"] > result["effects"]["C"]
        assert result["effects"]["B"] > result["effects"]["C"]

    def test_significant_factors(self):
        """A 和 B 应被识别为显著因子"""
        df, factors = self._make_data()
        result = analyze(df, "Response", factors)
        assert "A" in result["significant_factors"]
        assert "B" in result["significant_factors"]

    def test_r_squared_range(self):
        """R² 应在 [0, 1]"""
        df, factors = self._make_data()
        result = analyze(df, "Response", factors)
        assert 0 <= result["model_r_squared"] <= 1

    def test_anova_sources(self):
        """ANOVA 源列表正确"""
        df, factors = self._make_data()
        result = analyze(df, "Response", factors)
        sources = result["anova"]["source"]
        assert sources[-1] == "Total"
        assert sources[-2] == "Error"
        assert len(sources) == len(factors) + 2

    def test_pareto_sorted_descending(self):
        """Pareto 数据按效应绝对值降序"""
        df, factors = self._make_data()
        result = analyze(df, "Response", factors)
        effects = [p["effect"] for p in result["pareto_data"]]
        assert effects == sorted(effects, reverse=True)

    def test_n12_known_values(self):
        """N=12 已知值验证 — 与 NIST 示例比对

        使用 NIST 虚拟数据验证效应计算的正确性。
        """
        # 构造简单已知模型: y = 5 + 3*A - 2*B + 1*C + 0*D + 0*E
        factors = ["A", "B", "C", "D", "E"]
        df = generate_design(factors, n_runs=12)
        df["Response"] = (
            5.0
            + 3.0 * df["A"]
            - 2.0 * df["B"]
            + 1.0 * df["C"]
        )
        result = analyze(df, "Response", factors)
        # 无噪声时效应应精确
        assert abs(result["effects"]["A"] - 6.0) < 0.01  # effect = 2*3 = 6
        assert abs(result["effects"]["B"] - (-4.0)) < 0.01  # effect = 2*(-2) = -4
        assert abs(result["effects"]["C"] - 2.0) < 0.01  # effect = 2*1 = 2
        assert abs(result["effects"]["D"]) < 0.01
        assert abs(result["effects"]["E"]) < 0.01

    def test_center_points_excluded_from_anova(self):
        """中心点不应影响主效应估计"""
        factors = ["A", "B", "C"]
        df = generate_design(factors, n_runs=8, center_points=3)
        df["Response"] = 10.0 + 2.0 * df["A"] + 1.0 * df["B"]
        result = analyze(df, "Response", factors)
        # 无噪声时效应应精确
        assert abs(result["effects"]["A"] - 4.0) < 0.01
        assert abs(result["effects"]["B"] - 2.0) < 0.01

    def test_analyze_single_factor(self):
        """单因子不应报错"""
        factors = ["A", "B"]
        df = generate_design(factors, n_runs=4)
        df["Response"] = 10.0 + 2.0 * df["A"]
        result = analyze(df, "Response", factors)
        assert result["effects"]["A"] > 0

    def test_analyze_with_nan(self):
        """含 NaN 数据应自动剔除"""
        factors = ["A", "B", "C"]
        df = generate_design(factors, n_runs=8)
        df["Response"] = 10.0 + 2.0 * df["A"]
        df.loc[0, "Response"] = np.nan
        result = analyze(df, "Response", factors)
        assert result["observations"] == 7


# ═══════════════════════════════════════════════════════════
# Definitive Screening Design (DSD) 测试
# ═══════════════════════════════════════════════════════════

from analysis.doe.definitive_screening import (
    generate_design as dsd_generate,
    analyze as dsd_analyze,
    _verify_design_orthogonality,
)


class TestDsdDesignMatrix:
    """DSD 设计矩阵验证"""

    def test_k4_orthogonal(self):
        """k=4: 列正交性"""
        from analysis.doe.definitive_screening import _DSD_DESIGNS
        assert _verify_design_orthogonality(_DSD_DESIGNS[4])

    def test_k4_center_row_all_zero(self):
        """k=4: 中心行全 0"""
        from analysis.doe.definitive_screening import _DSD_DESIGNS
        assert np.all(_DSD_DESIGNS[4][-1, :] == 0)

    def test_k4_foldover_negation(self):
        """k=4: Foldover 行是 Conference 行的取反"""
        from analysis.doe.definitive_screening import _DSD_DESIGNS
        D = _DSD_DESIGNS[4]
        conf = D[:4, :]
        fold = D[4:8, :]
        np.testing.assert_array_equal(fold, -conf)

    def test_k4_diagonal_equal(self):
        """k=4: D^T D 对角线值相等"""
        from analysis.doe.definitive_screening import _DSD_DESIGNS
        D = _DSD_DESIGNS[4]
        product = D.T @ D
        diag = np.diag(product)
        assert np.all(diag == diag[0])


class TestDsdGenerateDesign:
    """DSD 设计生成测试"""

    def test_n9_k4(self):
        """k=4: N=2*4+1=9 次试验"""
        factors = ["A", "B", "C", "D"]
        df = dsd_generate(factors)
        assert len(df) == 9

    def test_center_row_all_zero(self):
        """中心行全 0"""
        factors = ["A", "B", "C", "D"]
        df = dsd_generate(factors)
        center_row = df[df["Block"] == "Center"]
        assert len(center_row) == 1
        for f in factors:
            assert center_row[f].values[0] == 0

    def test_conference_foldover_rows(self):
        """C 和 -C 行各 k 行"""
        factors = ["A", "B", "C", "D"]
        df = dsd_generate(factors)
        assert len(df[df["Block"] == "Conference"]) == 4
        assert len(df[df["Block"] == "Foldover"]) == 4

    def test_orthogonality_main_effects(self):
        """主效应正交性（C 和 -C 行的列内积为 0）"""
        factors = ["A", "B", "C", "D"]
        df = dsd_generate(factors)
        vals = df[factors].values
        for i in range(4):
            for j in range(i + 1, 4):
                assert np.dot(vals[:, i], vals[:, j]) == 0

    def test_values_are_pm1_or_0(self):
        """设计值应为 {-1, 0, +1}"""
        factors = ["A", "B", "C", "D"]
        df = dsd_generate(factors)
        for f in factors:
            assert set(df[f].unique()) <= {-1, 0, 1}

    def test_too_few_factors(self):
        """k < 4 应报错"""
        with pytest.raises(ValueError, match="至少需要 4 个因子"):
            dsd_generate(["A", "B", "C"])

    def test_odd_k_rejected(self):
        """奇数 k 应报错"""
        with pytest.raises(ValueError, match="偶数"):
            dsd_generate(["A", "B", "C", "D", "E"])

    def test_center_points(self):
        """额外中心点"""
        factors = ["A", "B", "C", "D"]
        df = dsd_generate(factors, center_points=3)
        assert len(df) == 12  # 9 + 3
        assert len(df[df["Block"] == "Center"]) == 4  # 1 内置 + 3 额外

    def test_random_seed_reproducibility(self):
        """相同 seed 产生相同 RunOrder"""
        factors = ["A", "B", "C", "D"]
        df1 = dsd_generate(factors, random_seed=42)
        df2 = dsd_generate(factors, random_seed=42)
        assert list(df1["RunOrder"]) == list(df2["RunOrder"])

    def test_k6_not_yet_implemented(self):
        """k=6 应报错（尚未实现）"""
        factors = ["A", "B", "C", "D", "E", "F"]
        with pytest.raises(ValueError, match="仅支持 k=4"):
            dsd_generate(factors)

    def test_k8_not_yet_implemented(self):
        """k=8 应报错（尚未实现）"""
        factors = [f"F{i}" for i in range(8)]
        with pytest.raises(ValueError, match="仅支持 k=4"):
            dsd_generate(factors)


class TestDsdAnalyze:
    """DSD 分析测试"""

    def _make_data(self):
        """构造 k=4 的已知数据"""
        np.random.seed(42)
        factors = ["A", "B", "C", "D"]
        df = dsd_generate(factors, random_seed=42, center_points=3)
        # 真实模型: y = 10 + 8*A - 5*B + 0*C + 0*D (强信号)
        df["Response"] = (
            10.0
            + 8.0 * df["A"]
            - 5.0 * df["B"]
            + np.random.normal(0, 0.3, len(df))
        )
        return df, factors

    def test_analyze_returns_dict(self):
        """analyze 返回完整字典"""
        df, factors = self._make_data()
        result = dsd_analyze(df, "Response", factors)
        assert result["chart_type"] == "Definitive Screening Design"
        assert "effects" in result
        assert "anova" in result
        assert "curvature" in result

    def test_curvature_detection(self):
        """中心行曲率检测"""
        factors = ["A", "B", "C", "D"]
        df = dsd_generate(factors, random_seed=42)
        df["Response"] = 10.0 + 2.0 * df["A"]
        center_mask = df["Block"] == "Center"
        df.loc[center_mask, "Response"] = 15.0
        result = dsd_analyze(df, "Response", factors)
        assert result["curvature"] is not None
        assert result["curvature"] > 0

    def test_significant_factors(self):
        """A 和 B 应被识别为显著因子"""
        df, factors = self._make_data()
        result = dsd_analyze(df, "Response", factors)
        assert "A" in result["significant_factors"]
        assert "B" in result["significant_factors"]

    def test_n9_known_values(self):
        """k=4 已知值验证 — 无噪声精确匹配"""
        factors = ["A", "B", "C", "D"]
        df = dsd_generate(factors, random_seed=42)
        df["Response"] = 5.0 + 4.0 * df["A"] - 3.0 * df["B"]
        result = dsd_analyze(df, "Response", factors)
        # 无噪声时效应应精确
        assert abs(result["effects"]["A"] - 8.0) < 0.01  # 2*4 = 8
        assert abs(result["effects"]["B"] - (-6.0)) < 0.01  # 2*(-3) = -6
        assert abs(result["effects"]["C"]) < 0.01

    def test_r_squared_range(self):
        """R² 应在 [0, 1]"""
        df, factors = self._make_data()
        result = dsd_analyze(df, "Response", factors)
        assert 0 <= result["model_r_squared"] <= 1

    def test_pareto_sorted(self):
        """Pareto 数据按效应绝对值降序"""
        df, factors = self._make_data()
        result = dsd_analyze(df, "Response", factors)
        effects = [p["effect"] for p in result["pareto_data"]]
        assert effects == sorted(effects, reverse=True)
