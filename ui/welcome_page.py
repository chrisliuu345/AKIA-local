"""欢迎页 — 居中内容柱、主次入口和最近项目。

信号与主窗口的连接保持原样，包括页面上不画出的 import_template_clicked。
页内滚动只包住入口和最近项目，避免和窗口共享滚动区叠成两根外层滚动条。
字标从现有高分辨率 PNG 按设备像素比缩小；源图不够高时保持原始像素，不再放大。
"""

import os

from PySide6.QtCore import QEvent, QPointF, QSize, Signal, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap, QRadialGradient
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from config.settings import APP_FULL_NAME
from core.i18n import i18n
from ui.font_config import get_ui_font
from ui.theme import colors as theme_colors
from ui.widgets.elided_label import ElidedLabel

# 版式常量。页边是柱两侧的最小留白；柱宽上限 860，更宽时只增加两侧空白。
# 字标上下留白把光晕中心留在首页上半部，而不是贴在顶边。
PAGE_MARGIN = 32
COLUMN_WIDTH = 860
HEADER_TOP = 96
HEADER_BOTTOM = 28
HEADER_GAP = 20
SECTION_GAP = 22
TILE_GAP = 12
ROW_GAP = 8
# 旧首页逻辑高度是 64。加大后仍低于字标原图高度（约 532px），只做缩小。
LOGO_HEIGHT = 96
GLOW_RADIUS = 280
GLOW_ALPHA = 28
PRIMARY_MIN_HEIGHT = 88
SECONDARY_MIN_HEIGHT = 72
RECENT_ROW_MIN_HEIGHT = 48
EMPTY_MIN_HEIGHT = 72
ACTION_RADIUS = 10
RECENT_RADIUS = 8
PATH_MAX_WIDTH = 420
RECENT_LIMIT = 5
PRIMARY_HINT_COLOR = "#5C5C5C"
MIN_PAGE_SIZE = QSize(640, 480)

_WORDMARK_CANDIDATES = (
    "assets/logo_wordmark_light.png",
    "assets/logo_wordmark.png",
    "logo.png",
)


def _font(size: int, bold: bool = False) -> QFont:
    font = QFont(get_ui_font(), size)
    font.setBold(bold)
    return font


class _ShrinkableElided(ElidedLabel):
    """允许布局把标签压窄到小于全文宽度，省略才有机会发生。"""

    def minimumSizeHint(self):
        hint = super().minimumSizeHint()
        return QSize(0, hint.height())


class _ClickableCard(QFrame):
    """左键、Enter 和 Space 触发；焦点框单独绘制，不挤占布局。"""

    activated = Signal()

    def __init__(self, *, radius: int, parent=None):
        super().__init__(parent)
        self._radius = radius
        self._pressed = False
        self._hover = False
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_Hover, True)

    def enterEvent(self, event):
        self._hover = True
        self._apply_chrome()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self._pressed = False
        self._apply_chrome()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._pressed = True
            self.setFocus(Qt.MouseFocusReason)
            self._apply_chrome()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        pressed = self._pressed
        self._pressed = False
        self._apply_chrome()
        if (
            pressed
            and event.button() == Qt.LeftButton
            and self.rect().contains(event.position().toPoint())
        ):
            self.activated.emit()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            self.activated.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.update()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.hasFocus():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(theme_colors()["accent_dark"]))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -2, -2), self._radius, self._radius)
        painter.end()

    def _apply_chrome(self):
        raise NotImplementedError


class _WelcomeAction(_ClickableCard):
    """主操作或次操作。kind 为 solid / outline / secondary，高度和字号因此不同。"""

    def __init__(self, title_key: str, desc_key: str, kind: str, parent=None):
        super().__init__(radius=ACTION_RADIUS, parent=parent)
        self._title_key = title_key
        self._desc_key = desc_key
        self._kind = kind
        self.setObjectName("welcomeAction")
        self.setProperty("kind", kind)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        if kind == "secondary":
            self.setMinimumHeight(SECONDARY_MIN_HEIGHT)
            title_size, desc_size = 13, 11
        else:
            self.setMinimumHeight(PRIMARY_MIN_HEIGHT)
            title_size, desc_size = 15, 12
        # 按钮和卡片标题不再加粗，小号黑体容易糊成一块。

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)
        layout.addStretch(1)

        self._title = QLabel()
        self._title.setFont(_font(title_size))
        self._title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._title.setWordWrap(True)
        self._title.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(self._title)

        self._desc = QLabel()
        self._desc.setFont(_font(desc_size))
        self._desc.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._desc.setWordWrap(True)
        self._desc.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(self._desc)
        layout.addStretch(1)
        self.refresh_texts()

    def refresh_texts(self):
        title = i18n.tr(self._title_key)
        self._title.setText(title)
        self._desc.setText(i18n.tr(self._desc_key))
        self.setAccessibleName(title)
        self._apply_chrome()

    def _colors(self) -> tuple[str, str, str, str]:
        tc = theme_colors()
        if self._kind == "solid":
            bg, border = "#E8E8E8", "#E8E8E8"
            title, desc = "#171717", PRIMARY_HINT_COLOR
            if self._pressed:
                bg, border = "#D0D0D0", "#D0D0D0"
            return bg, border, title, desc
        title, desc = tc["text_primary"], tc["text_secondary"]
        if self._kind == "outline":
            bg, border = tc["bg_card"], tc["border"]
            if self._pressed:
                bg = tc["bg_active"]
            return bg, border, title, desc
        bg, border = tc["bg_card"], tc["border"]
        if self._pressed:
            bg, border = tc["bg_active"], "#5C5C5C"
        elif self._hover:
            bg, border = tc["bg_hover"], "#5C5C5C"
        return bg, border, title, desc

    def _apply_chrome(self):
        bg, border, title, desc = self._colors()
        self.setStyleSheet(
            "QFrame#welcomeAction {"
            f"background-color: {bg};"
            f"border: 1px solid {border};"
            f"border-radius: {ACTION_RADIUS}px;"
            "}"
        )
        label = "background: transparent; border: none;"
        self._title.setStyleSheet(f"color: {title}; {label}")
        self._desc.setStyleSheet(f"color: {desc}; {label}")


class _RecentRow(_ClickableCard):
    def __init__(self, name: str, path: str, parent=None):
        super().__init__(radius=RECENT_RADIUS, parent=parent)
        self._path = path
        self.setObjectName("welcomeRecentRow")
        self.setAccessibleName(name)
        self.setAccessibleDescription(path)
        self.setToolTip(path)
        self.setMinimumHeight(RECENT_ROW_MIN_HEIGHT)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)

        self._name = _ShrinkableElided(name)
        self._name.setFont(_font(13))
        self._name.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._name.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._name.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(self._name, 1)

        self._path_label = _ShrinkableElided(path)
        self._path_label.setFont(_font(11))
        self._path_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._path_label.setMaximumWidth(PATH_MAX_WIDTH)
        self._path_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._path_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        layout.addWidget(self._path_label, 0)
        self._apply_chrome()

    def _apply_chrome(self):
        tc = theme_colors()
        bg, border = tc["bg_card"], tc["border"]
        if self._pressed:
            bg, border = tc["bg_active"], "#5C5C5C"
        elif self._hover:
            bg, border = tc["bg_hover"], "#5C5C5C"
        self.setStyleSheet(
            "QFrame#welcomeRecentRow {"
            f"background-color: {bg};"
            f"border: 1px solid {border};"
            f"border-radius: {RECENT_RADIUS}px;"
            "}"
        )
        plain = "background: transparent; border: none;"
        self._name.setStyleSheet(f"color: {tc['text_primary']}; {plain}")
        self._path_label.setStyleSheet(f"color: {tc['text_muted']}; {plain}")


class _CenteredColumn(QWidget):
    """把子栏限制在柱宽内并水平居中，左右至少留出页边。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.column = QWidget(self)
        self.column.setAttribute(Qt.WA_TranslucentBackground, True)
        self.column.setAutoFillBackground(False)
        self.column.setMaximumWidth(COLUMN_WIDTH)
        self.column.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        available = max(0, self.width() - PAGE_MARGIN * 2)
        width = min(COLUMN_WIDTH, available)
        x = (self.width() - width) // 2
        self.column.setGeometry(x, 0, width, max(0, self.height()))

    def sizeHint(self):
        hint = self.column.sizeHint()
        return QSize(COLUMN_WIDTH + PAGE_MARGIN * 2, hint.height())

    def minimumSizeHint(self):
        hint = self.column.minimumSizeHint()
        return QSize(0, hint.height())


class WelcomePage(QWidget):
    import_data_clicked = Signal()
    import_ie_clicked = Signal()
    import_template_clicked = Signal()
    diagnose_clicked = Signal()
    new_analysis_clicked = Signal()
    open_project_clicked = Signal()
    case_center_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._recent_items: list = []
        self._actions: list[_WelcomeAction] = []
        self._text_labels: list[tuple[QLabel, str]] = []
        self._wordmark_source = QPixmap()
        self._wordmark_path = ""
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setAutoFillBackground(False)
        self._setup_ui()
        self.refresh_texts()

    def set_recent_projects(self, items: list):
        self._recent_items = list(items or [])
        self._rebuild_recent_section()

    def minimumSizeHint(self):
        # 共享滚动区按这个提示定最小高度。内容更高时只滚页内滚动区。
        return QSize(MIN_PAGE_SIZE.width(), MIN_PAGE_SIZE.height())

    def sizeHint(self):
        return QSize(MIN_PAGE_SIZE.width(), MIN_PAGE_SIZE.height())

    def _load_wordmark_source(self) -> QPixmap:
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        for rel in _WORDMARK_CANDIDATES:
            path = os.path.join(root, rel)
            if not os.path.exists(path):
                continue
            candidate = QPixmap(path)
            if not candidate.isNull():
                self._wordmark_path = path
                return candidate
        self._wordmark_path = ""
        return QPixmap()

    def _wordmark_pixmap(self) -> QPixmap:
        source = self._wordmark_source
        if source.isNull():
            source = self._load_wordmark_source()
            self._wordmark_source = source
        if source.isNull():
            return source
        dpr = self.devicePixelRatioF() or 1.0
        target_px = max(1, int(round(LOGO_HEIGHT * dpr)))
        # 只从整张高分辨率字标缩小。源图像素不够时保持原图，避免放大发糊。
        if source.height() > target_px:
            scaled = source.scaledToHeight(target_px, Qt.SmoothTransformation)
            scaled.setDevicePixelRatio(dpr)
            return scaled
        native = QPixmap(source)
        native.setDevicePixelRatio(dpr)
        return native

    def _apply_logo(self):
        pixmap = self._wordmark_pixmap()
        self.logo_label.setPixmap(pixmap)
        self.logo_label.setAccessibleName(i18n.tr("welcome.title"))
        if pixmap.isNull():
            self.logo_label.setFixedSize(LOGO_HEIGHT * 4, LOGO_HEIGHT)
            return
        dpr = pixmap.devicePixelRatio() or 1.0
        self.logo_label.setFixedSize(
            max(1, int(round(pixmap.width() / dpr))),
            max(1, int(round(pixmap.height() / dpr))),
        )

    def _wordmark_center(self) -> QPointF:
        label = getattr(self, "logo_label", None)
        if label is None or label.width() <= 0:
            return QPointF(self.width() / 2.0, HEADER_TOP + LOGO_HEIGHT / 2.0)
        mapped = label.mapTo(self, label.rect().center())
        return QPointF(mapped)

    def _make_heading(self, key: str, size: int, color_key: str) -> QLabel:
        label = QLabel()
        label.setFont(_font(size))
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        tc = theme_colors()
        label.setStyleSheet(f"color: {tc[color_key]}; background: transparent; border: none;")
        self._text_labels.append((label, key))
        return label

    def _add_action(self, title_key: str, desc_key: str, kind: str, signal: Signal) -> _WelcomeAction:
        action = _WelcomeAction(title_key, desc_key, kind)
        action.activated.connect(signal.emit)
        self._actions.append(action)
        return action

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = _CenteredColumn()
        header_layout = QVBoxLayout(header.column)
        header_layout.setContentsMargins(0, HEADER_TOP, 0, HEADER_BOTTOM)
        header_layout.setSpacing(HEADER_GAP)

        self.logo_label = QLabel()
        self.logo_label.setObjectName("welcomeLogo")
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.logo_label.setStyleSheet("background: transparent;")
        self.logo_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        header_layout.addWidget(self.logo_label, 0, Qt.AlignHCenter)

        self.subtitle_label = QLabel()
        self.subtitle_label.setFont(_font(12))
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tc = theme_colors()
        self.subtitle_label.setStyleSheet(
            f"color: {tc['text_secondary']}; background: transparent;"
        )
        header_layout.addWidget(self.subtitle_label)
        root.addWidget(header)

        divider_host = _CenteredColumn()
        divider_layout = QVBoxLayout(divider_host.column)
        divider_layout.setContentsMargins(0, 0, 0, 0)
        divider_layout.setSpacing(0)
        divider = QFrame()
        divider.setObjectName("welcomeDivider")
        divider.setFixedHeight(1)
        divider.setFrameShape(QFrame.NoFrame)
        divider.setStyleSheet(
            f"background-color: {tc['border']}; border: none; max-height: 1px;"
        )
        divider_layout.addWidget(divider)
        divider_host.setFixedHeight(1)
        root.addWidget(divider_host)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self._scroll.viewport().setAutoFillBackground(False)
        self._scroll.viewport().setStyleSheet("background: transparent;")

        body_host = _CenteredColumn()
        body = QVBoxLayout(body_host.column)
        body.setContentsMargins(0, SECTION_GAP, 0, ROW_GAP)
        body.setSpacing(SECTION_GAP)

        start_label = self._make_heading("welcome.section_start", 11, "text_secondary")
        import_action = self._add_action(
            "welcome.import_sheet_title",
            "welcome.import_sheet_desc",
            "solid",
            self.import_data_clicked,
        )
        open_action = self._add_action(
            "welcome.open_project_title",
            "welcome.open_project_desc",
            "outline",
            self.open_project_clicked,
        )
        primary_row = QWidget()
        primary_row.setAutoFillBackground(False)
        primary_layout = QHBoxLayout(primary_row)
        primary_layout.setContentsMargins(0, 0, 0, 0)
        primary_layout.setSpacing(TILE_GAP)
        primary_layout.addWidget(import_action, 1)
        primary_layout.addWidget(open_action, 1)

        start_box = QWidget()
        start_box.setAutoFillBackground(False)
        start_layout = QVBoxLayout(start_box)
        start_layout.setContentsMargins(0, 0, 0, 0)
        start_layout.setSpacing(ROW_GAP)
        start_layout.addWidget(start_label)
        start_layout.addWidget(primary_row)
        body.addWidget(start_box)

        secondary_specs = (
            ("welcome.import_ie_title", "welcome.import_ie_desc", self.import_ie_clicked),
            ("welcome.new_analysis_title", "welcome.new_analysis_desc", self.new_analysis_clicked),
            ("welcome.diagnose_title", "welcome.diagnose_desc", self.diagnose_clicked),
            ("welcome.case_title", "welcome.case_desc", self.case_center_clicked),
        )
        grid_host = QWidget()
        grid_host.setAutoFillBackground(False)
        grid = QGridLayout(grid_host)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(TILE_GAP)
        grid.setVerticalSpacing(TILE_GAP)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        for index, (title_key, desc_key, signal) in enumerate(secondary_specs):
            action = self._add_action(title_key, desc_key, "secondary", signal)
            grid.addWidget(action, index // 2, index % 2)
        body.addWidget(grid_host)

        recent_label = self._make_heading("welcome.section_recent", 13, "text_primary")
        self.recent_list = QWidget()
        self.recent_list.setAutoFillBackground(False)
        self.recent_layout = QVBoxLayout(self.recent_list)
        self.recent_layout.setContentsMargins(0, 0, 0, 0)
        self.recent_layout.setSpacing(ROW_GAP)

        recent_box = QWidget()
        recent_box.setAutoFillBackground(False)
        recent_box_layout = QVBoxLayout(recent_box)
        recent_box_layout.setContentsMargins(0, 0, 0, 0)
        recent_box_layout.setSpacing(ROW_GAP)
        recent_box_layout.addWidget(recent_label)
        recent_box_layout.addWidget(self.recent_list)
        body.addWidget(recent_box)
        # 视口更高时把空白留在列表下面，避免把操作块拉高。
        body.addStretch(1)

        self._scroll.setWidget(body_host)
        root.addWidget(self._scroll, 1)

    def _clear_recent(self):
        while self.recent_layout.count():
            item = self.recent_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def _rebuild_recent_section(self):
        if not hasattr(self, "recent_layout"):
            return
        self._clear_recent()
        tc = theme_colors()
        items = self._recent_items[:RECENT_LIMIT]
        if not items:
            empty = QLabel(i18n.tr("welcome.recent_empty"))
            empty.setObjectName("welcomeRecentEmpty")
            empty.setFont(_font(12))
            empty.setAlignment(Qt.AlignCenter)
            empty.setWordWrap(True)
            empty.setMinimumHeight(EMPTY_MIN_HEIGHT)
            empty.setStyleSheet(
                f"color: {tc['text_muted']}; background-color: {tc['bg_card']};"
                f"border: 1px dashed {tc['border']}; border-radius: {ACTION_RADIUS}px;"
                "padding: 20px;"
            )
            self.recent_layout.addWidget(empty)
            return

        for item in items:
            name, path = item[0], item[1]
            row = _RecentRow(str(name), str(path))
            row.activated.connect(lambda p=str(path): self._open_recent(p))
            self.recent_layout.addWidget(row)

    def _open_recent(self, path: str):
        parent = self.window()
        loader = getattr(parent, "_load_project_by_path", None)
        if callable(loader):
            loader(path)

    def paintEvent(self, event):
        tc = theme_colors()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(tc["bg_body"]))

        center = self._wordmark_center()
        glow = QRadialGradient(center, float(GLOW_RADIUS))
        # 光晕只用很淡的白，避免欢迎页被字标蓝铺开。
        core = QColor("#FFFFFF")
        core.setAlpha(GLOW_ALPHA)
        edge = QColor("#FFFFFF")
        edge.setAlpha(0)
        glow.setColorAt(0.0, core)
        glow.setColorAt(1.0, edge)
        painter.fillRect(self.rect(), glow)
        painter.end()
        super().paintEvent(event)

    def refresh_texts(self):
        self._apply_logo()
        self.subtitle_label.setText(APP_FULL_NAME)
        for label, key in self._text_labels:
            label.setText(i18n.tr(key))
        for action in self._actions:
            action.refresh_texts()
        self._rebuild_recent_section()

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, "logo_label"):
            self._apply_logo()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.DevicePixelRatioChange and hasattr(self, "logo_label"):
            self._apply_logo()
