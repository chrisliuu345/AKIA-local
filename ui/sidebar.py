"""
左侧导航栏 — 分类分组 + 可折叠动画 + 支持后台功能按钮
"""

from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QScrollArea, QFrame,
)
from PySide6.QtCore import Signal, Qt, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
from PySide6.QtGui import QFont
from core.i18n import i18n
from config.settings import APP_VERSION, tab_allowed
from ui.theme import colors as theme_colors
from ui.widgets.elided_label import ElidedLabel
from ui.font_config import get_ui_font, get_mono_font


HOME_ITEM = (0, "sidebar.home")

CATEGORIES = [
    {
        "key": "sidebar.quality_tools",
        "items": [
            (1, "sidebar.spc"),
            (2, "sidebar.capability"),
            (3, "sidebar.msa"),
            (4, "sidebar.hypothesis"),
            (5, "sidebar.doe"),
            (6, "sidebar.regression"),
        ],
    },
    {
        "key": "sidebar.ie_tools",
        "items": [
            (7, "sidebar.time_study"),
            (8, "sidebar.work_sampling"),
            (9, "sidebar.line_balance"),
            (10, "sidebar.oee"),
            (11, "sidebar.vsm"),
            (21, "sidebar.worker_machine"),
            (22, "sidebar.std_work_combo"),
            (29, "sidebar.smed"),
            (31, "sidebar.tpm"),
        ],
    },
    {
        "key": "sidebar.sheet_tools",
        "items": [
            (23, "sidebar.sheet_merge"),
            (24, "sidebar.sheet_split"),
            (25, "sidebar.layered_form"),
        ],
    },
    {
        "key": "sidebar.chart_tools",
        "items": [
            (12, "sidebar.chart_tab"),
            (18, "sidebar.cap_comparison"),
            (19, "sidebar.trend"),
            (20, "sidebar.summary_panel"),
        ],
    },
    {
        "key": "sidebar.sampling_tools",
        "items": [
            (26, "sidebar.sampling"),
        ],
    },
    {
        "key": "sidebar.report",
        "items": [
            (27, "sidebar.dashboard"),
        ],
    },
    {
        "key": "sidebar.data_tools",
        "items": [
            (28, "sidebar.data_tools_tab"),
        ],
    },
    {
        "key": "sidebar.monitoring",
        "items": [
            (33, "sidebar.monitor"),
            (34, "sidebar.multi_plant"),
            (35, "sidebar.device"),
        ],
    },
    {
        "key": "sidebar.plugins",
        "items": [],
    },
    {
        "key": "sidebar.engineering_tools",
        "items": [
            (13, "sidebar.reliability"),
            (14, "sidebar.fishbone"),
            (15, "sidebar.pareto"),
            (16, "sidebar.fmea"),
            (17, "sidebar.control_plan"),
            (30, "sidebar.8d"),
            (32, "sidebar.ppap"),
        ],
    },
]

NAV_ITEMS = [HOME_ITEM]
for cat in CATEGORIES:
    NAV_ITEMS.extend(cat["items"])

MAX_HISTORY = 12
DIAGNOSIS_KEY = "sidebar.diagnose"


class CategoryGroup(QWidget):
    """可折叠分类组 — 带动画的展开/收起"""

    def __init__(self, title_key: str, items: list,
                 parent_sidebar=None, initially_expanded: bool = True):
        super().__init__(parent_sidebar)
        self.title_key = title_key
        self.items = items
        self.parent_sidebar = parent_sidebar
        self._expanded = initially_expanded
        self.sub_buttons: dict = {}
        self.sub_widgets: list = []
        self._anim = None
        self._full_container_height = 0
        self._header_height = 0
        self._full_height = 0

        self._setup_ui()

    def _setup_ui(self):
        tc = theme_colors(self)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self.header_btn = QPushButton()
        self.header_btn.setFixedHeight(40)
        self.header_btn.setCursor(Qt.PointingHandCursor)
        self.header_btn.setFlat(True)
        self.header_btn.clicked.connect(self.toggle)

        header_layout = QHBoxLayout(self.header_btn)
        header_layout.setContentsMargins(8, 0, 8, 0)
        header_layout.setSpacing(4)

        self._arrow_label = QLabel()
        self._arrow_label.setFixedWidth(18)
        self._arrow_label.setAlignment(Qt.AlignCenter)
        self._arrow_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        header_layout.addWidget(self._arrow_label)

        self._title_label = QLabel(i18n.tr(self.title_key))
        self._title_label.setFont(QFont(get_ui_font(), 12, QFont.Bold))
        self._title_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        header_layout.addWidget(self._title_label, 1)

        self._update_header_text()
        self._layout.addWidget(self.header_btn)

        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(12, 2, 0, 4)
        self.container_layout.setSpacing(1)

        if self.items:
            for idx, key in self.items:
                if not tab_allowed(idx):
                    continue
                btn = QPushButton()
                btn.setFont(QFont(get_ui_font(), 10))
                btn.setFixedHeight(32)
                btn.setCursor(Qt.PointingHandCursor)
                btn.setCheckable(True)
                btn.setText(i18n.tr(key))
                btn.setProperty("i18n_key", key)
                btn.clicked.connect(lambda checked, i=idx: self._on_sub_click(i))
                self.sub_buttons[idx] = btn
                self.sub_widgets.append(btn)
                self.container_layout.addWidget(btn)

        if not self.items:
            placeholder = QLabel(i18n.tr("sidebar.coming_soon"))
            placeholder.setFont(QFont(get_ui_font(), 9))
            placeholder.setStyleSheet(f"color: {tc['text_dim']}; padding: 4px 8px;")
            placeholder.setAlignment(Qt.AlignLeft)
            self.sub_widgets.append(placeholder)
            self.container_layout.addWidget(placeholder)
            self._expanded = False

        self.container_layout.addStretch()
        self._layout.addWidget(self.container)

        self._collapsed_height = 0
        self._expanded_height = self.container.sizeHint().height()
        self._header_height = 40

        if not self._expanded:
            self.container.setMaximumHeight(0)
            self.container.hide()
            self.setMaximumHeight(self._header_height)
        else:
            self.container.setMaximumHeight(self._expanded_height)
            self.setMaximumHeight(self._header_height + self._expanded_height)

    def _update_header_text(self):
        """更新箭头方向 — 箭头 QLabel 固定宽度，标题文字不会随箭头变化而跳动"""
        self._arrow_label.setText("▼" if self._expanded else "▶")

    def _on_sub_click(self, index: int):
        if self.parent_sidebar:
            self.parent_sidebar.navigation_changed.emit(index)

    def toggle(self):
        self._expanded = not self._expanded
        self._update_header_text()

        if self._anim and self._anim.state() == QParallelAnimationGroup.Running:
            self._anim.stop()

        if self._expanded:
            self.container.show()
            self_target = self._header_height + self._expanded_height
            container_target = self._expanded_height
        else:
            self_target = self._header_height
            container_target = 0

        self_anim = QPropertyAnimation(self, b"maximumHeight")
        self_anim.setDuration(200)
        self_anim.setStartValue(self.maximumHeight())
        self_anim.setEndValue(self_target)
        self_anim.setEasingCurve(QEasingCurve.InOutCubic)

        container_anim = QPropertyAnimation(self.container, b"maximumHeight")
        container_anim.setDuration(200)
        container_anim.setStartValue(self.container.maximumHeight())
        container_anim.setEndValue(container_target)
        container_anim.setEasingCurve(QEasingCurve.InOutCubic)

        self._anim = QParallelAnimationGroup()
        self._anim.addAnimation(self_anim)
        self._anim.addAnimation(container_anim)
        self._anim.finished.connect(self._on_anim_finished)
        self._anim.start()

    def _on_anim_finished(self):
        if not self._expanded:
            self.container.hide()

    def _recalc_height(self):
        """W72: 重新计算展开高度，确保动态内容变化后高度正确"""
        self._expanded_height = self.container.sizeHint().height()
        if self._expanded:
            self.container.setMaximumHeight(self._expanded_height)
            self.setMaximumHeight(self._header_height + self._expanded_height)

    def set_active(self, index: int):
        tc = theme_colors(self)
        accent_bright = tc["accent_bright"]
        hover_bg = tc["bg_hover"]
        active_bg = tc["bg_active"]

        for idx, btn in self.sub_buttons.items():
            is_active = (idx == index)
            btn.setChecked(is_active)
            if is_active:
                btn.setStyleSheet(
                    f"QPushButton {{"
                    f"background-color: {active_bg}; color: {accent_bright};"
                    f"border: none; border-left: 2px solid {accent_bright};"
                    f"border-radius: 4px; padding: 4px 10px; text-align: left;"
                    f"}}"
                )
            else:
                btn.setStyleSheet(
                    f"QPushButton {{"
                    f"background-color: transparent; color: {tc['text_primary']};"
                    f"border: none; border-left: 2px solid transparent;"
                    f"border-radius: 4px; padding: 4px 10px; text-align: left;"
                    f"}}"
                    f"QPushButton:hover {{"
                    f"background-color: {hover_bg};"
                    f"border-left: 2px solid {tc['accent']};"
                    f"}}"
                )

    def refresh_styles(self):
        tc = theme_colors(self)
        self._update_header_text()
        self._title_label.setText(i18n.tr(self.title_key))
        self._arrow_label.setStyleSheet(
            f"color: {tc['text_secondary']}; background: transparent; font-size: 11px;")
        self._title_label.setStyleSheet(
            f"color: {tc['text_secondary']}; background: transparent;")

    def refresh_sub_texts(self):
        for idx, key in self.items:
            if idx in self.sub_buttons:
                self.sub_buttons[idx].setText(i18n.tr(key))
        self._recalc_height()


class Sidebar(QWidget):
    navigation_changed = Signal(int)
    diagnose_clicked = Signal()
    llm_clicked = Signal()
    collapse_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.categories: list[CategoryGroup] = []
        self.nav_buttons: dict = {}
        self.action_buttons = []
        self.active_index = 0
        self.history_widgets = []
        self.history_data = []
        self._setup_ui()

    def _setup_ui(self):
        tc = theme_colors(self)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 18, 12, 14)
        layout.setSpacing(6)

        self.brand_label = QLabel(i18n.tr("sidebar.brand"))
        self.brand_label.setFont(QFont(get_ui_font(), 14))
        self.brand_label.setAlignment(Qt.AlignCenter)
        self.brand_label.setStyleSheet(f"color: {tc['text_primary']};")
        layout.addWidget(self.brand_label)

        ver = QLabel(f"v{APP_VERSION}")
        ver.setFont(QFont(get_ui_font(), 9))
        ver.setAlignment(Qt.AlignCenter)
        ver.setStyleSheet(f"color: {tc['text_secondary']};")
        layout.addWidget(ver)

        layout.addSpacing(8)

        self.home_btn = QPushButton()
        self.home_btn.setFont(QFont(get_ui_font(), 12))
        self.home_btn.setMinimumHeight(46)
        self.home_btn.setCursor(Qt.PointingHandCursor)
        self.home_btn.setCheckable(True)
        self.home_btn.setText(f"    {i18n.tr('sidebar.home')}")
        self.home_btn.setProperty("i18n_key", "sidebar.home")
        self.home_btn.clicked.connect(lambda: self.navigation_changed.emit(0))
        self.nav_buttons[0] = self.home_btn
        layout.addWidget(self.home_btn)

        first = True
        for cat_def in CATEGORIES:
            group = CategoryGroup(
                title_key=cat_def["key"],
                items=cat_def["items"],
                parent_sidebar=self,
                initially_expanded=False,
            )
            self.categories.append(group)
            layout.addWidget(group)

            for idx, btn in group.sub_buttons.items():
                self.nav_buttons[idx] = btn

            if not first:
                layout.addSpacing(0)
            first = False

        layout.addSpacing(6)

        self.diagnose_btn = QPushButton()
        self.diagnose_btn.setFont(QFont(get_ui_font(), 11, QFont.Bold))
        self.diagnose_btn.setMinimumHeight(40)
        self.diagnose_btn.setCursor(Qt.PointingHandCursor)
        self.diagnose_btn.clicked.connect(self.diagnose_clicked.emit)
        self.diagnose_btn.setText("  " + i18n.tr(DIAGNOSIS_KEY))
        self.diagnose_btn.setToolTip(i18n.tr(DIAGNOSIS_KEY))
        self.action_buttons.append(self.diagnose_btn)
        layout.addWidget(self.diagnose_btn)

        layout.addSpacing(4)

        self.llm_btn = QPushButton()
        self.llm_btn.setFont(QFont(get_ui_font(), 11, QFont.Bold))
        self.llm_btn.setMinimumHeight(40)
        self.llm_btn.setCursor(Qt.PointingHandCursor)
        self.llm_btn.clicked.connect(self.llm_clicked.emit)
        self.llm_btn.setText("  " + i18n.tr("sidebar.llm"))
        self.llm_btn.setToolTip(i18n.tr("sidebar.llm"))
        self.action_buttons.append(self.llm_btn)
        layout.addWidget(self.llm_btn)

        layout.addSpacing(8)

        history_header = QHBoxLayout()
        hl = QLabel(i18n.tr("sidebar.history"))
        hl.setFont(QFont(get_ui_font(), 10, QFont.Bold))
        hl.setStyleSheet(f"color: {tc['text_secondary']}; padding: 2px 4px;")
        history_header.addWidget(hl)
        history_header.addStretch()
        self.clear_hist_btn = QPushButton(i18n.tr("sidebar.history_clear"))
        self.clear_hist_btn.setFont(QFont(get_ui_font(), 8))
        self.clear_hist_btn.setFixedSize(40, 20)
        self.clear_hist_btn.setCursor(Qt.PointingHandCursor)
        self.clear_hist_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {tc['text_dim']}; "
            f"border: 1px solid {tc['border_light']}; "
            "border-radius: 3px; padding: 0; } "
            f"QPushButton:hover {{ color: {tc['text_primary']}; border-color: {tc['border']}; }}"
        )
        self.clear_hist_btn.clicked.connect(self.clear_history)
        history_header.addWidget(self.clear_hist_btn)
        layout.addLayout(history_header)

        self.history_list = QWidget()
        self.history_layout = QVBoxLayout(self.history_list)
        self.history_layout.setContentsMargins(0, 0, 0, 0)
        self.history_layout.setSpacing(0)
        layout.addWidget(self.history_list)

        layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.collapse_btn = QPushButton("  " + i18n.tr("sidebar.collapse"))
        self.collapse_btn.setFont(QFont(get_ui_font(), 10))
        self.collapse_btn.setMinimumHeight(32)
        self.collapse_btn.setCursor(Qt.PointingHandCursor)
        self.collapse_btn.setToolTip(i18n.tr("sidebar.collapse") + " (Ctrl+B)")
        self.collapse_btn.clicked.connect(self.collapse_requested.emit)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(scroll, 1)
        outer.addWidget(self.collapse_btn)

        self.set_active(0)
        self._refresh_styles()

    def set_active(self, index: int):
        self.active_index = index
        tc = theme_colors(self)
        accent_bright = tc["accent_bright"]
        hover_bg = tc["bg_hover"]
        active_bg = tc["bg_active"]

        is_home = (index == 0)
        self.home_btn.setChecked(is_home)
        if is_home:
            self.home_btn.setStyleSheet(
                f"QPushButton {{"
                f"background-color: {active_bg}; color: {accent_bright};"
                f"border: none; border-left: 2px solid {accent_bright};"
                f"border-radius: 6px; padding: 10px 12px; text-align: left;"
                f"}}"
            )
        else:
            self.home_btn.setStyleSheet(
                f"QPushButton {{"
                f"background-color: transparent; color: {tc['text_primary']};"
                f"border: none; border-left: 2px solid transparent;"
                f"border-radius: 6px; padding: 10px 12px; text-align: left;"
                f"}}"
                f"QPushButton:hover {{"
                f"background-color: {hover_bg}; border-left: 2px solid {tc['accent']};"
                f"}}"
            )

        for group in self.categories:
            group.set_active(index)

    def add_history(self, tab_index: int, analysis_type: str, key_result: str = ""):
        entry = {
            "tab_index": tab_index,
            "type": analysis_type,
            "result": key_result,
            "time": datetime.now().strftime("%H:%M"),
        }
        self.history_data.insert(0, entry)
        if len(self.history_data) > MAX_HISTORY:
            self.history_data.pop()
        self._rebuild_history()

    def clear_history(self):
        self.history_data.clear()
        self._rebuild_history()

    def add_plugin_entry(self, index: int, name: str):
        """动态添加插件项到侧栏「第三方插件」分类"""
        for group in self.categories:
            if group.title_key == "sidebar.plugins":
                btn = QPushButton(name)
                btn.setFont(QFont(get_ui_font(), 10))
                btn.setFixedHeight(32)
                btn.setCursor(Qt.PointingHandCursor)
                btn.setCheckable(True)
                btn.clicked.connect(lambda checked, i=index: self.navigation_changed.emit(i))
                btn.setProperty("plugin_name", name)
                group.sub_buttons[index] = btn
                group.sub_widgets.append(btn)
                group.container_layout.insertWidget(group.container_layout.count() - 1, btn)
                self.nav_buttons[index] = btn
                group._recalc_height()
                break

    def _rebuild_history(self):
        for w in self.history_widgets:
            w.setParent(None)
        self.history_widgets.clear()

        tc = theme_colors(self)
        max_row_width = 210 - 24 - 10

        for entry in self.history_data:
            row = QWidget()
            row.setMaximumWidth(max_row_width)
            row.setCursor(Qt.PointingHandCursor)
            row.setMinimumHeight(32)
            row.setToolTip(f"{entry['type']} — {entry['result']}")

            row.mousePressEvent = lambda e, ti=entry["tab_index"]: self.navigation_changed.emit(ti)

            rlayout = QHBoxLayout(row)
            rlayout.setContentsMargins(6, 2, 4, 2)
            rlayout.setSpacing(4)

            time_lbl = QLabel(entry["time"])
            time_lbl.setFont(QFont(get_mono_font(), 8))
            time_lbl.setFixedWidth(36)
            time_lbl.setStyleSheet(f"color: {tc['text_muted']};")
            rlayout.addWidget(time_lbl)

            type_lbl = ElidedLabel(entry["type"])
            type_lbl.setFont(QFont(get_ui_font(), 9))
            type_lbl.setStyleSheet(f"color: {tc['text_primary']};")
            rlayout.addWidget(type_lbl, 1)

            if entry["result"]:
                res_lbl = QLabel(entry["result"][:8])
                res_lbl.setFont(QFont(get_ui_font(), 8))
                res_lbl.setFixedWidth(50)
                res_lbl.setAlignment(Qt.AlignCenter)
                is_positive = "A" in entry["result"] or "可" in entry["result"]
                res_color = tc["accent"] if is_positive else tc["text_primary"]
                res_bg = tc["bg_active"]
                res_lbl.setStyleSheet(f"color: {res_color}; background: {res_bg}; "
                                      f"border-radius: 4px; padding: 1px 5px;")
                rlayout.addWidget(res_lbl)

            self.history_layout.addWidget(row)
            self.history_widgets.append(row)

        self.history_layout.addStretch()
        self.history_list.update()

    def _refresh_styles(self):
        tc = theme_colors(self)
        accent = tc["accent"]
        tc["accent_bright"]
        text_color = tc["text_primary"]

        self.setStyleSheet(f"background-color: {tc['bg_body']};")

        hover_bg = tc["bg_hover"]
        tc["bg_active"]

        for group in self.categories:
            group.header_btn.setStyleSheet(
                f"QPushButton {{"
                f"background-color: transparent;"
                f"border: none; border-radius: 4px;"
                f"text-align: left;"
                f"}}"
                f"QPushButton:hover {{"
                f"background-color: {hover_bg};"
                f"}}"
            )
            group.refresh_styles()

        for btn in self.action_buttons:
            btn.setStyleSheet(
                f"QPushButton {{"
                f"background-color: transparent; color: {text_color};"
                f"border: none; border-radius: 6px; padding: 8px 12px;"
                f"text-align: left;"
                f"}}"
                f"QPushButton:hover {{"
                f"background-color: {hover_bg};"
                f"}}"
            )

        self.diagnose_btn.setStyleSheet(
            f"QPushButton {{"
            f"background-color: transparent; color: {accent}; font-weight: bold;"
            f"border: 1px solid {accent}; border-radius: 6px; padding: 8px 12px;"
            f"text-align: left;"
            f"}}"
            f"QPushButton:hover {{"
            f"background-color: {hover_bg};"
            f"}}"
        )

        self.llm_btn.setStyleSheet(
            f"QPushButton {{"
            f"background-color: transparent; color: {tc['text_primary']}; "
            f"font-weight: bold;"
            f"border: 1px solid {tc['border_light']}; border-radius: 6px; padding: 8px 12px;"
            f"text-align: left;"
            f"}}"
            f"QPushButton:hover {{"
            f"background-color: {hover_bg};"
            f"}}"
        )

        self.collapse_btn.setStyleSheet(
            f"QPushButton {{"
            f"background-color: transparent; color: {tc['text_muted']};"
            f"border: none; border-top: 1px solid {tc['border_light']};"
            f"border-radius: 0; padding: 6px 12px;"
            f"}}"
            f"QPushButton:hover {{"
            f"color: {tc['text_primary']}; background-color: {hover_bg};"
            f"}}"
        )

    def refresh_texts(self):
        self.brand_label.setText(i18n.tr("sidebar.brand"))

        self.home_btn.setText(f"    {i18n.tr('sidebar.home')}")

        for group in self.categories:
            group.refresh_styles()
            group.refresh_sub_texts()

        self.diagnose_btn.setText("  " + i18n.tr(DIAGNOSIS_KEY))
        self.llm_btn.setText("  " + i18n.tr("sidebar.llm"))
        self.collapse_btn.setText("  " + i18n.tr("sidebar.collapse"))
        self._refresh_styles()
