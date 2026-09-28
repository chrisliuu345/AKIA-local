"""OPC-UA 连接器 — 工厂 PLC/设备节点读取。

config:
    endpoint: str    必填 (如 opc.tcp://192.168.1.5:4840)
    node_ids: {"CH0": "ns=2;i=1"}   节点映射
"""
import contextlib
from connectors.base import ConnectorBase

PLUGIN = {"name": "opcua", "category": "plc",
          "description": "OPC-UA 客户端 — PLC/设备节点读取"}

try:
    from asyncua import Client
    AVAILABLE = True
except ImportError:
    AVAILABLE = False


class Connector(ConnectorBase):
    def __init__(self, config: dict):
        super().__init__(config.get("name", "opcua-01"), config)
        self._client = None

    def open(self) -> None:
        if not AVAILABLE:
            raise ImportError("需要安装 asyncua")
        self._client = Client(self.config["endpoint"])
        try:
            self._client.connect()
        except Exception as e:
            self._client = None
            raise ConnectionError(f"OPC-UA 连接失败: {e}") from e

    def poll(self) -> list:
        if not self._client:
            return []
        samples = []
        for label, node in self.config.get("node_ids", {}).items():
            try:
                value = self._client.get_node(node).read_value()
                samples.append(self._sample(label, float(value)))
            except Exception:
                pass
        return samples

    def close(self) -> None:
        if self._client:
            with contextlib.suppress(Exception):
                self._client.disconnect()
            self._client = None
