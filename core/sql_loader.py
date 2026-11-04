"""
SQL 数据库加载引擎 — SQLAlchemy 统一接入 MySQL/PostgreSQL/SQL Server
输出接口与 DataLoader 保持一致: {table_name: DataFrame}
"""

import contextlib
from typing import Any
import re
from urllib.parse import quote
import pandas as pd
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine


def sanitize_connection_error(err) -> str:
    """将异常消息中的数据库连接串密码打码，防止密码经日志/弹窗泄露。"""
    text = str(err)
    text = re.sub(r"(://[^:/@\s]+:)[^@\s/]+(@)", r"\1******\2", text)
    text = re.sub(r"([A-Za-z_][\w.-]*:)[^@\s/]+(@)", r"\1******\2", text)
    return text


DB_TYPE_MAP = {
    "mysql": "mysql+pymysql",
    "postgresql": "postgresql+psycopg2",
    "mssql": "mssql+pyodbc",
}

DEFAULT_PORTS = {
    "mysql": 3306,
    "postgresql": 5432,
    "mssql": 1433,
}


# 主机只允许主机名、IPv4 或方括号 IPv6。@ / ? / # 会改写连接串的用户或查询参数。
_HOST_RE = re.compile(
    r"^(?:localhost"
    r"|(?:\d{1,3}\.){3}\d{1,3}"
    r"|\[[0-9A-Fa-f:.]+\]"
    r"|[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*)$"
)


def build_connection_string(config: dict) -> str:
    db_type = config["db_type"]
    driver = DB_TYPE_MAP.get(db_type)
    if not driver:
        raise ValueError(f"不支持的数据库类型: {db_type}")
    host = str(config.get("host") or "localhost").strip()
    if not _HOST_RE.fullmatch(host):
        raise ValueError("非法的数据库主机")
    try:
        port = int(config.get("port", DEFAULT_PORTS.get(db_type, 3306)))
    except (TypeError, ValueError) as exc:
        raise ValueError("非法的数据库端口") from exc
    if not 1 <= port <= 65535:
        raise ValueError("非法的数据库端口")
    database = config.get("database", "")
    user = config.get("user", "")
    password = config.get("password", "")
    safe_user = quote(str(user), safe="")
    safe_password = quote(str(password), safe="")
    safe_database = quote(str(database), safe="")
    if db_type == "mssql":
        return (f"{driver}://{safe_user}:{safe_password}@{host}:{port}/"
                f"{safe_database}?driver=ODBC+Driver+17+for+SQL+Server")
    return f"{driver}://{safe_user}:{safe_password}@{host}:{port}/{safe_database}"


class SqlLoader:
    def __init__(self):
        self.engine: Engine | None = None
        self.connection_config: dict[str, Any] = {}
        self.tables: dict[str, pd.DataFrame] = {}
        self.metadata: dict[str, Any] = {}

    def connect(self, config: dict) -> bool:
        self.connection_config = config.copy()
        conn_str = build_connection_string(config)
        self.engine = create_engine(conn_str, pool_pre_ping=True)
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            self.engine = None
            raise RuntimeError(f"数据库连接失败: {sanitize_connection_error(e)}") from e

    def get_table_names(self) -> list[str]:
        if not self.engine:
            raise RuntimeError("未连接到数据库")
        insp = inspect(self.engine)
        tables = insp.get_table_names()
        views = insp.get_view_names()
        return tables + views

    def load(self, table_names: list[str] | None = None) -> dict[str, pd.DataFrame]:
        if not self.engine:
            raise RuntimeError("未连接到数据库")
        if table_names is None:
            table_names = self.get_table_names()
        result = {}
        for name in table_names:
            try:
                df = pd.read_sql_table(name, self.engine)
                result[name] = df
            except Exception:
                try:
                    from sqlalchemy import MetaData, select
                    metadata = MetaData()
                    metadata.reflect(bind=self.engine, only=[name])
                    if name in metadata.tables:
                        tbl = metadata.tables[name]
                        stmt = select(tbl)
                        df = pd.read_sql_query(stmt, self.engine)
                        result[name] = df
                    else:
                        raise ValueError(f"表 '{name}' 反射失败")
                except Exception as e:
                    raise RuntimeError(f"读取表 '{name}' 失败: {sanitize_connection_error(e)}") from e
        self.tables = result
        self._extract_metadata()
        return result

    def get_preview(self, table_name: str, rows: int = 100) -> pd.DataFrame:
        """预览表数据 — 全部使用 SQLAlchemy ORM 参数化查询，杜绝 SQL 注入。
        优先使用 MetaData.reflect 反射表结构，回退到 pd.read_sql_table。"""
        if not self.engine:
            raise RuntimeError("未连接到数据库")
        try:
            from sqlalchemy import MetaData, select
            metadata = MetaData()
            metadata.reflect(bind=self.engine, only=[table_name])
            if table_name in metadata.tables:
                tbl = metadata.tables[table_name]
                stmt = select(tbl).limit(rows)
                return pd.read_sql_query(stmt, self.engine)
            raise ValueError(f"表 '{table_name}' 不存在")
        except Exception:
            try:
                return pd.read_sql_table(table_name, self.engine).head(rows)
            except Exception as e:
                raise RuntimeError(f"预览表 '{table_name}' 失败: {sanitize_connection_error(e)}") from e

    def get_table_names_like(self, pattern: str) -> list[str]:
        all_tables = self.get_table_names()
        return [t for t in all_tables if pattern.lower() in t.lower()]

    def disconnect(self):
        if self.engine:
            self.engine.dispose()
            self.engine = None
        self.tables = {}
        self.metadata = {}

    def __del__(self):
        """析构时自动释放数据库连接"""
        with contextlib.suppress(Exception):
            self.disconnect()

    def is_connected(self) -> bool:
        if not self.engine:
            return False
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def _extract_metadata(self):
        total_rows = sum(len(df) for df in self.tables.values())
        total_cols = {name: len(df.columns) for name, df in self.tables.items()}
        db_name = self.connection_config.get("database", "未知")
        self.metadata = {
            "source": f"数据库: {db_name}",
            "table_count": len(self.tables),
            "total_rows": total_rows,
            "columns_per_table": total_cols,
            "table_names": list(self.tables.keys()),
        }
