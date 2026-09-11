"""test_layering.py — 分层依赖守卫

约定:
- analysis/ 纯计算层：不得依赖 Qt（PySide6），保证无 GUI 环境可复用/可测
- core/ config/ output/ 基础层：不得依赖 ui/（v3.7.1 前存在 font_config 反向依赖）
- ui/ 允许依赖其下各层

仅做静态 import 扫描，不导入被测模块，运行成本极低。
"""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_BASE_LAYERS = ("core", "config", "output")


def _iter_python_files(package: str):
    return sorted((ROOT / package).rglob("*.py"))


def _imports(path: Path) -> set:
    """收集模块的顶层 import 目标（含 from X import Y 的 X）"""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                names.add(node.module)
    return names


class TestNoUiDependencyInBaseLayers:
    def test_core_config_output_do_not_import_ui(self):
        offenders = []
        for package in _BASE_LAYERS:
            for path in _iter_python_files(package):
                for name in _imports(path):
                    if name == "ui" or name.startswith("ui."):
                        offenders.append(f"{path.relative_to(ROOT)} -> {name}")
        assert offenders == [], "基础层不得依赖 ui: " + "; ".join(offenders)

    def test_font_config_reexport_still_works(self):
        """ui.font_config 兼容转发仍可用（旧 import 不炸）"""
        from ui.font_config import get_ui_font as via_ui
        from core.fonts import get_ui_font as canonical

        assert via_ui() == canonical()


class TestAnalysisLayerStaysQtFree:
    def test_analysis_does_not_import_pyside6(self):
        offenders = []
        for path in _iter_python_files("analysis"):
            for name in _imports(path):
                if name == "PySide6" or name.startswith("PySide6."):
                    offenders.append(str(path.relative_to(ROOT)))
        assert offenders == [], "analysis 层必须保持无 Qt: " + "; ".join(offenders)
