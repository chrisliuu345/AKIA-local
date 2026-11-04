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

    from ui.theme import APP_STYLESHEET, apply_dark_palette, ensure_combo_indicator
    apply_dark_palette()
    ensure_combo_indicator()
    app.setStyleSheet(APP_STYLESHEET)

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
