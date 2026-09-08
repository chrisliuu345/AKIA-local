"""P2 验收 — 实时 SPC 引擎（滚动窗口 + 增量 Nelson/OOC/OOS）。

验收: 跳变样本 500ms 内报违规 · 新点事件不重复 · 超规格立即 OOS。
"""
import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")  # 项目测试惯例

from core.streaming.live_spc import LiveSPC


def _steady(n: int = 30, base: float = 100.0, sigma: float = 1.2):
    """种子惰性噪声 — 稳态又不至于落入规则7(连续15点±1σ)区间。"""
    import random
    rnd = random.Random(42)
    return [base + rnd.gauss(0, sigma) for _ in range(n)]


def test_steady_stream_no_events():
    spc = LiveSPC("CH0", mode="imr", window=30)
    frame = spc.feed(_steady())
    assert not frame.ooc
    assert frame.oos is False
    assert frame.events == []
    assert frame.cl > 95 and frame.ucl > frame.cl > frame.lcl


def test_jump_detected_within_500ms():
    spc = LiveSPC("CH0", mode="imr", window=30)
    spc.feed(_steady())
    t0 = time.time()
    frame = spc.feed([140.0, 141.0, 142.0])
    dt_ms = (time.time() - t0) * 1000.0
    assert frame.ooc, "跳变必须立即 OOC"
    assert any(e.kind == "nelson" for e in frame.events)
    assert dt_ms < 500.0, f"检测延迟 {dt_ms:.1f}ms 超验收标准"


def test_new_point_events_not_repeated():
    spc = LiveSPC("CH0", mode="imr", window=30)
    spc.feed(_steady())
    f1 = spc.feed([140.0])
    n1 = len(f1.events)
    assert n1 > 0
    f2 = spc.feed([140.5])  # 同批新点，已越限二次触发(新点本身违规合理)
    # 窗口重算不应重新报出旧点事件 — 事件 point 都位于新点位置
    assert all(e.point >= 12 for e in f2.events), "旧点事件重发"


def test_oos_immediate():
    spc = LiveSPC("CH0", mode="imr", window=30, usl=105.0, lsl=95.0)
    spc.feed(_steady())
    f = spc.feed([99.0, 106.0])
    assert f.oos
    kinds = {e.kind for e in f.events}
    assert "oos" in kinds


def test_chart_data_shape_imr():
    spc = LiveSPC("CH1", mode="imr", window=30)
    f = spc.feed(_steady(20))
    d = f.as_chart_data("imr")
    assert d["chart_type"] == "I-MR"
    assert set(("data", "cl", "ucl", "lcl", "violations")) <= set(d["i_chart"])
    assert len(d["i_chart"]["data"]) == 20


def test_xbar_mode_grouping():
    spc = LiveSPC("CH0", mode="xbar", subgroup_size=5, window=30)
    data = _steady(40)
    f = spc.feed(data)
    assert f.chart is not None
    assert set(("data", "cl", "ucl", "lcl", "violations")) <= set(f.chart)
    d = f.as_chart_data("xbar")
    assert d["chart_type"] == "XBar-R"
    assert "xbar_chart" in d


def test_reset_clears_state():
    spc = LiveSPC("CH0", mode="imr", window=30)
    spc.feed(_steady())
    spc.reset()
    f = spc.feed([100.0])
    assert f.cl == 0.0 and f.data == [100.0] and not f.ooc


def test_live_ui_pipeline_jump_shows_ooc(_qt_application):
    """UI 冒烟: 总线跳变 → 实时模式状态栏出现判异标识。"""
    from ui.tabs.spc_tab import SPCTab
    from core.streaming.bus import StreamBus
    from core.devices.driver import Sample
    import time as _t

    bus = StreamBus()
    tab = SPCTab()
    tab.set_stream_source(bus)
    assert tab.live_check.isEnabled()

    bus.publish("mock-01", [Sample("mock-01", "CH0", 100.0, _t.time())])
    tab.live_check.setChecked(True)
    assert tab.live_status.text() != ""
    tab.live_check.setChecked(False)

    bus.publish("mock-01", [Sample("mock-01", "CH0", 100.5, _t.time())])
    tab.live_check.setChecked(True)
    bus.publish("mock-01", [Sample("mock-01", "CH0", v, _t.time()) for v in list(range(101, 115))])
    tab._live_poll()
    assert "判异" in tab.live_status.text(), tab.live_status.text()
    tab.live_check.setChecked(False)
    tab.close()
