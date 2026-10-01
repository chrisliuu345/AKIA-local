"""Dashboard v3.0 测试 — 垂直滚动 + 图表嵌入 + KPI 提取 + 状态色点"""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import matplotlib
matplotlib.use("Agg")

import pytest
from PySide6.QtWidgets import QApplication, QLabel, QWidget
from PySide6.QtCore import QSettings

from config import settings
from ui.tabs.dashboard_tab import DashboardTab
from ui.widgets.analysis_card import AnalysisCard


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
    s = QSettings("AKIA", "Dashboard")
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
    monkeypatch.setattr(FormulaDialog, "load_formulas", staticmethod(dict))
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


class TestVerticalLayout:
    """测试垂直滚动布局"""

    def test_cards_vertical排列(self, main, monkeypatch):
        main.analyses = {
            1: _cap("能力1", cpk=1.0),
            2: _cap("能力2", cpk=1.5),
            3: _cap("能力3", cpk=2.0),
        }
        tab = _make_tab(main, monkeypatch)
        tab.refresh()
        assert len(tab._cards) == 3
        # 所有卡片都在同一个 layout 中
        for card in tab._cards:
            assert card.parent() is not None
        tab.close()

    def test_many_cards_scrollable(self, main, monkeypatch):
        main.analyses = {
            i + 1: _cap(f"能力{i}", cpk=1.0 + i * 0.1) for i in range(10)
        }
        tab = _make_tab(main, monkeypatch)
        tab.refresh()
        assert len(tab._cards) == 10
        tab.close()


class TestCardDetails:
    def test_timestamp_rendered(self, main, monkeypatch):
        main.analyses = {2: _cap("能力", cpk=1.5,
                                 completed="2026-08-14T14:23:45")}
        tab = _make_tab(main, monkeypatch)
        tab.refresh()
        texts = _card_labels(tab._cards[0])
        assert any("14:23" in t for t in texts)
        tab.close()

    def test_timestamp_missing_no_label(self, main, monkeypatch):
        main.analyses = {2: _cap("能力", cpk=1.5)}
        tab = _make_tab(main, monkeypatch)
        tab.refresh()
        texts = _card_labels(tab._cards[0])
        assert not any("14:23" in t for t in texts)
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


class TestAnalysisCard:
    """测试 AnalysisCard 组件"""

    def test_card_with_metrics(self, app):
        card = AnalysisCard("能力分析", ["Cpk: 1.50", "Ppm: 3.4"], None)
        assert card is not None
        labels = card.findChildren(QLabel)
        texts = [lbl.text() for lbl in labels]
        assert any("能力分析" in t for t in texts)
        card.deleteLater()

    def test_card_with_placeholder(self, app):
        card = AnalysisCard("SPC", ["违规点: 3"], None, timestamp="14:23")
        assert card is not None
        placeholder = card.findChildren(QLabel)
        texts = [lbl.text() for lbl in placeholder]
        # figure=None → no chart area, just title + metrics + timestamp + dot
        assert any("SPC" in t for t in texts)
        assert any("14:23" in t for t in texts)
        assert any("违规点: 3" in t for t in texts)
        card.deleteLater()

    def test_card_with_no_metrics(self, app):
        card = AnalysisCard("空分析", [], None)
        assert card is not None
        card.deleteLater()


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
