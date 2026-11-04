"""AKIA 暗色主题 — 全局色彩、调色板、按钮样式、字体常量"""

import tempfile
from pathlib import Path

from PySide6.QtCore import QDir, Qt, QPointF
from PySide6.QtGui import QPalette, QColor, QFont, QImage, QPainter, QPen
from PySide6.QtWidgets import QApplication
from ui.font_config import get_ui_font

# 分析页配置区里上下叠放的按钮，行距本身几乎贴在一起。
CONFIG_BUTTON_GAP = 10

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
    # 灰阶贴近 Cursor：页面近黑，选中是安静的灰，不用蓝色铺底。
    p.setColor(QPalette.Window, QColor("#141414"))
    p.setColor(QPalette.WindowText, QColor("#EDEDED"))
    p.setColor(QPalette.Base, QColor("#101010"))
    p.setColor(QPalette.AlternateBase, QColor("#171717"))
    p.setColor(QPalette.Text, QColor("#EDEDED"))
    p.setColor(QPalette.Button, QColor("#1C1C1C"))
    p.setColor(QPalette.ButtonText, QColor("#EDEDED"))
    p.setColor(QPalette.Highlight, QColor("#2A2A2A"))
    p.setColor(QPalette.HighlightedText, QColor("#EDEDED"))
    p.setColor(QPalette.ToolTipBase, QColor("#1C1C1C"))
    p.setColor(QPalette.ToolTipText, QColor("#EDEDED"))
    p.setColor(QPalette.Disabled, QPalette.WindowText, QColor("#5C5C5C"))
    p.setColor(QPalette.Disabled, QPalette.Text, QColor("#5C5C5C"))
    p.setColor(QPalette.Disabled, QPalette.ButtonText, QColor("#5C5C5C"))
    # 立体框线用灰，避免 Fusion 默认把分隔线画成白条。
    p.setColor(QPalette.Light, QColor("#333333"))
    p.setColor(QPalette.Midlight, QColor("#2A2A2A"))
    p.setColor(QPalette.Mid, QColor("#2A2A2A"))
    p.setColor(QPalette.Dark, QColor("#1A1A1A"))
    p.setColor(QPalette.Shadow, QColor("#111111"))
    app.setPalette(p)


def colors(widget=None):
    # accent 是字标 “KIA” 的蓝，只给图表、链接和焦点。按钮和选中走灰阶。
    return {
        "text_primary": "#EDEDED",
        "text_secondary": "#A3A3A3",
        "text_muted": "#737373",
        "text_dim": "#5C5C5C",
        "border": "#333333",
        "border_light": "#2A2A2A",
        "bg_card": "#1C1C1C",
        "bg_body": "#141414",
        "bg_header": "#181818",
        "bg_hover": "#242424",
        "bg_active": "#2A2A2A",
        "bg_table_header": "#222222",
        "accent": "#4F73DC",
        "accent_dark": "#4F73DC",
        "accent_bright": "#8EABEA",
    }


# 焦点环用字标蓝，其余控件是灰阶。按钮圆角约 9px，字重不加粗，避免小号字糊成一块。
APP_STYLESHEET = """
        QWidget { background-color: #141414; color: #EDEDED; }
        QMainWindow { background-color: #141414; }
        QDialog { background-color: #141414; }
        QMenuBar { background-color: #181818; color: #EDEDED; }
        QMenuBar::item:selected { background-color: #2A2A2A; color: #EDEDED; border-radius: 6px; }
        QMenu { background-color: #1C1C1C; color: #EDEDED; border: 1px solid #333333; }
        QMenu::item:selected { background-color: #2A2A2A; color: #EDEDED; }
        QStatusBar { background-color: #181818; color: #A3A3A3; min-height: 24px; }
        QStatusBar::item { border: none; }
        QToolTip { background-color: #1C1C1C; color: #EDEDED; border: 1px solid #333333; }
        QScrollBar:vertical { width: 8px; background: #141414; border: none; }
        QScrollBar::handle:vertical { background: #3A3A3A; border-radius: 4px; min-height: 30px; }
        QScrollBar::handle:vertical:hover { background: #5C5C5C; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        QScrollBar:horizontal { height: 8px; background: #141414; border: none; }
        QScrollBar::handle:horizontal { background: #3A3A3A; border-radius: 4px; min-width: 30px; }
        QScrollBar::handle:horizontal:hover { background: #5C5C5C; }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
        QTableWidget { alternate-background-color: #171717; background-color: #101010; color: #EDEDED; }
        QTableWidget::item:selected { background-color: #2A2A2A; color: #EDEDED; }
        QTableWidget::item:hover { background: #242424; }
        QHeaderView::section { background-color: #222222; color: #A3A3A3; border: 1px solid #333333; padding: 4px; }
        QComboBox { background-color: #1C1C1C; color: #EDEDED; border: 1px solid #333333; border-radius: 8px; padding: 4px 8px; }
        QComboBox:hover { border: 1px solid #5C5C5C; }
        QComboBox:focus { border: 1px solid #4F73DC; }
        QComboBox QAbstractItemView { background-color: #1C1C1C; color: #EDEDED; selection-background-color: #2A2A2A; selection-color: #EDEDED; }
        /* 分析页下拉：右侧是一枚圆角灰按钮，描边和圆角与输入框一致，不用系统自带箭头。 */
        QComboBox[analysisCombo="true"] { padding-right: 34px; }
        QComboBox[analysisCombo="true"]::drop-down {
            subcontrol-origin: border;
            subcontrol-position: center right;
            width: 22px;
            border: 1px solid #333333;
            border-radius: 8px;
            background: #242424;
            margin: 3px 4px 3px 0;
        }
        QComboBox[analysisCombo="true"]::drop-down:hover {
            background: #2E2E2E;
            border-color: #5C5C5C;
        }
        QComboBox[analysisCombo="true"]::down-arrow {
            image: url(akia:combo_chevron.png);
            width: 10px;
            height: 10px;
        }
        QLineEdit { background-color: #101010; color: #EDEDED; border: 1px solid #333333; border-radius: 8px; padding: 4px 8px; }
        QLineEdit:focus { border: 1px solid #4F73DC; }
        QSpinBox, QDoubleSpinBox { background-color: #101010; color: #EDEDED; border: 1px solid #333333; border-radius: 8px; padding: 2px 6px; }
        QSpinBox:focus, QDoubleSpinBox:focus { border: 1px solid #4F73DC; }
        QGroupBox { color: #A3A3A3; border: 1px solid #333333; border-radius: 8px; margin-top: 8px; padding-top: 16px; }
        QGroupBox::title { color: #A3A3A3; padding: 0 6px; subcontrol-origin: margin; }
        QTextEdit, QPlainTextEdit { background-color: #101010; color: #EDEDED; border: 1px solid #333333; }
        QListWidget { background-color: #101010; color: #EDEDED; border: 1px solid #333333; }
        QListWidget::item:hover { background-color: #242424; }
        QListWidget::item:selected { background-color: #2A2A2A; color: #EDEDED; }
        QTreeWidget { background-color: #101010; color: #EDEDED; border: 1px solid #333333; }
        QTreeWidget::item:hover { background-color: #242424; }
        QTreeWidget::item:selected { background-color: #2A2A2A; color: #EDEDED; }
        QCheckBox { color: #EDEDED; }
        QRadioButton { color: #EDEDED; }
        QLabel { color: #EDEDED; background: transparent; }
        QSplitter::handle { background: #333333; }
        QTabWidget::pane { background-color: #141414; border: 1px solid #333333; }
        QTabBar::tab { background-color: #1C1C1C; color: #A3A3A3; border: 1px solid #333333; border-radius: 8px; padding: 6px 12px; }
        QTabBar::tab:selected { background-color: #2A2A2A; color: #EDEDED; }
        QProgressBar { background-color: #101010; border: none; border-radius: 4px; text-align: center; color: #EDEDED; }
        QProgressBar::chunk { background-color: #E8E8E8; border-radius: 4px; }
    """


BUTTON_PRIMARY = (
    "QPushButton { background-color: #E8E8E8; color: #171717; border: none;"
    "border-radius: 9px; padding: 12px 24px; }"
    "QPushButton:hover { background-color: #F4F4F4; }"
    "QPushButton:pressed { background-color: #D0D0D0; }"
)

BUTTON_SECONDARY = (
    "QPushButton { background-color: #242424; color: #EDEDED; border: 1px solid #3A3A3A;"
    "border-radius: 9px; padding: 6px 16px; min-width: 90px; }"
    "QPushButton:hover { background-color: #2E2E2E; }"
    "QPushButton:pressed { background-color: #1A1A1A; }"
)

BUTTON_TOGGLE = (
    "QPushButton { background-color: transparent; color: #A3A3A3; border: 1px solid #3A3A3A;"
    "border-radius: 9px; padding: 5px 14px; min-width: 64px; }"
    "QPushButton:hover { color: #EDEDED; border-color: #5C5C5C; }"
    "QPushButton:checked { background-color: #2A2A2A; color: #EDEDED; border-color: #3A3A3A; }"
)

BUTTON_PRIMARY_STRETCH = (
    "QPushButton { background-color: #E8E8E8; color: #171717; border: none;"
    "border-radius: 9px; padding: 12px 24px; }"
    "QPushButton:hover { background-color: #F4F4F4; }"
    "QPushButton:pressed { background-color: #D0D0D0; padding-top: 13px; padding-bottom: 11px; }"
)


def ensure_combo_indicator() -> None:
    """画出下拉按钮里的折线，并注册样式表用的 akia: 搜索路径。"""
    directory = Path(tempfile.gettempdir()) / "akia-ui"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "combo_chevron.png"
    if not path.exists():
        image = QImage(16, 16, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("#EDEDED"))
        pen.setWidthF(1.7)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPolyline([QPointF(4, 6), QPointF(8, 10.5), QPointF(12, 6)])
        painter.end()
        image.save(str(path))
    QDir.addSearchPath("akia", str(directory))
