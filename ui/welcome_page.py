"""欢迎/首页 — 暗色渐变背景 + 卡片式快速入口 + 最近项目"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QSizePolicy,
)
from PySide6.QtCore import Signal, Qt, QPointF
from PySide6.QtGui import (
    QFont, QColor, QPainter, QLinearGradient, QRadialGradient, QPen,
)
from ui.theme import colors as theme_colors

from core.i18n import i18n
from config.settings import APP_VERSION


class WelcomePage(QWidget):
    import_data_clicked = Signal()
    import_template_clicked = Signal()
    diagnose_clicked = Signal()
    new_analysis_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._recent_items: list = []  # [(name, path), ...]
        self._setup_ui()

    def set_recent_projects(self, items: list):
        self._recent_items = items or []
        self._rebuild_recent_section()

    def _setup_ui(self):
        tc = theme_colors()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setStyleSheet("QFrame { background: transparent; padding: 42px 60px 18px 60px; }")
        header_layout = QVBoxLayout(header)
        header_layout.setSpacing(4)

        title_font = QFont("Microsoft YaHei", 36, QFont.Bold)
        title_font.setLetterSpacing(QFont.AbsoluteSpacing, 3)
        self.title_label = QLabel(i18n.tr("welcome.title"))
        self.title_label.setFont(title_font)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("color: #ffffff; background: transparent;")
        header_layout.addWidget(self.title_label)

        self.subtitle_label = QLabel("AI 工业质量 + IE 分析平台")
        self.subtitle_label.setFont(QFont("Microsoft YaHei", 12))
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        self.subtitle_label.setStyleSheet(
            f"color: {tc['text_secondary']}; background: transparent;")
        header_layout.addWidget(self.subtitle_label)

        layout.addWidget(header)

        divider = QFrame()
        divider.setFixedHeight(2)
        divider.setStyleSheet(
            "QFrame { border: none; background: qlineargradient("
            "x1:0, y1:0, x2:1, y2:0, "
            "stop:0 transparent, stop:0.3 #4da6ff, stop:0.7 #1b5faa, stop:1 transparent); }"
        )
        layout.addWidget(divider)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        scroll.viewport().setAutoFillBackground(False)

        body = QWidget()
        body.setStyleSheet("background: transparent;")
        body.setAutoFillBackground(False)
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(50, 28, 50, 20)
        body_layout.setSpacing(16)

        # ── 快速入口卡片 ──
        cards_widget = QWidget()
        cards_widget.setStyleSheet("background: transparent;")
        cards_layout = QHBoxLayout(cards_widget)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(16)
        cards_layout.addStretch()

        card_defs = [
            ("", i18n.tr("welcome.import_btn"), "导入 Excel / CSV 数据文件", self.import_data_clicked),
            ("", "最近项目", "打开最近使用的 .qap 项目", None),
            ("", "新建分析", "直接跳转到分析模块", self.new_analysis_clicked),
            ("", i18n.tr("sidebar.diagnose"), "一键智能诊断数据质量", self.diagnose_clicked),
        ]

        for _, title, desc, signal in card_defs:
            card = self._make_card(title, desc, signal)
            cards_layout.addWidget(card)

        cards_layout.addStretch()
        body_layout.addWidget(cards_widget)

        # ── 最近项目 ──
        recent_header = QLabel("最近项目")
        recent_header.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        recent_header.setStyleSheet(
            f"color: {tc['text_secondary']}; background: transparent; padding: 0 4px;")
        body_layout.addWidget(recent_header)

        self.recent_list = QWidget()
        self.recent_list.setStyleSheet("background: transparent;")
        self.recent_layout = QVBoxLayout(self.recent_list)
        self.recent_layout.setContentsMargins(0, 0, 0, 0)
        self.recent_layout.setSpacing(4)
        body_layout.addWidget(self.recent_list)

        self._no_recent = QLabel("暂无最近项目 — 导入数据或打开项目开始分析")
        self._no_recent.setFont(QFont("Microsoft YaHei", 10))
        self._no_recent.setStyleSheet(
            f"color: {tc['text_muted']}; background: {tc['bg_card']}; "
            f"border: 1px dashed {tc['border']}; border-radius: 8px; padding: 18px;")
        self._no_recent.setAlignment(Qt.AlignCenter)
        self.recent_layout.addWidget(self._no_recent)

        body_layout.addStretch()

        self.version_label = QLabel(f"v{APP_VERSION}")
        self.version_label.setFont(QFont("Microsoft YaHei", 10))
        self.version_label.setAlignment(Qt.AlignCenter)
        self.version_label.setStyleSheet(
            f"color: {tc['text_secondary']}; background: transparent; padding-bottom: 8px;")
        body_layout.addWidget(self.version_label)

        scroll.setWidget(body)
        layout.addWidget(scroll, 1)

    def _make_card(self, title: str, desc: str, signal):
        tc = theme_colors()
        card = QFrame()
        card.setCursor(Qt.PointingHandCursor)
        card.setMinimumWidth(170)
        card.setMaximumWidth(200)
        card.setMinimumHeight(100)
        card.setStyleSheet(
            f"QFrame {{"
            f"background-color: {tc['bg_card']};"
            f"border: 1px solid {tc['border']}; border-radius: 10px;"
            f"}}"
            f"QFrame:hover {{"
            f"border-color: {tc['accent_bright']};"
            f"background-color: {tc['bg_hover']};"
            f"}}"
        )

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 16, 14, 14)
        card_layout.setSpacing(4)

        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setStyleSheet(
            f"color: {tc['text_primary']}; background: transparent; border: none;")
        card_layout.addWidget(title_lbl)

        desc_lbl = QLabel(desc)
        desc_lbl.setFont(QFont("Microsoft YaHei", 8))
        desc_lbl.setAlignment(Qt.AlignCenter)
        desc_lbl.setStyleSheet(
            f"color: {tc['text_muted']}; background: transparent; border: none;")
        desc_lbl.setWordWrap(True)
        card_layout.addWidget(desc_lbl)

        if signal is not None:
            def handler(e, s=signal):
                s.emit()
            card.mousePressEvent = handler

        return card

    def _rebuild_recent_section(self):
        for i in reversed(range(self.recent_layout.count())):
            w = self.recent_layout.itemAt(i).widget()
            if w:
                w.setParent(None)

        tc = theme_colors()

        if not self._recent_items:
            self._no_recent = QLabel("暂无最近项目 — 导入数据或打开项目开始分析")
            self._no_recent.setFont(QFont("Microsoft YaHei", 10))
            self._no_recent.setStyleSheet(
                f"color: {tc['text_muted']}; background: {tc['bg_card']}; "
                f"border: 1px dashed {tc['border']}; border-radius: 8px; padding: 18px;")
            self._no_recent.setAlignment(Qt.AlignCenter)
            self.recent_layout.addWidget(self._no_recent)
        else:
            for name, path in self._recent_items[:5]:
                row = QFrame()
                row.setCursor(Qt.PointingHandCursor)
                row.setStyleSheet(
                    f"QFrame {{ background: {tc['bg_card']}; "
                    f"border: 1px solid {tc['border']}; border-radius: 6px; "
                    f"padding: 8px 14px; }}"
                    f"QFrame:hover {{ border-color: {tc['accent_bright']}; }}"
                )
                row_layout = QHBoxLayout(row)
                row_layout.setContentsMargins(0, 0, 0, 0)

                name_lbl = QLabel(name)
                name_lbl.setFont(QFont("Microsoft YaHei", 10))
                name_lbl.setStyleSheet(
                    f"color: {tc['text_primary']}; background: transparent; border: none;")
                row_layout.addWidget(name_lbl, 1)

                path_lbl = QLabel(path)
                path_lbl.setFont(QFont("Microsoft YaHei", 8))
                path_lbl.setStyleSheet(
                    f"color: {tc['text_muted']}; background: transparent; border: none;")
                row_layout.addWidget(path_lbl)

                row._project_path = path
                row.mousePressEvent = lambda e, p=path: self._on_recent_click(p)
                self.recent_layout.addWidget(row)

            self.recent_layout.addStretch()

    def _on_recent_click(self, path: str):
        parent = self.window()
        if parent and hasattr(parent, '_load_project_from_path'):
            try:
                parent._load_project_from_path(path)
            except Exception:
                pass

    def paintEvent(self, event):
        tc = theme_colors()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        grad = QLinearGradient(0, 0, w, h)
        grad.setColorAt(0.0, QColor("#0d1526"))
        grad.setColorAt(1.0, QColor(tc["bg_body"]))
        painter.fillRect(self.rect(), grad)

        cx, cy = w / 2.0, min(h * 0.18, 180.0)
        glow = QRadialGradient(QPointF(cx, cy), max(w * 0.28, 220.0))
        glow_core = QColor(tc["accent"])
        glow_core.setAlpha(30)
        glow_edge = QColor(tc["accent"])
        glow_edge.setAlpha(0)
        glow.setColorAt(0.0, glow_core)
        glow.setColorAt(1.0, glow_edge)
        painter.fillRect(self.rect(), glow)

        ring_base = QColor(tc["accent_bright"])
        painter.setBrush(Qt.NoBrush)
        for radius, alpha in ((85, 20), (135, 11), (195, 6)):
            c = QColor(ring_base)
            c.setAlpha(alpha)
            painter.setPen(QPen(c, 1.5))
            painter.drawEllipse(QPointF(cx, cy), radius, radius)

        painter.end()
        super().paintEvent(event)

    def refresh_texts(self):
        self.title_label.setText(i18n.tr("welcome.title"))
