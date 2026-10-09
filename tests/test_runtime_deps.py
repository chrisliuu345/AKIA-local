"""启动期可选依赖处理测试（v4.3.0 B5）— matplotlib 缺失不阻断主程序。"""

import ast
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


class TestDependencyProbe:
    def test_complete_environment(self):
        from ui.runtime_deps import chart_dependency_hint, missing_chart_dependencies

        assert missing_chart_dependencies() == []
        assert chart_dependency_hint() == ""

    def test_missing_dependency_hint(self, monkeypatch):
        import ui.runtime_deps as module

        real_find_spec = importlib.util.find_spec

        def fake_find_spec(name, package=None):
            if name == "matplotlib":
                return None
            return real_find_spec(name, package)

        monkeypatch.setattr(module.importlib.util, "find_spec", fake_find_spec)
        missing = module.missing_chart_dependencies()
        assert "matplotlib" in missing
        hint = module.chart_dependency_hint()
        assert "缺少图表依赖" in hint
        assert "pip install" in hint


class TestMainEntry:
    def test_no_top_level_matplotlib_import(self):
        source = (ROOT / "main.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in tree.body:
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            assert not any(name.startswith("matplotlib") for name in names), \
                "main.py 不应在启动时导入 matplotlib"
        assert 'os.environ.setdefault("MPLBACKEND", "QtAgg")' in source

    def test_main_window_import_without_matplotlib(self):
        script = """
import sys

class _BlockMatplotlib:
    def find_spec(self, name, path=None, target=None):
        if name == "matplotlib" or name.startswith("matplotlib.") or name == "seaborn":
            raise ImportError("blocked: " + name)
        return None

sys.meta_path.insert(0, _BlockMatplotlib())
import ui.main_window
print("IMPORT_OK")
"""
        env = dict(os.environ)
        env["QT_QPA_PLATFORM"] = "offscreen"
        process = subprocess.run(
            [sys.executable, "-c", script], cwd=ROOT, env=env,
            capture_output=True, text=True, timeout=180, check=False)
        assert process.returncode == 0, process.stderr[-2000:]
        assert "IMPORT_OK" in process.stdout

    def test_lazy_tab_reports_dependency_hint(self, monkeypatch):
        pytest.importorskip("PySide6")
        from PySide6.QtWidgets import QMessageBox

        import ui.runtime_deps as deps
        from ui.main_window import MainWindow

        monkeypatch.setattr(deps, "missing_chart_dependencies",
                            lambda: ["matplotlib"])
        monkeypatch.setattr(deps, "chart_dependency_hint",
                            lambda missing=None: "缺少图表依赖: matplotlib\n  pip install matplotlib")
        warnings = []
        monkeypatch.setattr(QMessageBox, "warning",
                            staticmethod(lambda *a, **k: warnings.append(a)))

        window = MainWindow()
        try:
            monkeypatch.setattr(
                "importlib.import_module",
                lambda name: (_ for _ in ()).throw(
                    ImportError("No module named 'matplotlib'")))
            assert window._lazy_load_tab(12) is None  # ChartTab（图表类）
            assert warnings and "缺少图表依赖" in warnings[0][2]
            assert window._chart_dependency_warned is True
            notice = window.stack.widget(12)
            assert notice.objectName() == "dependency_notice_12"
        finally:
            window.close()


_BLOCK_CHART_DEPS = """
import sys

class _BlockMatplotlib:
    def find_spec(self, name, path=None, target=None):
        if name == "matplotlib" or name.startswith("matplotlib.") or name == "seaborn":
            raise ImportError("blocked: " + name)
        return None

sys.meta_path.insert(0, _BlockMatplotlib())
"""


class TestTabLazyLoading:
    def _run(self, script: str) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        env["QT_QPA_PLATFORM"] = "offscreen"
        return subprocess.run(
            [sys.executable, "-c", script], cwd=ROOT, env=env,
            capture_output=True, text=True, timeout=180, check=False)

    def test_tabs_package_lazy_exports(self):
        """ui.tabs 包初始化不得连带导入任何 Tab；from ui.tabs import X 保持可用。"""
        script = """
import sys
import ui.tabs
assert "ui.tabs.spc_tab" not in sys.modules, "包初始化不应导入 SPCTab"
from ui.tabs import SPCTab, FMEATab
assert SPCTab.__name__ == "SPCTab"
assert FMEATab.__name__ == "FMEATab"
print("LAZY_EXPORTS_OK")
"""
        process = self._run(script)
        assert process.returncode == 0, process.stderr[-2000:]
        assert "LAZY_EXPORTS_OK" in process.stdout

    def test_non_chart_tab_import_without_matplotlib(self):
        """缺 matplotlib 时，非图表 Tab 不应被包初始化连带打挂。"""
        script = _BLOCK_CHART_DEPS + """
import importlib
importlib.import_module("ui.tabs.fmea_tab")
importlib.import_module("ui.tabs.control_plan_tab")
assert "ui.tabs.spc_tab" not in sys.modules
print("NON_CHART_TABS_OK")
"""
        process = self._run(script)
        assert process.returncode == 0, process.stderr[-2000:]
        assert "NON_CHART_TABS_OK" in process.stdout

    def test_chart_icons_degrade_without_matplotlib(self):
        """缺 matplotlib 时图表类型图标退化为空 QIcon，不抛异常。"""
        script = _BLOCK_CHART_DEPS + """
from PySide6.QtWidgets import QApplication
app = QApplication([])
from ui.widgets.chart_icons import get_chart_icon, has_custom_icon
assert has_custom_icon("直方图")
assert get_chart_icon("直方图").isNull()
print("ICON_FALLBACK_OK")
"""
        process = self._run(script)
        assert process.returncode == 0, process.stderr[-2000:]
        assert "ICON_FALLBACK_OK" in process.stdout

    def test_main_reports_missing_core_dependency(self):
        """核心依赖缺失时给出可执行提示，而不是裸 ModuleNotFoundError 堆栈。"""
        script = """
import sys

class _BlockPySide6:
    def find_spec(self, name, path=None, target=None):
        if name == "PySide6" or name.startswith("PySide6."):
            raise ImportError("blocked: " + name)
        return None

sys.meta_path.insert(0, _BlockPySide6())
import runpy
runpy.run_path("main.py", run_name="__main__")
"""
        process = self._run(script)
        assert process.returncode == 1
        assert "缺少必需依赖" in process.stderr
        assert "PySide6" in process.stderr
        assert "Traceback" not in process.stderr
