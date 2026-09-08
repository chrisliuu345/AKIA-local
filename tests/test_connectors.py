"""P4 验收 — 连接器注册表 / 插件可用性 / DMIS+量具解析 / 协议 Mock 测试。

验收: PLC/量具连接器 Mock 测试通过（Modbus 用内嵌 server, MQTT 用假 broker）。
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")  # 项目测试惯例

from connectors.registry import discover, create_connector
from connectors.base import ConnectorBase


def test_registry_discovers_all_five_plugins():
    infos = discover()
    names = set(infos)
    assert {"modbus_tcp", "mqtt_sub", "opcua", "cmm_dmis", "serial_gage"} <= names
    assert infos["cmm_dmis"].category == "cmm"
    assert infos["modbus_tcp"].available  # pymodbus 已装


def test_create_unknown_plugin_raises():
    with pytest.raises(ValueError):
        create_connector("no_such_plugin")


def test_create_connector_returns_base():
    c = create_connector("cmm_dmis", {"name": "c", "source": "file", "path": "/x"})
    assert isinstance(c, ConnectorBase)
    assert c.name == "c"


def test_cmm_dmis_parses_meas_lines(tmp_path):
    src = tmp_path / "dmis.txt"
    src.write_text(
        "F(MEAS1)=MEAS/PE,2\n"
        "MEAS/POL,1, X,12.345,Y,-3.210,Z,0.012\n"
        "X 1.5 Y -2.5 Z 0.33 8.5\n"
        "ENDMES\n", encoding="utf-8",
    )
    c = create_connector("cmm_dmis", {"name": "cmm", "source": "file",
                                      "path": str(src), "axes": {"X": "X", "Y": "Y"}})
    c.open()
    samples = c.poll()
    c.close()
    vals = {(s.channel, round(s.value, 3)) for s in samples}
    assert ("X", 12.345) in vals and ("Y", -3.210) in vals
    # 无 MEAS 前缀行走轴模式
    assert ("X", 1.5) in vals


def test_serial_gage_parses_lines(monkeypatch):
    class FakeSerial:
        is_open = True

        def __init__(self):
            self.chunks = [b"", b""]  # 首轮空, 次轮出数据

        def read(self, n):
            return self.chunks.pop(0) if len(self.chunks) > 1 else b"25.40\n26.10\n"

        def close(self):
            pass

    import connectors.plugins.serial_gage as sg

    monkeypatch.setattr(sg.Connector, "open", lambda self: setattr(
        self, "_serial", FakeSerial()))
    c = sg.Connector({"name": "caliper", "tty": "/dev/ttyUSB0", "channel": "value"})
    c.open()
    c.poll()  # 首轮可能为半行
    s2 = c.poll()
    c.close()
    assert [s.value for s in s2] == [25.40, 26.10]
    assert all(s.channel == "value" and s.device == "caliper" for s in s2)


def test_mqtt_connector_parses_broker_payload(monkeypatch):
    import connectors.plugins.mqtt_sub as mq

    c = mq.Connector({"name": "iot", "broker": "127.0.0.1", "topic": "d/x",
                      "channels": ["CH0", "CH1"]})

    fake_client = type("FakeClient", (), {})()
    payload = b'{"CH0": 21.5, "CH1": 18.0}'
    from types import SimpleNamespace
    msg = SimpleNamespace(payload=payload)

    c._client = fake_client
    c._on_message(None, None, msg)
    samples = c.poll()
    assert {(s.channel, s.value) for s in samples} == {("CH0", 21.5), ("CH1", 18.0)}


def test_modbus_connector_mock_client(monkeypatch):
    """B8: 同步客户端 + register 映射 + 读失败安全。"""
    import connectors.plugins.modbus_tcp as mb

    class RR:
        def __init__(self, registers):
            self.registers = registers

    class FakeClient:
        def __init__(self, host, port=502):
            self.host, self.port = host, port
            self.connected = False

        def connect(self):
            self.connected = True
            return True

        def read_holding_registers(self, addr, count, slave):
            return RR([10, 20, 30][:count]) if slave == 1 else RR(None)

        def close(self):
            self.connected = False

    monkeypatch.setattr(mb, "ModbusTcpClient", FakeClient)
    c = mb.Connector({"name": "plc", "host": "127.0.0.1",
                      "registers": {"CH0": 0, "CH1": 1}})
    c.open()
    samples = c.poll()
    assert {(s.channel, s.value) for s in samples} == {("CH0", 10.0), ("CH1", 20.0)}
    assert samples[0].device == "plc"
    c._slave = 9
    assert c.poll() == []  # 读失败不抛异常, 下轮重试
    c.close()
    assert c._client is None
    assert c.poll() == []
