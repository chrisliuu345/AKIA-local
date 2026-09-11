"""v3.8.0-⑧ 看板可选鉴权 — token 校验 / WS 拒绝 / host 绑定 / 地址生成。"""
import json
import os
import time
import urllib.error
import urllib.request

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("uvicorn")

from core.storage.timeseries import TimeseriesStore
from core.streaming.bus import StreamBus
from core.devices.driver import Sample
from server.app import (
    create_app, dashboard_config, dashboard_url, start_thread, stop_thread,
)

TOKEN = "s3cret-token"


def _wait_ready(url: str, headers: dict | None = None, timeout: float = 10.0):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            req = urllib.request.Request(url, headers=headers or {})
            return urllib.request.urlopen(req, timeout=1)
        except urllib.error.HTTPError as e:
            return e          # 4xx 也算服务已就绪
        except Exception as e:  # noqa: BLE001 - 连接未就绪
            last = e
            time.sleep(0.2)
    pytest.fail(f"server did not start: {last}")


def test_dashboard_url_includes_token():
    assert dashboard_url("127.0.0.1", 8765) == "http://127.0.0.1:8765/"
    assert dashboard_url("127.0.0.1", 8765, TOKEN) == \
        f"http://127.0.0.1:8765/?token={TOKEN}"


def test_dashboard_config_defaults_and_secret(monkeypatch):
    import config.settings as settings

    monkeypatch.setattr(settings, "get_setting", lambda k, d=None: d)
    monkeypatch.setattr(settings, "get_secret", lambda k, d="": "")
    cfg = dashboard_config()
    assert cfg["host"] == "127.0.0.1" and cfg["port"] == 8765
    assert cfg["token"] is None

    monkeypatch.setattr(settings, "get_setting",
                        lambda k, d=None: {"dashboard_host": "0.0.0.0",
                                           "dashboard_port": "9000"}.get(k, d))
    monkeypatch.setattr(settings, "get_secret", lambda k, d="": TOKEN)
    cfg = dashboard_config()
    assert cfg == {"host": "0.0.0.0", "port": 9000, "token": TOKEN}


def test_dashboard_config_blocks_lan_without_token(monkeypatch):
    import config.settings as settings

    monkeypatch.setattr(settings, "get_setting",
                        lambda k, d=None: {"dashboard_host": "0.0.0.0"}.get(k, d))
    monkeypatch.setattr(settings, "get_secret", lambda k, d="": "")
    assert dashboard_config()["host"] == "127.0.0.1"        # 回退回环

    monkeypatch.setattr(
        settings, "get_setting",
        lambda k, d=None: {"dashboard_host": "0.0.0.0",
                           "dashboard_allow_lan_without_token": True}.get(k, d))
    assert dashboard_config()["host"] == "0.0.0.0"          # 显式放行


def test_http_requires_token_when_configured():
    bus = StreamBus()
    store = TimeseriesStore(os.path.join(os.environ.get("TMPDIR", "/tmp"),
                                         "qa_auth.db"))
    port = 18780
    thread = start_thread(bus, store, host="127.0.0.1", port=port,
                          auth_token=TOKEN)
    url = f"http://127.0.0.1:{port}"
    try:
        resp = _wait_ready(url + "/api/devices")
        assert isinstance(resp, urllib.error.HTTPError)
        assert resp.code == 401

        assert urllib.request.urlopen(
            f"{url}/api/devices?token={TOKEN}", timeout=3).status == 200
        assert urllib.request.urlopen(
            urllib.request.Request(url + "/api/devices",
                                   headers={"Authorization": f"Bearer {TOKEN}"}),
            timeout=3).status == 200
        with pytest.raises(urllib.error.HTTPError) as page_err:
            urllib.request.urlopen(url + "/", timeout=3)
        assert page_err.value.code == 401                    # 静态页同样受保护
        assert urllib.request.urlopen(url + f"/?token={TOKEN}",
                                      timeout=3).status == 200
        with pytest.raises(urllib.error.HTTPError) as err:
            urllib.request.urlopen(f"{url}/api/devices?token=wrong", timeout=3)
        assert err.value.code == 401
    finally:
        stop_thread(thread)
        store.close()


def test_ws_rejects_without_token():
    import websockets.sync.client as ws_client

    bus = StreamBus()
    store = TimeseriesStore(os.path.join(os.environ.get("TMPDIR", "/tmp"),
                                         "qa_auth_ws.db"))
    port = 18781
    thread = start_thread(bus, store, host="127.0.0.1", port=port,
                          auth_token=TOKEN)
    try:
        _wait_ready(f"http://127.0.0.1:{port}/api/devices?token={TOKEN}")
        # 未带令牌的 WS 握手会被服务端以 1008 关闭（客户端表现为建连失败/立刻断开）
        closed = False
        try:
            with ws_client.connect(f"ws://127.0.0.1:{port}/ws/stream") as ws:
                ws.recv(timeout=2)
        except Exception:  # noqa: BLE001 - 不同 websockets 版本抛错类型不同
            closed = True
        assert closed, "未授权 WS 连接必须被拒绝"

        with ws_client.connect(
                f"ws://127.0.0.1:{port}/ws/stream?token={TOKEN}") as ws:
            bus.publish("dev-x", [Sample("dev-x", "CH0", 5.0, time.time())])
            got = []
            deadline = time.time() + 5
            while time.time() < deadline and not got:
                try:
                    msg = json.loads(ws.recv(timeout=1))
                except TimeoutError:
                    continue
                if msg["type"] == "batch":
                    got = msg["samples"]
            assert got and got[0]["v"] == 5.0
    finally:
        stop_thread(thread)
        store.close()


def test_no_token_means_open_access():
    bus = StreamBus()
    store = TimeseriesStore(os.path.join(os.environ.get("TMPDIR", "/tmp"),
                                         "qa_open.db"))
    port = 18782
    thread = start_thread(bus, store, host="127.0.0.1", port=port)
    try:
        resp = _wait_ready(f"http://127.0.0.1:{port}/api/devices")
        assert not isinstance(resp, urllib.error.HTTPError)
        assert resp.status == 200
    finally:
        stop_thread(thread)
        store.close()


def test_create_app_exposes_routes(monkeypatch):
    app = create_app(StreamBus(), None, auth_token=TOKEN)
    paths = {getattr(r, "path", "") for r in app.routes}
    assert {"/", "/api/devices", "/api/history", "/api/plant", "/api/oee",
            "/api/cost", "/api/downtime", "/ws/stream"} <= paths
