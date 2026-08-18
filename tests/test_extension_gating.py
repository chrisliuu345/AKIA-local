"""ESP-32 硬件拓展安装门控测试（v2.6.0 打包发布）"""
import pytest
from PySide6.QtWidgets import QApplication

from config import settings


@pytest.fixture(scope="module")
def app():
    a = QApplication.instance() or QApplication([])
    yield a
    a.quit()


@pytest.fixture(autouse=True)
def _reset_overrides():
    saved = dict(settings._user_overrides)
    yield
    settings._user_overrides = saved


class TestTabAllowed:
    def test_default_enabled(self):
        settings._user_overrides = {}
        assert settings.esp32_extension_enabled() is True
        assert settings.tab_allowed(35) is True

    def test_explicit_enabled(self):
        settings._user_overrides = {"esp32_extension": True}
        assert settings.esp32_extension_enabled() is True
        assert settings.tab_allowed(35) is True

    def test_disabled_gates_only_device_tab(self):
        settings._user_overrides = {"esp32_extension": False}
        assert settings.esp32_extension_enabled() is False
        assert settings.tab_allowed(35) is False
        assert settings.tab_allowed(34) is True
        assert settings.tab_allowed(1) is True
        assert settings.tab_allowed(100) is True


class TestSidebarGating:
    def _group(self):
        from ui.sidebar import CategoryGroup
        return CategoryGroup(
            "sidebar.monitoring",
            [(33, "sidebar.monitor"), (34, "sidebar.multi_plant"), (35, "sidebar.device")],
        )

    def test_sidebar_hides_device_btn_when_disabled(self, app):
        settings._user_overrides = {"esp32_extension": False}
        g = self._group()
        assert 33 in g.sub_buttons
        assert 34 in g.sub_buttons
        assert 35 not in g.sub_buttons

    def test_sidebar_shows_device_btn_when_enabled(self, app):
        settings._user_overrides = {"esp32_extension": True}
        g = self._group()
        assert 35 in g.sub_buttons
