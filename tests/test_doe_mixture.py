"""
Mixture Design 单元测试

验证来源:
    Scheffé H (1958). Experiments with Mixtures. J Roy Stat Soc B, 20(2), 344-360.
    Cornell J A (2002). Experiments with Mixtures, 3rd ed. Wiley.
"""
import pytest
import numpy as np
from analysis.doe.mixture import (
    simplex_lattice,
    simplex_centroid,
    extreme_vertices,
    analyze,
    _build_scheffe_matrix,
    _model_term_names,
)


class TestSimplexLattice:
    """单纯形格子设计测试"""

    def test_3_2_point_count(self):
        """{3,2}: C(3+2-1,2) = 6 points"""
        df = simplex_lattice(["A", "B", "C"], degree=2)
        assert len(df) == 6

    def test_3_3_point_count(self):
        """{3,3}: C(5,3) = 10 points"""
        df = simplex_lattice(["A", "B", "C"], degree=3)
        assert len(df) == 10

    def test_4_2_point_count(self):
        """{4,2}: C(5,2) = 10 points"""
        df = simplex_lattice(["A", "B", "C", "D"], degree=2)
        assert len(df) == 10

    def test_proportions_sum_to_one(self):
        """所有行的比例之和 = 1"""
        df = simplex_lattice(["A", "B", "C"], degree=2)
        sums = df[["A", "B", "C"]].sum(axis=1)
        np.testing.assert_allclose(sums, 1.0, atol=1e-10)

    def test_proportions_in_lattice(self):
        """所有值在 {0, 1/m, ..., 1} 中"""
        m = 3
        df = simplex_lattice(["A", "B", "C"], degree=m)
        expected = np.arange(0, m + 1) / m
        for col in ["A", "B", "C"]:
            for v in df[col]:
                assert any(np.isclose(v, e) for e in expected)

    def test_too_few_components(self):
        """< 2 组分应报错"""
        with pytest.raises(ValueError):
            simplex_lattice(["A"])

    def test_too_many_components(self):
        """> 10 组分应报错"""
        with pytest.raises(ValueError):
            simplex_lattice(["C" + str(i) for i in range(11)])

    def test_invalid_degree(self):
        """degree < 1 应报错"""
        with pytest.raises(ValueError):
            simplex_lattice(["A", "B"], degree=0)

    def test_run_order_sequential(self):
        """RunOrder 应为顺序"""
        df = simplex_lattice(["A", "B", "C"], degree=2)
        assert list(df["RunOrder"]) == [1, 2, 3, 4, 5, 6]


class TestSimplexCentroid:
    """单纯形质心设计测试"""

    def test_q3_point_count(self):
        """q=3: 2^3 - 1 = 7 points"""
        df = simplex_centroid(["A", "B", "C"])
        assert len(df) == 7

    def test_q4_point_count(self):
        """q=4: 2^4 - 1 = 15 points"""
        df = simplex_centroid(["A", "B", "C", "D"])
        assert len(df) == 15

    def test_q2_point_count(self):
        """q=2: 2^2 - 1 = 3 points"""
        df = simplex_centroid(["A", "B"])
        assert len(df) == 3

    def test_proportions_sum_to_one(self):
        """所有行的比例之和 = 1"""
        df = simplex_centroid(["A", "B", "C"])
        sums = df[["A", "B", "C"]].sum(axis=1)
        np.testing.assert_allclose(sums, 1.0, atol=1e-10)

    def test_subset_size_column(self):
        """SubsetSize 列存在且正确"""
        df = simplex_centroid(["A", "B", "C"])
        assert "SubsetSize" in df.columns
        sizes = sorted(df["SubsetSize"].unique())
        assert sizes == [1, 2, 3]

    def test_vertices_are_pure(self):
        """子集大小=1 的行应为纯组分（一个=1，其余=0）"""
        df = simplex_centroid(["A", "B", "C"])
        verts = df[df["SubsetSize"] == 1]
        for _, row in verts.iterrows():
            vals = row[["A", "B", "C"]].values.astype(float)
            assert abs(vals.max() - 1.0) < 1e-10
            assert abs(vals.min()) < 1e-10

    def test_centroid_is_equal(self):
        """子集大小=q 的行应为等比例 (1/q, 1/q, ...)"""
        df = simplex_centroid(["A", "B", "C"])
        centroid = df[df["SubsetSize"] == 3]
        assert len(centroid) == 1
        np.testing.assert_allclose(
            centroid[["A", "B", "C"]].values.flatten(),
            [1/3, 1/3, 1/3], atol=1e-10
        )

    def test_too_few_components(self):
        """< 2 组分应报错"""
        with pytest.raises(ValueError):
            simplex_centroid(["A"])


class TestExtremeVertices:
    """极端顶点设计测试"""

    def test_no_constraints(self):
        """无约束 = 全顶点"""
        df = extreme_vertices(["A", "B", "C"],
                              lower_bounds=[0, 0, 0],
                              upper_bounds=[1, 1, 1])
        assert len(df) >= 3  # at least 3 vertices

    def test_proportions_sum_to_one(self):
        """所有行的比例之和 = 1"""
        df = extreme_vertices(["A", "B", "C"],
                              lower_bounds=[0.1, 0.1, 0.0],
                              upper_bounds=[0.8, 0.7, 0.6])
        sums = df[["A", "B", "C"]].sum(axis=1)
        np.testing.assert_allclose(sums, 1.0, atol=1e-6)

    def test_bounds_satisfied(self):
        """所有值满足约束"""
        lower = [0.2, 0.1, 0.0]
        upper = [0.8, 0.7, 0.6]
        df = extreme_vertices(["A", "B", "C"],
                              lower_bounds=lower, upper_bounds=upper)
        for col, l, u in zip(["A", "B", "C"], lower, upper, strict=True):
            assert (df[col] >= l - 1e-6).all()
            assert (df[col] <= u + 1e-6).all()

    def test_invalid_bounds_sum_lower(self):
        """下界之和 > 1 应报错"""
        with pytest.raises(ValueError):
            extreme_vertices(["A", "B", "C"],
                             lower_bounds=[0.4, 0.4, 0.3],
                             upper_bounds=[1.0, 1.0, 1.0])

    def test_invalid_bounds_sum_upper(self):
        """上界之和 < 1 应报错"""
        with pytest.raises(ValueError):
            extreme_vertices(["A", "B", "C"],
                             lower_bounds=[0.0, 0.0, 0.0],
                             upper_bounds=[0.3, 0.3, 0.3])

    def test_lower_exceeds_upper(self):
        """下界 > 上界应报错"""
        with pytest.raises(ValueError):
            extreme_vertices(["A", "B", "C"],
                             lower_bounds=[0.5, 0.0, 0.0],
                             upper_bounds=[0.3, 1.0, 1.0])

    def test_bounds_length_mismatch(self):
        """约束长度不匹配应报错"""
        with pytest.raises(ValueError):
            extreme_vertices(["A", "B", "C"],
                             lower_bounds=[0.0, 0.0],
                             upper_bounds=[1.0, 1.0, 1.0])


class TestScheffeMatrix:
    """Scheffé 设计矩阵测试"""

    def test_linear_columns(self):
        """linear: q 列"""
        X = np.array([[0.5, 0.5], [1.0, 0.0], [0.0, 1.0]])
        M = _build_scheffe_matrix(X, "linear")
        assert M.shape == (3, 2)

    def test_quadratic_columns(self):
        """quadratic: q + C(q,2) = 3 + 3 = 6 列"""
        X = np.array([[0.5, 0.3, 0.2], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
        M = _build_scheffe_matrix(X, "quadratic")
        assert M.shape == (3, 6)

    def test_special_cubic_columns(self):
        """special_cubic: q + C(q,2) + C(q,3) = 4 + 6 + 4 = 14 列"""
        X = np.random.dirichlet([1, 1, 1, 1], 5)
        M = _build_scheffe_matrix(X, "special_cubic")
        assert M.shape == (5, 14)

    def test_term_names_linear(self):
        """linear term names"""
        names = _model_term_names(["A", "B", "C"], "linear")
        assert names == ["A", "B", "C"]

    def test_term_names_quadratic(self):
        """quadratic term names"""
        names = _model_term_names(["A", "B", "C"], "quadratic")
        assert "A" in names
        assert "A*B" in names
        assert len(names) == 6

    def test_term_names_special_cubic(self):
        """special_cubic term names"""
        names = _model_term_names(["A", "B", "C"], "special_cubic")
        assert "A*B*C" in names
        assert len(names) == 7


class TestAnalyze:
    """混合设计分析测试"""

    def _make_data(self):
        """构造已知三元混合数据"""
        np.random.seed(42)
        df = simplex_centroid(["A", "B", "C"])
        # Known quadratic model: y = 10*A + 20*B + 15*C + 5*A*B
        df["Response"] = (
            10 * df["A"] + 20 * df["B"] + 15 * df["C"]
            + 5 * df["A"] * df["B"]
        )
        return df

    def test_analyze_returns_dict(self):
        """analyze 返回完整字典"""
        df = self._make_data()
        result = analyze(df, "Response", ["A", "B", "C"], model="quadratic")
        assert result["chart_type"] == "Mixture Design Analysis"
        assert "coefficients" in result
        assert "r_squared" in result
        assert "anova" in result

    def test_known_coefficients(self):
        """已知系数精确匹配"""
        df = self._make_data()
        result = analyze(df, "Response", ["A", "B", "C"], model="quadratic")
        coeffs = result["coefficients"]
        assert abs(coeffs["A"] - 10.0) < 0.01
        assert abs(coeffs["B"] - 20.0) < 0.01
        assert abs(coeffs["C"] - 15.0) < 0.01
        assert abs(coeffs["A*B"] - 5.0) < 0.01

    def test_r_squared_one(self):
        """无噪声数据 R² = 1"""
        df = self._make_data()
        result = analyze(df, "Response", ["A", "B", "C"], model="quadratic")
        assert abs(result["r_squared"] - 1.0) < 0.001

    def test_r_squared_range(self):
        """R² 在 [0, 1]"""
        np.random.seed(42)
        df = simplex_centroid(["A", "B", "C"])
        df["Response"] = 10 * df["A"] + 20 * df["B"] + np.random.normal(0, 0.5, 7)
        result = analyze(df, "Response", ["A", "B", "C"], model="quadratic")
        assert 0 <= result["r_squared"] <= 1

    def test_adjusted_r_squared_less(self):
        """校正 R² < R²"""
        df = self._make_data()
        result = analyze(df, "Response", ["A", "B", "C"], model="quadratic")
        assert result["r_squared_adjusted"] <= result["r_squared"]

    def test_anova_sources(self):
        """ANOVA source 列包含正确项"""
        df = self._make_data()
        result = analyze(df, "Response", ["A", "B", "C"], model="quadratic")
        sources = result["anova"]["source"]
        assert "A" in sources
        assert "A*B" in sources
        assert "Residual" in sources
        assert "Total" in sources

    def test_chart_type(self):
        """chart_type 正确"""
        df = self._make_data()
        result = analyze(df, "Response", ["A", "B", "C"], model="quadratic")
        assert result["chart_type"] == "Mixture Design Analysis"

    def test_invalid_model(self):
        """无效模型应报错"""
        df = self._make_data()
        with pytest.raises(ValueError):
            analyze(df, "Response", ["A", "B", "C"], model="cubic")

    def test_special_cubic_needs_3_components(self):
        """special_cubic 需要 >= 3 组分"""
        df = simplex_lattice(["A", "B"], degree=2)
        df["Response"] = 10 * df["A"] + 20 * df["B"]
        with pytest.raises(ValueError):
            analyze(df, "Response", ["A", "B"], model="special_cubic")

    def test_linear_model(self):
        """线性模型"""
        df = simplex_centroid(["A", "B", "C"])
        df["Response"] = 10 * df["A"] + 20 * df["B"] + 15 * df["C"]
        result = analyze(df, "Response", ["A", "B", "C"], model="linear")
        assert result["model"] == "linear"
        assert result["num_parameters"] == 3

    def test_design_points_count(self):
        """design_points 与数据行数一致"""
        df = self._make_data()
        result = analyze(df, "Response", ["A", "B", "C"], model="quadratic")
        assert result["design_points"] == 7

    def test_significant_terms(self):
        """已知数据的显著项"""
        df = self._make_data()
        result = analyze(df, "Response", ["A", "B", "C"], model="quadratic",
                         alpha=0.05)
        # All main effects + A*B should be significant
        sig = result["significant_terms"]
        assert "A" in sig
        assert "B" in sig
