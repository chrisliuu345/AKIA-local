"""图表交互缩放（v3.8.0）— 滚轮缩放 / Shift+滚轮 纵向缩放 / 双击复位。

仅用于实时图表（普通分析图保持既有交互），纯函数 zoom_range 独立可测。
"""
from __future__ import annotations

MIN_SPAN = 1e-9


def zoom_range(lo: float, hi: float, factor: float,
               center: float | None = None) -> tuple[float, float]:
    """按 factor 缩放区间 [lo, hi]；factor<1 放大，>1 缩小。

    center 为不动点（通常是鼠标位置），缺省取区间中点。
    退化区间（hi<=lo）原样返回；缩放后跨度下限 MIN_SPAN 防止塌缩。
    """
    if not (hi > lo):
        return lo, hi
    c = (lo + hi) / 2.0 if center is None else float(center)
    c = min(max(c, lo), hi)
    new_lo = c - (c - lo) * factor
    new_hi = c + (hi - c) * factor
    if new_hi - new_lo < MIN_SPAN:
        mid = (new_lo + new_hi) / 2.0
        return mid - MIN_SPAN / 2.0, mid + MIN_SPAN / 2.0
    return new_lo, new_hi


def attach_wheel_zoom(canvas) -> None:
    """给 matplotlib canvas 挂滚轮缩放 + 双击复位。

    横向缩放作用于所有共享 x 轴的子图（控制图上下两栏同步）；按住 Shift
    时改为纵向缩放鼠标所在子图。
    """
    fig = canvas.figure
    home: dict[int, tuple] = {id(ax): (ax.get_xlim(), ax.get_ylim())
                              for ax in fig.axes}

    def _scale_axes(axes, factor: float, center, axis: str) -> None:
        for ax in axes:
            if axis == "x":
                lo, hi = ax.get_xlim()
                ax.set_xlim(*zoom_range(lo, hi, factor, center))
            else:
                lo, hi = ax.get_ylim()
                ax.set_ylim(*zoom_range(lo, hi, factor, center))

    def on_scroll(event):
        if event.inaxes is None:
            return
        factor = 0.85 if event.step > 0 else 1.0 / 0.85
        shift = "shift" in (event.key or "")
        if shift:
            y_lo, y_hi = event.inaxes.get_ylim()
            span = (y_hi - y_lo) or 1.0
            frac = 0.5 if event.ydata is None else (event.ydata - y_lo) / span
            center = y_lo + span * frac
            _scale_axes([event.inaxes], factor, center, "y")
        else:
            shared = [ax for ax in fig.axes
                      if ax.get_shared_x_axes().joined(ax, event.inaxes)]
            _scale_axes(shared, factor, event.xdata, "x")
        canvas.draw_idle()

    def on_dblclick(event):
        for ax in fig.axes:
            xlim, ylim = home.get(id(ax), (None, None))
            if xlim:
                ax.set_xlim(*xlim)
            if ylim:
                ax.set_ylim(*ylim)
        canvas.draw_idle()

    canvas.mpl_connect("scroll_event", on_scroll)
    canvas.mpl_connect("button_press_event", on_dblclick)
