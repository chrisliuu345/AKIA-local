"""
Fractional Factorial Design 单元测试

验证来源:
    Montgomery D C (2017). Design and Analysis of Experiments, 9th ed.
    Table 8-2 through 8-5.
"""
import pytest
import numpy as np
from analysis.doe.fractional import (
    generate_design,
    analyze,
    compute_defining_relation,
    compute_resolution,
    compute_alias_structure,
    _base_factorial,
    _parse_generator,
    _apply_generator,
)


class TestBaseFactorial:
    """基础因子生成测试"""

    def test_k2(self):
        """2^2 = 4 行"""
        d = _base_factorial(2)
        assert d.shape == (4, 2)
        assert set(d.flatten()) <= {-1, 1}

    def test_k3(self):
        """2^3 = 8 行"""
        d = _base_factorial(3)
        assert d.shape == (8, 3)

    def test_orthogonality(self):
        """列间正交"""
        d = _base_factorial(3)
        for i in range(3):
            for j in range(i + 1, 3):
                assert np.dot(d[:, i], d[:, j]) == 0


class TestGeneratorParsing:
    """生成元解析测试"""

    def test_single_letter(self):
        """'A' → [0]"""
        assert _parse_generator("A") == [0]

    def test_multi_letter(self):
        """'ABC' → [0,1,2]"""
        assert _parse_generator("ABC") == [0, 1, 2]

    def test_lowercase(self):
        """'abc' → [0,1,2]"""
        assert _parse_generator("abc") == [0, 1, 2]


class TestGeneratorApplication:
    """生成元应用测试"""

    def test_ab_product(self):
        """D = A*B 列乘积"""
        base = _base_factorial(2)
        d_col = _apply_generator(base, [0, 1])
        expected = base[:, 0] * base[:, 1]
        np.testing.assert_array_equal(d_col, expected)


class TestDefiningRelation:
    """定义关系测试"""

    def test_single_generator(self):
        """单个生成元"""
        result = compute_defining_relation(["AB"])
        assert "AB" in result

    def test_two_generators(self):
        """两个生成元 + 乘积"""
        result = compute_defining_relation(["AB", "AC"])
        assert "AB" in result
        assert "AC" in result
        assert "BC" in result  # AB * AC = B*C (symmetric difference)

    def test_sorted_by_length(self):
        """按长度排序"""
        result = compute_defining_relation(["ABD", "ACE"])
        lengths = [len(w) for w in result]
        assert lengths == sorted(lengths)


class TestResolution:
    """分辨率测试"""

    def test_resolution_3(self):
        """最小词长 = 3"""
        assert compute_resolution(["ABC"]) == 3

    def test_resolution_4(self):
        """最小词长 = 4"""
        assert compute_resolution(["ABCD"]) == 4

    def test_resolution_5(self):
        """最小词长 = 5"""
        assert compute_resolution(["ABCDE"]) == 5

    def test_empty_relation(self):
        """空关系 = 999 (全因子)"""
        assert compute_resolution([]) == 999


class TestAliasStructure:
    """别名结构测试"""

    def test_2_3_1_aliases(self):
        """2^(3-1) 设计: A aliased with BC"""
        factors = ["A", "B", "C"]
        # D = AB, so C = AB (design has A, B, C columns)
        design = np.array([
            [1, 1, 1],
            [1, -1, -1],
            [-1, 1, -1],
            [-1, -1, 1],
        ])
        aliases = compute_alias_structure(factors, design)
        # A column == BC column, so A aliased with BC
        alias_groups = list(aliases.values())
        found_a_bc = any("A" in g and "B*C" in g for g in alias_groups)
        assert found_a_bc


class TestGenerateDesign:
    """设计生成测试"""

    def test_2_3_1(self):
        """2^(3-1): 4 runs, 3 factors"""
        factors = ["A", "B", "C"]
        df = generate_design(factors, fraction="1/2", random_seed=42)
        assert len(df) == 4
        assert list(df.columns[:3]) == ["A", "B", "C"]

    def test_2_4_1(self):
        """2^(4-1): 8 runs, 4 factors"""
        factors = ["A", "B", "C", "D"]
        df = generate_design(factors, fraction="1/2", random_seed=42)
        assert len(df) == 8

    def test_2_5_2(self):
        """2^(5-2): 8 runs, 5 factors"""
        factors = ["A", "B", "C", "D", "E"]
        df = generate_design(factors, fraction="1/4", random_seed=42)
        assert len(df) == 8

    def test_2_7_3(self):
        """2^(7-3): 16 runs, 7 factors"""
        factors = ["A", "B", "C", "D", "E", "F", "G"]
        df = generate_design(factors, fraction="1/8", random_seed=42)
        assert len(df) == 16

    def test_center_points(self):
        """中心点添加"""
        factors = ["A", "B", "C"]
        df = generate_design(factors, fraction="1/2", center_points=3, random_seed=42)
        assert len(df) == 7  # 4 + 3

    def test_block_column(self):
        """区组列"""
        factors = ["A", "B", "C"]
        df = generate_design(factors, fraction="1/2", block=True, random_seed=42)
        assert "Block" in df.columns

    def test_resolution_in_output(self):
        """分辨率记录在输出中"""
        factors = ["A", "B", "C"]
        df = generate_design(factors, fraction="1/2", random_seed=42)
        assert "Resolution" in df.columns
        assert df["Resolution"].iloc[0] > 0

    def test_defining_relation_in_output(self):
        """定义关系记录在输出中"""
        factors = ["A", "B", "C"]
        df = generate_design(factors, fraction="1/2", random_seed=42)
        assert "DefiningRelation" in df.columns
        assert "I=" in df["DefiningRelation"].iloc[0]

    def test_invalid_fraction(self):
        """无效分数应报错"""
        with pytest.raises(ValueError):
            generate_design(["A", "B", "C"], fraction="1/3")

    def test_too_few_factors(self):
        """因子数 < 2 应报错"""
        with pytest.raises(ValueError):
            generate_design(["A"], fraction="1/2")

    def test_too_many_factors(self):
        """因子数 > 15 应报错"""
        with pytest.raises(ValueError):
            generate_design([f"F{i}" for i in range(16)], fraction="1/2")

    def test_values_are_pm1(self):
        """设计值应为 ±1"""
        factors = ["A", "B", "C", "D"]
        df = generate_design(factors, fraction="1/2", random_seed=42)
        for f in factors:
            assert set(df[f].unique()) <= {-1, 1}


class TestAnalyze:
    """分析测试"""

    def _make_data(self):
        """构造 2^(4-1) 已知数据"""
        np.random.seed(42)
        factors = ["A", "B", "C", "D"]
        df = generate_design(factors, fraction="1/2", random_seed=42)
        df["Response"] = 10.0 + 5.0 * df["A"] - 3.0 * df["B"] + np.random.normal(0, 0.3, 8)
        return df, factors

    def test_analyze_returns_dict(self):
        """analyze 返回完整字典"""
        df, factors = self._make_data()
        result = analyze(df, "Response", factors)
        assert result["chart_type"] == "Fractional Factorial Design"
        assert "effects" in result
        assert "anova" in result
        assert "alias_groups" in result

    def test_effects_sign_and_magnitude(self):
        """A 和 B 效应应为正/负且较大"""
        df, factors = self._make_data()
        result = analyze(df, "Response", factors)
        assert result["effects"]["A"] > result["effects"]["C"]
        assert result["effects"]["B"] < 0

    def test_n8_known_values(self):
        """无噪声已知值精确匹配"""
        factors = ["A", "B", "C", "D"]
        df = generate_design(factors, fraction="1/2", random_seed=42)
        df["Response"] = 5.0 + 4.0 * df["A"] - 2.0 * df["B"]
        result = analyze(df, "Response", factors)
        assert abs(result["effects"]["A"] - 8.0) < 0.01
        assert abs(result["effects"]["B"] - (-4.0)) < 0.01

    def test_r_squared_range(self):
        """R² 在 [0, 1]"""
        df, factors = self._make_data()
        result = analyze(df, "Response", factors)
        assert 0 <= result["model_r_squared"] <= 1

    def test_pareto_sorted(self):
        """Pareto 按效应绝对值降序"""
        df, factors = self._make_data()
        result = analyze(df, "Response", factors)
        effects = [p["effect"] for p in result["pareto_data"]]
        assert effects == sorted(effects, reverse=True)

    def test_alias_groups_present(self):
        """别名组存在"""
        factors = ["A", "B", "C"]
        df = generate_design(factors, fraction="1/2", random_seed=42)
        df["Response"] = 10.0 + 2.0 * df["A"]
        result = analyze(df, "Response", factors)
        assert isinstance(result["alias_groups"], dict)
