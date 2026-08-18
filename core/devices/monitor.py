import logging
import threading
import time
from collections.abc import Callable

from core.devices.device import Device, Esp32InputDevice, MaixcamVisionDevice
from core.devices.protocol import MessageType, Heartbeat, encode_message
from core.devices.transport import SerialTransport, TransportError

logger = logging.getLogger(__name__)

PING_INTERVAL = 3.0
PING_TIMEOUT = 9.0


class DeviceMonitor:
    """Opens a persistent SerialTransport per device and routes protocol messages.

    Attached devices get their transport field set and receive message routing:
      DATA  -> Esp32InputDevice.add_data
      META  -> Esp32InputDevice.set_channels
      PING  -> PONG reply
      HELLO/RECOGNITION -> forwarded via on_event (device_tab decides state)
    A single background ticker sends PING heartbeats to all attached devices.
    """

    def __init__(self, on_event: Callable[[str, str, dict], None] | None = None):
        self._on_event = on_event
        self._attached: dict[str, Device] = {}
        self._heartbeats: dict[str, Heartbeat] = {}
        self._ticker = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        if self._ticker and self._ticker.is_alive():
            return
        self._stop_event.clear()
        self._ticker = threading.Thread(
            target=self._tick_loop, daemon=True, name="device-monitor"
        )
        self._ticker.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._ticker and self._ticker.is_alive():
            self._ticker.join(timeout=3)
        for device in list(self._attached.values()):
            self.detach(device)

    def attach(self, device: Device) -> bool:
        if device.transport and device.transport.is_open():
            self._attached[device.device_id] = device
            self._heartbeats[device.device_id] = Heartbeat(PING_INTERVAL, PING_TIMEOUT)
            return True
        transport = SerialTransport(
            device.port, device.baudrate,
            on_message=self._make_handler(device),
            on_error=self._make_error_handler(device),
        )
        try:
            transport.open()
        except TransportError as e:
            logger.warning("DeviceMonitor attach failed for %s: %s", device.device_id, e)
            return False
        try:
            transport.reset_board()
        except TransportError:
            pass
        device.transport = transport
        self._attached[device.device_id] = device
        self._heartbeats[device.device_id] = Heartbeat(PING_INTERVAL, PING_TIMEOUT)
        try:
            transport.send(encode_message(
                MessageType.HELLO,
                device_id="pc_host", device_type="pc_host", fw_version="0.0",
            ))
        except TransportError:
            pass
        return True

    def detach(self, device: Device) -> None:
        device_id = device.device_id
        self._attached.pop(device_id, None)
        self._heartbeats.pop(device_id, None)
        if device.transport:
            try:
                device.transport.close()
            except Exception:
                pass
            device.transport = None

    def _make_handler(self, device: Device):
        def handler(msg: dict):
            mt = msg.get("type")
            device.mark_heartbeat()
            hb = self._heartbeats.get(device.device_id)
            if hb:
                hb.mark_received()
            if mt == MessageType.DATA:
                if isinstance(device, Esp32InputDevice):
                    device.add_data(msg.get("values", []))
            elif mt == MessageType.META:
                if isinstance(device, Esp32InputDevice):
                    device.set_channels(msg.get("channels", []))
            elif mt == MessageType.PING:
                if device.transport and device.transport.is_open():
                    try:
                        device.transport.send(encode_message(
                            MessageType.PONG, device_id=device.device_id))
                    except TransportError:
                        pass
            elif mt == MessageType.RECOGNITION:
                if isinstance(device, MaixcamVisionDevice):
                    device.add_recognition(msg)
            if self._on_event:
                try:
                    self._on_event(device.device_id, mt or "unknown", msg)
                except Exception:
                    logger.exception("DeviceMonitor on_event callback failed")
        return handler

    def _make_error_handler(self, device: Device):
        def on_error(exc: Exception):
            logger.warning("DeviceMonitor transport error on %s: %s", device.device_id, exc)
            if self._on_event:
                try:
                    self._on_event(device.device_id, "error", {"error": str(exc)})
                except Exception:
                    pass
        return on_error

    def _tick_loop(self):
        while not self._stop_event.is_set():
            now = time.time()
            for device in list(self._attached.values()):
                hb = self._heartbeats.get(device.device_id)
                if not hb or not device.transport or not device.transport.is_open():
                    continue
                if hb.is_timed_out() and self._on_event:
                    try:
                        self._on_event(device.device_id, "timeout", {})
                    except Exception:
                        pass
                    continue
                if hb.should_send_ping():
                    try:
                        device.transport.send(encode_message(
                            MessageType.PING, device_id="pc_host"))
                        hb.sent_ping()
                    except TransportError:
                        pass
            for _ in range(10):
                if self._stop_event.is_set():
                    return
                time.sleep(0.1)
