"""网络设备（MaixCAM TCP 接入）单元测试：TcpTransport / probe / monitor attach / 固件逻辑。

使用 127.0.0.1 环回 socket 模拟设备端，不依赖真实硬件。
"""
import json
import socket
import threading

import pytest

from core.devices.protocol import encode_message, MessageType
from core.devices.transport import TcpTransport, TransportError
from core.devices.discovery import probe_network_device
from core.devices.device import MaixcamVisionDevice
from core.devices.monitor import DeviceMonitor

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "firmware"))
import maixcam_server


class _FakeMaixcamServer:
    """环回 JSON-lines 服务端：hello/ping/command 应答，模拟 maixcam。"""

    DEVICE_ID = "test_cam"

    def __init__(self):
        self._srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._srv.bind(("127.0.0.1", 0))
        self.port = self._srv.getsockname()[1]
        self._srv.listen(2)
        self._stop = threading.Event()
        self.thread = threading.Thread(target=self._accept_loop, daemon=True)
        self.thread.start()

    def _accept_loop(self):
        self._srv.settimeout(0.2)
        while not self._stop.is_set():
            try:
                conn, _ = self._srv.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            threading.Thread(
                target=self._handle, args=(conn,), daemon=True).start()

    def _handle(self, conn):
        conn.settimeout(0.2)
        buf = b""
        try:
            while not self._stop.is_set():
                try:
                    data = conn.recv(4096)
                except socket.timeout:
                    continue
                if not data:
                    return
                buf += data
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    try:
                        msg = json.loads(line.decode("utf-8", "replace"))
                    except Exception:
                        continue
                    self._reply(conn, msg)
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _reply(self, conn, msg):
        mtype = msg.get("type")
        if mtype == "hello":
            reply = {"type": "hello", "device_id": self.DEVICE_ID,
                     "device_type": "maixcam", "fw_version": "9.9"}
        elif mtype == "ping":
            reply = {"type": "pong", "device_id": self.DEVICE_ID}
        elif mtype == "command":
            reply = {"type": "ack", "device_id": self.DEVICE_ID,
                     "command": msg.get("command", ""), "result": "ok"}
        else:
            return
        conn.sendall((json.dumps(reply) + "\n").encode("utf-8"))

    def close(self):
        self._stop.set()
        try:
            self._srv.close()
        except Exception:
            pass


@pytest.fixture()
def fake_server():
    srv = _FakeMaixcamServer()
    yield srv
    srv.close()


class TestTcpTransport:
    def test_open_send_receive_pong(self, fake_server):
        received = []
        got = threading.Event()
        t = TcpTransport(
            f"127.0.0.1:{fake_server.port}",
            on_message=lambda m: (received.append(m), got.set()),
        )
        t.open()
        assert t.is_open()
        assert t.port_name == f"127.0.0.1:{fake_server.port}"
        t.send(encode_message(MessageType.PING, device_id="pc_host"))
        assert got.wait(3), "no pong within 3s"
        assert received[0]["type"] == "pong"
        assert received[0]["device_id"] == _FakeMaixcamServer.DEVICE_ID
        t.close()
        assert not t.is_open()

    def test_receive_multiple_lines_one_packet(self, fake_server):
        received = []
        got2 = threading.Event()

        def on_msg(m):
            received.append(m)
            if len(received) >= 2:
                got2.set()

        t = TcpTransport(f"127.0.0.1:{fake_server.port}", on_message=on_msg)
        t.open()
        # hello 会触发服务端回复 hello；再发 ping 触发 pong，两行可能一次到达
        t.send(encode_message(MessageType.HELLO, device_id="pc_host"))
        t.send(encode_message(MessageType.PING, device_id="pc_host"))
        assert got2.wait(3)
        types = {m["type"] for m in received}
        assert "hello" in types and "pong" in types
        t.close()

    def test_send_not_open_raises(self):
        t = TcpTransport("127.0.0.1:1")
        with pytest.raises(TransportError):
            t.send(b"x")

    def test_connect_refused_raises(self):
        t = TcpTransport("127.0.0.1:1", connect_timeout=1)
        with pytest.raises(TransportError):
            t.open()

    def test_close_idempotent(self):
        t = TcpTransport("127.0.0.1:1", connect_timeout=1)
        t.close()
        t.close()


class TestProbeNetworkDevice:
    def test_probe_success(self, fake_server):
        info = probe_network_device(f"127.0.0.1:{fake_server.port}")
        assert info is not None
        assert info.device_id == _FakeMaixcamServer.DEVICE_ID
        assert info.device_type == "maixcam"
        assert info.fw_version == "9.9"
        assert info.port == f"127.0.0.1:{fake_server.port}"

    def test_probe_invalid_address(self):
        assert probe_network_device("no-port-here") is None
        assert probe_network_device("") is None

    def test_probe_refused(self):
        assert probe_network_device("127.0.0.1:1", timeout=1) is None


class TestMonitorNetworkAttach:
    def test_attach_uses_tcp_transport(self, fake_server):
        mon = DeviceMonitor()
        dev = MaixcamVisionDevice(
            "test_cam", port=f"127.0.0.1:{fake_server.port}")
        assert mon.attach(dev) is True
        assert isinstance(dev.transport, TcpTransport)
        assert dev.transport.is_open()
        mon.detach(dev)
        assert dev.transport is None

    def test_attach_recognition_routing(self, fake_server):
        events = []
        mon = DeviceMonitor(
            on_event=lambda did, ev, payload: events.append((did, ev)))
        dev = MaixcamVisionDevice(
            "test_cam", port=f"127.0.0.1:{fake_server.port}")
        assert mon.attach(dev) is True
        # 服务端对 attach 时的 HELLO 回 hello → on_event 转发
        deadline_hint = 20
        import time as _time
        ok = False
        for _ in range(deadline_hint):
            if any(ev == "hello" for _, ev in events):
                ok = True
                break
            _time.sleep(0.1)
        assert ok, f"hello event not seen: {events}"
        mon.detach(dev)

    def test_recognition_record_added(self, fake_server):
        mon = DeviceMonitor()
        dev = MaixcamVisionDevice(
            "test_cam", port=f"127.0.0.1:{fake_server.port}")
        assert mon.attach(dev) is True
        dev.add_recognition({"class": "demo", "confidence": 0.9})
        assert dev.record_count == 1
        rec = dev.get_recent_records(1)[0]
        assert rec["class"] == "demo"
        assert "_timestamp" in rec
        mon.detach(dev)


class TestMaixcamServerLogic:
    def test_handle_hello(self):
        state = {"stream_on": False}
        replies = maixcam_server.handle_message({"type": "hello"}, state)
        assert len(replies) == 1
        assert replies[0]["type"] == "hello"
        assert replies[0]["device_type"] == "maixcam"
        assert replies[0]["device_id"] == maixcam_server.DEVICE_ID

    def test_handle_ping(self):
        replies = maixcam_server.handle_message(
            {"type": "ping"}, {"stream_on": False})
        assert replies[0]["type"] == "pong"
        assert replies[0]["device_id"] == maixcam_server.DEVICE_ID

    def test_handle_command_echo(self):
        replies = maixcam_server.handle_message(
            {"type": "command", "command": "echo:hi"}, {"stream_on": False})
        assert replies[0]["type"] == "ack"
        assert replies[0]["command"] == "echo:hi"
        assert replies[0]["result"] == "ok"

    def test_handle_command_stream_toggle(self):
        state = {"stream_on": False}
        on = maixcam_server.handle_message(
            {"type": "command", "command": "stream:on"}, state)
        assert on[0]["result"] == "ok"
        assert state["stream_on"] is True
        off = maixcam_server.handle_message(
            {"type": "command", "command": "stream:off"}, state)
        assert off[0]["result"] == "ok"
        assert state["stream_on"] is False

    def test_handle_command_errors(self):
        state = {"stream_on": False}
        r1 = maixcam_server.handle_message(
            {"type": "command", "command": "bogus:1"}, state)
        assert r1[0]["result"].startswith("error: unknown command")
        r2 = maixcam_server.handle_message(
            {"type": "command", "command": "echo"}, state)
        assert r2[0]["result"].startswith("error: echo needs text")
        r3 = maixcam_server.handle_message(
            {"type": "command", "command": "stream:bad"}, state)
        assert r3[0]["result"].startswith("error: stream value")

    def test_handle_unknown_type_ignored(self):
        assert maixcam_server.handle_message(
            {"type": "whatever"}, {"stream_on": False}) == []


class TestMaixcamServerEndToEnd:
    """固件 handle_message 直接跑在环回服务端上（更接近实机）。"""

    def test_firmware_protocol_over_loopback(self, fake_server):
        # 用固件逻辑替换 fake server 的应答逻辑
        orig_reply = fake_server._reply
        states = {}

        def firmware_reply(conn, msg):
            state = states.setdefault(id(conn), {"stream_on": False})
            for reply in maixcam_server.handle_message(msg, state):
                conn.sendall(
                    (json.dumps(reply) + "\n").encode("utf-8"))

        fake_server._reply = firmware_reply
        try:
            info = probe_network_device(f"127.0.0.1:{fake_server.port}")
            assert info is not None
            assert info.device_type == "maixcam"
            assert info.device_id == maixcam_server.DEVICE_ID
        finally:
            fake_server._reply = orig_reply
