"""
图表类型图库面板单元测试
"""

import time

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget

from ui.widgets.chart_gallery import ChartGallery, GALLERY_GROUPS
from ui.widgets.chart_icons import get_chart_icon, has_custom_icon
from analysis.charts.chart_generator import CHART_TYPES


@pytest.fixture
def gallery():
    return ChartGallery(list(CHART_TYPES))


class TestChartGallery:
    def test_default_collapsed(self, gallery):
        assert gallery.is_expanded() is False
        assert gallery._body.isHidden() is True

    def test_body_is_popup_panel(self, gallery):
        # 展开体为独立浮层（Qt.Popup）：不占父布局高度，不受配置列高度限制
        assert isinstance(gallery._body, QWidget)
        assert gallery._body.isWindow() is True
        assert bool(gallery._body.windowFlags() & Qt.Popup)
        assert gallery._body.isHidden() is True

    def test_popup_tiles_keep_full_size(self, gallery):
        # 固定三列、固定宽度：窄配置列展开也不会压缩图标选项
        gallery.expand()
        app = QApplication.instance()
        app.processEvents()
        assert gallery._body.sizeHint().width() >= 3 * 152
        rects = []
        for btn in gallery._tile_buttons.values():
            assert btn.size().width() == 152
            assert btn.size().height() == 44
            assert btn.size().width() >= btn.sizeHint().width()
            rects.append(btn.geometry())
        for i, r1 in enumerate(rects):
            for r2 in rects[i + 1:]:
                assert not r1.intersects(r2)

    def test_all_types_have_tiles(self, gallery):
        assert set(gallery._tile_buttons) == set(CHART_TYPES)

    def test_toggle_expand(self, gallery):
        gallery.expand()
        assert gallery.is_expanded() is True
        assert gallery._body.isHidden() is False
        gallery.collapse()
        assert gallery.is_expanded() is False
        assert gallery._body.isHidden() is True

    def test_click_emits_and_collapses(self, gallery):
        chosen = []
        gallery.type_chosen.connect(chosen.append)
        gallery.expand()
        gallery._tile_buttons["箱线图"].click()
        assert chosen == ["箱线图"]
        assert gallery.is_expanded() is False
        assert gallery.current_type() == "箱线图"
        assert gallery._current_label.text() == "箱线图"

    def test_set_current_highlights(self, gallery):
        gallery.set_current("帕累托图")
        assert gallery.current_type() == "帕累托图"
        assert "4da6ff" in gallery._tile_buttons["帕累托图"].styleSheet()

    def test_groups_cover_all_types(self):
        known = {n for _, names in GALLERY_GROUPS for n in names}
        assert known == set(CHART_TYPES)

    def test_every_tile_has_non_null_icon(self, gallery):
        for name, btn in gallery._tile_buttons.items():
            assert btn.icon().isNull() is False, name
            assert btn.iconSize().width() == 22

    def test_icon_cache_reused(self):
        assert get_chart_icon("直方图") is get_chart_icon("直方图")
        assert get_chart_icon("散点矩阵图") is get_chart_icon("散点矩阵图")

    def test_all_icons_generate_fast(self):
        t0 = time.perf_counter()
        for name in CHART_TYPES:
            if has_custom_icon(name):
                get_chart_icon(name)
        elapsed = time.perf_counter() - t0
        assert elapsed < 2.0, f"图标生成过慢: {elapsed*1000:.0f}ms"

    def test_unknown_type_returns_placeholder(self):
        icon = get_chart_icon("不存在的类型")
        assert icon is not None and icon.isNull() is True


class TestChartTabGalleryIntegration:
    def test_tile_switches_chart_type_and_config(self):
        from ui.tabs.chart_tab import ChartTab
        tab = ChartTab()
        assert tab.chart_gallery is not None
        assert not tab.chart_gallery.is_expanded()

        tab.chart_gallery.expand()
        tab.chart_gallery._tile_buttons["散点图"].click()
        app = QApplication.instance()
        app.processEvents()
        assert tab.chart_type_combo.currentText() == "散点图"
        assert len(tab._col_widgets) == 2  # X 轴列 + Y 轴列
        assert tab.chart_gallery.current_type() == "散点图"

        tab.chart_gallery.expand()
        tab.chart_gallery._tile_buttons["直方图"].click()
        app.processEvents()
        assert tab.chart_type_combo.currentText() == "直方图"
        assert len(tab._col_widgets) == 1  # 数值列
