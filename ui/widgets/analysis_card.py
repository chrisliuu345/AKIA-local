"""AnalysisCard — 单个分析结果卡片：标题 + 指标 + 图表快照

用于 Dashboard 垂直滚动面板，每个分析类型一张卡片。
图表通过 QPixmap 快照嵌入（非 live canvas），避免多 matplotlib 实例性能问题。
"""

from copy import deepcopy
from io import BytesIO

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from ui.theme import colors as theme_colors, FONT_11B, FONT_9
from ui.widgets.flow_layout import FlowLayout

try:
    import matplotlib.pyplot as _plt
    _HAS_MPL = True
except ImportError:
    _HAS_MPL = False

CHART_SNAPSHOT_W = 1000
CHART_SNAPSHOT_H = 600
CHART_DPI = 200

CARD_PADDING = 16
CARD_RADIUS = 10


def _thumbnail_face() -> str:
    """快照底色跟界面页底，不再铺白。"""
    return theme_colors().get("bg_body", "#141414")


def _line_readable_on(face: str, fig) -> None:
    """快照坐标区改成界面黑。贴近黑底的折线和文字改成能看清的颜色。"""
    import matplotlib.colors as mcolors

    bg = mcolors.to_rgb(face)
    ink = theme_colors().get("accent", "#4F73DC")
    text_color = theme_colors().get("text_primary", "#EDEDED")

    def too_close(color) -> bool:
        try:
            rgb = mcolors.to_rgb(color)
        except (ValueError, TypeError):
            return False
        return sum((channel - base) ** 2 for channel, base in zip(rgb, bg, strict=True)) < 0.08

    for ax in fig.axes:
        try:
            ax.set_facecolor(face)
        except (AttributeError, ValueError):
            continue
        for line in getattr(ax, "lines", []):
            if too_close(line.get_color()):
                line.set_color(ink)
        for spine in ax.spines.values():
            if too_close(spine.get_edgecolor()):
                spine.set_edgecolor("#333333")
        for text in list(getattr(ax, "texts", [])) + [ax.title, ax.xaxis.label, ax.yaxis.label]:
            if too_close(text.get_color()):
                text.set_color(text_color)
        ax.tick_params(colors=theme_colors().get("text_secondary", "#A3A3A3"))


def figure_to_pixmap(fig, width: int = CHART_SNAPSHOT_W,
                     height: int = CHART_SNAPSHOT_H, dpi: int = CHART_DPI) -> QPixmap | None:
    """将 matplotlib Figure 渲染为 QPixmap 快照。底色是界面黑，不是白。"""
    if not _HAS_MPL or fig is None:
        return None
    try:
        fig2 = deepcopy(fig)
        fig2.set_size_inches(width / dpi, height / dpi, forward=False)
        face = _thumbnail_face()
        fig2.patch.set_facecolor(face)
        _line_readable_on(face, fig2)
        buf = BytesIO()
        fig2.savefig(buf, format="png", dpi=dpi, bbox_inches="tight",
                     facecolor=face, edgecolor=face)
        buf.seek(0)
        pm = QPixmap()
        pm.loadFromData(buf.read())
        _plt.close(fig2)
        return pm if not pm.isNull() else None
    except Exception:
        return None


class AnalysisCard(QFrame):
    """单个分析结果卡片 — 垂直排列：标题行 + 指标行 + 图表区"""

    def __init__(self, atype: str, rows: list[str], figure=None,
                 status_color: str = "#737373", timestamp: str = "",
                 parent=None):
        super().__init__(parent)
        self._atype = atype
        self._setup_ui(rows, figure, status_color, timestamp)

    def _setup_ui(self, rows: list[str], figure, status_color: str, timestamp: str):
        tc = theme_colors()

        self.setStyleSheet(
            f"AnalysisCard {{ background:{tc['bg_card']}; "
            f"border:1px solid {tc['border']}; border-radius:{CARD_RADIUS}px; }}"
        )
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.setMinimumWidth(400)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(CARD_PADDING, CARD_PADDING, CARD_PADDING, CARD_PADDING)
        outer.setSpacing(8)

        hdr = QHBoxLayout()
        hdr.setSpacing(6)

        title_lbl = QLabel(self._atype)
        title_lbl.setFont(FONT_11B)
        title_lbl.setWordWrap(True)
        title_lbl.setStyleSheet(f"color:{tc['accent_bright']}; background:transparent;")
        title_lbl.setMinimumWidth(120)
        title_lbl.setToolTip(self._atype)
        hdr.addWidget(title_lbl, 1)

        if timestamp:
            ts_lbl = QLabel(timestamp)
            ts_lbl.setFont(FONT_9)
            ts_lbl.setStyleSheet(f"color:{tc['text_muted']}; background:transparent;")
            ts_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            ts_lbl.setFixedWidth(50)
            hdr.addWidget(ts_lbl)

        dot = QLabel("●")
        dot.setFixedSize(12, 12)
        dot.setAlignment(Qt.AlignCenter)
        dot.setStyleSheet(f"color:{status_color}; font-size:9px; background:transparent;")
        hdr.addWidget(dot)

        outer.addLayout(hdr)

        if rows:
            metrics_widget = self._build_metrics_widget(rows, tc)
            outer.addWidget(metrics_widget)

        pm = figure_to_pixmap(figure) if figure is not None else None
        if pm is not None:
            chart_lbl = QLabel()
            chart_lbl.setPixmap(pm.scaled(
                CHART_SNAPSHOT_W, CHART_SNAPSHOT_H,
                Qt.KeepAspectRatio, Qt.SmoothTransformation,
            ))
            chart_lbl.setAlignment(Qt.AlignCenter)
            chart_lbl.setStyleSheet(f"background:{tc['bg_body']}; border-radius:6px;")
            chart_lbl.setMinimumHeight(180)
            outer.addWidget(chart_lbl, 1)

    def _build_metrics_widget(self, rows: list[str], tc: dict) -> QFrame:
        """将指标行排列在 FlowLayout 中，自动换行防止截断"""
        container = QFrame()
        container.setStyleSheet(
            f"QFrame {{ background:{tc['bg_body']}; border-radius:6px; }}"
        )
        flow = FlowLayout(container, margin=10, h_spacing=12, v_spacing=4)

        metric_font = FONT_11B
        for text in rows:
            lbl = QLabel(text)
            lbl.setFont(metric_font)
            lbl.setWordWrap(True)
            lbl.setStyleSheet(f"color:{tc['text_primary']}; background:transparent;")
            lbl.setMinimumWidth(60)
            lbl.setMinimumHeight(24)
            flow.addWidget(lbl)

        return container
