"""SQLite 时序存储层 v1 — 设备→通道→时间序列，批量写入。

单文件 stdlib sqlite3 实现；PostgreSQL 后续以同方法签名接入。

v3.8.0-⑥ 新增保留策略: 原始点按分钟降采样到 measurements_1m（avg/min/max/
count，幂等重算），再按保留期清理原始点与聚合点，长期趋势仍可查询。
"""
import sqlite3
import threading
import time
from dataclasses import dataclass
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
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS measurements_1m (
                device    TEXT NOT NULL,
                channel   TEXT NOT NULL,
                bucket_ts REAL NOT NULL,
                avg_v     REAL NOT NULL,
                min_v     REAL NOT NULL,
                max_v     REAL NOT NULL,
                n         INTEGER NOT NULL,
                PRIMARY KEY (device, channel, bucket_ts)
            )
            """
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

    # ---------- v3.8.0-⑥ 降采样 / 保留策略 ----------
    def rollup(self, bucket_s: int = 60, until_ts: float | None = None) -> int:
        """把 [.., until_ts) 的原始点按 bucket_s 聚合写入 measurements_1m。

        只聚合完整桶（bucket 右边界 <= until_ts）；重复调用幂等（覆盖重算）。
        返回写入/更新的桶数。
        """
        bucket = max(1, int(bucket_s))
        until = float(until_ts if until_ts is not None else time.time())
        with self._lock:
            cur = self._conn.execute(
                """
                INSERT INTO measurements_1m
                    (device, channel, bucket_ts, avg_v, min_v, max_v, n)
                SELECT device, channel, b, AVG(value), MIN(value), MAX(value),
                       COUNT(*)
                FROM (
                    SELECT device, channel, value,
                           CAST(ts / :bucket AS INTEGER) * :bucket AS b
                    FROM measurements
                )
                WHERE b + :bucket <= :until
                GROUP BY device, channel, b
                ON CONFLICT (device, channel, bucket_ts) DO UPDATE SET
                    avg_v = excluded.avg_v, min_v = excluded.min_v,
                    max_v = excluded.max_v, n = excluded.n
                """,
                {"bucket": bucket, "until": until},
            )
            self._conn.commit()
            return int(cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0)

    def query_rollup(self, device: str, channel: str | None = None,
                     since_ts: float | None = None,
                     limit: int = 2000) -> list["RollupPoint"]:
        sql = ("SELECT device, channel, bucket_ts, avg_v, min_v, max_v, n "
               "FROM measurements_1m WHERE device = ?")
        args: list = [device]
        if channel:
            sql += " AND channel = ?"
            args.append(channel)
        if since_ts:
            sql += " AND bucket_ts >= ?"
            args.append(since_ts)
        sql += " ORDER BY bucket_ts ASC LIMIT ?"
        args.append(limit)
        with self._lock:
            rows = self._conn.execute(sql, args).fetchall()
        return [RollupPoint(r[0], r[1], r[2], r[3], r[4], r[5], int(r[6]))
                for r in rows]

    def count_rollup(self, device: str | None = None) -> int:
        sql = "SELECT COUNT(*) FROM measurements_1m"
        args: list = []
        if device:
            sql += " WHERE device = ?"
            args.append(device)
        with self._lock:
            return int(self._conn.execute(sql, args).fetchone()[0])

    def prune_rollup(self, cutoff_ts: float) -> int:
        with self._lock:
            cur = self._conn.execute(
                "DELETE FROM measurements_1m WHERE bucket_ts < ?", (cutoff_ts,))
            self._conn.commit()
            return int(cur.rowcount)

    def maintain(self, raw_retention_s: float | None = None,
                 rollup_retention_s: float | None = None,
                 bucket_s: int = 60, now: float | None = None) -> dict:
        """降采样 + 保留期清理（幂等，可周期调用）。

        raw_retention_s=None → 不清理原始点；rollup_retention_s=None → 不清理聚合。
        """
        now = float(now if now is not None else time.time())
        rolled = self.rollup(bucket_s=bucket_s, until_ts=now)
        pruned_raw = 0
        pruned_rollup = 0
        if raw_retention_s is not None:
            pruned_raw = self.prune_older_than(now - float(raw_retention_s))
        if rollup_retention_s is not None:
            pruned_rollup = self.prune_rollup(now - float(rollup_retention_s))
        return {"rolled_buckets": rolled, "pruned_raw": pruned_raw,
                "pruned_rollup": pruned_rollup}

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


@dataclass
class RollupPoint:
    """分钟聚合点 — 长期趋势查询结果。"""
    device: str
    channel: str
    bucket_ts: float
    avg: float
    min: float
    max: float
    n: int

    def as_dict(self) -> dict:
        return {"t": self.bucket_ts, "ch": self.channel, "avg": self.avg,
                "min": self.min, "max": self.max, "n": self.n}


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
