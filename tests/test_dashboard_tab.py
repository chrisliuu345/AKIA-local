"""Dashboard 自适应卡片测试 — 列数策略/卡片尺寸/时间戳/状态色点/动画开关 (v2.4.1)"""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import matplotlib
matplotlib.use("Agg")

import pytest
from PySide6.QtWidgets import QApplication, QLabel, QWidget
from PySide6.QtCore import QSettings

from config import settings
from ui.tabs.dashboard_tab import DashboardTab


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _anim_off():
    original = dict(settings._user_overrides)
    settings._user_overrides = {"animations_enabled": False}
    yield
    settings._user_overrides = original


@pytest.fixture(autouse=True)
def _dash_settings():
    s = QSettings("QA-Tool", "Dashboard")
    keys = ("order", "hidden", "auto_refresh")
    saved = {k: s.value(k) for k in keys}
    for k in keys:
        s.remove(k)
    yield
    for k in keys:
        if saved[k] is not None:
            s.setValue(k, saved[k])
        else:
            s.remove(k)


class FakeMain(QWidget):
    def __init__(self, analyses=None):
        super().__init__()
        self.analyses = analyses if analyses is not None else {}
        self.current_data = {"raw_data": None}


@pytest.fixture
def main(app):
    return FakeMain()


def _cap(atype, cpk=None, extra=None, completed=None):
    result = {"capability": {}}
    if cpk is not None:
        result["capability"]["cpk"] = cpk
    if extra:
        result.update(extra)
    e = {"analysis_type": atype, "params": {}, "result": result}
    if completed:
        e["_completed_at"] = completed
    return e


def _make_tab(main, monkeypatch):
    monkeypatch.setattr("ui.tabs.dashboard_tab.describe_variables",
                        lambda analyses, df: {})
    from ui.dialogs.formula_dialog import FormulaDialog
    monkeypatch.setattr(FormulaDialog, "load_formulas", staticmethod(lambda: {}))
    tab = DashboardTab()
    tab.setParent(main)
    return tab


def _card_labels(card):
    return [lbl.text() for lbl in card.findChildren(QLabel)]


def _dot(card):
    for lbl in card.findChildren(QLabel):
        if lbl.text() == "●":
            return lbl
    return None


class TestColumnStrategy:
    def _run(self, main, monkeypatch, n):
        main.analyses = {
            i + 1: _cap(f"能力{i}", cpk=1.0 + i * 0.1) for i in range(n)
        }
        tab = _make_tab(main, monkeypatch)
        tab.refresh()
        return tab

    def test_three_cards_single_column(self, main, monkeypatch):
        tab = self._run(main, monkeypatch, 3)
        assert len(tab._cards) == 3
        assert tab._cards[0].size().width() == 560
        assert tab._cards[0].size().height() == 260
        cols = {tab.grid.getItemPosition(i)[1] for i in range(3)}
        assert cols == {0}
        tab.close()

    def test_six_cards_two_columns(self, main, monkeypatch):
        tab = self._run(main, monkeypatch, 6)
        assert len(tab._cards) == 6
        assert tab._cards[0].size().width() == 330
        cols = {tab.grid.getItemPosition(i)[1] for i in range(6)}
        assert cols == {0, 1}
        tab.close()

    def test_seven_cards_three_columns(self, main, monkeypatch):
        tab = self._run(main, monkeypatch, 7)
        assert len(tab._cards) == 7
        assert tab._cards[0].size().width() == 240
        cols = {tab.grid.getItemPosition(i)[1] for i in range(7)}
        assert cols == {0, 1, 2}
        tab.close()


class TestCardDetails:
    def test_timestamp_rendered(self, main, monkeypatch):
        main.analyses = {2: _cap("能力", cpk=1.5,
                                 completed="2026-08-14T14:23:45")}
        tab = _make_tab(main, monkeypatch)
        tab.refresh()
        texts = _card_labels(tab._cards[0])
        assert any("更新于 14:23" in t for t in texts)
        tab.close()

    def test_timestamp_missing_no_label(self, main, monkeypatch):
        main.analyses = {2: _cap("能力", cpk=1.5)}
        tab = _make_tab(main, monkeypatch)
        tab.refresh()
        texts = _card_labels(tab._cards[0])
        assert not any("更新于" in t for t in texts)
        tab.close()

    def test_dot_green_for_good_cpk(self, main, monkeypatch):
        main.analyses = {2: _cap("能力", cpk=1.5)}
        tab = _make_tab(main, monkeypatch)
        tab.refresh()
        dot = _dot(tab._cards[0])
        assert dot is not None
        assert "#27ae60" in dot.styleSheet()
        tab.close()

    def test_dot_red_for_bad_cpk(self, main, monkeypatch):
        main.analyses = {2: _cap("能力", cpk=0.9)}
        tab = _make_tab(main, monkeypatch)
        tab.refresh()
        dot = _dot(tab._cards[0])
        assert dot is not None
        assert "#e74c3c" in dot.styleSheet()
        tab.close()

    def test_dot_red_for_violations(self, main, monkeypatch):
        main.analyses = {1: {"analysis_type": "SPC", "params": {},
                             "result": {"xbar_chart": {"violations": [1, 2]}}}}
        tab = _make_tab(main, monkeypatch)
        tab.refresh()
        dot = _dot(tab._cards[0])
        assert dot is not None
        assert "#e74c3c" in dot.styleSheet()
        tab.close()


class TestAnimationsAndFingerprint:
    def test_no_effect_when_animations_off(self, main, monkeypatch):
        main.analyses = {2: _cap("能力", cpk=1.5)}
        tab = _make_tab(main, monkeypatch)
        tab.refresh()
        for card in tab._cards:
            assert card.graphicsEffect() is None
        tab.close()

    def test_fingerprint_ignores_completed_at(self, main, monkeypatch):
        main.analyses = {2: _cap("能力", cpk=1.5)}
        tab = _make_tab(main, monkeypatch)
        fp1 = tab._analyses_fingerprint()
        main.analyses = {2: _cap("能力", cpk=1.5,
                                 completed="2026-08-14T14:23:45")}
        fp2 = tab._analyses_fingerprint()
        assert fp1 == fp2
        tab.close()


class TestEmptyState:
    def test_empty_analyses_shows_empty_card(self, main, monkeypatch):
        tab = _make_tab(main, monkeypatch)
        tab.refresh()
        assert len(tab._cards) == 1
        assert isinstance(tab._cards[0], QLabel)
        assert tab._cards[0].text()
        tab.close()
