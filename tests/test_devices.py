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
from core.devices.monitor import DeviceMonitor
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

    def test_meta_roundtrip(self):
        raw = encode_message(MessageType.META, device_id="esp1",
                             channels=[{"name": "t", "unit": "C", "kind": "ds18b20"}])
        msg = decode_message(raw.decode("utf-8").strip())
        assert msg["type"] == "meta"
        assert msg["channels"][0]["name"] == "t"

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

    @patch("serial.Serial")
    def test_read_loop_buf_bounded(self, mock_serial_cls):
        """C04: 无换行噪声流时 _buf 不超过 MAX_LINE_LEN"""
        from core.devices.protocol import MAX_LINE_LEN
        mock_inst = MagicMock()
        mock_inst.is_open = True
        mock_inst.read.side_effect = [b"A" * 100000, TransportError("stop")]
        mock_serial_cls.return_value = mock_inst

        errors = []
        transport = SerialTransport("COM3", on_message=lambda m: None, on_error=errors.append)
        transport._serial = mock_inst
        transport._read_loop()

        assert len(transport._buf) <= MAX_LINE_LEN
        assert len(errors) == 1

    @patch("serial.Serial")
    def test_read_loop_recovers_after_overflow(self, mock_serial_cls):
        """C04: 溢出截断丢弃坏数据，后续合法消息仍能解析"""
        from core.devices.protocol import MAX_LINE_LEN
        mock_inst = MagicMock()
        mock_inst.is_open = True
        noise_line = b"A" * (MAX_LINE_LEN + 500) + b"\n"
        line = b'{"type":"data","values":[1.0]}\n'
        mock_inst.read.side_effect = [noise_line, line, TransportError("stop")]
        mock_serial_cls.return_value = mock_inst

        messages = []
        transport = SerialTransport("COM3", on_message=messages.append, on_error=lambda e: None)
        transport._serial = mock_inst
        transport._read_loop()

        assert len(messages) == 1
        assert messages[0]["values"] == [1.0]

    @patch("serial.Serial")
    def test_read_loop_callback_error_does_not_kill_thread(self, mock_serial_cls):
        """C05: on_message 回调异常只记日志，读线程继续且 on_error 不受影响"""
        mock_inst = MagicMock()
        mock_inst.is_open = True
        line = b'{"type":"data","values":[1.0]}\n'
        mock_inst.read.side_effect = [line, line, TransportError("stop")]
        mock_serial_cls.return_value = mock_inst

        calls = []

        def handler(msg):
            calls.append(msg["values"])
            if len(calls) == 1:
                raise TypeError("bad values")

        errors = []
        transport = SerialTransport("COM3", on_message=handler, on_error=errors.append)
        transport._serial = mock_inst
        transport._read_loop()

        assert calls == [[1.0], [1.0]], "回调抛异常后第二条消息仍应送达"
        assert len(errors) == 1
        assert not isinstance(errors[0], TypeError), "on_error 只应收到 I/O 错误"


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
    def test_esp32_input_samples(self):
        dev = Esp32InputDevice("in1", "COM3")
        dev.add_data([1.0, 2.0, 3.0])
        assert dev.data_count == 1
        assert dev.get_recent_data(2) == [[1.0, 2.0, 3.0]]
        assert dev.latest_values == [1.0, 2.0, 3.0]
        dev.add_data([4.0, 5.0, 6.0])
        assert dev.data_count == 2
        assert dev.get_recent_data(1) == [[4.0, 5.0, 6.0]]
        assert dev.device_type == "esp32_in"

    def test_esp32_input_channels(self):
        dev = Esp32InputDevice("in1", "COM3")
        assert dev.channel_labels() == []
        dev.set_channels([{"name": "temp", "unit": "C", "kind": "ds18b20"}])
        assert dev.channels[0]["kind"] == "ds18b20"
        assert dev.channel_labels() == ["temp (C)"]
        dev.add_data([23.5])
        assert dev.channel_labels() == ["temp (C)"]

    def test_esp32_input_channel_fallback(self):
        dev = Esp32InputDevice("in1", "COM3")
        dev.add_data([1, 2, 3])
        assert dev.channel_labels() == ["CH0", "CH1", "CH2"]

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

    def test_monitoring_default_on(self):
        d = Device("e1", "esp32_in")
        assert d.monitoring is True
        d.monitoring = False
        assert d.monitoring is False


# ── Monitor ──

class TestDeviceMonitor:
    @patch("core.devices.monitor.SerialTransport")
    def test_attach_and_route_messages(self, mock_transport_cls):
        mock_transport = MagicMock()
        mock_transport.is_open.return_value = True
        mock_transport_cls.return_value = mock_transport
        events = []
        mon = DeviceMonitor(on_event=lambda did, ev, pl: events.append((did, ev)))
        dev = Esp32InputDevice("in1", "COM3")

        assert mon.attach(dev) is True
        assert dev.transport is mock_transport
        sent = mock_transport.send.call_args_list[0][0][0]
        assert b'"type":"hello"' in sent

        handler = mock_transport_cls.call_args.kwargs["on_message"]

        handler({"type": "data", "values": [10, 20]})
        assert dev.data_count == 1
        assert dev.latest_values == [10, 20]
        assert ("in1", "data") in events

        handler({"type": "meta", "channels": [{"name": "t", "unit": "C", "kind": "ds18b20"}]})
        assert dev.channels[0]["name"] == "t"

        handler({"type": "ping"})
        pong = mock_transport.send.call_args_list[-1][0][0]
        assert b'"type":"pong"' in pong

        mon.detach(dev)
        mock_transport.close.assert_called_once()
        assert dev.transport is None

    @patch("core.devices.monitor.SerialTransport")
    def test_attach_fails_on_open_error(self, mock_transport_cls):
        from core.devices.transport import TransportError
        mock_transport_cls.return_value.open.side_effect = TransportError("boom")
        mon = DeviceMonitor()
        dev = Device("e1", "esp32_in", "COM3")
        assert mon.attach(dev) is False
        assert dev.transport is None

    @patch("core.devices.monitor.SerialTransport")
    def test_stop_detaches_all(self, mock_transport_cls):
        mock_transport = MagicMock()
        mock_transport.is_open.return_value = True
        mock_transport_cls.return_value = mock_transport
        mon = DeviceMonitor()
        dev = Esp32InputDevice("in1", "COM3")
        assert mon.attach(dev) is True
        mon.stop()
        mock_transport.close.assert_called_once()
        assert dev.transport is None

    @patch("core.devices.monitor.SerialTransport")
    def test_detach_stops_monitoring(self, mock_transport_cls):
        mock_transport = MagicMock()
        mock_transport.is_open.return_value = True
        mock_transport_cls.return_value = mock_transport
        mon = DeviceMonitor()
        dev = Esp32InputDevice("in1", "COM3")
        assert mon.attach(dev) is True
        assert "in1" in mon._attached
        assert "in1" in mon._heartbeats

        mon.detach(dev)

        assert "in1" not in mon._attached
        assert "in1" not in mon._heartbeats
        assert dev.transport is None
        mock_transport.close.assert_called_once()

    @patch("core.devices.monitor.SerialTransport")
    def test_reattach_after_detach(self, mock_transport_cls):
        mock_transport = MagicMock()
        mock_transport.is_open.return_value = True
        mock_transport_cls.return_value = mock_transport
        mon = DeviceMonitor()
        dev = Esp32InputDevice("in1", "COM3")
        assert mon.attach(dev) is True
        handler1 = mock_transport_cls.call_args.kwargs["on_message"]
        handler1({"type": "data", "values": [1, 2]})
        assert dev.data_count == 1

        mon.detach(dev)
        assert mock_transport.close.call_count == 1

        assert mon.attach(dev) is True
        assert mock_transport_cls.call_count == 2
        assert mock_transport.reset_board.call_count == 2
        handler2 = mock_transport_cls.call_args.kwargs["on_message"]
        assert handler2 is not handler1
        handler2({"type": "data", "values": [3, 4]})
        assert dev.data_count == 2
        assert dev.latest_values == [3, 4]