"""数据连接器注册表 — 扫描 connectors/plugins/*.py 并探测可用性。"""

import importlib
import logging
from pathlib import Path

from connectors.base import PluginInfo

logger = logging.getLogger(__name__)

PLUGINS_DIR = Path(__file__).parent / "plugins"
_CACHE: dict[str, PluginInfo] | None = None


def discover(refresh: bool = False) -> dict[str, PluginInfo]:
    """返回 {插件名: PluginInfo}。可选库缺失 → available=False 但不报错。"""
    global _CACHE
    if _CACHE is not None and not refresh:
        return _CACHE
    infos = {}
    for path in sorted(PLUGINS_DIR.glob("*.py")):
        if path.name.startswith("_"):
            continue
        mod_name = f"connectors.plugins.{path.stem}"
        meta = _load_meta(mod_name)
        if meta is None:
            continue
        infos[meta.name] = meta
    _CACHE = infos
    return infos


def _load_meta(mod_name: str) -> PluginInfo | None:
    try:
        mod = importlib.import_module(mod_name)
    except Exception as e:
        logger.warning("connector plugin %s failed to load: %s", mod_name, e)
        return None
    doc = getattr(mod, "PLUGIN", None)
    connector_cls = getattr(mod, "Connector", None)
    if not doc or connector_cls is None:
        return None
    return PluginInfo(
        name=doc.get("name", mod_name.rsplit(".", 1)[-1]),
        category=doc.get("category", "other"),
        description=doc.get("description", ""),
        available=bool(getattr(connector_cls, "AVAILABLE", True)),
        create=connector_cls,
    )


def create_connector(plugin_name: str, config: dict | None = None):
    """按插件名实例化; 库缺失则抛 ConnectorError。"""
    info = discover().get(plugin_name)
    if info is None:
        raise ValueError(f"未知连接器插件: {plugin_name}")
    if not info.available:
        raise ImportError(f"连接器插件 '{plugin_name}' 依赖库未安装，请按需安装")
    return info.create(config or {})
