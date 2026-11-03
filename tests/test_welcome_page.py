"""欢迎页版式：信号、文案、最近项目和无障碍名。"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QSizePolicy, QVBoxLayout, QWidget

from config.settings import APP_FULL_NAME, APP_VERSION
from core.i18n import i18n
from ui.welcome_page import LOGO_HEIGHT, WelcomePage

app = QApplication.instance() or QApplication([])

ACTION_TITLES = (
    "导入工作表",
    "打开项目",
    "导入IE数据",
    "新建分析",
    "智能诊断",
    "改善案例",
)
EMPTY_TEXT = "还没有最近项目。导入工作表或打开 .qap 项目后，会显示在这里。"
SIGNALS = (
    "import_data_clicked",
    "import_ie_clicked",
    "import_template_clicked",
    "diagnose_clicked",
    "new_analysis_clicked",
    "open_project_clicked",
    "case_center_clicked",
)


def _page() -> WelcomePage:
    page = WelcomePage()
    page.resize(1090, 800)
    page.show()
    app.processEvents()
    return page


def _collected(page: QWidget) -> str:
    parts: list[str] = []
    for widget in [page, *page.findChildren(QWidget)]:
        parts.append(widget.accessibleName())
        parts.append(widget.accessibleDescription())
        tooltip = widget.toolTip()
        if tooltip:
            parts.append(tooltip)
        if isinstance(widget, QLabel):
            parts.append(widget.text())
    return "\n".join(parts)


def _action(page: WelcomePage, title: str) -> QWidget:
    matches = [
        widget
        for widget in page.findChildren(QWidget, "welcomeAction")
        if widget.accessibleName() == title
    ]
    assert len(matches) == 1, title
    return matches[0]


def test_seven_signals_exist():
    for name in SIGNALS:
        assert hasattr(WelcomePage, name), name


def test_visible_copy_and_no_template_or_version():
    page = _page()
    try:
        text = _collected(page)
        for title in ACTION_TITLES:
            assert title in text
        assert "选择一个 .qap 项目文件" in text
        assert "打开最近使用的 .qap 项目" not in text
        assert EMPTY_TEXT in text
        assert APP_FULL_NAME in text
        assert "加载分析模板" not in text
        assert f"v{APP_VERSION}" not in text
        assert i18n.tr("welcome.section_start") == "开始"
        assert i18n.tr("welcome.open_project_desc") == "选择一个 .qap 项目文件"
    finally:
        page.close()


def test_accessible_names_match_action_titles():
    page = _page()
    try:
        names = [
            widget.accessibleName()
            for widget in page.findChildren(QWidget, "welcomeAction")
        ]
        assert names == list(ACTION_TITLES)
        for title in ACTION_TITLES:
            assert _action(page, title).accessibleName() == title
    finally:
        page.close()


def test_primary_actions_are_larger_than_secondary():
    page = _page()
    try:
        primary = _action(page, "导入工作表")
        secondary = _action(page, "导入IE数据")
        assert primary.minimumHeight() > secondary.minimumHeight()
        assert primary.height() > secondary.height()
        assert primary.property("kind") == "solid"
        assert _action(page, "打开项目").property("kind") == "outline"
        assert secondary.property("kind") == "secondary"
    finally:
        page.close()


def test_actions_stay_inside_centered_column_when_page_is_wide():
    page = _page()
    try:
        page.resize(1400, 800)
        app.processEvents()
        primary = _action(page, "导入工作表")
        assert primary.width() < 500
        logo_center = page.logo_label.mapTo(page, page.logo_label.rect().center())
        assert abs(logo_center.x() - page.width() / 2) <= 2
    finally:
        page.close()


def test_empty_recent_has_no_path_rows():
    page = _page()
    try:
        page.set_recent_projects([])
        app.processEvents()
        assert page.findChildren(QWidget, "welcomeRecentRow") == []
        empty = page.findChild(QLabel, "welcomeRecentEmpty")
        assert empty is not None
        assert empty.text() == EMPTY_TEXT
        assert "/tmp/" not in _collected(page)
    finally:
        page.close()


def test_recent_list_keeps_five_and_hides_the_sixth():
    page = _page()
    try:
        items = [(f"项目{i}", f"/tmp/akia_recent_{i}.qap") for i in range(6)]
        page.set_recent_projects(items)
        app.processEvents()
        rows = page.findChildren(QWidget, "welcomeRecentRow")
        assert len(rows) == 5
        assert page.findChild(QLabel, "welcomeRecentEmpty") is None
        text = _collected(page)
        for i in range(5):
            assert f"/tmp/akia_recent_{i}.qap" in text
            assert f"项目{i}" in text
        assert "/tmp/akia_recent_5.qap" not in text
        assert "项目5" not in text
    finally:
        page.close()


def test_refresh_texts_keeps_visible_sentences():
    page = _page()
    try:
        page.subtitle_label.setText("changed")
        _action(page, "导入工作表").setAccessibleName("changed")
        page.refresh_texts()
        app.processEvents()
        text = _collected(page)
        assert page.subtitle_label.text() == APP_FULL_NAME
        for title in ACTION_TITLES:
            assert title in text
        assert EMPTY_TEXT in text
        assert "选择一个 .qap 项目文件" in text
        assert "加载分析模板" not in text
    finally:
        page.close()


def test_left_click_and_keys_emit_right_click_does_not():
    page = _page()
    try:
        got: list[str] = []
        page.import_data_clicked.connect(lambda: got.append("click"))
        action = _action(page, "导入工作表")
        QTest.mouseClick(action, Qt.LeftButton)
        assert got == ["click"]
        QTest.mouseClick(action, Qt.RightButton)
        assert got == ["click"]
        action.setFocus()
        QTest.keyClick(action, Qt.Key_Return)
        QTest.keyClick(action, Qt.Key_Space)
        QTest.keyClick(action, Qt.Key_Enter)
        assert got == ["click", "click", "click", "click"]
    finally:
        page.close()


def test_recent_row_calls_loader_on_left_click_only():
    class Host(QWidget):
        def __init__(self):
            super().__init__()
            self.loaded: list[str] = []
            self.page = WelcomePage()
            layout = QVBoxLayout(self)
            layout.addWidget(self.page)

        def _load_project_by_path(self, path: str):
            self.loaded.append(path)

    host = Host()
    host.resize(1000, 800)
    host.page.set_recent_projects([("线A", "/tmp/akia_line_a.qap"), ("线B", "/tmp/akia_line_b.qap")])
    host.show()
    app.processEvents()
    try:
        rows = host.page.findChildren(QWidget, "welcomeRecentRow")
        QTest.mouseClick(rows[0], Qt.RightButton)
        assert host.loaded == []
        QTest.mouseClick(rows[0], Qt.LeftButton)
        assert host.loaded == ["/tmp/akia_line_a.qap"]
        rows[1].setFocus()
        QTest.keyClick(rows[1], Qt.Key_Space)
        assert host.loaded == ["/tmp/akia_line_a.qap", "/tmp/akia_line_b.qap"]
    finally:
        host.close()


def test_wordmark_is_enlarged_from_the_high_res_asset():
    page = _page()
    try:
        assert page._wordmark_path.endswith("logo_wordmark_light.png")
        source = QImage(page._wordmark_path)
        assert source.width() >= 2000
        assert source.height() >= 500
        pixmap = page.logo_label.pixmap()
        assert pixmap is not None and not pixmap.isNull()
        assert not page.logo_label.hasScaledContents()
        assert pixmap.height() <= source.height()
        logical = pixmap.height() / pixmap.devicePixelRatio()
        assert logical == LOGO_HEIGHT
        assert page.logo_label.height() > 64
        assert page.logo_label.height() == LOGO_HEIGHT
    finally:
        page.close()


def test_page_hint_stays_small_enough_for_the_shared_scroll_area():
    page = _page()
    try:
        hint = page.minimumSizeHint()
        assert hint.width() == 640
        assert hint.height() == 480
        policy = page.sizePolicy()
        assert policy.horizontalPolicy() == QSizePolicy.Expanding
        assert policy.verticalPolicy() == QSizePolicy.Expanding
        assert page._scroll.verticalScrollBar().maximum() == 0
    finally:
        page.close()


def test_removed_ring_and_gradient_decoration():
    source_path = os.path.join(os.path.dirname(__file__), "..", "ui", "welcome_page.py")
    with open(source_path, encoding="utf-8") as handle:
        source = handle.read()
    assert "drawEllipse" not in source
    assert "#0d1526" not in source
    assert "qlineargradient" not in source
    assert "APP_VERSION" not in source
