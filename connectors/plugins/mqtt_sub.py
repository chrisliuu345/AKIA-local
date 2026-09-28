"""MQTT 订阅连接器 — ESP32 / Arduino Opta / RPi 统一接入。

config:
    broker: str   必填 (如 192.168.1.10)
    port: int     默认 1883
    topic: str    订阅主题 (如 plant/machine1/data)
    channels: [str]   解析载荷键名; 缺失时整条载荷取数值
"""
import contextlib
import json

from connectors.base import ConnectorBase

PLUGIN = {"name": "mqtt_sub", "category": "iot",
          "description": "MQTT 订阅 — ESP32/Arduino Opta/树莓派统一接入"}

try:
    import paho.mqtt.client as mqtt
    AVAILABLE = True
except ImportError:
    AVAILABLE = False


class Connector(ConnectorBase):
    def __init__(self, config: dict):
        super().__init__(config.get("name", "iot-01"), config)
        self._latest: dict[str, object] = {}
        self._client = None

    def open(self) -> None:
        if not AVAILABLE:
            raise ImportError("需要安装 paho-mqtt")
        self._client = mqtt.Client(client_id=self.name)
        self._client.on_message = self._on_message
        self._client.connect(self.config["broker"],
                             port=int(self.config.get("port", 1883)), keepalive=30)
        self._client.loop_start()
        self._client.subscribe(self.config["topic"])

    def _on_message(self, _client, _userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            self._latest["value"] = msg.payload.decode("utf-8", errors="replace")
            return
        if isinstance(payload, dict):
            self._latest.update(payload)
        else:
            self._latest["value"] = payload

    def poll(self) -> list:
        channels = self.config.get("channels", []) or list(self._latest)
        samples = []
        for ch in channels:
            if ch not in self._latest:
                continue
            with contextlib.suppress(TypeError, ValueError):
                samples.append(self._sample(ch, float(self._latest[ch])))
        return samples

    def close(self) -> None:
        if self._client:
            self._client.loop_stop()
            with contextlib.suppress(Exception):
                self._client.disconnect()
            self._client = None
