import logging
from datetime import datetime

import pandas as pd

from app.services.connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class DatabaseConnector(BaseConnector):
    """Connector for PostgreSQL external databases.

    Supports two modes:
    - Structured: connect → list tables → select table → import
    - Custom SQL: connect → execute read-only query → import result
    """

    def __init__(self, credentials: dict):
        super().__init__(credentials)
        self.host = credentials["host"]
        self.port = int(credentials.get("port", 5432))
        self.database = credentials["database"]
        self.user = credentials["user"]
        self.password = credentials["password"]

    def _get_connection(self):
        import psycopg2
        return psycopg2.connect(
            host=self.host,
            port=self.port,
            dbname=self.database,
            user=self.user,
            password=self.password,
            connect_timeout=10,
        )

    def test_connection(self) -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
            return True
        except Exception as exc:
            logger.warning("Database connection test failed: %s", exc)
            return False

    def get_available_data_types(self) -> list[str]:
        return ["orders", "customers", "products", "ad_spend", "reviews"]

    def list_tables(self) -> list[str]:
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' ORDER BY table_name"
        )

        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return tables

    def fetch_data(
        self,
        data_type: str,
        since: datetime | None = None,
    ) -> pd.DataFrame:
        table = self.credentials.get("table")
        query = self.credentials.get("query")

        if query:
            return self._execute_query(query)
        elif table:
            safe_table = self._validate_table_name(table)
            sql = f"SELECT * FROM {safe_table}"
            if since:
                sql += f" WHERE updated_at >= %s"
                return self._execute_query(sql, params=(since.isoformat(),))
            return self._execute_query(sql)
        else:
            raise ValueError("Either 'table' or 'query' must be provided in credentials")

    def preview_query(self, query: str, limit: int = 50) -> pd.DataFrame:
        """Execute a read-only query and return limited preview rows."""
        safe_query = self._ensure_read_only(query)
        if "LIMIT" not in safe_query.upper():
            safe_query = f"{safe_query.rstrip(';')} LIMIT {limit}"
        return self._execute_query(safe_query)

    def _execute_query(self, query: str, params: tuple | None = None) -> pd.DataFrame:
        conn = self._get_connection()
        try:
            df = pd.read_sql(query, conn, params=params)
            logger.info("Database query returned %d rows", len(df))
            return df
        finally:
            conn.close()

    @staticmethod
    def _validate_table_name(name: str) -> str:
        """Prevent SQL injection in table names — allow only alphanumeric + underscores."""
        import re
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name):
            raise ValueError(f"Invalid table name: {name}")
        return name

    @staticmethod
    def _ensure_read_only(query: str) -> str:
        """Reject queries that attempt to modify data."""
        import re

        # Strip SQL comments to prevent bypass via /* comment */ DROP TABLE
        stripped = re.sub(r'/\*.*?\*/', ' ', query, flags=re.DOTALL)
        stripped = re.sub(r'--[^\n]*', ' ', stripped)
        stripped = stripped.strip()

        if not stripped:
            raise ValueError("Empty query")

        allowed_starts = {"SELECT", "WITH", "EXPLAIN", "SHOW"}
        forbidden = {"INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE",
                     "CREATE", "GRANT", "REVOKE", "EXEC", "EXECUTE", "CALL",
                     "MERGE", "REPLACE", "RENAME", "COPY"}

        # Check all statements (split on semicolon to catch multi-statement injection)
        statements = [s.strip() for s in stripped.split(";") if s.strip()]
        for stmt in statements:
            first_word = stmt.split()[0].upper() if stmt.split() else ""
            if first_word in forbidden:
                raise ValueError(f"Only SELECT queries are allowed, got: {first_word}")
            if first_word not in allowed_starts:
                raise ValueError(f"Only SELECT queries are allowed, got: {first_word}")
        return query
