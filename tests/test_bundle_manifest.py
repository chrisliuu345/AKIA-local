"""打包完整性棘轮（2026-10-15 审查）— 动态导入模块必须显式收集。

回归背景：``ui/_tab_registry.py``（Tab 懒加载）与 ``connectors/registry.py``
（连接器插件发现）经 importlib 动态导入，PyInstaller 无法静态跟踪；
v4.2.0–v4.4.0 全部 AppImage 与 Windows onedir 构建实测缺失
``ui.tabs.*`` / ``connectors.plugins.*``——打包版所有 Tab 与连接器插件不可用。
"""

import ast
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _literal_assignment(source: str, name: str):
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == name
                for target in node.targets):
            return ast.literal_eval(node.value)
    return None


class TestBuildScriptCollection:
    def test_collect_submodules_lists_dynamic_packages(self):
        source = (ROOT / "build_pyinstaller.py").read_text(encoding="utf-8")
        collected = _literal_assignment(source, "COLLECT_SUBMODULES")
        assert collected is not None, \
            "build_pyinstaller.py 必须定义 COLLECT_SUBMODULES（动态导入包显式收集）"
        assert {"ui.tabs", "connectors.plugins"} <= set(collected), \
            "Tab 懒加载 / 连接器插件发现依赖这两个包的子模块收集"
        assert "--collect-submodules" in source, \
            "COLLECT_SUBMODULES 必须接线到 PyInstaller 命令"

    def test_build_runs_bundle_verification(self):
        source = (ROOT / "build_pyinstaller.py").read_text(encoding="utf-8")
        assert "verify_bundle.py" in source, \
            "构建收尾必须调用产物完整性校验（tools/verify_bundle.py）"


class TestConnectorPluginManifest:
    def test_plugin_modules_match_directory(self):
        from connectors.plugins import PLUGIN_MODULES

        on_disk = sorted(
            path.stem for path in (ROOT / "connectors" / "plugins").glob("*.py")
            if not path.name.startswith("_"))
        assert sorted(PLUGIN_MODULES) == on_disk, \
            "新增/删除连接器插件后必须同步 connectors/plugins/__init__.py 清单"

    def test_static_manifest_used_when_directory_unscannable(self, monkeypatch):
        """冻结打包场景：源码目录不可扫描时仍能给出全部插件候选。"""
        import connectors.plugins as plugins_pkg
        import connectors.registry as registry

        real_glob = Path.glob

        def fake_glob(self, pattern):
            if self == registry.PLUGINS_DIR:
                return iter(())
            return real_glob(self, pattern)

        monkeypatch.setattr(registry.Path, "glob", fake_glob)
        registry._CACHE = None
        try:
            stems = registry._candidate_stems()
        finally:
            registry._CACHE = None
        assert stems == list(plugins_pkg.PLUGIN_MODULES)


class TestDynamicModuleResolution:
    def test_tab_registry_modules_resolvable_in_source(self):
        from ui._tab_registry import TAB_REGISTRY

        for entry in TAB_REGISTRY:
            module_path = str(entry[3])
            assert module_path.startswith("ui.tabs."), module_path
            assert importlib.util.find_spec(module_path) is not None, \
                f"Tab 注册表模块无法解析: {module_path}"

    def test_verify_bundle_required_set(self):
        from tools.verify_bundle import required_modules

        required = required_modules()
        assert {"ui.tabs", "connectors.plugins"} <= required
        assert "ui.tabs.spc_tab" in required
        assert "connectors.plugins.opcua" in required
