import contextlib
import abc
import logging
import socket
import threading
import time
from collections.abc import Callable

logger = logging.getLogger(__name__)


class TransportError(Exception):
    pass


class Transport(abc.ABC):
    @abc.abstractmethod
    def open(self) -> None: ...

    @abc.abstractmethod
    def close(self) -> None: ...

    @abc.abstractmethod
    def send(self, data: bytes) -> None: ...

    @abc.abstractmethod
    def is_open(self) -> bool: ...

    @property
    @abc.abstractmethod
    def port_name(self) -> str: ...


class SerialTransport(Transport):
    def __init__(self, port: str, baudrate: int = 115200,
                 on_message: Callable[[dict], None] | None = None,
                 on_error: Callable[[Exception], None] | None = None):
        self._port = port
        self._baudrate = baudrate
        self.on_message = on_message
        self.on_error = on_error
        self._serial = None
        self._read_thread = None
        self._stop_event = threading.Event()
        self._buf = b""

    def open(self) -> None:
        import serial
        try:
            self._serial = serial.Serial(
                port=self._port,
                baudrate=self._baudrate,
                timeout=0.5,
            )
            self._stop_event.clear()
            self._read_thread = threading.Thread(
                target=self._read_loop, daemon=True, name=f"serial-{self._port}"
            )
            self._read_thread.start()
            logger.info("SerialTransport opened %s @ %d", self._port, self._baudrate)
        except Exception as e:
            raise TransportError(f"Failed to open {self._port}: {e}") from e

    def close(self) -> None:
        self._stop_event.set()
        if self._read_thread and self._read_thread.is_alive():
            self._read_thread.join(timeout=3)
        if self._serial and self._serial.is_open:
            with contextlib.suppress(Exception):
                self._serial.close()
        self._serial = None
        logger.info("SerialTransport closed %s", self._port)

    def send(self, data: bytes) -> None:
        if not self._serial or not self._serial.is_open:
            raise TransportError("Serial port not open")
        try:
            self._serial.write(data)
        except Exception as e:
            raise TransportError(f"Write error on {self._port}: {e}") from e

    def is_open(self) -> bool:
        return self._serial is not None and self._serial.is_open

    def reset_board(self) -> None:
        """Hard-reset the attached board into normal boot mode.

        Wire mapping observed on the QA-Tool ESP32 DevKit:
        RTS = EN (reset), DTR = GPIO0 (BOOT).
        Hold reset (RTS True) with GPIO0 high (DTR False), then release.
        """
        if not self._serial or not self._serial.is_open:
            raise TransportError("Serial port not open")
        try:
            self._serial.setDTR(False)
            self._serial.setRTS(True)
            time.sleep(0.3)
            self._serial.setRTS(False)
            time.sleep(0.2)
            self._serial.reset_input_buffer()
        except Exception as e:
            raise TransportError(f"Reset board on {self._port} failed: {e}") from e

    @property
    def port_name(self) -> str:
        return self._port

    def _read_loop(self):
        from core.devices.protocol import MAX_LINE_LEN, decode_message
        while not self._stop_event.is_set():
            try:
                if not self._serial or not self._serial.is_open:
                    break
                data = self._serial.read(4096)
                if not data:
                    continue
                self._buf += data
                if len(self._buf) > MAX_LINE_LEN:
                    logger.warning(
                        "read buffer exceeded %d bytes, dropping %d bytes",
                        MAX_LINE_LEN, len(self._buf) - MAX_LINE_LEN,
                    )
                    self._buf = self._buf[-MAX_LINE_LEN:]
                while b"\n" in self._buf:
                    line, self._buf = self._buf.split(b"\n", 1)
                    try:
                        text = line.decode("utf-8", errors="replace")
                    except Exception:
                        continue
                    msg = decode_message(text)
                    if msg and self.on_message:
                        try:
                            self.on_message(msg)
                        except Exception as e:
                            logger.exception("on_message callback error: %s", e)
            except Exception as e:
                if self.on_error:
                    self.on_error(e)
                break


class TcpTransport(Transport):
    """JSON-lines transport over TCP for network devices (e.g. MaixCAM).

    address: "host:port" (e.g. "192.168.50.46:9000").  Same message routing
    contract as SerialTransport (on_message / on_error callbacks).
    """

    def __init__(self, address: str,
                 on_message: Callable[[dict], None] | None = None,
                 on_error: Callable[[Exception], None] | None = None,
                 connect_timeout: float = 3.0):
        self._address = address
        self.on_message = on_message
        self.on_error = on_error
        self._connect_timeout = connect_timeout
        self._sock: socket.socket | None = None
        self._read_thread = None
        self._stop_event = threading.Event()
        self._buf = b""

    def open(self) -> None:
        try:
            host, port_s = self._address.rsplit(":", 1)
            port = int(port_s)
            self._sock = socket.create_connection(
                (host, port), timeout=self._connect_timeout)
            self._sock.settimeout(0.5)
        except Exception as e:
            self._sock = None
            raise TransportError(f"Failed to connect {self._address}: {e}") from e
        self._stop_event.clear()
        self._read_thread = threading.Thread(
            target=self._read_loop, daemon=True, name=f"tcp-{self._address}"
        )
        self._read_thread.start()
        logger.info("TcpTransport opened %s", self._address)

    def close(self) -> None:
        self._stop_event.set()
        if self._read_thread and self._read_thread.is_alive():
            self._read_thread.join(timeout=3)
        if self._sock:
            with contextlib.suppress(Exception):
                self._sock.close()
        self._sock = None
        logger.info("TcpTransport closed %s", self._address)

    def send(self, data: bytes) -> None:
        if not self._sock:
            raise TransportError("TCP socket not open")
        try:
            self._sock.sendall(data)
        except Exception as e:
            raise TransportError(f"Write error on {self._address}: {e}") from e

    def is_open(self) -> bool:
        return self._sock is not None

    @property
    def port_name(self) -> str:
        return self._address

    def _read_loop(self):
        from core.devices.protocol import MAX_LINE_LEN, decode_message
        while not self._stop_event.is_set():
            try:
                if not self._sock:
                    break
                data = self._sock.recv(4096)
                if not data:
                    if self.on_error:
                        self.on_error(TransportError("Connection closed by peer"))
                    break
                self._buf += data
                if len(self._buf) > MAX_LINE_LEN:
                    logger.warning(
                        "read buffer exceeded %d bytes, dropping %d bytes",
                        MAX_LINE_LEN, len(self._buf) - MAX_LINE_LEN,
                    )
                    self._buf = self._buf[-MAX_LINE_LEN:]
                while b"\n" in self._buf:
                    line, self._buf = self._buf.split(b"\n", 1)
                    try:
                        text = line.decode("utf-8", errors="replace")
                    except Exception:
                        continue
                    msg = decode_message(text)
                    if msg and self.on_message:
                        try:
                            self.on_message(msg)
                        except Exception as e:
                            logger.exception("on_message callback error: %s", e)
            except TimeoutError:
                continue
            except OSError as e:
                if self._stop_event.is_set():
                    break
                if self.on_error:
                    self.on_error(e)
                break