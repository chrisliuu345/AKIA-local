"""Modbus TCP 连接器 — 寄存器/线圈读取（覆盖 95% 工厂 PLC）。

config:
    host: str              必填
    port: int             默认 502
    slave: int            默认 1
    registers: {"CH0": 0, "CH1": 1}   读数地址映射(0-based)
    count: int             每次读寄存器数, 默认 len(registers)
"""
import asyncio

from connectors.base import ConnectorBase

PLUGIN = {"name": "modbus_tcp", "category": "plc",
          "description": "Modbus TCP 寄存器读取 — 覆盖 95% 工厂 PLC"}

try:
    from pymodbus.client import AsyncModbusTcpClient
    AVAILABLE = True
except ImportError:
    AVAILABLE = False


class Connector(ConnectorBase):
    def __init__(self, config: dict):
        super().__init__(config.get("name", "plc-01"), config)
        self._client = None
        self._registers = [int(a) for a in self.config.get("registers", {}).values()]
        self._labels = list(self.config.get("registers", {}).keys())
        self._slave = int(self.config.get("slave", 1))
        self._count = int(self.config.get("count", len(self._registers) or 1))

    def open(self) -> None:
        if not AVAILABLE:
            raise ImportError("需要安装 pymodbus")
        self._client = AsyncModbusTcpClient(
            self.config["host"], port=int(self.config.get("port", 502)))
        if not self._client.connect():
            raise ConnectionError(f"Modbus 连接失败 {self.config['host']}")

    def poll(self) -> list:
        if not self._client:
            return []
        rr = asyncio.run(self._read_all())
        samples = []
        for label, addr in zip(self._labels, self._registers, strict=False):
            if addr < len(rr):
                samples.append(self._sample(label, float(rr[addr])))
        return samples

    async def _read_all(self):
        result = await self._client.read_holding_registers(
            self._registers[0], count=self._count, slave=self._slave)
        return getattr(result, "registers", []) or []

    def close(self) -> None:
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None
