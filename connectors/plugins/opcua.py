"""OPC-UA 连接器 — 工厂 PLC/设备节点读取。

config:
    endpoint: str    必填 (如 opc.tcp://192.168.1.5:4840)
    node_ids: {"CH0": "ns=2;i=1"}   节点映射

连接失败和任一节点读数失败都向上抛出，不把缺数当成 0 或静默跳过。
"""
import contextlib

from connectors.base import ConnectorBase

PLUGIN = {"name": "opcua", "category": "plc",
          "description": "OPC-UA 客户端 — PLC/设备节点读取"}

try:
    import asyncua  # noqa: F401
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
        from asyncua.sync import Client

        endpoint = str(self.config.get("endpoint") or "").strip()
        if not endpoint:
            raise ConnectionError("OPC-UA 连接失败: 未配置端点")
        client = Client(endpoint, timeout=4)
        try:
            client.connect()
        except Exception as e:
            with contextlib.suppress(Exception):
                client.disconnect()
            raise ConnectionError(f"OPC-UA 连接失败: {e}") from e
        self._client = client

    def poll(self) -> list:
        if not self._client:
            raise ConnectionError("OPC-UA 读数失败: 尚未连接")
        node_ids = self.config.get("node_ids") or {}
        if not node_ids:
            raise ConnectionError("OPC-UA 读数失败: 未配置节点")
        samples = []
        errors = []
        for label, node in node_ids.items():
            try:
                value = self._client.get_node(node).read_value()
                samples.append(self._sample(label, float(value)))
            except Exception as e:
                errors.append(f"{label}: {e}")
        if errors:
            raise ConnectionError("OPC-UA 读数失败: " + "; ".join(errors))
        return samples

    def close(self) -> None:
        if self._client:
            with contextlib.suppress(Exception):
                self._client.disconnect()
            self._client = None
