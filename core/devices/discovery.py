import logging
import time
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
    # Opening a serial port resets an attached ESP32 (auto-reset circuit); the
    # board needs ~1-2s to boot and announces itself (HELLO) right after boot,
    # so the read window must cover the boot stream.
    window = max(timeout, 4.0)
    for info in ports:
        port = info.device
        try:
            import serial
            with serial.Serial(port=port, baudrate=115200, timeout=0.2) as ser:
                # ESP32 boards with an auto-reset circuit reboot on serial line
                # transitions.  Pulse the board so it always boots normally
                # (RTS=EN reset, DTR=GPIO0; mapping seen on the QA-Tool board).
                try:
                    ser.setDTR(False)
                    ser.setRTS(True)
                    time.sleep(0.3)
                    ser.setRTS(False)
                    time.sleep(0.2)
                    ser.reset_input_buffer()
                except Exception:
                    pass
                hello = encode_message(MessageType.HELLO, device_id="pc_discovery",
                                       device_type="pc_scanner", fw_version="0.0")
                ser.write(hello)
                deadline = time.time() + window
                found_here = False
                while time.time() < deadline:
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
                                found_here = True
                                break
                    if found_here:
                        break
        except Exception as e:
            logger.debug("Discovery skip %s: %s", port, e)
    return found