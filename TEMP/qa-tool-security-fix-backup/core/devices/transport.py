import abc
import logging
import threading
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
            try:
                self._serial.close()
            except Exception:
                pass
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

    @property
    def port_name(self) -> str:
        return self._port

    def _read_loop(self):
        from core.devices.protocol import decode_message
        while not self._stop_event.is_set():
            try:
                if not self._serial or not self._serial.is_open:
                    break
                data = self._serial.read(4096)
                if not data:
                    continue
                self._buf += data
                while b"\n" in self._buf:
                    line, self._buf = self._buf.split(b"\n", 1)
                    try:
                        text = line.decode("utf-8", errors="replace")
                    except Exception:
                        continue
                    msg = decode_message(text)
                    if msg and self.on_message:
                        self.on_message(msg)
            except Exception as e:
                if self.on_error:
                    self.on_error(e)
                break