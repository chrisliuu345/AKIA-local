"""
AKIA — 主入口
"""

import sys
import os
import contextlib

os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"

# matplotlib 不再在启动时导入：仅设置后端环境变量（PYTHON 解释器在首次 import
# matplotlib 时生效）。缺少 matplotlib 时主界面/数据/分析/案例/证据功能仍可用。
os.environ.setdefault("MPLBACKEND", "QtAgg")

import warnings

# 数值退化告警（log(0)、除零等）出自第三方与算法层的边界样本：
# 不静默丢弃，改用 "once" —— 每个位置只提示一次，避免刷屏又保留可见性
warnings.filterwarnings("once", category=RuntimeWarning,
                        message=".*invalid value encountered.*")


#: 主界面硬依赖（缺失时无法创建窗口；matplotlib/seaborn 等图表依赖不在此列）
CORE_DEPENDENCIES = ("PySide6", "numpy", "pandas")


def _missing_core_dependencies() -> list[str]:
    """启动前探测硬依赖；不 import 任何第三方包。"""
    import importlib.util

    missing: list[str] = []
    for name in CORE_DEPENDENCIES:
        try:
            if importlib.util.find_spec(name) is None:
                missing.append(name)
        except (ImportError, ValueError):
            missing.append(name)
    return missing


def _core_dependency_message(missing: list[str]) -> str:
    return (
        f"AKIA 启动失败：缺少必需依赖: {', '.join(missing)}\n"
        f"当前解释器: {sys.executable}\n"
        "请使用项目虚拟环境启动，或先安装依赖：\n"
        "  python -m pip install -r requirements.txt\n"
        "  python main.py"
    )


LOGO_PATH = os.path.join(os.path.dirname(__file__), "logo.png")

def main():
    missing = _missing_core_dependencies()
    if missing:
        print(_core_dependency_message(missing), file=sys.stderr)
        return 1

    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
        from PySide6.QtCore import QTimer
        from PySide6.QtGui import QFont, QIcon

        from config.settings import APP_NAME, APP_VERSION, ORGANIZATION
        from ui.font_config import get_ui_font
    except ImportError as exc:  # find_spec 正常但安装损坏
        print(_core_dependency_message([exc.name or "核心依赖"]), file=sys.stderr)
        return 1

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORGANIZATION)

    # 旧版 QSettings 数据一次性迁移：窗口布局 / 最近项目 / 公式 / LLM 等
    from core.settings_migration import migrate_legacy_qsettings
    migrate_legacy_qsettings()

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

    # 自本版起取消加载界面：启动后直接构建并显示主界面
    from ui.main_window import MainWindow
    window = MainWindow()
    window.show()
    app.processEvents()

    from ui.runtime_deps import chart_dependency_hint
    dependency_hint = chart_dependency_hint()
    if dependency_hint:
        window.statusBar().showMessage(
            f"{dependency_hint.splitlines()[0]} · 图表功能不可用", 15000)

    # 重依赖预热移到首帧之后：不占用首屏等待时间
    def _warm_background():
        with contextlib.suppress(ImportError):  # 缺 matplotlib 时跳过图表预热
            from output.chart_engine import _ensure_font
            _ensure_font()
        import threading

        def _warm_modules():
            import importlib

            for name in ("scipy.stats", "statsmodels", "seaborn"):
                with contextlib.suppress(ImportError):  # 可选重依赖缺失不阻断
                    importlib.import_module(name)
        threading.Thread(target=_warm_modules, daemon=True).start()
    QTimer.singleShot(600, _warm_background)

    if os.path.exists(LOGO_PATH):
        window.setWindowIcon(QIcon(LOGO_PATH))

    window.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")

    try:
        return app.exec()
    except Exception as e:
        QMessageBox.critical(None, "启动失败", f"程序启动异常:\n{e!s}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
