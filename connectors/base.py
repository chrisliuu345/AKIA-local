"""连接器抽象 — 协议优先 + 插件化。每个硬件协议一个插件, 按需安装。

ConnectorBase 与 DeviceDriver 同构 (open/poll/close)，poll 输出 Sample。
插件注册表: connectors/plugins/*.py 定义 PLUGIN 元数据 + Connector 类；
可选协议库在插件 open() 内延迟导入，缺失时插件被标记 unavailable，不影响主程序。
"""
import abc
import time
from dataclasses import dataclass

from core.devices.driver import Sample


class ConnectorError(Exception):
    pass


@dataclass(frozen=True)
class PluginInfo:
    name: str
    category: str  # plc / iot / vision / cmm / gage
    description: str
    available: bool
    create: callable


class ConnectorBase(abc.ABC):
    """连接器基类。config 为 dict(插件自定义), 名称标识数据源 topic。"""

    def __init__(self, name: str, config: dict | None = None):
        self.name = name
        self.config = dict(config or {})

    @abc.abstractmethod
    def open(self) -> None: ...

    @abc.abstractmethod
    def poll(self) -> list[Sample]: ...

    def close(self) -> None:
        raise NotImplementedError

    def _sample(self, channel: str, value: float, ts: float | None = None) -> Sample:
        return Sample(self.name, channel, float(value), ts if ts is not None else time.time())
