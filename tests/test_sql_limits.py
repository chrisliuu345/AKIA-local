"""数据库连接超时与 SQL 加载行数上限。"""

from unittest.mock import MagicMock

from sqlalchemy import create_engine, text

from core.sql_loader import (
    CONNECT_TIMEOUT_SECONDS,
    SQL_LOAD_MAX_ROWS,
    SqlLoader,
    connect_args_for,
)


def test_mysql_connect_passes_login_timeout(monkeypatch):
    captured = {}

    def fake_engine(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        engine = MagicMock()
        engine.connect.return_value.__enter__.return_value = MagicMock()
        return engine

    monkeypatch.setattr("core.sql_loader.create_engine", fake_engine)
    assert SqlLoader().connect({
        "db_type": "mysql", "host": "localhost", "port": 3306,
        "database": "demo", "user": "reader", "password": "secret",
    })
    assert captured["pool_timeout"] == CONNECT_TIMEOUT_SECONDS
    assert captured["connect_args"] == connect_args_for("mysql")


def test_mssql_uses_driver_timeout_key():
    assert connect_args_for("mssql") == {"timeout": CONNECT_TIMEOUT_SECONDS}
    assert connect_args_for("postgresql")["connect_timeout"] == CONNECT_TIMEOUT_SECONDS


def test_load_keeps_only_the_row_cap():
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(text("create table readings (id integer)"))
        conn.execute(text(
            "insert into readings (id) values (1), (2), (3), (4), (5)"
        ))
    loader = SqlLoader()
    loader.engine = engine
    loaded = loader.load(["readings"], max_rows=2)
    assert list(loaded["readings"]["id"]) == [1, 2]
    assert loader.metadata["truncated_tables"] == ["readings"]
    assert loader.metadata["row_limit"] == SQL_LOAD_MAX_ROWS
    assert loader.metadata["total_rows"] == 2


def _engine_with_rows(ddl: str, insert: str):
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(text(ddl))
        conn.execute(text(insert))
    return engine


def test_truncation_is_ordered_by_primary_key():
    """没有 ORDER BY 时前 N 行不确定；有主键就按主键，结果才能复现。"""
    engine = _engine_with_rows(
        "create table readings (id integer primary key, v real)",
        "insert into readings (id, v) values (5, 5), (3, 3), (1, 1), (4, 4), (2, 2)",
    )
    loader = SqlLoader()
    loader.engine = engine
    loaded = loader.load(["readings"], max_rows=3)
    assert list(loaded["readings"]["id"]) == [1, 2, 3]
    assert loader.truncated_tables == ["readings"]


def test_unreflected_fallback_is_still_row_limited(monkeypatch):
    engine = _engine_with_rows(
        "create table readings (id integer)",
        "insert into readings (id) values (1), (2), (3), (4), (5)",
    )
    loader = SqlLoader()
    loader.engine = engine

    def reflection_down(name, fetch_rows):
        raise RuntimeError("reflect failed")

    monkeypatch.setattr(loader, "_read_limited", reflection_down)
    fetched = {}
    real = loader._read_unreflected

    def spy(name, fetch_rows):
        fetched["rows"] = fetch_rows
        return real(name, fetch_rows)

    monkeypatch.setattr(loader, "_read_unreflected", spy)
    loaded = loader.load(["readings"], max_rows=2)
    assert fetched["rows"] == 3  # 多取一行判断截断，而不是整表读入
    assert list(loaded["readings"]["id"]) == [1, 2]
    assert loader.truncated_tables == ["readings"]


def test_reconnect_disposes_previous_engine(monkeypatch):
    disposed = []
    first = MagicMock()
    first.dispose.side_effect = lambda: disposed.append(True)
    loader = SqlLoader()
    loader.engine = first
    second = MagicMock()
    second.connect.return_value.__enter__.return_value = MagicMock()
    monkeypatch.setattr("core.sql_loader.create_engine", lambda *a, **k: second)
    assert loader.connect({"db_type": "mysql", "host": "localhost", "port": 3306,
                           "database": "d", "user": "u", "password": "p"})
    assert disposed == [True]
    assert loader.engine is second
