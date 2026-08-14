"""告警通知引擎单测 (v2.4 E3) — 状态机/规则/日志/文案 + MonitorTab 接入"""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from config import settings as app_settings
from core.alert_rules import (
    AlertState, AlertTracker, AlertLog, AlertRules, format_alert_message,
)


@pytest.fixture(autouse=True)
def _reset_overrides(monkeypatch):
    saved = dict(app_settings._user_overrides)
    monkeypatch.setattr(app_settings, "_user_overrides", {})
    yield
    monkeypatch.setattr(app_settings, "_user_overrides", saved)


class TestAlertStateMachine:
    def test_transitions(self):
        t = AlertTracker()
        assert t.update(0) == AlertState.NONE
        assert t.update(0) == AlertState.NONE
        assert t.update(5) == AlertState.NEW
        assert t.update(7) == AlertState.ONGOING
        assert t.update(0) == AlertState.CLEARED
        assert t.update(0) == AlertState.NONE

    def test_reset(self):
        t = AlertTracker()
        t.update(4)
        t.reset()
        assert t.update(3) == AlertState.NEW

    def test_non_int_violations(self):
        t = AlertTracker()
        assert t.update(None) == AlertState.NONE
        assert t.update("3") == AlertState.NEW


class TestAlertRules:
    def test_defaults(self):
        assert AlertRules.min_violations() == 1
        assert AlertRules.popup_enabled() is True
        assert AlertRules.sound_enabled() is True
        assert AlertRules.log_enabled() is True

    def test_overrides(self, monkeypatch):
        monkeypatch.setattr(app_settings, "_user_overrides", {
            "alert_min_violations": 2,
            "alert_popup_enabled": False,
            "alert_sound_enabled": False,
            "alert_log_enabled": False,
        })
        assert AlertRules.min_violations() == 2
        assert AlertRules.popup_enabled() is False
        assert AlertRules.sound_enabled() is False
        assert AlertRules.log_enabled() is False


class TestAlertLog:
    def test_add_newest_first(self):
        log = AlertLog(max_entries=5)
        log.add("a")
        log.add("b")
        entries = log.entries()
        assert len(log) == 2
        assert entries[0][1] == "b"

    def test_ring_buffer(self):
        log = AlertLog(max_entries=2)
        for m in ("a", "b", "c"):
            log.add(m)
        assert len(log) == 2
        assert log.entries()[0][1] == "c"
        assert log.entries()[1][1] == "b"

    def test_clear(self):
        log = AlertLog()
        log.add("x")
        log.clear()
        assert len(log) == 0


class TestFormatMessage:
    def test_new_and_cleared(self):
        new_msg = format_alert_message(AlertState.NEW, 3, "data.xlsx")
        assert "3" in new_msg and "data.xlsx" in new_msg
        cleared_msg = format_alert_message(AlertState.CLEARED, 0, "data.xlsx")
        assert "data.xlsx" in cleared_msg

    def test_no_message_for_other_states(self):
        assert format_alert_message(AlertState.NONE, 0, "f") == ""
        assert format_alert_message(AlertState.ONGOING, 2, "f") == ""


@pytest.fixture(scope="module")
def _qt_app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


class TestMonitorTabAlert:
    @pytest.fixture
    def tab(self, _qt_app, monkeypatch):
        monkeypatch.setattr(app_settings, "_user_overrides", {
            "alert_popup_enabled": False,
            "alert_sound_enabled": False,
        })
        from ui.tabs.monitor_tab import MonitorTab
        return MonitorTab()

    def test_new_alert_fires_once_then_cleared(self, tab):
        tab._check_alerts(3, "a.xlsx")
        assert not tab.alert_banner.isHidden()
        assert len(tab._alert_log) == 1
        assert "3" in tab._alert_log.entries()[0][1]

        tab._check_alerts(5, "a.xlsx")
        assert len(tab._alert_log) == 1      # ONGOING 去重不记录

        tab._check_alerts(0, "a.xlsx")
        assert len(tab._alert_log) == 2      # CLEARED 记录
        assert "a.xlsx" in tab._alert_log.entries()[0][1]

    def test_min_violations_threshold(self, tab, monkeypatch):
        monkeypatch.setattr(app_settings, "_user_overrides", {
            "alert_min_violations": 2,
            "alert_popup_enabled": False,
            "alert_sound_enabled": False,
        })
        tab._check_alerts(1, "b.xlsx")
        assert len(tab._alert_log) == 0      # 低于阈值不告警
        tab._check_alerts(2, "b.xlsx")
        assert len(tab._alert_log) == 1      # 跨过阈值触发 NEW

    def test_log_panel_refresh(self, tab):
        tab._check_alerts(2, "c.xlsx")
        text = tab.alert_log_view.toPlainText()
        assert "c.xlsx" in text
        assert "[" in text                  # 时间戳前缀
