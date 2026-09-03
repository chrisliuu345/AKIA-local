"""QA-Tool 暗色主题 — 全局色彩、调色板、按钮样式、字体常量"""

from PySide6.QtGui import QPalette, QColor, QFont
from PySide6.QtWidgets import QApplication
from ui.font_config import get_ui_font

FONT_FAMILY = get_ui_font()

def _f(size: int, bold: bool = False) -> QFont:
    f = QFont(FONT_FAMILY, size)
    if bold: f.setBold(True)
    return f

FONT_8  = _f(8);   FONT_9  = _f(9);   FONT_10 = _f(10)
FONT_11 = _f(11);  FONT_12 = _f(12);  FONT_13 = _f(13)
FONT_14 = _f(14);  FONT_18 = _f(18);  FONT_20 = _f(20)
FONT_36 = _f(36);  FONT_40 = _f(40)
FONT_8B  = _f(8, True);   FONT_9B  = _f(9, True)
FONT_10B = _f(10, True);  FONT_11B = _f(11, True)
FONT_12B = _f(12, True);  FONT_14B = _f(14, True)
FONT_18B = _f(18, True);  FONT_36B = _f(36, True)


def is_dark_theme(widget=None) -> bool:
    return True


def apply_dark_palette():
    app = QApplication.instance()
    if not app:
        return
    p = QPalette()
    p.setColor(QPalette.Window, QColor(28, 28, 36))
    p.setColor(QPalette.WindowText, QColor(225, 226, 230))
    p.setColor(QPalette.Base, QColor(36, 36, 46))
    p.setColor(QPalette.AlternateBase, QColor(43, 43, 53))
    p.setColor(QPalette.Text, QColor(225, 226, 230))
    p.setColor(QPalette.Button, QColor(48, 48, 58))
    p.setColor(QPalette.ButtonText, QColor(225, 226, 230))
    p.setColor(QPalette.Highlight, QColor(27, 95, 170))
    p.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    p.setColor(QPalette.ToolTipBase, QColor(40, 40, 50))
    p.setColor(QPalette.ToolTipText, QColor(225, 226, 230))
    p.setColor(QPalette.Disabled, QPalette.WindowText, QColor(120, 120, 120))
    p.setColor(QPalette.Disabled, QPalette.Text, QColor(120, 120, 120))
    p.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(120, 120, 120))
    app.setPalette(p)


def colors(widget=None):
    return {
        "text_primary":   "#e1e2e6",
        "text_secondary": "#a0a3ae",
        "text_muted":     "#6e7080",
        "text_dim":       "#5a5c6a",
        "border":         "#3a3a48",
        "border_light":   "#2a2a36",
        "bg_card":        "#262632",
        "bg_body":        "#181822",
        "bg_header":      "#13131c",
        "bg_hover":       "#363648",
        "bg_active":      "#2a384a",
        "bg_table_header": "#2c2c38",
        "accent":         "#1b5faa",
        "accent_dark":    "#14508a",
        "accent_bright":  "#4da6ff",
    }


BUTTON_PRIMARY = (
    "QPushButton { background-color: #1b5faa; color: #fff; border: none;"
    "border-radius: 8px; padding: 12px 24px; font-weight: bold; }"
    "QPushButton:hover { background-color: #1f6fc0; }"
    "QPushButton:pressed { background-color: #124478; }"
)

BUTTON_SECONDARY = (
    "QPushButton { background-color: #1b5faa; color: #fff; border: none;"
    "border-radius: 6px; padding: 6px 16px; min-width: 90px; }"
    "QPushButton:hover { background-color: #1f6fc0; }"
    "QPushButton:pressed { background-color: #124478; }"
)

BUTTON_TOGGLE = (
    "QPushButton { background-color: transparent; color: #a0a3ae; border: 1px solid #3a3a48;"
    "border-radius: 6px; padding: 5px 14px; min-width: 64px; }"
    "QPushButton:hover { color: #e1e2e6; border-color: #4da6ff; }"
    "QPushButton:checked { background-color: #1b5faa; color: #fff; border-color: #1b5faa; }"
)

BUTTON_PRIMARY_STRETCH = (
    "QPushButton { background-color: #1b5faa; color: #fff; border: none;"
    "border-radius: 8px; padding: 12px 24px; font-weight: bold; }"
    "QPushButton:hover { background-color: #1f6fc0; }"
    "QPushButton:pressed { background-color: #124478; padding-top: 13px; padding-bottom: 11px; }"
)
