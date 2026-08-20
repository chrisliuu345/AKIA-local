import json
import logging
import os
import tempfile
import threading
from collections.abc import Callable

from core.devices.device import Device
from core.devices.protocol import DeviceState

logger = logging.getLogger(__name__)

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "user_config.json")


class DeviceRegistry:
    def __init__(self, on_device_changed: Callable[[str, DeviceState], None] | None = None):
        self._devices: dict[str, Device] = {}
        self._on_device_changed = on_device_changed
        self._lock = threading.Lock()

    @property
    def devices(self) -> dict[str, Device]:
        return dict(self._devices)

    def get(self, device_id: str) -> Device | None:
        return self._devices.get(device_id)

    def add(self, device: Device) -> None:
        self._devices[device.device_id] = device
        self._set_state(device.device_id, DeviceState.DISCOVERED)

    def remove(self, device_id: str) -> None:
        self._devices.pop(device_id, None)

    def set_online(self, device_id: str) -> None:
        self._set_state(device_id, DeviceState.ONLINE)

    def set_offline(self, device_id: str) -> None:
        self._set_state(device_id, DeviceState.OFFLINE)

    def set_error(self, device_id: str) -> None:
        self._set_state(device_id, DeviceState.ERROR)

    def update_heartbeat(self, device_id: str) -> None:
        dev = self._devices.get(device_id)
        if dev:
            dev.mark_heartbeat()

    def rename(self, device_id: str, new_name: str) -> None:
        dev = self._devices.get(device_id)
        if dev:
            dev.custom_name = new_name

    def stop_all(self) -> None:
        for dev in self._devices.values():
            if dev.transport:
                try:
                    dev.transport.close()
                except Exception:
                    pass
        self._devices.clear()

    def load_persistent(self) -> list[dict]:
        with self._lock:
            try:
                if os.path.exists(_CONFIG_PATH):
                    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                    return cfg.get("devices", [])
            except Exception:
                pass
            return []

    def save_persistent(self) -> None:
        with self._lock:
            devices_data = []
            for dev in self._devices.values():
                devices_data.append({
                    "device_id": dev.device_id,
                    "device_type": dev.device_type,
                    "custom_name": dev.custom_name,
                    "port": dev.port,
                    "baudrate": dev.baudrate,
                })
            try:
                cfg = {}
                if os.path.exists(_CONFIG_PATH):
                    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                cfg["devices"] = devices_data
                # 原子写：先写临时文件再 os.replace，避免多实例并发读改写丢数据 (W89)
                dir_name = os.path.dirname(_CONFIG_PATH) or "."
                os.makedirs(dir_name, exist_ok=True)
                fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
                try:
                    with os.fdopen(fd, "w", encoding="utf-8") as f:
                        json.dump(cfg, f, indent=2, ensure_ascii=False)
                    os.replace(tmp_path, _CONFIG_PATH)
                finally:
                    if os.path.exists(tmp_path):
                        try:
                            os.remove(tmp_path)
                        except OSError:
                            pass
            except Exception as e:
                logger.warning("Failed to save device config: %s", e)

    def _set_state(self, device_id: str, state: DeviceState) -> None:
        dev = self._devices.get(device_id)
        if dev:
            dev.state = state
            if self._on_device_changed:
                self._on_device_changed(device_id, state)