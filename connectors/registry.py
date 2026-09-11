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


def specs_from_settings(settings) -> list[dict]:
    """user_config.json 的 `connectors` 配置 → 规范化规格列表（v3.8.0-⑦）。

    支持两种写法:
        "connectors": ["modbus_tcp"]
        "connectors": [{"plugin": "mqtt_sub", "name": "line1",
                        "config": {"topic": "qa/line1"}}]
    """
    if not settings:
        return []
    if isinstance(settings, dict):
        settings = list(settings.values())
    specs: list[dict] = []
    for item in settings:
        if isinstance(item, str):
            specs.append({"plugin": item, "name": item, "config": {}})
            continue
        if not isinstance(item, dict):
            continue
        plugin = str(item.get("plugin") or item.get("type") or "").strip()
        if not plugin:
            continue
        config = item.get("config")
        config = dict(config) if isinstance(config, dict) else {}
        name = str(item.get("name") or config.get("name") or plugin)
        specs.append({"plugin": plugin, "name": name, "config": config,
                      "enabled": bool(item.get("enabled", True))})
    return [s for s in specs if s.get("enabled", True)]


def create_drivers(specs: list[dict]) -> tuple[list, list[tuple[str, str]]]:
    """规格 → 驱动实例。单项失败不影响其他数据源，返回 (drivers, errors)。"""
    drivers: list = []
    errors: list[tuple[str, str]] = []
    for spec in specs or []:
        name = str(spec.get("name") or spec.get("plugin") or "connector")
        try:
            config = dict(spec.get("config") or {})
            config.setdefault("name", name)
            drivers.append(create_connector(str(spec.get("plugin")), config))
        except Exception as e:
            logger.warning("connector %s 初始化失败: %s", name, e)
            errors.append((name, str(e)))
    return drivers, errors
