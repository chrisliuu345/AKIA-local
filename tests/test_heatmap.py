"""
热力图与散点矩阵单元测试
"""

import pytest
import numpy as np
import pandas as pd
from analysis.charts.heatmap import (
    create_correlation_heatmap,
    create_scatter_matrix,
    _compute_correlation_matrix,
    _significance_stars,
)


@pytest.fixture
def sample_df():
    np.random.seed(42)
    return pd.DataFrame({
        "A": np.random.normal(100, 15, 100),
        "B": np.random.normal(50, 10, 100),
        "C": np.random.normal(200, 30, 100),
        "D": np.random.normal(75, 20, 100),
    })


@pytest.fixture
def small_df():
    return pd.DataFrame({
        "X": [1, 2, 3, 4, 5],
        "Y": [2, 4, 5, 4, 5],
        "Z": [5, 3, 2, 1, 0],
    })


class TestSignificanceStars:
    def test_highly_significant(self):
        assert _significance_stars(0.001) == "***"

    def test_very_significant(self):
        assert _significance_stars(0.005) == "**"

    def test_significant(self):
        assert _significance_stars(0.03) == "*"

    def test_not_significant(self):
        assert _significance_stars(0.1) == ""

    def test_boundary(self):
        assert _significance_stars(0.05) == "*"
        assert _significance_stars(0.049) == "*"


class TestComputeCorrelationMatrix:
    def test_pearson(self, sample_df):
        corr, p_values = _compute_correlation_matrix(sample_df, ["A", "B", "C"])
        assert corr.shape == (3, 3)
        assert p_values.shape == (3, 3)
        assert np.all(np.diag(corr) == 1.0)

    def test_spearman(self, sample_df):
        corr, _p_values = _compute_correlation_matrix(sample_df, ["A", "B"], method="spearman")
        assert corr.shape == (2, 2)
        assert -1 <= corr.iloc[0, 1] <= 1

    def test_kendall(self, sample_df):
        corr, _p_values = _compute_correlation_matrix(sample_df, ["A", "B"], method="kendall")
        assert corr.shape == (2, 2)

    def test_single_column(self, sample_df):
        corr, _p_values = _compute_correlation_matrix(sample_df, ["A"])
        assert corr.shape == (1, 1)
        assert corr.iloc[0, 0] == 1.0


class TestCorrelationHeatmap:
    def test_basic(self, sample_df):
        fig = create_correlation_heatmap(sample_df)
        assert fig is not None
        assert len(fig.axes) > 0

    def test_with_specific_cols(self, sample_df):
        fig = create_correlation_heatmap(sample_df, numeric_cols=["A", "B"])
        assert fig is not None

    def test_no_annotations(self, sample_df):
        fig = create_correlation_heatmap(sample_df, options={"show_annotations": False})
        assert fig is not None

    def test_no_significance(self, sample_df):
        fig = create_correlation_heatmap(sample_df, options={"show_significance": False})
        assert fig is not None

    def test_custom_colormap(self, sample_df):
        fig = create_correlation_heatmap(sample_df, options={"colormap": "coolwarm"})
        assert fig is not None

    def test_custom_fontsize(self, sample_df):
        fig = create_correlation_heatmap(sample_df, options={"label_fontsize": 12, "annot_fontsize": 10})
        assert fig is not None

    def test_spearman_method(self, sample_df):
        fig = create_correlation_heatmap(sample_df, options={"method": "spearman"})
        assert fig is not None

    def test_insufficient_columns(self):
        df = pd.DataFrame({"A": [1, 2, 3]})
        fig = create_correlation_heatmap(df)
        assert fig is not None

    def test_empty_df(self):
        df = pd.DataFrame()
        fig = create_correlation_heatmap(df)
        assert fig is not None


class TestScatterMatrix:
    def test_basic(self, sample_df):
        fig = create_scatter_matrix(sample_df)
        assert fig is not None

    def test_with_specific_cols(self, sample_df):
        fig = create_scatter_matrix(sample_df, numeric_cols=["A", "B"])
        assert fig is not None

    def test_no_regression(self, sample_df):
        fig = create_scatter_matrix(sample_df, options={"show_regression": False})
        assert fig is not None

    def test_customPointSize(self, sample_df):
        fig = create_scatter_matrix(sample_df, options={"point_size": 50})
        assert fig is not None

    def test_custom_alpha(self, sample_df):
        fig = create_scatter_matrix(sample_df, options={"point_alpha": 0.3})
        assert fig is not None

    def test_custom_fontsize(self, sample_df):
        fig = create_scatter_matrix(sample_df, options={"label_fontsize": 12})
        assert fig is not None

    def test_insufficient_columns(self):
        df = pd.DataFrame({"A": [1, 2, 3]})
        fig = create_scatter_matrix(df)
        assert fig is not None

    def test_small_dataset(self, small_df):
        fig = create_scatter_matrix(small_df)
        assert fig is not None
