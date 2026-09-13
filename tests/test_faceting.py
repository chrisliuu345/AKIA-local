"""
小多图（分面图）单元测试
"""

import matplotlib
matplotlib.use("Agg")

import numpy as np
import pandas as pd
import pytest

from analysis.charts.faceting import (
    create_small_multiples,
    facet_group_table,
    layout,
    _clean,
    _bin_count,
    faceting_summary_lines,
    GROUP_LIMIT,
)


@pytest.fixture
def facet_df():
    """5 个分组，样本数递减：A=50, B=40, C=30, D=20, E=10"""
    np.random.seed(7)
    sizes = [50, 40, 30, 20, 10]
    parts = []
    for i, name in enumerate(["A", "B", "C", "D", "E"]):
        parts.append(pd.DataFrame({
            "数值": np.random.normal(100 + i * 10, 5, sizes[i]),
            "分组": name,
        }))
    return pd.concat(parts, ignore_index=True)


@pytest.fixture
def many_group_df():
    """15 个分组，超过 GROUP_LIMIT=12"""
    np.random.seed(3)
    parts = []
    for i in range(15):
        parts.append(pd.DataFrame({
            "数值": np.random.normal(50, 10, 30),
            "分组": f"G{i:02d}",
        }))
    return pd.concat(parts, ignore_index=True)


class TestLayout:
    def test_col_mode(self):
        assert layout(12, "col", 3) == (4, 3)
        assert layout(10, "col", 4) == (3, 4)

    def test_row_mode(self):
        assert layout(10, "row", 3) == (3, 4)
        assert layout(5, "row", 6) == (5, 1)

    def test_grid_mode(self):
        assert layout(9, "grid", 3) == (3, 3)
        nrows, ncols = layout(10, "grid", 1)
        assert abs(nrows - ncols) <= 1 and nrows * ncols >= 10

    def test_single_group(self):
        assert layout(1, "col", 3) == (1, 1)
        assert layout(1, "row", 3) == (1, 1)
        assert layout(1, "grid", 3) == (1, 1)

    def test_wrap_clamped(self):
        for mode in ("col", "row"):
            nrows, ncols = layout(3, mode, 0)
            assert nrows * ncols >= 3
            nrows2, ncols2 = layout(3, mode, -2)
            assert nrows2 * ncols2 >= 3


class TestClean:
    def test_normal(self, facet_df):
        vals, groups, ok = _clean(facet_df, "数值", "分组")
        assert ok is True
        assert len(vals) == len(groups) == 150

    def test_nan_group_goes_missing(self):
        df = pd.DataFrame({"数值": [1.0, 2.0, 3.0], "分组": ["x", None, "x"]})
        vals, groups, ok = _clean(df, "数值", "分组")
        assert ok is True
        assert len(vals) == 3
        assert groups.tolist() == ["x", "(缺失)", "x"]

    def test_nan_value_rows_dropped(self):
        df = pd.DataFrame({"数值": [1.0, np.nan, "abc"], "分组": ["x", "x", "y"]})
        _vals, _groups, ok = _clean(df, "数值", "分组")
        assert ok is False  # 只剩 1 个有效样本

    def test_missing_columns(self):
        df = pd.DataFrame({"数值": [1.0, 2.0]})
        _vals, _groups, ok = _clean(df, "数值", "不存在")
        assert ok is False
        _, _, ok2 = _clean(None, "数值", "分组")
        assert ok2 is False

    def test_too_few_samples(self):
        df = pd.DataFrame({"数值": [1.0], "分组": ["x"]})
        _, _, ok = _clean(df, "数值", "分组")
        assert ok is False


class TestFacetGroupTable:
    def test_sorted_desc_and_limited(self, many_group_df):
        kept, dropped, counts = facet_group_table(many_group_df, "数值", "分组")
        assert len(kept) == GROUP_LIMIT
        assert len(dropped) == 3
        assert counts[kept[0]] == 30

    def test_custom_limit(self, many_group_df):
        kept, _, _ = facet_group_table(many_group_df, "数值", "分组", limit=5)
        assert len(kept) == 5

    def test_within_limit_no_drop(self, facet_df):
        kept, dropped, counts = facet_group_table(facet_df, "数值", "分组")
        assert len(kept) == 5
        assert dropped == []
        assert counts["A"] == 50

    def test_counts_exclude_nan_value_rows(self):
        df = pd.DataFrame({
            "数值": [1.0, 2.0, np.nan, np.nan],
            "分组": ["x", "x", "x", "y"],
        })
        kept, _dropped, counts = facet_group_table(df, "数值", "分组")
        assert kept == ["x"]
        assert "y" not in kept
        assert "y" not in counts  # 0 个有效样本的组不参与分面
        assert counts["x"] == 2


class TestSmallMultiplesFigure:
    def test_axes_grid_matches_cap(self, many_group_df):
        fig = create_small_multiples(many_group_df, "数值", "分组", options={})
        # 12 组 + 4 个 off 占位 = 4 行 x 3 列 = 12 轴
        assert len(fig.axes) == 12
        assert fig.axes[0].get_title().endswith("(n=30)")
        fig2 = create_small_multiples(many_group_df, "数值", "分组",
                                      options={"col_wrap": 2})
        assert len(fig2.axes) == 12  # 6 行 x 2 列

    def test_within_limit_exact_fit(self, facet_df):
        fig = create_small_multiples(facet_df, "数值", "分组", options={"col_wrap": 5})
        assert len(fig.axes) == 5
        for ax in fig.axes:
            title = ax.get_title()
            assert title.startswith("(") is False
            assert "n=" in title and title.endswith(")")

    def test_single_group(self):
        df = pd.DataFrame({"数值": np.random.normal(0, 1, 40), "分组": ["仅一组"] * 40})
        fig = create_small_multiples(df, "数值", "分组")
        assert len(fig.axes) == 1

    def test_histogram_share_x_common_edges(self, facet_df):
        opts = {"share_x": True, "facet_kind": "直方图"}
        fig = create_small_multiples(facet_df, "数值", "分组", options=opts)
        drawn = [ax for ax in fig.axes if ax.get_title()]
        assert len(drawn) == 5
        xlims = {tuple(ax.get_xlim()) for ax in drawn}
        assert len(xlims) == 1  # 所有子图共享同一 X 范围

    def test_boxplot_kind(self, facet_df):
        fig = create_small_multiples(facet_df, "数值", "分组",
                                     options={"facet_kind": "箱线图", "col_wrap": 3})
        drawn = [ax for ax in fig.axes if ax.get_title()]
        assert len(drawn) == 5  # 2 行 x 3 列网格中 5 个绘制 + 1 个 off
        assert len(fig.axes) == 6
        assert len(drawn[0].get_xticks()) == 0

    def test_missing_group_col_message(self, facet_df):
        fig = create_small_multiples(facet_df, "数值", "不存在的分组")
        assert len(fig.axes) == 1

    def test_invalid_value_col_message(self, facet_df):
        fig = create_small_multiples(facet_df, "不存在的值", "分组")
        assert len(fig.axes) == 1

    def test_row_mode_order(self, facet_df):
        opts = {"facet_mode": "row", "col_wrap": 2}
        fig = create_small_multiples(facet_df, "数值", "分组", options=opts)
        # row 模式：2 行 -> ncols=3，共 6 轴（1 个 off）
        assert len(fig.axes) == 6


class TestBinCount:
    def test_bounds(self):
        assert 5 <= _bin_count(2) <= 50
        assert _bin_count(2000) == 50


class TestSummaryLines:
    def test_basic(self, facet_df):
        lines = faceting_summary_lines(facet_df, "数值", "分组")
        text = "\n".join(lines)
        assert "数值" in text and "5 组" in text
        assert "A: n=50" in text
        assert "被省略" not in text

    def test_omitted_note(self, many_group_df):
        lines = faceting_summary_lines(many_group_df, "数值", "分组")
        text = "\n".join(lines)
        assert "15 组" in text
        assert "被省略" in text

    def test_invalid(self):
        assert faceting_summary_lines(None, "a", "b") == []


class TestGeneratorIntegration:
    def test_generate_chart_dispatch(self, facet_df):
        from analysis.charts.chart_generator import generate_chart
        data = {"df": facet_df, "columns": ["数值", "分组"]}
        fig = generate_chart("小多图", data, {
            "title": "按组分布",
            "chart_options": {"facet_kind": "箱线图", "col_wrap": 2},
        })
        assert fig is not None
        assert fig.axes[0].get_title().startswith("A ")
