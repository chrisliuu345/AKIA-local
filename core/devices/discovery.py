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


DEVICE_LIMIT = 8  # 单次扫描最多探测的串口数，防止多串口机器长时间阻塞 UI (W87)


def discover_devices(timeout: float = 0.5,
                     cancel_check=None) -> list[DeviceInfo]:
    """扫描串口并识别 QA-Tool 设备。

    timeout: 每个端口的读窗口（至少 4s，覆盖板子 boot 流）。
    cancel_check: 可选回调 `() -> bool`，返回 True 时立即停止扫描
                  （用于后台任务被取消的场景，W87）。
    """
    import serial.tools.list_ports
    from core.devices.protocol import encode_message, decode_message, MessageType

    found: list[DeviceInfo] = []
    ports = list(serial.tools.list_ports.comports())
    if len(ports) > DEVICE_LIMIT:
        logger.info("Discovery limited to %d of %d ports (W87)", DEVICE_LIMIT, len(ports))
        ports = ports[:DEVICE_LIMIT]
    # Opening a serial port resets an attached ESP32 (auto-reset circuit); the
    # board needs ~1-2s to boot and announces itself (HELLO) right after boot,
    # so the read window must cover the boot stream.
    window = max(timeout, 4.0)
    for info in ports:
        if cancel_check is not None and cancel_check():
            logger.info("Discovery cancelled by caller")
            break
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
                    if cancel_check is not None and cancel_check():
                        break
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


def probe_network_device(address: str, timeout: float = 3.0) -> DeviceInfo | None:
    """探测网络设备（JSON-lines TCP，如 MaixCAM）。

    address: "host:port"（如 "192.168.50.46:9000"）。
    连接后发送 HELLO，等待设备回复 HELLO（含 device_id/device_type/fw_version）。
    成功返回 DeviceInfo（port 字段即 address），失败返回 None。
    """
    import socket
    from core.devices.protocol import encode_message, decode_message, MessageType

    try:
        host, port_s = address.rsplit(":", 1)
        port = int(port_s)
    except ValueError:
        logger.debug("probe_network_device invalid address: %s", address)
        return None
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            hello = encode_message(MessageType.HELLO,
                                   device_id="pc_discovery",
                                   device_type="pc_scanner", fw_version="0.0")
            sock.sendall(hello)
            deadline = time.time() + timeout
            buf = b""
            while time.time() < deadline:
                data = sock.recv(4096)
                if not data:
                    break
                buf += data
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    msg = decode_message(line.decode("utf-8", errors="replace"))
                    if not msg:
                        continue
                    if msg.get("type") == MessageType.HELLO:
                        did = msg.get("device_id", "")
                        if not did:
                            return None
                        return DeviceInfo(
                            device_id=did,
                            device_type=msg.get("device_type", "unknown"),
                            port=address,
                            fw_version=msg.get("fw_version", ""),
                            description=f"network {host}",
                        )
    except Exception as e:
        logger.debug("probe_network_device skip %s: %s", address, e)
    return None