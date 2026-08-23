import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class DeviceInfo:
    device_id: str
    device_type: str
    port: str
    baudrate: int = 115200
    fw_version: str = ""
    description: str = ""


def discover_devices(timeout: float = 0.5) -> list[DeviceInfo]:
    import serial.tools.list_ports
    from core.devices.protocol import encode_message, decode_message, MessageType

    found: list[DeviceInfo] = []
    ports = list(serial.tools.list_ports.comports())
    for info in ports:
        port = info.device
        try:
            import serial
            with serial.Serial(port=port, baudrate=115200, timeout=timeout) as ser:
                hello = encode_message(MessageType.HELLO, device_id="pc_discovery",
                                       device_type="pc_scanner", fw_version="0.0")
                ser.write(hello)
                resp = ser.read(4096)
                if not resp:
                    continue
                for raw_line in resp.split(b"\n"):
                    if not raw_line.strip():
                        continue
                    try:
                        line = raw_line.decode("utf-8", errors="replace")
                    except Exception:
                        continue
                    msg = decode_message(line)
                    if not msg:
                        continue
                    if msg.get("type") == MessageType.HELLO:
                        did = msg.get("device_id", "")
                        dtype = msg.get("device_type", "unknown")
                        fw = msg.get("fw_version", "")
                        known = {d.device_id for d in found}
                        if did and did not in known:
                            found.append(DeviceInfo(
                                device_id=did, device_type=dtype,
                                port=port, fw_version=fw,
                                description=info.description,
                            ))
        except Exception as e:
            logger.debug("Discovery skip %s: %s", port, e)
    return found