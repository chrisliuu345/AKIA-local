"""P3 验收 — FastAPI 看板: 历史 API / WS 广播 / 50 并发无退化。

验收: WebSocket 并发 50 连接无性能退化（全部收到广播）。
"""
import os
import time
import urllib.request
import json as _json

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("uvicorn")

from core.devices.driver import Sample
from core.plant import PlantConfig, Line, Station
from core.storage.timeseries import TimeseriesStore
from core.streaming.bus import StreamBus
from core.streaming.oee_live import LiveOEEComputer
from server.app import start_thread, stop_thread

PORT = 18765


@pytest.fixture
def server(tmp_path, _qt_application):
    bus = StreamBus()
    store = TimeseriesStore(tmp_path / "srv.db")
    thread = start_thread(bus, store, host="127.0.0.1", port=PORT)
    url = f"http://127.0.0.1:{PORT}/api/devices"
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as r:
                r.read()
            break
        except Exception:
            time.sleep(0.2)
    else:
        pytest.fail("server did not start")
    yield bus, store, f"127.0.0.1:{PORT}"
    stop_thread(thread)


def test_history_api_and_devices(server):
    bus, store, addr = server
    samples = [Sample("line-01", "CH0", 1.5, 100.0),
               Sample("line-01", "CH0", 2.5, 101.0),
               Sample("line-01", "CH0", 3.5, 102.0)]
    bus.publish("line-01", samples)
    store.insert_samples(samples)  # 模拟 IngestRunner 入库侧

    raw = urllib.request.urlopen(f"http://{addr}/api/devices", timeout=3).read()
    assert _json.loads(raw)["topics"] == ["line-01"]

    raw = urllib.request.urlopen(
        f"http://{addr}/api/history?device=line-01&channel=CH0", timeout=3).read()
    got = _json.loads(raw)["samples"]
    assert [s["v"] for s in got] == [1.5, 2.5, 3.5]

    # 入库后历史查询走 SQLite
    assert store.count("line-01") == 3


def test_ws_broadcast(server):
    import websockets.sync.client as ws_client

    bus, store, addr = server
    received = []
    with ws_client.connect(f"ws://{addr}/ws/stream") as ws:
        bus.publish("mock-a", [Sample("mock-a", "CH1", 42.0, 100.0)])
        deadline = time.time() + 5
        while time.time() < deadline and not received:
            try:
                msg = _json.loads(ws.recv(timeout=1))
            except TimeoutError:
                continue
            if msg["type"] == "batch":
                received.extend(msg["samples"])
    assert received and received[0]["dev"] == "mock-a" and received[0]["v"] == 42.0


def test_50_concurrent_ws_connections(server):
    import websockets.sync.client as ws_client

    bus, store, addr = server
    n = 50
    clients = []
    for _ in range(n):
        try:
            clients.append(ws_client.connect(f"ws://{addr}/ws/stream"))
        except Exception as e:
            pytest.fail(f"第 {len(clients)+1} 个连接失败: {e}")

    ok_connected = len(clients)
    assert ok_connected == n, f"只有 {ok_connected}/{n} 连接成功"
    try:
        bus.publish("line-01", [Sample("line-01", "CH0", 9.0, 100.0)])
        t0 = time.time()
        for i, ws in enumerate(clients):
            got = False
            while time.time() - t0 < 5:
                try:
                    msg = _json.loads(ws.recv(timeout=1))
                except TimeoutError:
                    continue
                if msg["type"] == "batch":
                    got = True
                    break
            assert got, f"第 {i} 个连接未收到广播"
    finally:
        for ws in clients:
            try:
                ws.close()
            except Exception:
                pass


def test_dashboard_page_served(server):
    bus, store, addr = server
    raw = urllib.request.urlopen(f"http://{addr}/", timeout=3).read()
    text = raw.decode("utf-8")
    assert "QA-Tool 实时 SPC 云看板" in text
    assert "ws://" in text
    # B1 回归: 图表对象必须缓存 ch 字段
    assert "charts[key] = { card, meta: t2, cv, pts: [], ch };" in text, "ch 字段缺失"


def test_plant_status_uses_injected_config_and_tags():
    """B2: /api/plant 使用注入的 plant 配置, 状态灯按在线/判异着色。"""
    import time as _t
    bus = StreamBus()
    store = None
    plant = PlantConfig(lines=[Line(name="L1", stations=[
        Station(name="S1", device="dev-a", channels=["CH0"], usl=110.0),
        Station(name="S2", device="dev-b", channels=["CH0"]),
    ])])
    oee = LiveOEEComputer(bus, plant, window_s=600.0)
    thread = start_thread(bus, store, port=18766, plant=plant, oee=oee)
    url = "http://127.0.0.1:18766"
    deadline = _t.time() + 10
    while _t.time() < deadline:
        try:
            urllib.request.urlopen(url + "/api/plant", timeout=1).read()
            break
        except Exception:
            _t.sleep(0.2)
    else:
        pytest.fail("server did not start")
    try:
        bus.publish("dev-a", [Sample("dev-a", "CH0", 100.0, _t.time()),
                              Sample("dev-a", "CH0", 131.0, _t.time())])
        raw = urllib.request.urlopen(url + "/api/plant", timeout=3).read()
        lines = _json.loads(raw)["lines"]
        assert lines[0]["name"] == "L1"
        st = {st["name"]: st for st in lines[0]["stations"]}
        assert st["S1"]["status"] == "yellow"  # OOS 越限
        assert st["S2"]["status"] == "red"     # 无数据离线
        raw = urllib.request.urlopen(url + "/api/oee", timeout=3).read()
        oee_lines = _json.loads(raw)["lines"]
        assert "L1" in oee_lines and oee_lines["L1"]["samples"] == 2
    finally:
        stop_thread(thread)
        oee.stop()


def test_ws_abrupt_disconnect_then_continue(server):
    """B3: 客户端硬断连后服务照常广播, 新连接可继续收数。"""
    import websockets.sync.client as ws_client
    bus, store, addr = server
    ws = ws_client.connect(f"ws://{addr}/ws/stream")
    import socket as _sock
    ws.socket.shutdown(_sock.SHUT_RDWR)
    ws.socket.close()  # 客户端硬断连(跳过 WS 关闭握手)
    bus.publish("h1", [Sample("h1", "CH0", 1.0, 100.0)])
    with ws_client.connect(f"ws://{addr}/ws/stream") as ws2:
        bus.publish("h2", [Sample("h2", "CH0", 2.0, 101.0)])
        got = []
        deadline = time.time() + 5
        while time.time() < deadline and not got:
            try:
                msg = _json.loads(ws2.recv(timeout=1))
            except TimeoutError:
                continue
            if msg["type"] == "batch":
                got = msg["samples"]
        assert got and got[0]["dev"] == "h2"
