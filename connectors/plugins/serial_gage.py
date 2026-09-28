"""RS232/USB 量具连接器 — 通用数值解析（Mitutoyo SPC 等逐行传输量具）。

config:
    tty: str          必填 串口号
    baud: int         默认 9600
    channel: str      通道名, 默认 "value"
"""
import contextlib
import re

from connectors.base import ConnectorBase

PLUGIN = {"name": "serial_gage", "category": "gage",
          "description": "RS232/USB 量具采集（逐行数值传输设备）"}

_NUM = re.compile(r"[-+]?\d+(?:\.\d+)?")


class Connector(ConnectorBase):
    def __init__(self, config: dict):
        super().__init__(config.get("name", "gage-01"), config)
        self._serial = None
        self._buf = ""

    def open(self) -> None:
        import serial
        self._serial = serial.Serial(self.config["tty"],
                                     baudrate=int(self.config.get("baud", 9600)),
                                     timeout=0.5)

    def poll(self) -> list:
        if not self._serial or not self._serial.is_open:
            return []
        try:
            raw = self._serial.read(4096)
        except Exception:
            return []
        if not raw:
            return []
        self._buf += raw.decode("utf-8", errors="replace")
        samples = []
        lines = self._buf.split("\n")
        self._buf = lines[-1]
        channel = self.config.get("channel", "value")
        for line in lines[:-1]:
            m = _NUM.search(line)
            if m:
                samples.append(self._sample(channel, float(m.group())))
        return samples

    def close(self) -> None:
        if self._serial:
            with contextlib.suppress(Exception):
                self._serial.close()
            self._serial = None
