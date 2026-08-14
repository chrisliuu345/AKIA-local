"""用户设置生效链路测试 — DPI 动态生效 / 用户字体接线 (v2.4 P1-5)"""

import pytest

from config import settings


@pytest.fixture(autouse=True)
def _reset_overrides():
    original = dict(settings._user_overrides)
    yield
    settings._user_overrides = original


class TestChartDpiEffective:
    def test_dpi_follows_user_override(self):
        from analysis.charts import chart_generator
        settings._user_overrides = {"chart_dpi": 200}
        assert chart_generator._dpi() == 200

    def test_dpi_falls_back_to_module_default(self):
        from analysis.charts import chart_generator
        settings._user_overrides = {}
        assert chart_generator._dpi() == settings.CHART_DPI


class TestUserFontWiring:
    def test_setup_chinese_font_prefers_user_font(self, monkeypatch):
        import matplotlib.pyplot as plt
        from output.chart_engine import setup_chinese_font
        import matplotlib.font_manager as fm

        available = ["TestUserFont", "DejaVu Sans"]
        monkeypatch.setattr(
            fm, "_load_fontmanager", lambda *a, **k: None)
        monkeypatch.setattr(
            fm.fontManager, "ttflist",
            [type("F", (), {"name": n})() for n in available],
        )
        settings._user_overrides = {"font_family": "TestUserFont"}
        setup_chinese_font()
        assert plt.rcParams["font.sans-serif"][0] == "TestUserFont"
