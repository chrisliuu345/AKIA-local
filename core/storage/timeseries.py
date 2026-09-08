"""SQLite 时序存储层 v1 — 设备→通道→时间序列，批量写入。

单文件 stdlib sqlite3 实现；PostgreSQL 后续以同方法签名接入。
"""
import sqlite3
import threading
import time
from pathlib import Path

from core.devices.driver import Sample


class TimeseriesStore:
    def __init__(self, path: str | Path):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS measurements (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                device  TEXT NOT NULL,
                channel TEXT NOT NULL,
                ts      REAL NOT NULL,
                value   REAL NOT NULL
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_meas_dev_chan_ts "
            "ON measurements (device, channel, ts DESC)"
        )
        self._conn.commit()

    def insert_samples(self, samples: list[Sample]) -> int:
        if not samples:
            return 0
        with self._lock:
            self._conn.executemany(
                "INSERT INTO measurements (device, channel, ts, value) VALUES (?, ?, ?, ?)",
                [(s.device, s.channel, s.ts, s.value) for s in samples],
            )
            self._conn.commit()
            return len(samples)

    def query(self, device: str, channel: str | None = None,
              since_ts: float | None = None, limit: int = 1000) -> list[Sample]:
        sql = "SELECT device, channel, ts, value FROM measurements WHERE device = ?"
        args: list = [device]
        if channel:
            sql += " AND channel = ?"
            args.append(channel)
        if since_ts:
            sql += " AND ts >= ?"
            args.append(since_ts)
        sql += " ORDER BY ts ASC LIMIT ?"
        args.append(limit)
        with self._lock:
            rows = self._conn.execute(sql, args).fetchall()
        return [Sample(r[0], r[1], r[3], r[2]) for r in rows]

    def count(self, device: str | None = None) -> int:
        sql = "SELECT COUNT(*) FROM measurements"
        args: list = []
        if device:
            sql += " WHERE device = ?"
            args.append(device)
        with self._lock:
            return int(self._conn.execute(sql, args).fetchone()[0])

    def prune_older_than(self, cutoff_ts: float) -> int:
        with self._lock:
            cur = self._conn.execute("DELETE FROM measurements WHERE ts < ?", (cutoff_ts,))
            self._conn.commit()
            return cur.rowcount

    def close(self) -> None:
        with self._lock:
            try:
                self._conn.close()
            except sqlite3.Error:
                pass


def default_store_path() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "data" / "timeseries.db"


class StreamingStatus:
    """采集运行状态统计（延迟、吞吐）— 供看板/告警复用。"""

    def __init__(self):
        self.samples_total = 0
        self.last_latency_ms = 0.0
        self.max_latency_ms = 0.0

    def report(self, samples: list[Sample], now: float | None = None) -> None:
        if not samples:
            return
        now = now or time.time()
        lat = max(now - s.ts for s in samples) * 1000.0
        self.last_latency_ms = lat
        self.max_latency_ms = max(self.max_latency_ms, lat)
        self.samples_total += len(samples)
