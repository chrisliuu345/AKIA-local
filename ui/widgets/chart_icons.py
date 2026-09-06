"""
图表类型线条图标 — 用 matplotlib 运行期生成迷你图，替代 emoji

线条风单色（主题蓝 #4da6ff + 白高光），透明背景，与暗色界面一致。
懒生成 + 模块级缓存；生成失败返回空 QIcon（按钮退化为纯文字）。
"""

from io import BytesIO
from typing import Callable, Dict

from matplotlib.patches import Rectangle
from PySide6.QtGui import QIcon, QPixmap

_BLUE = "#4da6ff"
_WHITE = "#e1e2e6"
_ICON_PX = 120


def _new_fig():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(_ICON_PX / 100, _ICON_PX / 100), dpi=100)
    fig.patch.set_alpha(0.0)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    return fig, ax


def _finish(fig):
    buf = BytesIO()
    fig.savefig(buf, format="png", transparent=True, dpi=100)
    import matplotlib.pyplot as plt
    plt.close(fig)
    buf.seek(0)
    pm = QPixmap()
    pm.loadFromData(buf.read(), "PNG")
    return QIcon(pm)


def _histogram(ax):
    for i, h in enumerate([0.35, 0.62, 0.85, 0.55, 0.4, 0.25]):
        x = 0.1 + i * 0.14
        ax.plot([x, x, x + 0.08, x + 0.08], [0.08, h, h, 0.08], color=_BLUE, lw=1.6)
    ax.plot([0.1, 0.9], [0.08, 0.08], color=_WHITE, lw=1.0)


def _boxplot(ax):
    ax.plot([0.24, 0.36], [0.15, 0.15], color=_WHITE, lw=1.0)
    ax.plot([0.64, 0.76], [0.15, 0.15], color=_WHITE, lw=1.0)
    ax.plot([0.24, 0.36], [0.85, 0.85], color=_WHITE, lw=1.0)
    ax.plot([0.64, 0.76], [0.85, 0.85], color=_WHITE, lw=1.0)
    ax.plot([0.3, 0.3], [0.15, 0.32], color=_WHITE, lw=1.0)
    ax.plot([0.3, 0.3], [0.68, 0.85], color=_WHITE, lw=1.0)
    ax.plot([0.7, 0.7], [0.15, 0.32], color=_WHITE, lw=1.0)
    ax.plot([0.7, 0.7], [0.68, 0.85], color=_WHITE, lw=1.0)
    box = [(0.3, 0.32), (0.3, 0.68), (0.7, 0.68), (0.7, 0.32), (0.3, 0.32)]
    xs, ys = zip(*box)
    ax.plot(xs, ys, color=_BLUE, lw=1.6)
    ax.plot([0.3, 0.7], [0.5, 0.5], color=_BLUE, lw=1.6)


def _scatter(ax):
    pts = [(0.2, 0.72), (0.35, 0.5), (0.5, 0.62), (0.65, 0.38),
           (0.8, 0.55), (0.3, 0.28), (0.55, 0.25), (0.75, 0.18)]
    for x, y in pts:
        ax.plot([x], [y], "o", ms=3.2, color=_BLUE, mec=_WHITE, mew=0.6)


def _probplot(ax):
    pts = [0.12, 0.22, 0.36, 0.52, 0.68, 0.87]
    ys = [0.1, 0.22, 0.4, 0.55, 0.7, 0.88]
    ax.plot(pts, ys, "o", ms=3.0, color=_BLUE, mec=_WHITE, mew=0.6)
    ax.plot([0.1, 0.92], [0.08, 0.9], color=_WHITE, lw=0.9, ls=":")


def _matrix(ax):
    for i in range(4):
        for j in range(4):
            x, y = 0.1 + j * 0.2, 0.1 + i * 0.2
            if i > j:
                color = _BLUE
                alpha = 0.6 if j >= 2 else 0.35
            else:
                color = "#3a4a63"
                alpha = 0.4
            ax.add_patch(Rectangle((x, y), 0.2, 0.2,
                                   facecolor=color, alpha=alpha,
                                   edgecolor=_WHITE, lw=0.7))


def _scatter_matrix(ax):
    for i in range(3):
        for j in range(3):
            x, y = 0.12 + j * 0.28, 0.12 + i * 0.28
            ax.add_patch(Rectangle((x, y), 0.24, 0.24,
                                       facecolor="none", edgecolor=_BLUE, lw=0.9))
            ax.plot([x + 0.05, x + 0.16, x + 0.11], [y + 0.16, y + 0.08, y + 0.19],
                    "o", ms=1.6, color=_BLUE)


def _residual(ax):
    ax.add_patch(Rectangle((0.08, 0.1), 0.4, 0.8, facecolor="none",
                               edgecolor=_BLUE, lw=1.0))
    pts = [(0.16, 0.62), (0.26, 0.44), (0.36, 0.55), (0.2, 0.28), (0.3, 0.36), (0.4, 0.24)]
    for x, y in pts:
        ax.plot([x], [y], "o", ms=2.2, color=_BLUE)
    ax.plot([0.12, 0.44], [0.42, 0.42], color=_WHITE, lw=0.8, ls="--")
    ax.add_patch(Rectangle((0.54, 0.1), 0.38, 0.8, facecolor="none",
                               edgecolor=_BLUE, lw=1.0))
    for h, y in [(0.5, 0.18), (0.8, 0.3)]:
        pass
    ax.plot([0.72, 0.72], [0.2, 0.7], color=_BLUE, lw=2.2)
    ax.plot([0.72, 0.72], [0.2, 0.44], color=_WHITE, lw=0.9)


def _pareto(ax):
    heights = [0.85, 0.62, 0.5, 0.34]
    for i, h in enumerate(heights):
        x = 0.1 + i * 0.2
        ax.add_patch(Rectangle((x, 0.1), 0.16, h,
                                   facecolor=_BLUE, alpha=0.55,
                                   edgecolor=_BLUE, lw=0.9))
    ax.plot([0.1, 0.3, 0.5, 0.7], [0.95, 0.78, 0.66, 0.5],
            color=_WHITE, lw=1.0, marker="o", ms=2.0)


def _small_multiples(ax):
    for i in range(2):
        for j in range(2):
            x, y = 0.1 + j * 0.42, 0.1 + i * 0.42
            ax.add_patch(Rectangle((x, y), 0.38, 0.38, facecolor="none",
                                       edgecolor=_BLUE, lw=0.8))
            ax.plot([x + 0.06, x + 0.2, x + 0.19], [y + 0.08, y + 0.26, y + 0.16],
                    color=_BLUE, lw=1.1)


def _main_effects(ax):
    for j, ys in enumerate([[0.2, 0.62], [0.42, 0.44], [0.24, 0.68]]):
        xs = [0.15, 0.85]
        ax.plot(xs, ys, color=_BLUE if j != 1 else _WHITE, lw=1.3,
                marker="o", ms=2.2, mec=_BLUE if j != 1 else _WHITE, mew=0.5)


def _interaction(ax):
    ax.plot([0.2, 0.8], [0.7, 0.3], color=_BLUE, lw=1.5, marker="o", ms=2.4)
    ax.plot([0.2, 0.8], [0.3, 0.7], color=_WHITE, lw=1.5, marker="o", ms=2.4)


def _contour(ax):
    import numpy as np
    t = np.linspace(0, 3.14 * 2, 40)
    for k in (1.0, 0.66, 0.33):
        r = 0.32 * k
        ax.plot(0.5 + r * np.cos(t), 0.5 + r * np.sin(t),
                color=_BLUE, lw=1.1, alpha=0.9)


def _surface_3d(ax):
    import numpy as np
    for j in range(4):
        xs = np.linspace(0.1, 0.9, 30)
        ys = 0.2 + 0.55 * np.exp(-((xs - 0.5) ** 2) / 0.15) * (0.6 + j * 0.1)
        ax.plot(xs, ys, color=_BLUE if j % 2 == 0 else _WHITE, lw=1.0)
        ax.plot([xs[0], xs[0]], [ys[0] - 0.12, ys[0]], color=_BLUE, lw=0.8)


def _time_series(ax):
    xs = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.72, 0.82, 0.9]
    ys = [0.35, 0.55, 0.42, 0.72, 0.58, 0.8, 0.62, 0.86, 0.68]
    ax.plot(xs, ys, color=_BLUE, lw=1.5, marker="o", ms=2.2)
    ax.plot([0.1, 0.9], [0.55, 0.62], color=_WHITE, lw=0.8, ls="--")


def _bubble(ax):
    for x, y, r in [(0.3, 0.45, 0.13), (0.55, 0.6, 0.08), (0.7, 0.32, 0.18),
                    (0.42, 0.22, 0.06)]:
        import matplotlib.patches as mpatches
        ax.add_patch(mpatches.Circle((x, y), r, facecolor=_BLUE, alpha=0.35,
                                     edgecolor=_BLUE, lw=1.0))


def _radar(ax):
    import numpy as np
    ang = np.linspace(0, 2 * np.pi, 5, endpoint=False)
    vals = [0.7, 0.45, 0.62, 0.38, 0.55]
    xs = [0.5 + 0.35 * v * np.cos(a) for v, a in zip(vals, ang)]
    ys = [0.5 + 0.35 * v * np.sin(a) for v, a in zip(vals, ang)]
    ax.plot(xs + xs[:1], ys + ys[:1], color=_BLUE, lw=1.4)
    for a in ang:
        ax.plot([0.5, 0.5 + 0.35 * np.cos(a)], [0.5, 0.5 + 0.35 * np.sin(a)],
                color=_WHITE, lw=0.6)


def _waterfall(ax):
    tops = [0.75, 0.55, 0.62, 0.3]
    prev = 0.1
    for i, (x, top) in enumerate(zip([0.1, 0.3, 0.5, 0.7], tops)):
        ax.add_patch(Rectangle((x, prev), 0.16, top - prev,
                                   facecolor=_BLUE, alpha=0.5 if i < 3 else 0.8,
                                   edgecolor=_BLUE, lw=0.9))
        prev = top


_DRAW_FUNCS: Dict[str, Callable] = {
    "直方图": _histogram,
    "箱线图": _boxplot,
    "散点图": _scatter,
    "概率图": _probplot,
    "矩阵图": _matrix,
    "散点矩阵图": _scatter_matrix,
    "残差图": _residual,
    "帕累托图": _pareto,
    "小多图": _small_multiples,
    "主效应图": _main_effects,
    "交互效应图": _interaction,
    "等值线图": _contour,
    "3D曲面图": _surface_3d,
    "时间序列图": _time_series,
    "气泡图": _bubble,
    "雷达图": _radar,
    "瀑布图": _waterfall,
}

_CACHE: Dict[str, QIcon] = {}


def _icon_for(chart_type: str) -> QIcon:
    import matplotlib.pyplot as plt
    fig, ax = _new_fig()
    try:
        _DRAW_FUNCS[chart_type](ax)
        return _finish(fig)
    except Exception:
        plt.close(fig)
        return QIcon()


def get_chart_icon(chart_type: str) -> QIcon:
    """获取图表类型线条图标（懒生成 + 缓存）"""
    if chart_type not in _CACHE:
        _CACHE[chart_type] = _icon_for(chart_type)
    return _CACHE[chart_type]


def has_custom_icon(chart_type: str) -> bool:
    return chart_type in _DRAW_FUNCS
