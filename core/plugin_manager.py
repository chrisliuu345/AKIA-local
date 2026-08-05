"""插件管理器 — 扫描/加载/注册/管理第三方插件"""

import os, sys, importlib.util, logging
from typing import List, Dict, Any
from PySide6.QtWidgets import QWidget

_log = logging.getLogger("QA-Tool.Plugin")

class IPlugin:
    """插件接口 — 第三方 Tab 扩展需实现此接口"""
    name: str = "Unnamed"
    version: str = "0.1"
    category: str = "engineering"  # quality|ie|chart|engineering|sheet|sampling|report
    icon: str = "🔌"
    description: str = ""

    def create_tab(self, parent=None) -> QWidget:
        raise NotImplementedError

    def analyze(self, df) -> Dict[str, Any]:
        return {}


class PluginManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._plugins: Dict[str, IPlugin] = {}
            cls._instance._loaded = False
        return cls._instance

    @property
    def plugins(self) -> Dict[str, IPlugin]:
        return self._plugins

    def discover(self, plugin_dir: str = None):
        if self._loaded: return
        if plugin_dir is None:
            plugin_dir = os.path.join(os.path.dirname(__file__), "..", "plugins")
        if not os.path.isdir(plugin_dir): return
        for fname in sorted(os.listdir(plugin_dir)):
            if fname.startswith("_") or not fname.endswith(".py"): continue
            path = os.path.join(plugin_dir, fname)
            name = fname[:-3]
            try:
                spec = importlib.util.spec_from_file_location(f"plugin_{name}", path)
                module = importlib.util.module_from_spec(spec)
                sys.modules[f"plugin_{name}"] = module
                spec.loader.exec_module(module)
                if hasattr(module, "PLUGIN"):
                    p = module.PLUGIN
                    if isinstance(p, IPlugin):
                        self._plugins[name] = p
                        _log.info("Loaded plugin: %s v%s", p.name, p.version)
            except Exception as e:
                _log.warning("Failed to load plugin %s: %s", fname, e)
        self._loaded = True

    def get_sidebar_entries(self) -> List[tuple]:
        """返回 [(index, i18n_key), ...] 用于侧栏注册"""
        entries = []
        base_idx = 100  # 插件使用 100+ 的 index
        for i, (name, p) in enumerate(self._plugins.items()):
            entries.append((base_idx + i, f"plugin_{name}"))
        return entries

    def get_tab(self, index: int) -> QWidget:
        base_idx = 100
        keys = list(self._plugins.keys())
        i = index - base_idx
        if 0 <= i < len(keys):
            return self._plugins[keys[i]].create_tab()
        return None
