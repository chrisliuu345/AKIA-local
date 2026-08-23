"""设备通信内核单元测试 — mock 串口回环"""
import json
import time
import pytest
from unittest.mock import patch, MagicMock

from core.devices.protocol import (
    encode_message, decode_message, MessageType, HandshakeProtocol, HandshakeStep, Heartbeat,
)
from core.devices.transport import SerialTransport, TransportError
from core.devices.discovery import discover_devices
from core.devices.registry import DeviceRegistry, DeviceState
from core.devices.device import Device, Esp32InputDevice, Esp32OutputDevice, MaixcamVisionDevice


# ── Protocol ──

class TestProtocol:
    def test_encode_decode_roundtrip(self):
        raw = encode_message(MessageType.HELLO, device_id="esp1", device_type="esp32_in")
        line = raw.decode("utf-8").strip()
        msg = decode_message(line)
        assert msg["type"] == "hello"
        assert msg["device_id"] == "esp1"
        assert msg["device_type"] == "esp32_in"

    def test_decode_invalid_json(self):
        assert decode_message("not json") is None

    def test_decode_empty(self):
        assert decode_message("") is None

    def test_decode_too_long(self):
        assert decode_message("x" * 70000) is None

    def test_handshake_full_flow(self):
        hs = HandshakeProtocol("pc", "pc_scanner")
        assert hs.step == HandshakeStep.IDLE
        hello = hs.build_hello()
        assert hs.step == HandshakeStep.WAITING_ACK
        msg = decode_message(hello.decode("utf-8").strip())
        assert msg["type"] == "hello"
        # Simulate device parsing our hello
        device_hs = HandshakeProtocol("esp1", "esp32_in")
        ack = device_hs.process_message(msg)
        assert ack is not None
        ack_msg = decode_message(ack.decode("utf-8").strip())
        assert ack_msg["type"] == "ack"
        # PC receives ack
        resp = hs.process_message(ack_msg)
        assert resp is not None
        ready_msg = decode_message(resp.decode("utf-8").strip())
        assert ready_msg["type"] == "ready"
        assert hs.step == HandshakeStep.COMPLETE

    def test_handshake_device_side(self):
        device_hs = HandshakeProtocol("esp1", "esp32_in")
        hello = device_hs.build_hello()
        hello_msg = decode_message(hello.decode("utf-8").strip())
        # PC receives hello
        pc_hs = HandshakeProtocol("pc", "pc_scanner")
        ack = pc_hs.process_message(hello_msg)
        assert ack is not None
        ack_msg = decode_message(ack.decode("utf-8").strip())
        assert ack_msg["type"] == "ack"
        # Device receives ack
        ready = device_hs.process_message(ack_msg)
        assert ready is not None
        assert device_hs.step == HandshakeStep.COMPLETE

    def test_heartbeat_timeout(self):
        hb = Heartbeat(interval=1.0, timeout=3.0)
        assert not hb.is_timed_out()
        hb.mark_received()
        assert not hb.is_timed_out()
        # Simulate time passing
        original = time.time
        try:
            time.time = lambda: original() + 10
            assert hb.is_timed_out()
        finally:
            time.time = original


# ── Transport ──

class TestSerialTransport:
    @patch("serial.Serial")
    def test_open_close(self, mock_serial_cls):
        mock_inst = MagicMock()
        mock_inst.is_open = True
        mock_serial_cls.return_value = mock_inst

        transport = SerialTransport("COM3", on_message=lambda m: None)
        transport.open()
        assert transport.is_open()
        assert transport.port_name == "COM3"
        mock_serial_cls.assert_called_with(port="COM3", baudrate=115200, timeout=0.5)

        transport.close()
        mock_inst.close.assert_called_once()

    @patch("serial.Serial")
    def test_send(self, mock_serial_cls):
        mock_inst = MagicMock()
        mock_inst.is_open = True
        mock_serial_cls.return_value = mock_inst

        transport = SerialTransport("COM3")
        transport.open()
        data = b"test\n"
        transport.send(data)
        mock_inst.write.assert_called_with(data)

    @patch("serial.Serial")
    def test_send_fails_when_closed(self, mock_serial_cls):
        transport = SerialTransport("COM3")
        with pytest.raises(TransportError):
            transport.send(b"data")


# ── Discovery ──

class TestDiscovery:
    @patch("serial.tools.list_ports.comports")
    def test_discover_no_ports(self, mock_comports):
        mock_comports.return_value = []
        result = discover_devices(timeout=0.1)
        assert result == []

    @patch("serial.tools.list_ports.comports")
    @patch("serial.Serial")
    def test_discover_handshake(self, mock_serial_cls, mock_comports):
        mock_port = MagicMock()
        mock_port.device = "COM3"
        mock_port.description = "USB Serial"
        mock_comports.return_value = [mock_port]

        hello_resp = encode_message(MessageType.HELLO, device_id="esp1",
                                     device_type="esp32_in", fw_version="1.0")
        mock_inst = MagicMock()
        mock_inst.read.return_value = hello_resp
        mock_inst.__enter__.return_value = mock_inst
        mock_serial_cls.return_value = mock_inst

        result = discover_devices(timeout=0.1)
        assert len(result) == 1
        assert result[0].device_id == "esp1"
        assert result[0].device_type == "esp32_in"
        assert result[0].port == "COM3"


# ── Registry ──

class TestRegistry:
    def test_add_and_state(self):
        reg = DeviceRegistry()
        d = Device("test1", "esp32_in", "COM3")
        reg.add(d)
        assert reg.get("test1") is d
        assert d.state == DeviceState.DISCOVERED

    def test_state_transitions(self):
        events = []
        reg = DeviceRegistry(on_device_changed=lambda did, s: events.append((did, s)))
        d = Device("e1", "esp32_in", "COM3")
        reg.add(d)
        reg.set_online("e1")
        assert d.state == DeviceState.ONLINE
        reg.set_offline("e1")
        assert d.state == DeviceState.OFFLINE
        reg.set_error("e1")
        assert d.state == DeviceState.ERROR
        assert len(events) == 4

    def test_rename(self):
        reg = DeviceRegistry()
        d = Device("e1", "esp32_in", "COM3")
        reg.add(d)
        reg.rename("e1", "数据采集器")
        assert d.custom_name == "数据采集器"
        assert d.display_name == "数据采集器"

    def test_stop_all(self):
        reg = DeviceRegistry()
        d = Device("e1", "esp32_in", "COM3")
        reg.add(d)
        reg.stop_all()
        assert len(reg.devices) == 0


# ── Device models ──

class TestDeviceModels:
    def test_esp32_input_data(self):
        dev = Esp32InputDevice("in1", "COM3")
        dev.add_data([1.0, 2.0, 3.0])
        assert dev.data_count == 3
        assert dev.get_recent_data(2) == [2.0, 3.0]
        assert dev.device_type == "esp32_in"

    def test_esp32_output_command(self):
        dev = Esp32OutputDevice("out1", "COM4")
        assert dev.command_history == []

    def test_maixcam_records(self):
        dev = MaixcamVisionDevice("cam1")
        dev.add_recognition({"class": "person", "confidence": 0.95})
        dev.add_recognition({"class": "phone", "confidence": 0.87})
        assert dev.record_count == 2
        recent = dev.get_recent_records(1)
        assert len(recent) == 1
        assert recent[0]["class"] == "phone"

    def test_device_display_name(self):
        d = Device("raw_id", "esp32_in")
        assert d.display_name == "raw_id"
        d.custom_name = "我的设备"
        assert d.display_name == "我的设备"

    def test_device_to_dict(self):
        d = Device("e1", "esp32_in", "COM3", 115200, "1.0")
        data = d.to_dict()
        assert data["device_id"] == "e1"
        assert data["device_type"] == "esp32_in"
        assert data["port"] == "COM3"
        assert data["state"] == "discovered"