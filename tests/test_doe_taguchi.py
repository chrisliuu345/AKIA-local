"""
Taguchi Design 单元测试

验证来源:
    Taguchi G, Konishi S (1987). Orthogonal Arrays and Linear Graphs.
    Montgomery D C (2017). Design and Analysis of Experiments, 9th ed.
    NIST Engineering Statistics Handbook, Section 5.5.6.
"""
import pytest
import numpy as np
from analysis.doe.taguchi import (
    generate_design,
    compute_sn_ratio,
    response_table,
    analyze,
    _ARRAYS,
)


class TestOrthogonalArrays:
    """正交阵正交性验证"""

    def _check_orthogonality(self, name):
        d = np.array(_ARRAYS[name]["design"])
        n, k = d.shape
        for i in range(k):
            for j in range(i + 1, k):
                combos = {}
                for r in range(n):
                    key = (d[r, i], d[r, j])
                    combos[key] = combos.get(key, 0) + 1
                nlevels_i = len(np.unique(d[:, i]))
                nlevels_j = len(np.unique(d[:, j]))
                expected = n / (nlevels_i * nlevels_j)
                for v in combos.values():
                    assert abs(v - expected) < 0.01, \
                        name + " cols " + str(i) + "," + str(j) + " not orthogonal"

    def test_l4_orthogonal(self):
        self._check_orthogonality("L4")

    def test_l8_orthogonal(self):
        self._check_orthogonality("L8")

    def test_l9_orthogonal(self):
        self._check_orthogonality("L9")

    def test_l12_orthogonal(self):
        self._check_orthogonality("L12")

    def test_l16_orthogonal(self):
        self._check_orthogonality("L16")

    def test_l18_orthogonal(self):
        self._check_orthogonality("L18")

    def test_l4_shape(self):
        d = np.array(_ARRAYS["L4"]["design"])
        assert d.shape == (4, 3)

    def test_l8_shape(self):
        d = np.array(_ARRAYS["L8"]["design"])
        assert d.shape == (8, 7)

    def test_l9_shape(self):
        d = np.array(_ARRAYS["L9"]["design"])
        assert d.shape == (9, 4)

    def test_l12_shape(self):
        d = np.array(_ARRAYS["L12"]["design"])
        assert d.shape == (12, 11)

    def test_l16_shape(self):
        d = np.array(_ARRAYS["L16"]["design"])
        assert d.shape == (16, 15)

    def test_l18_shape(self):
        d = np.array(_ARRAYS["L18"]["design"])
        assert d.shape == (18, 8)


class TestGenerateDesign:
    """设计生成测试"""

    def test_l4_auto_select(self):
        """自动选择 L4（3 个 2-level 因子）"""
        df = generate_design(["A", "B", "C"], random_seed=42)
        assert len(df) == 4
        assert df["Array"].iloc[0] == "L4"

    def test_l8_auto_select(self):
        """自动选择 L8（5 个 2-level 因子）"""
        df = generate_design(["A", "B", "C", "D", "E"], random_seed=42)
        assert len(df) == 8
        assert df["Array"].iloc[0] == "L8"

    def test_l9_3level(self):
        """L9 用于 3-level 因子"""
        df = generate_design(["A", "B", "C", "D"],
                             factor_levels=[3, 3, 3, 3], random_seed=42)
        assert len(df) == 9
        assert df["Array"].iloc[0] == "L9"

    def test_l12_explicit(self):
        """显式指定 L12"""
        df = generate_design(["A", "B", "C", "D", "E", "F"],
                             array="L12", random_seed=42)
        assert len(df) == 12
        assert df["Array"].iloc[0] == "L12"

    def test_l16_explicit(self):
        """显式指定 L16"""
        df = generate_design(["A", "B", "C", "D", "E", "F", "G", "H"],
                             array="L16", random_seed=42)
        assert len(df) == 16
        assert df["Array"].iloc[0] == "L16"

    def test_l18_mixed_levels(self):
        """L18 混合水平（1 个 2-level + 3 个 3-level）"""
        df = generate_design(["A", "B", "C", "D"],
                             factor_levels=[2, 3, 3, 3], random_seed=42)
        assert len(df) == 18
        assert df["Array"].iloc[0] == "L18"

    def test_too_few_factors(self):
        """因子数 < 2 应报错"""
        with pytest.raises(ValueError):
            generate_design(["A"])

    def test_too_many_2level(self):
        """超过 16 个 2-level 因子应报错"""
        with pytest.raises(ValueError):
            generate_design(["F" + str(i) for i in range(17)])

    def test_too_many_3level(self):
        """超过 4 个 3-level 因子应报错"""
        with pytest.raises(ValueError):
            generate_design(["A", "B", "C", "D", "E"],
                            factor_levels=[3, 3, 3, 3, 3])

    def test_values_are_pm1(self):
        """设计值应为 1,2"""
        df = generate_design(["A", "B", "C"], random_seed=42)
        for f in ["A", "B", "C"]:
            assert set(df[f].unique()) <= {1, 2}

    def test_values_3level(self):
        """3-level 设计值应为 1,2,3"""
        df = generate_design(["A", "B", "C", "D"],
                             factor_levels=[3, 3, 3, 3], random_seed=42)
        for f in ["A", "B", "C", "D"]:
            assert set(df[f].unique()) <= {1, 2, 3}

    def test_run_order_randomized(self):
        """RunOrder 应已随机化"""
        df = generate_design(["A", "B", "C"], random_seed=42)
        assert list(df["RunOrder"]) != list(range(1, 5))

    def test_std_order_sequential(self):
        """StdOrder 应为顺序"""
        df = generate_design(["A", "B", "C"], random_seed=42)
        assert list(df["StdOrder"]) == [1, 2, 3, 4]

    def test_invalid_array_name(self):
        """无效数组名应报错"""
        with pytest.raises(ValueError):
            generate_design(["A", "B", "C"], array="L99")


class TestSnRatio:
    """S/N 比计算测试"""

    def test_larger_is_better(self):
        """Larger-is-better: S/N = -10*log10(mean(1/y^2))"""
        values = [85, 90, 88, 87]
        sn = compute_sn_ratio(values, "larger_is_better")
        expected = -10 * np.log10(np.mean(1.0 / np.array(values) ** 2))
        assert abs(sn - expected) < 0.01

    def test_smaller_is_better(self):
        """Smaller-is-better: S/N = -10*log10(mean(y^2))"""
        values = [2.5, 2.8, 3.1, 2.9]
        sn = compute_sn_ratio(values, "smaller_is_better")
        expected = -10 * np.log10(np.mean(np.array(values) ** 2))
        assert abs(sn - expected) < 0.01

    def test_nominal_is_best(self):
        """Nominal-is-best (I): S/N = 10*log10(mean^2/var)"""
        values = [5.01, 4.99, 5.02, 4.98]
        sn = compute_sn_ratio(values, "nominal_is_best")
        y_bar = np.mean(values)
        s2 = np.var(values, ddof=1)
        expected = 10 * np.log10(y_bar ** 2 / s2)
        assert abs(sn - expected) < 0.01

    def test_nominal_is_best_ii(self):
        """Nominal-is-best (II): S/N = -10*log10(var)"""
        values = [5.01, 4.99, 5.02, 4.98]
        sn = compute_sn_ratio(values, "nominal_is_best_ii")
        s2 = np.var(values, ddof=1)
        expected = -10 * np.log10(s2)
        assert abs(sn - expected) < 0.01

    def test_single_value(self):
        """单个值：nominal 返回 inf"""
        sn = compute_sn_ratio([5.0], "nominal_is_best")
        assert sn == float("inf")

    def test_invalid_type(self):
        """无效 S/N 类型应报错"""
        with pytest.raises(ValueError):
            compute_sn_ratio([1, 2, 3], "unknown_type")


class TestResponseTable:
    """响应表测试"""

    def test_response_table_structure(self):
        """响应表结构验证"""
        df = generate_design(["A", "B", "C"], random_seed=42)
        sn = np.array([10.0, 20.0, 15.0, 25.0])
        rt = response_table(df, sn, ["A", "B", "C"])
        for f in ["A", "B", "C"]:
            assert "level_averages" in rt[f]
            assert "delta" in rt[f]
            assert "best_level" in rt[f]
            assert "rank" in rt[f]

    def test_response_table_ranking(self):
        """Rank 应按 delta 降序（rank 1 = highest delta）"""
        df = generate_design(["A", "B", "C"], random_seed=42)
        sn = np.array([10.0, 20.0, 15.0, 25.0])
        rt = response_table(df, sn, ["A", "B", "C"])
        # Rank 1 should have highest delta
        deltas = {f: rt[f]["delta"] for f in ["A", "B", "C"]}
        max_delta_factor = max(deltas, key=deltas.get)
        assert rt[max_delta_factor]["rank"] == 1

    def test_best_level(self):
        """best_level 应对应最高平均 S/N"""
        df = generate_design(["A", "B", "C"], random_seed=42)
        sn = np.array([10.0, 20.0, 15.0, 25.0])
        rt = response_table(df, sn, ["A", "B", "C"])
        for f in ["A", "B", "C"]:
            best = rt[f]["best_level"]
            best_avg = rt[f]["level_averages"][best]
            assert best_avg == max(rt[f]["level_averages"].values())


class TestAnalyze:
    """分析测试"""

    def _make_data(self):
        """构造已知数据"""
        np.random.seed(42)
        df = generate_design(["A", "B", "C", "D"], random_seed=42)
        df["Response"] = 10.0 + 5.0 * df["A"] - 3.0 * df["B"] + np.random.normal(0, 0.3, 8)
        return df

    def test_analyze_returns_dict(self):
        """analyze 返回完整字典"""
        df = self._make_data()
        result = analyze(df, "Response", ["A", "B", "C", "D"])
        assert result["chart_type"] == "Taguchi Analysis"
        assert "response_table" in result
        assert "anova" in result
        assert "optimal" in result
        assert "predicted_sn" in result

    def test_n8_known_values(self):
        """无噪声已知值精确匹配"""
        df = generate_design(["A", "B", "C"], random_seed=42)
        df["Response"] = 10.0 + 4.0 * df["A"] - 2.0 * df["B"]
        result = analyze(df, "Response", ["A", "B", "C"])
        # A 应为最高 rank
        assert result["response_table"]["A"]["rank"] == 1

    def test_anova_ss_total(self):
        """ANOVA SS_total 应等于 SS_model + SS_error"""
        df = self._make_data()
        result = analyze(df, "Response", ["A", "B", "C", "D"])
        ss_model = sum(result["anova"]["ss"][:-2])
        ss_error = result["anova"]["ss"][-2]
        ss_total = result["anova"]["ss"][-1]
        assert abs(ss_model + ss_error - ss_total) < 0.01

    def test_contribution_sum(self):
        """贡献率之和应约为 100%"""
        df = self._make_data()
        result = analyze(df, "Response", ["A", "B", "C", "D"])
        total = sum(result["contribution_pct"].values())
        assert abs(total - 100.0) < 1.0

    def test_optimal_structure(self):
        """最优组合结构验证"""
        df = self._make_data()
        result = analyze(df, "Response", ["A", "B", "C", "D"])
        for f in ["A", "B", "C", "D"]:
            assert "best_level" in result["optimal"][f]
            assert "best_avg_sn" in result["optimal"][f]
            assert "rank" in result["optimal"][f]

    def test_predicted_sn(self):
        """预测 S/N 应为合理值"""
        df = self._make_data()
        result = analyze(df, "Response", ["A", "B", "C", "D"])
        assert isinstance(result["predicted_sn"], float)
        assert result["predicted_sn"] != 0.0

    def test_sn_type_forwarded(self):
        """S/N 类型应正确传递"""
        df = self._make_data()
        result = analyze(df, "Response", ["A", "B", "C", "D"],
                         sn_type="smaller_is_better")
        assert result["sn_type"] == "smaller_is_better"

    def test_l9_analyze(self):
        """L9 设计分析"""
        df = generate_design(["A", "B", "C", "D"],
                             factor_levels=[3, 3, 3, 3], random_seed=42)
        df["Response"] = 10.0 + 2.0 * df["A"] - 1.0 * df["C"]
        result = analyze(df, "Response", ["A", "B", "C", "D"])
        assert len(result["response_table"]) == 4
        assert result["observations"] == 9


class TestNoiseFactors:
    """内外表(噪声因子)扩展 — 回归: 曾缺 _build_plackett_burman 与 L9 list 切片"""

    def test_noise_2level_uses_hadamard_inner_array(self):
        df = generate_design(["A", "B", "C", "D", "E", "F"],
                             noise_factors=["N1", "N2"], noise_levels=[2, 2],
                             random_seed=1)
        assert {"N1_Noise", "N2_Noise"} <= set(df.columns)
        assert df["N1_Noise"].isin([1, 2]).all()
        # 每主试验行配对的内表行数 = 2^2
        n_main = len(df) // 4
        assert len(df) == n_main * 4

    def test_noise_3level_uses_L9_inner_array(self):
        df = generate_design(["A", "B"],
                             noise_factors=["N1", "N2", "N3"],
                             noise_levels=[3, 3, 3], random_seed=2)
        assert len(df) == 36  # 主阵 4 行(2^2?) × L9 9 行
        for c in ("N1_Noise", "N2_Noise", "N3_Noise"):
            assert df[c].isin([1, 2, 3]).all()
        assert set(df["N1_Noise"].unique()) == {1, 2, 3}

    def test_noise_inner_array_columns_orthogonal(self):
        from analysis.doe.taguchi import _build_plackett_burman
        a = _build_plackett_burman(8)
        assert a.shape == (8, 7)
        assert np.allclose(a.T @ a, np.eye(7) * 8)
