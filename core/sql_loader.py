"""
SQL 数据库加载引擎 — SQLAlchemy 统一接入 MySQL/PostgreSQL/SQL Server
输出接口与 DataLoader 保持一致: {table_name: DataFrame}
"""

from typing import Dict, List, Optional, Any
import pandas as pd
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine


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


def build_connection_string(config: dict) -> str:
    db_type = config["db_type"]
    driver = DB_TYPE_MAP.get(db_type)
    if not driver:
        raise ValueError(f"不支持的数据库类型: {db_type}")
    host = config.get("host", "localhost")
    port = config.get("port", DEFAULT_PORTS.get(db_type, 3306))
    database = config.get("database", "")
    user = config.get("user", "")
    password = config.get("password", "")
    if db_type == "mssql":
        return f"{driver}://{user}:{password}@{host}:{port}/{database}?driver=ODBC+Driver+17+for+SQL+Server"
    return f"{driver}://{user}:{password}@{host}:{port}/{database}"


class SqlLoader:
    def __init__(self):
        self.engine: Optional[Engine] = None
        self.connection_config: Dict[str, Any] = {}
        self.tables: Dict[str, pd.DataFrame] = {}
        self.metadata: Dict[str, Any] = {}

    def connect(self, config: dict) -> bool:
        self.connection_config = config.copy()
        conn_str = build_connection_string(config)
        self.engine = create_engine(conn_str, pool_pre_ping=True)
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            self.engine = None
            raise

    def get_table_names(self) -> List[str]:
        if not self.engine:
            raise RuntimeError("未连接到数据库")
        insp = inspect(self.engine)
        tables = insp.get_table_names()
        views = insp.get_view_names()
        return tables + views

    def load(self, table_names: Optional[List[str]] = None) -> Dict[str, pd.DataFrame]:
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
                    from sqlalchemy import text as sa_text
                    # 安全引用表名（双引号包裹，来自 inspect 返回值，非用户输入）
                    safe_name = name.replace('"', '""')
                    df = pd.read_sql_query(
                        sa_text(f'SELECT * FROM "{safe_name}"'), self.engine
                    )
                    result[name] = df
                except Exception as e:
                    raise RuntimeError(f"读取表 '{name}' 失败: {e}")
        self.tables = result
        self._extract_metadata()
        return result

    def get_preview(self, table_name: str, rows: int = 100) -> pd.DataFrame:
        """预览表数据 — 全部使用 SQLAlchemy ORM 参数化查询，杜绝 SQL 注入。
        优先使用 MetaData.reflect 反射表结构，回退到 pd.read_sql_table。"""
        if not self.engine:
            raise RuntimeError("未连接到数据库")
        try:
            from sqlalchemy import Table, MetaData, select
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
                raise RuntimeError(f"预览表 '{table_name}' 失败: {e}")

    def get_table_names_like(self, pattern: str) -> List[str]:
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
        try:
            self.disconnect()
        except Exception:
            pass

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
