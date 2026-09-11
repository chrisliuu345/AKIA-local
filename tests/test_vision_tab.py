"""Vision Tab 测试 — 注册/懒加载/端到端视频分析/发送工时研究/依赖降级提示。"""
import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication


def _pump_until(condition, timeout: float = 30.0) -> bool:
    app = QApplication.instance()
    deadline = time.time() + timeout
    while time.time() < deadline:
        app.processEvents()
        if condition():
            return True
        time.sleep(0.02)
    return False


@pytest.fixture
def tab(_qt_application):
    from ui.tabs.vision_tab import VisionTab

    widget = VisionTab()
    widget.resize(1200, 800)
    widget.show()
    yield widget
    widget._stop_workers()
    widget.close()
    widget.deleteLater()


def _write_phase_video(tmp_path):
    cv2 = pytest.importorskip("cv2")
    path = tmp_path / "vision_phase.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"),
                             10.0, (320, 240))
    assert writer.isOpened()
    for i in range(45):
        frame = np.full((240, 320, 3), 28, dtype=np.uint8)
        t = i / 10.0
        if t < 2.5:                          # 原地作业 → 工作周期
            size = int(42 + 12 * np.sin(i / 4.0))
            x, y = 160 - size // 2, 120 - size // 2
            frame[y:y + size, x:x + size] = 235
        else:                                # 匀速移动 → 走动
            x = 10 + int((300 - 40 - 10) * min(1.0, (t - 2.5) / 2.0))
            frame[100:140, x:x + 40] = 235
        writer.write(frame)
    writer.release()
    return str(path)


def test_tab_registered_with_expected_entry():
    from ui._tab_registry import INDEX_MAP, TAB_INDEX, TAB_REGISTRY

    entry = INDEX_MAP[37]
    assert entry[2] == "VisionTab"
    assert entry[3] == "ui.tabs.vision_tab"
    assert TAB_INDEX["vision"] == 37
    assert any(e[0] == 37 for e in TAB_REGISTRY)


def test_sidebar_and_menu_include_vision():
    from ui.main_window import MainWindow

    win = MainWindow()
    try:
        assert 37 in win.sidebar.nav_buttons
        assert win.sidebar.nav_buttons[37].text() == "视频时间研究"
        ie_menu = None
        for action in win.menuBar().actions():
            menu = action.menu()
            if menu is None:
                continue
            for sub in menu.actions():
                if sub.menu() and "IE" in sub.text():
                    ie_menu = sub.menu()
        assert ie_menu is not None
        assert any(a.text() == "视频时间研究" for a in ie_menu.actions())
    finally:
        win.close()


def test_tab_widgets_and_backend_status(tab):
    from analysis.vision import vision_available

    assert tab.source_combo.count() == 5
    assert tab.ratio_table.columnCount() == 3
    assert tab.cycle_table.columnCount() == 3
    assert "后端:" in tab.backend_label.text() or not vision_available()
    assert tab.start_btn.isEnabled() == vision_available()


def test_analysis_end_to_end_and_send_to_time_study(tab, tmp_path):
    pytest.importorskip("cv2")
    path = _write_phase_video(tmp_path)
    tab.source_combo.setCurrentIndex(tab.source_combo.findData("file"))
    tab.source_edit.setText(path)
    tab.sample_fps_spin.setValue(10.0)
    tab.max_seconds_spin.setValue(30)
    received: list = []
    tab.send_to_time_study.connect(received.append)

    tab._on_start()
    assert _pump_until(lambda: tab.result is not None
                       or "失败" in tab.summary_label.text())
    assert tab.result is not None, tab.progress_label.text()
    assert tab.result.frames >= 35
    assert tab.result.cycles, "应识别出作业周期"
    assert tab.ratio_table.rowCount() > 0
    assert tab.cycle_table.rowCount() == len(tab.result.cycles)
    assert tab.send_btn.isEnabled()
    assert "完成" in tab.progress_label.text() or "后端" in tab.summary_label.text()

    tab._on_send_to_time_study()
    assert received and len(received[0]) == len(tab.result.cycles)
    assert received[0][0].observation_time > 0


def test_source_and_roi_validation(tab):
    with pytest.raises(ValueError):
        tab._source_spec()                      # 默认是文件类型且路径为空
    tab.source_edit.setText("/tmp/definitely-missing-vision-clip.mp4")
    with pytest.raises(FileNotFoundError):
        tab._source_spec()
    tab.source_combo.setCurrentIndex(tab.source_combo.findData("synthetic"))
    assert tab._source_spec() == "synthetic"
    tab.roi_edit.setText("1,2,3")
    with pytest.raises(ValueError):
        tab._build_config()


def test_missing_opencv_shows_install_hint(_qt_application, monkeypatch):
    import analysis.vision as vision_pkg
    from ui.tabs.vision_tab import VisionTab

    monkeypatch.setattr(vision_pkg, "cv2_available", lambda: False)
    widget = VisionTab()
    try:
        assert widget.start_btn.isEnabled() is False
        assert "requirements-vision" in widget.backend_label.text()
    finally:
        widget.close()
        widget.deleteLater()
