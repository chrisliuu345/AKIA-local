"""v3.8.0-1 实时图表增强 — USL/LSL 规格线 + 缩放。

覆盖: LiveSPC 规格限输出 / 控制图规格线绘制 / 滚轮缩放纯函数与绑定 / 看板资产
断言（规格线 + 缩放交互存在）。
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from core.streaming.live_spc import LiveSPC


def _steady(n: int = 40, base: float = 100.0):
    import random
    rnd = random.Random(7)
    return [base + rnd.gauss(0, 1.0) for _ in range(n)]


def test_spec_limits_only_when_configured():
    spc = LiveSPC("CH0", window=30)
    assert spc.spec_limits() == {}
    assert "spec" not in spc.feed(_steady()).as_chart_data("imr")

    spc = LiveSPC("CH0", window=30, usl=110.0)
    assert spc.spec_limits() == {"usl": 110.0}
    assert spc.feed(_steady()).as_chart_data("imr")["spec"] == {"usl": 110.0}


def test_chart_data_carries_spec_for_both_modes():
    spc = LiveSPC("CH0", mode="xbar", subgroup_size=5, window=30,
                  usl=105.0, lsl=95.0)
    data = spc.feed(_steady()).as_chart_data("xbar")
    assert data["spec"] == {"usl": 105.0, "lsl": 95.0}


def _line_labels(fig):
    return [line.get_label() for ax in fig.axes for line in ax.get_lines()]


def test_control_chart_draws_spec_lines():
    import matplotlib.pyplot as plt

    from output.chart_engine import create_control_chart

    spc = LiveSPC("CH0", window=30, usl=104.0, lsl=96.0)
    frame = spc.feed(_steady())
    fig = create_control_chart(frame.as_chart_data("imr"), title="t")
    labels = _line_labels(fig)
    assert any(label.startswith("USL=") for label in labels)
    assert any(label.startswith("LSL=") for label in labels)
    plt.close(fig)


def test_control_chart_without_spec_has_no_spec_lines():
    import matplotlib.pyplot as plt

    from output.chart_engine import create_control_chart

    spc = LiveSPC("CH0", window=30)
    frame = spc.feed(_steady())
    fig = create_control_chart(frame.as_chart_data("imr"), title="t")
    labels = _line_labels(fig)
    assert not any(label.startswith(("USL=", "LSL=")) for label in labels)
    plt.close(fig)


def test_zoom_range_contracts_and_keeps_center():
    from ui.widgets.chart_zoom import zoom_range

    assert zoom_range(0.0, 100.0, 0.5) == (25.0, 75.0)
    # 不动点保持: center=0 时下界不动
    assert zoom_range(0.0, 100.0, 0.5, center=0.0) == (0.0, 50.0)
    # 退化区间原样返回
    assert zoom_range(5.0, 5.0, 0.5) == (5.0, 5.0)
    # 极端缩小时跨度不为 0
    lo, hi = zoom_range(0.0, 100.0, 1e-18)
    assert hi > lo


def test_zoom_range_center_clamped_to_bounds():
    from ui.widgets.chart_zoom import zoom_range

    assert zoom_range(0.0, 10.0, 0.5, center=999.0) == (5.0, 10.0)


def test_attach_wheel_zoom_binds_without_error():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_agg import FigureCanvasAgg

    from ui.widgets.chart_zoom import attach_wheel_zoom

    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [1, 2, 3])
    canvas = FigureCanvasAgg(fig)
    before = ax.get_xlim()
    attach_wheel_zoom(canvas)
    assert ax.get_xlim() == before
    plt.close(fig)


def test_dashboard_asset_has_spec_and_zoom():
    html = Path("server/dashboard.html").read_text(encoding="utf-8")
    assert "USL" in html and "LSL" in html
    assert "wheel" in html and "dblclick" in html       # 缩放 / 复位
    assert "mousedown" in html and "mousemove" in html  # 拖拽平移
    assert "specs" in html and "c2185b" in html         # 规格线样式
