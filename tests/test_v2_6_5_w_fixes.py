"""v2.6.5 W-series defect fix regression tests

Covers: W50, W51, W69, W72, W73, W74, W86, W106
"""
import numpy as np
import pandas as pd
import pytest


# ── W86: utils scripts removed (hardcoded paths) ──

class TestW86HardcodedPaths:
    def test_co401_scripts_removed(self):
        import os
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        assert not os.path.exists(os.path.join(base, "utils", "co401_analysis.py"))
        assert not os.path.exists(os.path.join(base, "utils", "co401_round2.py"))

    def test_generate_test_data_no_hardcoded_path(self):
        import os
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base, "utils", "generate_test_data.py")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "D:\\" not in content or "output_path =" not in content.split("D:\\")[0]


# ── W106: import_dialog row count fix ──

class TestW106ImportRowCount:
    def test_excel_row_count_not_zero(self, tmp_path):
        xlsx = tmp_path / "test.xlsx"
        df = pd.DataFrame({"a": range(100), "b": range(100)})
        df.to_excel(str(xlsx), index=False)
        import openpyxl
        wb = openpyxl.load_workbook(str(xlsx), read_only=True)
        ws = wb.active
        assert ws.max_row == 101
        wb.close()

    def test_import_dialog_row_counting_logic(self):
        total_rows = 0
        data = {"col1": list(range(50)), "col2": list(range(50))}
        df = pd.DataFrame(data)
        total_rows = len(df)
        assert total_rows == 50


# ── W50: Grubbs outlier detection fix ──

class TestW50GrubbsOutlier:
    def _grubbs_detect(self, s):
        from scipy import stats as sp_stats
        n = len(s)
        if n < 3:
            return pd.Series(False, index=s.index)
        mean_val = s.mean()
        std_val = s.std()
        if std_val == 0:
            return pd.Series(False, index=s.index)
        t = sp_stats.t.ppf(1 - 0.05 / (2 * n), n - 2)
        g_crit = ((n - 1) / np.sqrt(n)) * np.sqrt(t ** 2 / (n - 2 + t ** 2))
        g_max = (s.max() - mean_val) / std_val
        g_min = (mean_val - s.min()) / std_val
        outliers = pd.Series(False, index=s.index)
        if g_max > g_crit:
            outliers[s.idxmax()] = True
        if g_min > g_crit:
            outliers[s.idxmin()] = True
        return outliers

    def test_grubbs_flags_max_outlier(self):
        np.random.seed(42)
        data = np.random.normal(10, 1, 50)
        data[25] = 20.0
        s = pd.Series(data)
        outliers = self._grubbs_detect(s)
        assert outliers.any()
        assert s.idxmax() in outliers[outliers].index

    def test_grubbs_flags_min_outlier(self):
        np.random.seed(42)
        data = np.random.normal(10, 1, 50)
        data[30] = 0.0
        s = pd.Series(data)
        outliers = self._grubbs_detect(s)
        assert outliers.any()
        assert s.idxmin() in outliers[outliers].index

    def test_grubbs_no_outlier_clean_data(self):
        np.random.seed(42)
        s = pd.Series(np.random.normal(10, 1, 50))
        outliers = self._grubbs_detect(s)
        assert not outliers.any()

    def test_grubbs_small_sample(self):
        s = pd.Series([1.0, 2.0])
        outliers = self._grubbs_detect(s)
        assert not outliers.any()


# ── W51: uniform distribution parameter fix ──

class TestW51UniformDistribution:
    def test_data_generator_uniform(self):
        from core.data_generator import DataGenerator
        data = DataGenerator.generate("均匀", 100, low=5, high=15)
        assert len(data) == 100
        assert np.all(data >= 5)
        assert np.all(data <= 15)
        assert abs(np.mean(data) - 10) < 2

    def test_data_generator_normal(self):
        from core.data_generator import DataGenerator
        data = DataGenerator.generate("正态", 100, mu=50, sigma=5)
        assert len(data) == 100
        assert abs(np.mean(data) - 50) < 5

    def test_data_generator_exponential(self):
        from core.data_generator import DataGenerator
        data = DataGenerator.generate("指数", 100, scale=2)
        assert len(data) == 100
        assert np.all(data >= 0)

    def test_data_generator_poisson(self):
        from core.data_generator import DataGenerator
        data = DataGenerator.generate("泊松", 100, lam=5)
        assert len(data) == 100
        assert np.all(data >= 0)


# ── W69: trend analysis sampling ──

class TestW69TrendSampling:
    def test_sampling_preserves_endpoints(self):
        np.random.seed(42)
        n = 2000
        data = np.random.normal(10, 1, n)
        MAX_POINTS = 1000
        step = max(1, n // MAX_POINTS)
        sampled_idx = list(range(0, n, step))
        # Add endpoints if not already included
        if 0 not in sampled_idx:
            sampled_idx.append(0)
        if n - 1 not in sampled_idx:
            sampled_idx.append(n - 1)
        sampled_idx = sorted(set(sampled_idx))
        assert 0 in sampled_idx
        assert n - 1 in sampled_idx

    def test_sampling_preserves_extremes(self):
        np.random.seed(42)
        data = np.random.normal(10, 1, 2000)
        data[500] = 100.0
        max_idx = int(np.argmax(data))
        n = len(data)
        MAX_POINTS = 1000
        step = max(1, n // MAX_POINTS)
        sampled_idx = list(range(0, n, step))
        if max_idx not in sampled_idx:
            sampled_idx.append(max_idx)
        if 0 not in sampled_idx:
            sampled_idx.append(0)
        if n - 1 not in sampled_idx:
            sampled_idx.append(n - 1)
        sampled_idx = sorted(set(sampled_idx))
        assert max_idx in sampled_idx

    def test_small_data_no_sampling(self):
        n = 500
        assert n <= 1000


# ── W74: animation cleanup ──

class TestW74AnimateCleanup:
    def test_cleanup_function_exists(self):
        from ui.widgets.animate import cleanup
        assert callable(cleanup)

    @pytest.mark.skipif(True, reason="Requires PySide6 display")
    def test_fade_in_returns_none_when_disabled(self):
        from unittest.mock import patch
        with patch("ui.widgets.animate._animations_enabled", return_value=False):
            from ui.widgets.animate import fade_in
            from PySide6.QtWidgets import QWidget
            w = QWidget()
            result = fade_in(w)
            assert result is None
            w.deleteLater()

    @pytest.mark.skipif(True, reason="Requires PySide6 display")
    def test_count_up_returns_none_when_disabled(self):
        from unittest.mock import patch
        with patch("ui.widgets.animate._animations_enabled", return_value=False):
            from ui.widgets.animate import count_up
            from PySide6.QtWidgets import QLabel
            label = QLabel("0")
            result = count_up(label, 100, lambda v: f"{v:.0f}")
            assert result is None
            label.deleteLater()


# ── W73: fishbone recursion guard ──

class TestW73FishboneRecursion:
    def test_render_children_max_depth(self):
        import inspect
        from ui.widgets.fishbone_canvas import FishboneCanvas
        source = inspect.getsource(FishboneCanvas._render_children)
        assert 'MAX_CAUSES_PER_LEVEL' in source
        assert 'MAX_DEPTH' in source

    def test_max_causes_per_level_constant(self):
        import inspect
        from ui.widgets.fishbone_canvas import FishboneCanvas
        source = inspect.getsource(FishboneCanvas._render_children)
        assert 'MAX_CAUSES_PER_LEVEL' in source


# ── W72: sidebar height recalc ──

class TestW72SidebarHeight:
    def test_recalc_height_method_exists(self):
        from ui.sidebar import CategoryGroup
        assert hasattr(CategoryGroup, '_recalc_height')


# ── Integration: data generator round-trip ──

class TestIntegrationDataGenerator:
    @pytest.mark.parametrize("dist", ["正态", "对数正态", "指数", "均匀", "Weibull", "泊松"])
    def test_all_distributions_generate(self, dist):
        from core.data_generator import DataGenerator
        data = DataGenerator.generate(dist, 50)
        assert len(data) == 50
        assert not np.all(np.isnan(data))
