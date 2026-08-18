import json
import time
from enum import Enum

MAX_LINE_LEN = 65536


class DeviceState(Enum):
    DISCOVERED = "discovered"
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"


class MessageType:
    HELLO = "hello"
    ACK = "ack"
    READY = "ready"
    PING = "ping"
    PONG = "pong"
    DATA = "data"
    META = "meta"
    COMMAND = "command"
    RECOGNITION = "recognition"
    ERROR = "error"


class HandshakeStep(Enum):
    IDLE = "idle"
    WAITING_ACK = "waiting_ack"
    WAITING_READY = "waiting_ready"
    COMPLETE = "complete"
    FAILED = "failed"


def encode_message(msg_type: str, **kwargs) -> bytes:
    payload = {"type": msg_type, "timestamp": time.time(), **kwargs}
    line = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return (line + "\n").encode("utf-8")


def decode_message(line: str) -> dict | None:
    if not line or len(line) > MAX_LINE_LEN:
        return None
    try:
        obj = json.loads(line)
        if not isinstance(obj, dict) or "type" not in obj:
            return None
        return obj
    except (json.JSONDecodeError, ValueError):
        return None


class HandshakeProtocol:
    def __init__(self, device_id: str, device_type: str, fw_version: str = "1.0.0"):
        self.device_id = device_id
        self.device_type = device_type
        self.fw_version = fw_version
        self.step = HandshakeStep.IDLE

    def reset(self):
        self.step = HandshakeStep.IDLE

    def build_hello(self) -> bytes:
        self.step = HandshakeStep.WAITING_ACK
        return encode_message(
            MessageType.HELLO,
            device_id=self.device_id,
            device_type=self.device_type,
            fw_version=self.fw_version,
        )

    def build_ack(self, device_id: str) -> bytes:
        return encode_message(MessageType.ACK, device_id=device_id)

    def build_ready(self) -> bytes:
        self.step = HandshakeStep.COMPLETE
        return encode_message(MessageType.READY, device_id=self.device_id)

    def process_message(self, msg: dict) -> bytes | None:
        mt = msg.get("type")
        if mt == MessageType.HELLO and self.step == HandshakeStep.IDLE:
            self.step = HandshakeStep.WAITING_READY
            return self.build_ack(msg.get("device_id", ""))
        if mt == MessageType.ACK and self.step == HandshakeStep.WAITING_ACK:
            return self.build_ready()
        if mt == MessageType.READY and self.step == HandshakeStep.WAITING_READY:
            self.step = HandshakeStep.COMPLETE
        return None


class Heartbeat:
    def __init__(self, interval: float = 3.0, timeout: float = 9.0):
        self.interval = interval
        self.timeout = timeout
        self._last_recv = 0.0
        self._last_sent = 0.0

    def mark_received(self):
        self._last_recv = time.time()

    def should_send_ping(self) -> bool:
        return time.time() - self._last_sent >= self.interval

    def sent_ping(self):
        self._last_sent = time.time()

    def is_timed_out(self) -> bool:
        return self._last_recv > 0 and time.time() - self._last_recv > self.timeout