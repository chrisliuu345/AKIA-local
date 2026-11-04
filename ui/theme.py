"""AKIA 暗色主题 — 全局色彩、调色板、按钮样式、字体常量"""

from PySide6.QtGui import QPalette, QColor, QFont
from PySide6.QtWidgets import QApplication
from ui.font_config import get_ui_font

FONT_FAMILY = get_ui_font()


def _f(size: int, bold: bool = False) -> QFont:
    f = QFont(FONT_FAMILY, size)
    if bold:
        f.setBold(True)
    return f


FONT_8 = _f(8)
FONT_9 = _f(9)
FONT_10 = _f(10)
FONT_11 = _f(11)
FONT_12 = _f(12)
FONT_13 = _f(13)
FONT_14 = _f(14)
FONT_18 = _f(18)
FONT_20 = _f(20)
FONT_36 = _f(36)
FONT_40 = _f(40)
FONT_8B = _f(8, True)
FONT_9B = _f(9, True)
FONT_10B = _f(10, True)
FONT_11B = _f(11, True)
FONT_12B = _f(12, True)
FONT_14B = _f(14, True)
FONT_18B = _f(18, True)
FONT_36B = _f(36, True)


def is_dark_theme(widget=None) -> bool:
    return True


def apply_dark_palette():
    app = QApplication.instance()
    if not app:
        return
    p = QPalette()
    # 大面积保持近黑，只掺一点 #0100AD，避免把窗口铺成高饱和蓝。
    p.setColor(QPalette.Window, QColor("#0C0C1E"))
    p.setColor(QPalette.WindowText, QColor("#E4E4F2"))
    p.setColor(QPalette.Base, QColor("#101028"))
    p.setColor(QPalette.AlternateBase, QColor("#14142E"))
    p.setColor(QPalette.Text, QColor("#E4E4F2"))
    p.setColor(QPalette.Button, QColor("#161632"))
    p.setColor(QPalette.ButtonText, QColor("#E4E4F2"))
    p.setColor(QPalette.Highlight, QColor("#4648FF"))
    p.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    p.setColor(QPalette.ToolTipBase, QColor("#161632"))
    p.setColor(QPalette.ToolTipText, QColor("#E4E4F2"))
    p.setColor(QPalette.Disabled, QPalette.WindowText, QColor("#6E6E9A"))
    p.setColor(QPalette.Disabled, QPalette.Text, QColor("#6E6E9A"))
    p.setColor(QPalette.Disabled, QPalette.ButtonText, QColor("#6E6E9A"))
    app.setPalette(p)


def colors(widget=None):
    # 深色界面：文字和强调用较亮色阶；#4648FF 只留给主按钮和选中。
    return {
        "text_primary": "#E4E4F2",
        "text_secondary": "#C3C2FF",
        "text_muted": "#8A8AB8",
        "text_dim": "#6E6E9A",
        "border": "#3A3A66",
        "border_light": "#2A2A4E",
        "bg_card": "#161632",
        "bg_body": "#0C0C1E",
        "bg_header": "#07071A",
        "bg_hover": "#222248",
        "bg_active": "#242458",
        "bg_table_header": "#1C1C3A",
        "accent": "#4648FF",
        "accent_dark": "#1C1DEC",
        "accent_bright": "#9394FE",
    }


# 全局控件色与 colors() 同一套。焦点用 #1C1DEC，静止边框用压暗的长春花，避免满屏亮线。
APP_STYLESHEET = """
        QWidget { background-color: #0C0C1E; color: #E4E4F2; }
        QMainWindow { background-color: #0C0C1E; }
        QDialog { background-color: #0C0C1E; }
        QMenuBar { background-color: #07071A; color: #E4E4F2; }
        QMenuBar::item:selected { background-color: #4648FF; color: #ffffff; }
        QMenu { background-color: #161632; color: #E4E4F2; border: 1px solid #3A3A66; }
        QMenu::item:selected { background-color: #4648FF; color: #ffffff; }
        QStatusBar { background-color: #07071A; color: #C3C2FF; min-height: 24px; }
        QStatusBar::item { border: none; }
        QToolTip { background-color: #161632; color: #E4E4F2; border: 1px solid #9394FE; }
        QScrollBar:vertical { width: 8px; background: #0C0C1E; border: none; }
        QScrollBar::handle:vertical { background: #3A3A66; border-radius: 4px; min-height: 30px; }
        QScrollBar::handle:vertical:hover { background: #9394FE; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        QScrollBar:horizontal { height: 8px; background: #0C0C1E; border: none; }
        QScrollBar::handle:horizontal { background: #3A3A66; border-radius: 4px; min-width: 30px; }
        QScrollBar::handle:horizontal:hover { background: #9394FE; }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
        QTableWidget { alternate-background-color: #14142E; background-color: #101028; color: #E4E4F2; }
        QTableWidget::item:selected { background-color: #4648FF; color: #ffffff; }
        QTableWidget::item:hover { background: #222248; }
        QHeaderView::section { background-color: #1C1C3A; color: #C3C2FF; border: 1px solid #3A3A66; padding: 4px; }
        QComboBox { background-color: #161632; color: #E4E4F2; border: 1px solid #3A3A66; border-radius: 4px; padding: 4px 8px; }
        QComboBox:hover { border: 1px solid #9394FE; }
        QComboBox:focus { border: 1px solid #1C1DEC; }
        QComboBox QAbstractItemView { background-color: #161632; color: #E4E4F2; selection-background-color: #4648FF; selection-color: #ffffff; }
        QLineEdit { background-color: #101028; color: #E4E4F2; border: 1px solid #3A3A66; border-radius: 4px; padding: 4px 8px; }
        QLineEdit:focus { border: 1px solid #1C1DEC; }
        QSpinBox, QDoubleSpinBox { background-color: #101028; color: #E4E4F2; border: 1px solid #3A3A66; border-radius: 4px; padding: 2px 6px; }
        QSpinBox:focus, QDoubleSpinBox:focus { border: 1px solid #1C1DEC; }
        QGroupBox { color: #C3C2FF; border: 1px solid #3A3A66; border-radius: 6px; margin-top: 8px; padding-top: 16px; }
        QGroupBox::title { color: #C3C2FF; padding: 0 6px; subcontrol-origin: margin; }
        QTextEdit, QPlainTextEdit { background-color: #101028; color: #E4E4F2; border: 1px solid #3A3A66; }
        QListWidget { background-color: #101028; color: #E4E4F2; border: 1px solid #3A3A66; }
        QListWidget::item:hover { background-color: #222248; }
        QListWidget::item:selected { background-color: #4648FF; color: #ffffff; }
        QTreeWidget { background-color: #101028; color: #E4E4F2; border: 1px solid #3A3A66; }
        QTreeWidget::item:hover { background-color: #222248; }
        QTreeWidget::item:selected { background-color: #4648FF; color: #ffffff; }
        QCheckBox { color: #E4E4F2; }
        QRadioButton { color: #E4E4F2; }
        QLabel { color: #E4E4F2; background: transparent; }
        QSplitter::handle { background: #3A3A66; }
        QTabWidget::pane { background-color: #0C0C1E; border: 1px solid #3A3A66; }
        QTabBar::tab { background-color: #161632; color: #C3C2FF; border: 1px solid #3A3A66; padding: 6px 12px; }
        QTabBar::tab:selected { background-color: #0C0C1E; color: #E4E4F2; border-bottom: 2px solid #4648FF; }
        QProgressBar { background-color: #101028; border: none; border-radius: 3px; text-align: center; color: #E4E4F2; }
        QProgressBar::chunk { background-color: #4648FF; border-radius: 3px; }
    """


BUTTON_PRIMARY = (
    "QPushButton { background-color: #4648FF; color: #ffffff; border: none;"
    "border-radius: 8px; padding: 12px 24px; font-weight: bold; }"
    "QPushButton:hover { background-color: #5C5EFF; }"
    "QPushButton:pressed { background-color: #1C1DEC; }"
)

BUTTON_SECONDARY = (
    "QPushButton { background-color: #9394FE; color: #0100AD; border: none;"
    "border-radius: 6px; padding: 6px 16px; min-width: 90px; }"
    "QPushButton:hover { background-color: #C3C2FF; color: #0100AD; }"
    "QPushButton:pressed { background-color: #1C1DEC; color: #ffffff; }"
)

BUTTON_TOGGLE = (
    "QPushButton { background-color: transparent; color: #C3C2FF; border: 1px solid #9394FE;"
    "border-radius: 6px; padding: 5px 14px; min-width: 64px; }"
    "QPushButton:hover { color: #E4E4F2; border-color: #1C1DEC; }"
    "QPushButton:checked { background-color: #4648FF; color: #ffffff; border-color: #4648FF; }"
)

BUTTON_PRIMARY_STRETCH = (
    "QPushButton { background-color: #4648FF; color: #ffffff; border: none;"
    "border-radius: 8px; padding: 12px 24px; font-weight: bold; }"
    "QPushButton:hover { background-color: #5C5EFF; }"
    "QPushButton:pressed { background-color: #1C1DEC; padding-top: 13px; padding-bottom: 11px; }"
)
