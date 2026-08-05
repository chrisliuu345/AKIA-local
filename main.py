"""
QA-Tool — 主入口
Minitab式启动: Splash画面 → 精细化进度 → 主窗口 → 登录
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


LOGO_PATH = os.path.join(os.path.dirname(__file__), "logo.png")


# 保存原始 splash 画布（不含进度条和文字），每次重绘基于它
_SPLASH_BASE: QPixmap = None


def _update_splash(splash: QSplashScreen, pct: int, status: str = ""):
    """在 splash 底部绘制进度条 + 状态文字（每次从原始画布重绘, 避免重叠）"""
    global _SPLASH_BASE
    if _SPLASH_BASE is None:
        _SPLASH_BASE = QPixmap(splash.pixmap())

    pm = QPixmap(_SPLASH_BASE)
    painter = QPainter(pm)
    w, h = pm.width(), pm.height()
    bar_w = int(w * 0.7)
    bar_h = 6
    bar_x = (w - bar_w) // 2
    bar_y = h - 46

    # 清除底部区域 (用背景色覆盖旧进度条+旧文字)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#181822"))
    painter.drawRect(0, bar_y - 28, w, 80)

    # 进度条底色
    painter.setBrush(QColor(60, 60, 70))
    painter.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 3, 3)

    # 进度填充
    fill_w = int(bar_w * pct / 100)
    painter.setBrush(QColor("#4da6ff"))
    painter.drawRoundedRect(bar_x, bar_y, fill_w, bar_h, 3, 3)

    # 状态文字 (离进度条上方 22px)
    if status:
        painter.setPen(QColor("#a0a3ae"))
        painter.setFont(QFont("Microsoft YaHei", 9))
        painter.drawText(0, bar_y - 22, w, 16, Qt.AlignCenter, status)

    painter.end()
    splash.setPixmap(pm)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("QA-Tool")

    if os.path.exists(LOGO_PATH):
        app.setWindowIcon(QIcon(LOGO_PATH))

    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)
    app.setStyle("Fusion")

    # ── 全局暗色调色板 (必须在所有 widget 之前) ──
    from ui.theme import apply_dark_palette
    apply_dark_palette()

    # ── 全局暗色 QSS 样式 (跨平台暗色保障) ──
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

    # ── Splash 启动画面 ──
    splash_img = QPixmap(LOGO_PATH) if os.path.exists(LOGO_PATH) else None
    if splash_img and not splash_img.isNull():
        scaled = splash_img.scaled(320, 192, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        canvas = QPixmap(400, 300)
        canvas.fill(QColor("#181822"))
        painter = QPainter(canvas)
        x = (canvas.width() - scaled.width()) // 2
        y = (canvas.height() - scaled.height()) // 2 - 24
        painter.drawPixmap(x, y, scaled)
        painter.end()
        splash = QSplashScreen(canvas)
    else:
        splash = QSplashScreen()
    splash.show()
    splash.raise_()
    app.processEvents()

    # ── 精细化加载 (12 步) ──
    steps = [
        (5,  "初始化运行环境..."),
        (10, "加载认证系统..."),
        (20, "初始化用户数据..."),
        (28, "加载核心分析引擎..."),
        (35, "导入 SPC 控制图模块..."),
        (42, "导入过程能力分析模块..."),
        (48, "导入 MSA/假设检验/DOE 模块..."),
        (55, "加载 IE 工业工程模块..."),
        (62, "加载工程工具模块..."),
        (70, "构建应用主窗口..."),
        (78, "初始化侧栏导航..."),
        (85, "连接信号与数据路由..."),
        (92, "恢复窗口布局..."),
        (97, "准备就绪..."),
        (100, "启动完成"),
    ]

    for pct, status in steps:
        _update_splash(splash, pct, status)
        app.processEvents()

        # 在特定阶段执行实际初始化
        if pct == 10:
            from core.auth import AuthManager
            auth = AuthManager()
        elif pct == 28:
            from ui.main_window import MainWindow
        elif pct == 70:
            window = MainWindow(user=None, splash=splash)

    # ── 关闭 Splash，显示主窗口 ──
    splash.close()
    window.show()
    app.processEvents()

    if os.path.exists(LOGO_PATH):
        window.setWindowIcon(QIcon(LOGO_PATH))

    # ── 登录 ──
    from ui.dialogs.login_dialog import LoginDialog
    login = LoginDialog(auth, parent=window)
    if login.exec() != LoginDialog.Accepted:
        window.close()
        return 0

    window.current_user = login.user
    window.refresh_menu_for_user()
    role_suffix = f" — {login.user.role}" if login.user else ""
    window.setWindowTitle(f"{APP_NAME} v{APP_VERSION}{role_suffix}")

    try:
        return app.exec()
    except Exception as e:
        QMessageBox.critical(None, "启动失败", f"程序启动异常:\n{str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
