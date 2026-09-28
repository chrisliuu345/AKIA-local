"""QA-Tool 实时 SPC 云看板 — FastAPI + WebSocket 独立服务。

用法:
    python -m server.app [--port 8765] [--host 127.0.0.1]

同进程数据源: 由主程序 `server.launcher` 以线程方式启动时共享 StreamBus +
TimeseriesStore；独立 CLI 时自动构建 Mock 采集演示流。
"""
import contextlib
import argparse
import asyncio
import json
import secrets
import threading
import time
from pathlib import Path

from core.streaming.bus import StreamBus
from core.storage.timeseries import TimeseriesStore, default_store_path

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")

_STATIC = Path(__file__).parent / "dashboard.html"


def dashboard_config() -> dict:
    """从 user_config 读取看板绑定参数（v3.8.0-⑧）。

    - dashboard_host / dashboard_port: 监听地址（多机部署时才改为 0.0.0.0）
    - dashboard_token: 访问令牌（敏感键 → 经密钥库加密存储）
    非回环地址且未设置令牌时，除非显式打开 dashboard_allow_lan_without_token，
    一律回退到 127.0.0.1 —— 避免车间网络里裸暴露数据接口。
    """
    from config.settings import get_secret, get_setting

    host = str(get_setting("dashboard_host", DEFAULT_HOST) or DEFAULT_HOST).strip()
    try:
        port = int(get_setting("dashboard_port", DEFAULT_PORT) or DEFAULT_PORT)
    except (TypeError, ValueError):
        port = DEFAULT_PORT
    token = str(get_secret("dashboard_token", "") or "").strip()
    if host not in LOOPBACK_HOSTS and not token and not bool(
            get_setting("dashboard_allow_lan_without_token", False)):
        host = DEFAULT_HOST
    return {"host": host, "port": port, "token": token or None}


def dashboard_url(host: str, port: int, token: str | None = None) -> str:
    """看板访问地址（带令牌时自动携带 ?token=）。"""
    base = f"http://{host}:{port}/"
    if token:
        return f"{base}?token={token}"
    return base


def create_app(bus: StreamBus, store: TimeseriesStore | None = None,
               plant=None, oee=None, auth_token: str | None = None,
               downtime=None):
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse

    app = FastAPI(title="QA-Tool 实时看板", docs_url=None, redoc_url=None)

    def _authorized(request) -> bool:
        """v3.8.0 可选鉴权: Bearer 头或 ?token= 查询参数。未配置 token 时全放行。"""
        if not auth_token:
            return True
        header = request.headers.get("authorization", "")
        if header.lower().startswith("bearer "):
            if secrets.compare_digest(header[7:].strip(), auth_token):
                return True
        supplied = request.query_params.get("token", "")
        return bool(supplied) and secrets.compare_digest(supplied, auth_token)

    @app.middleware("http")
    async def _auth_middleware(request, call_next):
        if _authorized(request):
            return await call_next(request)
        return PlainTextResponse("401 未授权: 缺少或错误的看板访问令牌", status_code=401)

    @app.get("/")
    async def index():
        return FileResponse(_STATIC)

    @app.get("/api/devices")
    async def devices():
        return {"topics": bus.topics()}

    @app.get("/api/history")
    async def history(device: str, channel: str | None = None,
                      since: float | None = None, limit: int = 500,
                      agg: str | None = None):
        """历史查询 — agg=1m 时返回分钟降采样（v3.8.0-⑥），否则原始点。"""
        if agg in ("1m", "1min", "minute") and store is not None:
            points = store.query_rollup(device, channel, since_ts=since, limit=limit)
            if points:
                return JSONResponse({"device": device, "agg": "1m",
                                     "samples": [p.as_dict() for p in points]})
        samples = []
        if store is not None:
            samples = store.query(device, channel, since_ts=since, limit=limit)
        if not samples:
            # 未入库(仅内存流)时回退总线缓冲
            samples = bus.recent(device, n=limit)
            if channel:
                samples = [s for s in samples if s.channel == channel]
        return JSONResponse({
            "device": device,
            "samples": [{"t": s.ts, "ch": s.channel, "v": s.value} for s in samples],
        })

    @app.get("/api/plant")
    async def plant_status():
        """产线拓扑 + 工位状态灯（绿/黄/红: 正常 / 判异·超规格 / 离线）。"""
        if plant is None:
            return JSONResponse({"lines": []})
        from core.streaming.live_spc import LiveSPC

        cfg = plant
        now = time.time()
        recent_data: dict[str, list] = {dev: bus.recent(dev, n=30) for dev in bus.topics()}
        stats = {}
        for dev, recent in recent_data.items():
            stale = bool(recent) and (now - recent[-1].ts) > 5.0
            stats[dev] = {"online": bool(recent) and not stale}
        ooc_live: dict[tuple[str, str], bool] = {}
        for line in cfg.lines:
            for st in line.stations:
                vals_by_ch: dict[str, list[float]] = {}
                for s in recent_data.get(st.device, []):
                    vals_by_ch.setdefault(s.channel, []).append(s.value)
                for ch in st.channels or []:
                    spc = LiveSPC("x", mode="imr", window=30, usl=st.usl, lsl=st.lsl)
                    frame = spc.feed(vals_by_ch.get(ch, []))
                    ooc_live[(st.device, ch)] = frame.ooc or frame.oos
        lines = []
        for line in cfg.lines:
            stations = []
            for st in line.stations:
                dev = st.device
                online = stats.get(dev, {}).get("online", False)
                alert = any(ooc_live.get((st.device, ch), False) for ch in st.channels or [])
                status = "red" if not online else ("yellow" if alert else "green")
                stations.append({"name": st.name, "device": dev,
                                 "channels": st.channels, "status": status,
                                 "online": online, "alert": alert,
                                 # v3.8.0: 规格线/节拍 → 看板控制图 USL·LSL 绘制
                                 "specs": {ch: {"usl": st.usl, "lsl": st.lsl}
                                           for ch in (st.channels or [])},
                                 "ideal_cycle_time_s": line.cycle_time_for(st)})
            lines.append({"name": line.name, "stations": stations,
                          "unit_cost": line.unit_cost,
                          "scrap_cost": line.loss_per_unit(),
                          "downtime_cost_per_min": line.downtime_cost_per_min,
                          "shift": line.shift})
        tracker = downtime if downtime is not None else getattr(oee, "downtime", None)
        return JSONResponse({
            "lines": lines,
            "downtime_reason_codes": list(getattr(tracker, "reason_codes", ()) or ()),
        })

    @app.get("/api/oee")
    async def oee_metrics():
        if oee is None:
            return JSONResponse({"lines": {}})
        payload = {"lines": oee.snapshot()}
        tracker = downtime if downtime is not None else getattr(oee, "downtime", None)
        if tracker is not None:
            window = float(getattr(oee, "window_s", 600.0))
            payload["downtime"] = tracker.snapshot(window)
        return JSONResponse(payload)

    @app.post("/api/downtime")
    async def downtime_action(payload: dict):
        """停机原因码记录（v3.8.0-⑤）: {"line":..,"action":"start|end","reason":..}"""
        tracker = downtime if downtime is not None else getattr(oee, "downtime", None)
        if tracker is None:
            return JSONResponse({"ok": False, "error": "未启用停机追踪"}, status_code=400)
        line = str(payload.get("line") or "")
        action = str(payload.get("action") or "start")
        if not line:
            return JSONResponse({"ok": False, "error": "缺少产线"}, status_code=400)
        if action == "end":
            rec = tracker.end(line)
            if rec is None:
                return JSONResponse({"ok": False, "error": "该产线未处于停机状态"},
                                    status_code=409)
            return JSONResponse({"ok": True, "ended": rec.reason,
                                 "seconds": round(rec.duration(), 2)})
        rec = tracker.start(line, payload.get("reason") or "其他",
                            device=payload.get("device") or "")
        return JSONResponse({"ok": True, "reason": rec.reason, "start_ts": rec.start_ts})

    @app.get("/api/cost")
    async def cost_metrics():
        """成本损失估算（v3.8.0-④）— 超规格量 × 单件损失 + 停机成本。"""
        if plant is None:
            return JSONResponse({"lines": {}})
        from core.streaming.cost import CostAnalyzer

        samples_by_device = {dev: bus.recent(dev, n=5000) for dev in bus.topics()}
        snapshot = oee.snapshot() if oee is not None else None
        analyzer = CostAnalyzer(plant, downtime=getattr(oee, "downtime", None))
        return JSONResponse({"lines": analyzer.estimate(samples_by_device, snapshot)})

    @app.websocket("/ws/stream")
    async def stream(ws: WebSocket):
        if auth_token:
            supplied = ws.query_params.get("token", "")
            if not (supplied and secrets.compare_digest(supplied, auth_token)):
                await ws.close(code=1008)
                return
        await ws.accept()
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()
        device = ws.query_params.get("device", "")

        def on_batch(samples):
            if not samples:
                return
            if device and samples[0].device != device:
                return
            payload = json.dumps({
                "type": "batch",
                "samples": [{"dev": s.device, "t": s.ts, "ch": s.channel, "v": s.value}
                            for s in samples],
            })
            loop.call_soon_threadsafe(queue.put_nowait, payload)

        if device:
            unsub = bus.subscribe(device, on_batch)
        else:
            unsub = bus.subscribe(None, on_batch)

        async def sender():
            try:
                while True:
                    await ws.send_text(await queue.get())
            except Exception:
                pass  # 客户端硬断连/服务端停机 — receive 循环处结束并由 finally 清理

        task = loop.create_task(sender())
        try:
            while True:
                await ws.receive_text()  # 客户端心跳/测试周期，断连即抛异常
        except WebSocketDisconnect:
            pass  # 客户端主动断开属正常路径
        finally:
            task.cancel()
            unsub()
            with contextlib.suppress(Exception):
                await ws.close()

    return app


def start_thread(bus: StreamBus, store: TimeseriesStore | None = None,
                 host: str = DEFAULT_HOST, port: int = DEFAULT_PORT,
                 plant=None, oee=None, auth_token: str | None = None,
                 downtime=None):
    """在线程内启动 uvicorn — 桌面端菜单入口使用。"""
    import uvicorn

    app = create_app(bus, store, plant=plant, oee=oee, auth_token=auth_token,
                     downtime=downtime)
    cfg = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(cfg)
    thread = threading.Thread(target=server.run, daemon=True,
                              name="qa-tool-live-dashboard")
    thread.stop_server = lambda: setattr(server, "should_exit", True)  # 供外部停止
    thread.start()
    return thread


def stop_thread(thread, timeout: float = 5.0) -> None:
    if thread is None or not callable(getattr(thread, "stop_server", None)):
        return
    thread.stop_server()
    if thread.is_alive():
        thread.join(timeout=timeout)


if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser(description="QA-Tool 实时看板服务")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--token", default="",
                        help="访问令牌（留空 = 不鉴权；设置后 HTTP/WS 均需携带）")
    args = parser.parse_args()

    store = TimeseriesStore(default_store_path())
    bus = StreamBus()
    token = args.token.strip() or None

    def _demo_source():
        from core.devices.driver import MockDriver
        from core.streaming.collector import IngestRunner
        runner = IngestRunner(bus, store, [MockDriver("demo-01", rate_hz=1.0)])
        runner.start()
        return runner

    _demo_source()
    print(f"QA-Tool 实时看板: http://{args.host}:{args.port}")
    uvicorn.run(create_app(bus, store, auth_token=token), host=args.host,
                port=args.port, log_level="warning")
