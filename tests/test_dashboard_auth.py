"""v3.8.0-⑧ 看板可选鉴权 — token 校验 / WS 拒绝 / host 绑定 / 地址生成。"""
import json
import os
import socket
import time
import urllib.error
import urllib.request
from pathlib import Path

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


pytestmark = [pytest.mark.requires_socket, pytest.mark.requires_server]
def _free_port() -> int:
    """向系统申请一个空闲端口，避免固定端口在满载回归时被占用/冲突。"""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _wait_ready(url: str, headers: dict | None = None, timeout: float = 10.0):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            req = urllib.request.Request(url, headers=headers or {})
            return urllib.request.urlopen(req, timeout=1)
        except urllib.error.HTTPError as e:
            return e          # 4xx 也算服务已就绪
        except Exception as e:  # 连接未就绪（服务仍在启动）
            last = e
            time.sleep(0.2)
    pytest.fail(f"server did not start: {last}")


def test_dashboard_url_omits_token():
    assert dashboard_url("127.0.0.1", 8765) == "http://127.0.0.1:8765/"
    url = dashboard_url("127.0.0.1", 8765, TOKEN)
    assert url == "http://127.0.0.1:8765/"
    assert TOKEN not in url


def test_dashboard_config_defaults_and_secret(monkeypatch):
    import config.settings as settings

    saved = {}
    monkeypatch.setattr(settings, "save_config", saved.update)
    monkeypatch.setattr(settings, "get_setting", lambda k, d=None: d)
    monkeypatch.setattr(settings, "get_secret", lambda k, d="": "")
    cfg = dashboard_config()
    assert cfg["host"] == "127.0.0.1" and cfg["port"] == 8765
    assert cfg["token"]
    assert saved["dashboard_token"] == cfg["token"]
    assert "token=" not in dashboard_url(cfg["host"], cfg["port"], cfg["token"])

    monkeypatch.setattr(settings, "get_setting",
                        lambda k, d=None: {"dashboard_host": "0.0.0.0",
                                           "dashboard_port": "9000"}.get(k, d))
    monkeypatch.setattr(settings, "get_secret", lambda k, d="": TOKEN)
    cfg = dashboard_config()
    assert cfg == {"host": "0.0.0.0", "port": 9000, "token": TOKEN}


def test_dashboard_config_uses_token_on_lan_host(monkeypatch):
    import config.settings as settings

    monkeypatch.setattr(settings, "save_config", lambda values: None)
    monkeypatch.setattr(settings, "get_setting",
                        lambda k, d=None: {"dashboard_host": "0.0.0.0"}.get(k, d))
    monkeypatch.setattr(settings, "get_secret", lambda k, d="": "")
    cfg = dashboard_config()
    assert cfg["host"] == "0.0.0.0"
    assert cfg["token"]


def test_http_requires_token_when_configured():
    bus = StreamBus()
    store = TimeseriesStore(os.path.join(os.environ.get("TMPDIR", "/tmp"),
                                         "akia_auth.db"))
    port = _free_port()
    thread = start_thread(bus, store, host="127.0.0.1", port=port,
                          auth_token=TOKEN)
    url = f"http://127.0.0.1:{port}"
    try:
        resp = _wait_ready(url + "/api/devices")
        assert isinstance(resp, urllib.error.HTTPError)
        assert resp.code == 401

        with pytest.raises(urllib.error.HTTPError) as query_err:
            urllib.request.urlopen(f"{url}/api/devices?token={TOKEN}", timeout=3)
        assert query_err.value.code == 401
        assert urllib.request.urlopen(
            urllib.request.Request(url + "/api/devices",
                                   headers={"Authorization": f"Bearer {TOKEN}"}),
            timeout=3).status == 200
        page = urllib.request.urlopen(url + "/", timeout=3)
        body = page.read().decode("utf-8")
        assert page.status == 200
        assert TOKEN not in page.geturl()
        assert TOKEN not in body
        assert f"akia_dashboard={TOKEN}" in page.headers.get("Set-Cookie", "")
        denied = urllib.request.Request(
            url + "/api/devices",
            headers={"Authorization": f"Bearer {TOKEN}",
                     "Origin": "https://evil.example"},
        )
        with pytest.raises(urllib.error.HTTPError) as origin_err:
            urllib.request.urlopen(denied, timeout=3)
        assert origin_err.value.code == 403
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
                                         "akia_auth_ws.db"))
    port = _free_port()
    thread = start_thread(bus, store, host="127.0.0.1", port=port,
                          auth_token=TOKEN)
    try:
        _wait_ready(f"http://127.0.0.1:{port}/api/devices",
                    headers={"Authorization": f"Bearer {TOKEN}"})
        # 未带令牌的 WS 握手会被服务端以 1008 关闭（客户端表现为建连失败/立刻断开）
        closed = False
        try:
            with ws_client.connect(f"ws://127.0.0.1:{port}/ws/stream") as ws:
                ws.recv(timeout=2)
        except Exception:  # 不同 websockets 版本抛错类型不同
            closed = True
        assert closed, "未授权 WS 连接必须被拒绝"
        query_closed = False
        try:
            with ws_client.connect(
                    f"ws://127.0.0.1:{port}/ws/stream?token={TOKEN}") as ws:
                ws.recv(timeout=2)
        except Exception:
            query_closed = True
        assert query_closed, "地址中的令牌不得作为 WS 凭证"

        with ws_client.connect(
                f"ws://127.0.0.1:{port}/ws/stream",
                additional_headers={"Cookie": f"akia_dashboard={TOKEN}"}) as ws:
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
    port = _free_port()
    thread = start_thread(bus, store, host="127.0.0.1", port=port)
    try:
        resp = _wait_ready(f"http://127.0.0.1:{port}/api/devices")
        assert not isinstance(resp, urllib.error.HTTPError)
        assert resp.status == 200
    finally:
        stop_thread(thread)
        store.close()


def test_dashboard_page_escapes_untrusted_text():
    html = Path("server/dashboard.html").read_text(encoding="utf-8")
    assert "function esc(" in html
    assert "esc(line.name)" in html
    assert "esc(st.name)" in html and "esc(st.device)" in html
    assert "location.search).get(\"token\")" not in html
    assert "?token=" not in html


def test_create_app_exposes_routes(monkeypatch):
    app = create_app(StreamBus(), None, auth_token=TOKEN)
    paths = {getattr(r, "path", "") for r in app.routes}
    assert {"/", "/api/devices", "/api/history", "/api/plant", "/api/oee",
            "/api/cost", "/api/downtime", "/ws/stream"} <= paths
