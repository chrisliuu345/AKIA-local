"""QA-Tool 实时 SPC 云看板 — FastAPI + WebSocket 独立服务。

用法:
    python -m server.app [--port 8765] [--host 127.0.0.1]

同进程数据源: 由主程序 `server.launcher` 以线程方式启动时共享 StreamBus +
TimeseriesStore；独立 CLI 时自动构建 Mock 采集演示流。
"""
import argparse
import asyncio
import json
import threading
import time
from pathlib import Path

from core.streaming.bus import StreamBus
from core.storage.timeseries import TimeseriesStore, default_store_path

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765

_STATIC = Path(__file__).parent / "dashboard.html"


def create_app(bus: StreamBus, store: TimeseriesStore | None = None,
               plant=None, oee=None):
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.responses import FileResponse, JSONResponse

    app = FastAPI(title="QA-Tool 实时看板", docs_url=None, redoc_url=None)

    @app.get("/")
    async def index():
        return FileResponse(_STATIC)

    @app.get("/api/devices")
    async def devices():
        return {"topics": bus.topics()}

    @app.get("/api/history")
    async def history(device: str, channel: str | None = None,
                      since: float | None = None, limit: int = 500):
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
        from core import plant as plant_mod
        cfg = plant_mod.PlantConfig.load()
        now = time.time()
        stats = {}
        for dev in bus.topics():
            recent = bus.recent(dev, n=1)
            stale = bool(recent) and (now - recent[-1].ts) > 5.0
            stats[dev] = {"online": bool(recent) and not stale}
        from core.streaming.live_spc import LiveSPC
        ooc_live: dict[tuple[str, str], bool] = {}
        for line in cfg.lines:
            for st in line.stations:
                spc = LiveSPC("x", mode="imr", window=30, usl=st.usl, lsl=st.lsl)
                for ch in st.channels or []:
                    spc.reset()
                    frame = spc.feed([s.value for s in bus.recent(st.device, n=30)
                                      if s.channel == ch])
                    key = (st.device, ch)
                    ooc_live[key] = frame.ooc or frame.oos
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
                                 "online": online, "alert": alert})
            lines.append({"name": line.name, "stations": stations})
        return JSONResponse({"lines": lines})

    @app.get("/api/oee")
    async def oee_metrics():
        if oee is None:
            return JSONResponse({"lines": {}})
        return JSONResponse({"lines": oee.snapshot()})

    @app.websocket("/ws/stream")
    async def stream(ws: WebSocket):
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
            while True:
                await ws.send_text(await queue.get())

        task = loop.create_task(sender())
        try:
            while True:
                await ws.receive_text()  # 客户端心跳/测试周期，断连即抛异常
        except WebSocketDisconnect:
            pass
        finally:
            task.cancel()
            unsub()
            try:
                await ws.close()
            except Exception:
                pass

    return app


def start_thread(bus: StreamBus, store: TimeseriesStore | None = None,
                 host: str = DEFAULT_HOST, port: int = DEFAULT_PORT,
                 plant=None, oee=None):
    """在线程内启动 uvicorn — 桌面端菜单入口使用。"""
    import uvicorn

    app = create_app(bus, store, plant=plant, oee=oee)
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
    args = parser.parse_args()

    store = TimeseriesStore(default_store_path())
    bus = StreamBus()

    def _demo_source():
        from core.devices.driver import MockDriver
        from core.streaming.collector import IngestRunner
        runner = IngestRunner(bus, store, [MockDriver("demo-01", rate_hz=1.0)])
        runner.start()
        return runner

    _demo_source()
    print(f"QA-Tool 实时看板: http://{args.host}:{args.port}")
    uvicorn.run(create_app(bus, store), host=args.host, port=args.port,
                log_level="warning")
