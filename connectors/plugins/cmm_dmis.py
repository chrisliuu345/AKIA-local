"""CMM DMIS 连接器 — 三坐标测量机 DMIS 输出解析（RS232/USB/文件）。

config:
    source: "tty" | "file"    数据来源, 默认 file
    tty: str                  串口号 (source=tty 时)
    path: str                 文件/管道 (source=file 时)
    axes: {"X": "X", "Y": "Y", "Z": "Z"}   轴映射(通道名→DMIS 关键字)
    baud: int                 默认 9600
"""
import re
import time

from connectors.base import ConnectorBase

PLUGIN = {"name": "cmm_dmis", "category": "cmm",
          "description": "三坐标测量机 DMIS 输出解析 — RS232/USB/文件"}

try:
    import serial  # noqa: F401  # pyserial 已在主依赖
    AVAILABLE = True
except ImportError:
    AVAILABLE = False

# DMIS 实测语句示例: MEAS/POL,1, X,12.345,Y,-3.210,Z,0.012
# 轴值成对出现: 关键字(X/Y/Z) + 分隔符(逗号/空格/冒号) + 数值
_VAL_PAIR = re.compile(r"([XYZ])\s*[,: ]\s*([-+0-9.]+)")


class Connector(ConnectorBase):
    def __init__(self, config: dict):
        super().__init__(config.get("name", "cmm-01"), config)
        self._file_obj = None
        self._buf = ""

    def open(self) -> None:
        if not AVAILABLE:
            raise ImportError("需要安装 pyserial")
        source = self.config.get("source", "file")
        if source == "tty":
            self._file_obj = serial.Serial(
                self.config["tty"], baudrate=int(self.config.get("baud", 9600)),
                timeout=0.5)
        else:
            self._file_obj = open(self.config["path"], encoding="utf-8",
                                  errors="replace")
        # 串口/管道跳到末尾只读新增输出; 普通文件从头读
        if source == "tty":
            try:
                self._file_obj.seek(0, 2)
            except (OSError, ValueError):
                pass

    def poll(self) -> list:
        if not self._file_obj:
            return []
        chunk = self._read()
        if not chunk:
            return []
        self._buf += chunk
        samples = []
        lines = self._buf.split("\n")
        self._buf = lines[-1]
        for line in lines[:-1]:
            samples.extend(self._parse(line))
        return samples

    def _read(self) -> str:
        try:
            raw = self._file_obj.read(4096)
        except Exception:
            return ""
        if isinstance(raw, (bytes, bytearray)):
            return raw.decode("utf-8", errors="replace")
        return raw if isinstance(raw, str) else ""

    def _parse(self, line: str) -> list:
        axes = self.config.get("axes", {"X": "X", "Y": "Y", "Z": "Z"})
        values: dict[str, float] = {}
        if line.strip().upper().startswith("MEAS"):
            for m in _VAL_PAIR.finditer(line.upper()):
                values[m.group(1)] = float(m.group(2))
        if not values:
            for m in _VAL_PAIR.finditer(line.upper()):
                values[m.group(1)] = float(m.group(2))
        now = time.time()
        return [self._sample(ch, values[key], now)
                for key, ch in axes.items() if key in values]

    def close(self) -> None:
        if self._file_obj:
            try:
                self._file_obj.close()
            except Exception:
                pass
            self._file_obj = None
