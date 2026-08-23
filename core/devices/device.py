import time
from collections import deque

from core.devices.protocol import DeviceState
from core.devices.transport import Transport


class Device:
    def __init__(self, device_id: str, device_type: str, port: str = "",
                 baudrate: int = 115200, fw_version: str = ""):
        self.device_id = device_id
        self.device_type = device_type
        self.port = port
        self.baudrate = baudrate
        self.fw_version = fw_version
        self.custom_name = ""
        self.state = DeviceState.DISCOVERED
        self._last_heartbeat = 0.0
        self.monitoring = True
        self.transport: Transport | None = None

    @property
    def display_name(self) -> str:
        return self.custom_name or self.device_id

    @property
    def last_heartbeat(self) -> float:
        return self._last_heartbeat

    def mark_heartbeat(self):
        self._last_heartbeat = time.time()

    def to_dict(self) -> dict:
        return {
            "device_id": self.device_id,
            "device_type": self.device_type,
            "port": self.port,
            "baudrate": self.baudrate,
            "fw_version": self.fw_version,
            "custom_name": self.custom_name,
            "state": self.state.value,
        }


class Esp32InputDevice(Device):
    def __init__(self, device_id: str, port: str = "", baudrate: int = 115200,
                 fw_version: str = "", max_samples: int = 1000):
        super().__init__(device_id, "esp32_in", port, baudrate, fw_version)
        self._samples: deque[list[float]] = deque(maxlen=max_samples)
        self._latest_values: list[float] = []
        self._channels: list[dict] = []

    def set_channels(self, channels: list[dict]) -> None:
        self._channels = [dict(c) for c in channels]

    @property
    def channels(self) -> list[dict]:
        return list(self._channels)

    def channel_labels(self) -> list[str]:
        n = max(len(self._latest_values), len(self._channels))
        if self._channels:
            labels = []
            for i, c in enumerate(self._channels):
                unit = c.get("unit", "")
                label = c.get("name", f"CH{i}")
                if unit:
                    label = f"{label} ({unit})"
                labels.append(label)
            for i in range(len(self._channels), n):
                labels.append(f"CH{i}")
            return labels
        return [f"CH{i}" for i in range(n)]

    def add_data(self, values: list[float]) -> None:
        self._latest_values = list(values)
        self._samples.append(list(values))

    def get_recent_data(self, n: int = 50) -> list[list[float]]:
        return [list(s) for s in list(self._samples)[-n:]]

    @property
    def data_count(self) -> int:
        return len(self._samples)

    @property
    def latest_values(self) -> list[float]:
        return list(self._latest_values)


class Esp32OutputDevice(Device):
    def __init__(self, device_id: str, port: str = "", baudrate: int = 115200,
                 fw_version: str = ""):
        super().__init__(device_id, "esp32_out", port, baudrate, fw_version)
        self._command_history: deque[tuple[str, str]] = deque(maxlen=100)
        self._ack_history: deque[dict] = deque(maxlen=100)
        self._last_ack: dict | None = None

    def send_command(self, command: str) -> None:
        from core.devices.protocol import encode_message, MessageType
        if not self.transport or not self.transport.is_open():
            raise RuntimeError(f"Device {self.device_id} transport not open")
        payload = encode_message(MessageType.COMMAND, command=command,
                                 device_id=self.device_id)
        self.transport.send(payload)
        self._command_history.appendleft((time.time(), command))
        self._last_ack = None

    def record_ack(self, msg: dict) -> None:
        self._last_ack = dict(msg)
        self._ack_history.appendleft(dict(msg))

    @property
    def command_history(self) -> list[tuple[str, str]]:
        return list(self._command_history)

    @property
    def ack_history(self) -> list[dict]:
        return list(self._ack_history)

    @property
    def last_ack(self) -> dict | None:
        return self._last_ack


class MaixcamVisionDevice(Device):
    def __init__(self, device_id: str, port: str = "", baudrate: int = 115200,
                 fw_version: str = ""):
        super().__init__(device_id, "maixcam", port, baudrate, fw_version)
        self._records: deque[dict] = deque(maxlen=500)

    def add_recognition(self, record: dict) -> None:
        record["_timestamp"] = time.time()
        self._records.appendleft(record)

    def get_recent_records(self, n: int = 20) -> list[dict]:
        return list(self._records)[:n]

    @property
    def record_count(self) -> int:
        return len(self._records)