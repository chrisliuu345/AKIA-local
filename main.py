"""
QA-Tool — 主入口
"""

import sys
import os

os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"

import matplotlib
matplotlib.use("QtAgg")

from PySide6.QtWidgets import QApplication, QMessageBox, QSplashScreen
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QIcon

from config.settings import APP_NAME, APP_VERSION
from ui.font_config import get_ui_font


LOGO_PATH = os.path.join(os.path.dirname(__file__), "logo.png")

COLOR_UPPER = "#0d2847"
COLOR_LOWER = "#4da6ff"
COLOR_BAR_BG = "#0a1e38"
COLOR_BAR_FILL = "#ffffff"

_SPLASH_LOGICAL_W = 300
_SPLASH_LOGICAL_H = 200
_SPLASH_SPLIT_RATIO = 0.81


def _get_screen_dpr():
    """获取主屏幕的 devicePixelRatio"""
    try:
        from PySide6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen()
        if screen:
            return screen.devicePixelRatio()
    except Exception:
        pass
    return 1.0


def _create_splash_canvas() -> QPixmap:
    """创建双色 splash 画布（自适应 DPI）"""
    dpr = _get_screen_dpr()
    w = int(_SPLASH_LOGICAL_W * dpr)
    h = int(_SPLASH_LOGICAL_H * dpr)
    split_y = int(h * _SPLASH_SPLIT_RATIO)
    bar_h = max(2, int(3 * dpr))
    margin_x = int(14 * dpr)
    margin_top = int(28 * dpr)
    margin_bottom = int(10 * dpr)
    font_size = max(7, int(9 * dpr))

    pm = QPixmap(w, h)
    pm.fill(QColor(COLOR_LOWER))

    painter = QPainter(pm)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    painter.setRenderHint(QPainter.Antialiasing)

    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(COLOR_UPPER))
    painter.drawRect(0, 0, w, split_y)

    if os.path.exists(LOGO_PATH):
        logo = QPixmap(LOGO_PATH)
        if not logo.isNull():
            max_h = split_y - margin_top - margin_bottom
            max_w = w - margin_x * 2
            scaled = logo.scaled(max_w, max_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            x = (w - scaled.width()) // 2
            y = (split_y - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)

    painter.setPen(QColor(COLOR_UPPER))
    font = QFont(get_ui_font(), -1, QFont.Bold)
    font.setPixelSize(font_size)
    painter.setFont(font)
    text_rect = Qt.AlignRight | Qt.AlignVCenter
    painter.drawText(0, split_y, w - int(16 * dpr), h - split_y, text_rect, "IE-Quality Analysis Tool")

    painter.end()
    return pm


def _update_splash(splash: QSplashScreen, pct: int, base: QPixmap = None):
    """更新进度条（位于两色交接处）"""
    global _splash_base
    if base is not None:
        _splash_base = base
    if _splash_base is None:
        return
    pm = QPixmap(_splash_base)
    painter = QPainter(pm)

    w = pm.width()
    h = pm.height()
    dpr = _get_screen_dpr()
    split_y = int(h * _SPLASH_SPLIT_RATIO)
    bar_h = max(2, int(3 * dpr))
    bar_y = split_y - bar_h // 2
    fill_w = int(w * pct / 100)

    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(COLOR_BAR_BG))
    painter.drawRect(0, bar_y, w, bar_h)

    if fill_w > 0:
        painter.setBrush(QColor(COLOR_BAR_FILL))
        painter.drawRect(0, bar_y, fill_w, bar_h)

    painter.end()
    splash.setPixmap(pm)


_splash_base: QPixmap = None


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("QA-Tool")

    if os.path.exists(LOGO_PATH):
        app.setWindowIcon(QIcon(LOGO_PATH))

    font = QFont(get_ui_font(), 10)
    app.setFont(font)
    app.setStyle("Fusion")

    from ui.theme import apply_dark_palette
    apply_dark_palette()

    app.setStyleSheet("""
        QWidget { background-color: #181822; color: #e1e2e6; }
        QMainWindow { background-color: #181822; }
        QDialog { background-color: #181822; }
        QMenuBar { background-color: #13131c; color: #e1e2e6; }
        QMenuBar::item:selected { background-color: #363648; }
        QMenu { background-color: #262632; color: #e1e2e6; border: 1px solid #3a3a48; }
        QMenu::item:selected { background-color: #363648; }
        QStatusBar { background-color: #13131c; color: #a0a3ae; min-height: 24px; }
        QStatusBar::item { border: none; }
        QToolTip { background-color: #363648; color: #e1e2e6; border: 1px solid #3a3a48; }
        QScrollBar:vertical { width: 8px; background: #181822; border: none; }
        QScrollBar::handle:vertical { background: #3a3a48; border-radius: 4px; min-height: 30px; }
        QScrollBar::handle:vertical:hover { background: #4a4a5a; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        QScrollBar:horizontal { height: 8px; background: #181822; border: none; }
        QScrollBar::handle:horizontal { background: #3a3a48; border-radius: 4px; min-width: 30px; }
        QScrollBar::handle:horizontal:hover { background: #4a4a5a; }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
        QTableWidget { alternate-background-color: #22222e; background-color: #1c1c26; color: #e1e2e6; }
        QTableWidget::item:hover { background: #363648; }
        QHeaderView::section { background-color: #2c2c38; color: #a0a3ae; border: 1px solid #3a3a48; padding: 4px; }
        QComboBox { background-color: #262632; color: #e1e2e6; border: 1px solid #3a3a48; border-radius: 4px; padding: 4px 8px; }
        QComboBox:hover { border: 1px solid #4da6ff; }
        QComboBox:focus { border: 1px solid #4da6ff; }
        QComboBox QAbstractItemView { background-color: #262632; color: #e1e2e6; selection-background-color: #363648; }
        QLineEdit { background-color: #1c1c26; color: #e1e2e6; border: 1px solid #3a3a48; border-radius: 4px; padding: 4px 8px; }
        QLineEdit:focus { border: 1px solid #4da6ff; }
        QSpinBox, QDoubleSpinBox { background-color: #1c1c26; color: #e1e2e6; border: 1px solid #3a3a48; border-radius: 4px; padding: 2px 6px; }
        QSpinBox:focus, QDoubleSpinBox:focus { border: 1px solid #4da6ff; }
        QGroupBox { color: #a0a3ae; border: 1px solid #3a3a48; border-radius: 6px; margin-top: 8px; padding-top: 16px; }
        QGroupBox::title { color: #a0a3ae; padding: 0 6px; subcontrol-origin: margin; }
        QTextEdit, QPlainTextEdit { background-color: #1c1c26; color: #e1e2e6; border: 1px solid #3a3a48; }
        QListWidget { background-color: #1c1c26; color: #e1e2e6; border: 1px solid #3a3a48; }
        QListWidget::item:hover { background-color: #363648; }
        QListWidget::item:selected { background-color: #2a384a; }
        QTreeWidget { background-color: #1c1c26; color: #e1e2e6; border: 1px solid #3a3a48; }
        QTreeWidget::item:hover { background-color: #363648; }
        QTreeWidget::item:selected { background-color: #2a384a; }
        QCheckBox { color: #e1e2e6; }
        QRadioButton { color: #e1e2e6; }
        QLabel { color: #e1e2e6; background: transparent; }
        QSplitter::handle { background: #3a3a48; }
        QTabWidget::pane { background-color: #181822; border: 1px solid #3a3a48; }
        QTabBar::tab { background-color: #262632; color: #a0a3ae; border: 1px solid #3a3a48; padding: 6px 12px; }
        QTabBar::tab:selected { background-color: #181822; color: #e1e2e6; }
        QProgressBar { background-color: #1c1c26; border: none; border-radius: 3px; text-align: center; color: #e1e2e6; }
        QProgressBar::chunk { background-color: #1b5faa; border-radius: 3px; }
    """)

    global _splash_base
    _splash_base = _create_splash_canvas()
    splash = QSplashScreen(_splash_base)
    splash.show()
    splash.raise_()
    app.processEvents()

    import threading
    def _warmup():
        import scipy.stats  # noqa: F401
        import statsmodels  # noqa: F401
        import seaborn      # noqa: F401
    threading.Thread(target=_warmup, daemon=True).start()

    steps = [5, 10, 20, 28, 35, 42, 48, 55, 62, 70, 78, 85, 92, 97, 100]

    for pct in steps:
        _update_splash(splash, pct)
        app.processEvents()

        if pct == 28:
            from ui.main_window import MainWindow
        elif pct == 70:
            window = MainWindow(splash=splash)

    splash.close()
    window.show()
    app.processEvents()

    if os.path.exists(LOGO_PATH):
        window.setWindowIcon(QIcon(LOGO_PATH))

    window.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")

    try:
        return app.exec()
    except Exception as e:
        QMessageBox.critical(None, "启动失败", f"程序启动异常:\n{str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
