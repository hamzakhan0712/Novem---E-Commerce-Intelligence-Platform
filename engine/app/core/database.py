import logging
import shutil
import sqlite3
import threading
from datetime import datetime

import duckdb

from app.config import DATA_DIR, DUCKDB_PATH, SQLITE_PATH

logger = logging.getLogger(__name__)

_duckdb_conn: duckdb.DuckDBPyConnection | None = None
_sqlite_local = threading.local()
_duckdb_lock = threading.Lock()
_sqlite_lock = threading.Lock()


def _cleanup_stale_wal() -> None:
    """Remove stale DuckDB WAL/tmp files left by a crashed process.

    DuckDB replays the WAL on next open. If the WAL is stale (owning
    process no longer exists), we can safely delete it so the new
    connection can acquire an exclusive lock.
    """
    wal_path = DUCKDB_PATH.with_suffix(".duckdb.wal")
    if not wal_path.exists():
        return
    # Try to open read-write and checkpoint — this flushes the WAL
    try:
        tmp = duckdb.connect(str(DUCKDB_PATH))
        tmp.execute("CHECKPOINT")
        tmp.close()
        logger.info("Flushed stale DuckDB WAL via checkpoint")
    except Exception:
        # Could not open r/w — WAL may be locked by a live process.
        # Attempt to remove the WAL file directly (only works if the
        # owning process has already terminated but the OS released the lock).
        try:
            wal_path.unlink()
            logger.warning("Deleted stale WAL file: %s", wal_path)
        except OSError:
            logger.error(
                "DuckDB WAL file is locked by another process. "
                "If another engine instance is running, stop it first. "
                "WAL path: %s",
                wal_path,
            )


def _check_duckdb_integrity() -> bool:
    """Run integrity check on existing DuckDB file. Returns True if healthy."""
    if not DUCKDB_PATH.exists():
        return True
    _cleanup_stale_wal()
    try:
        test_conn = duckdb.connect(str(DUCKDB_PATH), read_only=True)
        test_conn.execute("PRAGMA database_size")
        test_conn.close()
        logger.info("DuckDB integrity check passed")
        return True
    except Exception as exc:
        logger.error("DuckDB integrity check failed: %s", exc)
        corrupted_name = DUCKDB_PATH.with_suffix(
            f".corrupted.{datetime.now().strftime('%Y%m%d%H%M%S')}"
        )
        shutil.move(str(DUCKDB_PATH), str(corrupted_name))
        logger.warning("Corrupted DuckDB moved to %s", corrupted_name)
        return False


def _check_sqlite_integrity() -> bool:
    """Run integrity check on existing SQLite file. Returns True if healthy."""
    if not SQLITE_PATH.exists():
        return True
    try:
        test_conn = sqlite3.connect(str(SQLITE_PATH))
        result = test_conn.execute("PRAGMA integrity_check").fetchone()
        test_conn.close()
        if result and result[0] == "ok":
            logger.info("SQLite integrity check passed")
            return True
        logger.error("SQLite integrity check returned: %s", result)
    except Exception as exc:
        logger.error("SQLite integrity check failed: %s", exc)
    corrupted_name = SQLITE_PATH.with_suffix(
        f".corrupted.{datetime.now().strftime('%Y%m%d%H%M%S')}"
    )
    shutil.move(str(SQLITE_PATH), str(corrupted_name))
    logger.warning("Corrupted SQLite moved to %s", corrupted_name)
    return False


def run_integrity_checks() -> None:
    """Run integrity checks on both databases before full init."""
    _check_duckdb_integrity()
    _check_sqlite_integrity()


def get_duckdb_connection() -> duckdb.DuckDBPyConnection:
    """Return an isolated cursor from the shared DuckDB connection.

    Each caller gets its own execution context so concurrent queries
    (e.g. from parallel API calls) don't collide with each other.
    """
    global _duckdb_conn
    with _duckdb_lock:
        if _duckdb_conn is None:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            _duckdb_conn = duckdb.connect(str(DUCKDB_PATH))
            logger.info("DuckDB connected: %s", DUCKDB_PATH)
        return _duckdb_conn.cursor()


def get_sqlite_connection() -> sqlite3.Connection:
    """Return a thread-local SQLite connection.

    Each thread gets its own connection to avoid 'bad parameter or API misuse'
    errors from concurrent access on a single connection object.
    """
    conn = getattr(_sqlite_local, "conn", None)
    if conn is None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(SQLITE_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _sqlite_local.conn = conn
        logger.info("SQLite connected (thread-local): %s", SQLITE_PATH)
    return conn


# ── DuckDB Schema (Analytical — store-scoped) ──────────────────────────
# Every analytical table is keyed by store_id, ensuring full data isolation
# between stores. Imports UPSERT into these tables via natural keys.


def init_duckdb_schema() -> None:
    conn = get_duckdb_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            store_id VARCHAR NOT NULL,
            order_id VARCHAR NOT NULL,
            order_date TIMESTAMP NOT NULL,
            customer_id VARCHAR NOT NULL,
            customer_email_hash VARCHAR,
            customer_name_hash VARCHAR,
            product_id VARCHAR NOT NULL,
            product_name VARCHAR,
            category VARCHAR,
            quantity DECIMAL(12,2) NOT NULL,
            unit_price DECIMAL(12,2) NOT NULL,
            total_price DECIMAL(12,2) NOT NULL,
            discount_amount DECIMAL(12,2) DEFAULT 0,
            currency VARCHAR(10) NOT NULL DEFAULT 'INR',
            status VARCHAR NOT NULL DEFAULT 'completed',
            refund_amount DECIMAL(12,2) DEFAULT 0,
            refund_reason VARCHAR,
            channel VARCHAR,
            region VARCHAR,
            line_item_index INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (store_id, order_id, product_id, line_item_index)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            store_id VARCHAR NOT NULL,
            customer_id VARCHAR NOT NULL,
            email_hash VARCHAR,
            name_hash VARCHAR,
            first_order_date TIMESTAMP,
            last_order_date TIMESTAMP,
            total_orders INTEGER DEFAULT 0,
            total_spend DECIMAL(12,2) DEFAULT 0,
            avg_order_value DECIMAL(12,2) DEFAULT 0,
            region VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (store_id, customer_id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            store_id VARCHAR NOT NULL,
            product_id VARCHAR NOT NULL,
            product_name VARCHAR NOT NULL,
            category VARCHAR,
            subcategory VARCHAR,
            parent_product_id VARCHAR,
            unit_cost DECIMAL(12,2),
            current_stock INTEGER,
            status VARCHAR DEFAULT 'active',
            size VARCHAR,
            color VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (store_id, product_id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS ad_spend (
            store_id VARCHAR NOT NULL,
            date DATE NOT NULL,
            channel VARCHAR NOT NULL,
            campaign_name VARCHAR,
            impressions INTEGER DEFAULT 0,
            clicks INTEGER DEFAULT 0,
            spend DECIMAL(12,2) NOT NULL DEFAULT 0,
            currency VARCHAR(3) NOT NULL DEFAULT 'INR',
            conversions INTEGER DEFAULT 0,
            revenue_attributed DECIMAL(12,2) DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (store_id, date, channel, campaign_name)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            store_id VARCHAR NOT NULL,
            review_id VARCHAR NOT NULL,
            product_id VARCHAR NOT NULL,
            customer_id VARCHAR,
            review_date TIMESTAMP NOT NULL,
            rating INTEGER,
            review_text TEXT NOT NULL,
            sentiment_score DECIMAL(4,3),
            sentiment_label VARCHAR,
            aspects VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (store_id, review_id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS stock_levels (
            store_id VARCHAR NOT NULL,
            product_id VARCHAR NOT NULL,
            snapshot_date DATE NOT NULL,
            quantity_on_hand INTEGER NOT NULL DEFAULT 0,
            lead_time_days INTEGER,
            reorder_point INTEGER,
            safety_stock INTEGER,
            warehouse VARCHAR,
            location VARCHAR,
            status VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (store_id, product_id, snapshot_date)
        )
    """)

    logger.info("DuckDB schema initialized")


# ── SQLite Schema (Metadata — user & app data) ─────────────────────────
# Single-user model: one user_profile row, multiple stores underneath.


def init_sqlite_schema() -> None:
    conn = get_sqlite_connection()

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS user_profile (
            id TEXT PRIMARY KEY DEFAULT 'default',
            name TEXT NOT NULL DEFAULT 'User',
            avatar_seed TEXT,
            avatar_photo TEXT,
            email TEXT,
            password_hash TEXT,
            is_setup_complete INTEGER DEFAULT 0,
            currency TEXT DEFAULT 'INR',
            region TEXT DEFAULT 'IN',
            date_format TEXT DEFAULT 'YYYY-MM-DD',
            fiscal_year_start TEXT DEFAULT 'january',
            timezone TEXT DEFAULT 'UTC',
            security_question TEXT,
            security_answer_hash TEXT,
            email_verified INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            expires_at TEXT
        );

        CREATE TABLE IF NOT EXISTS stores (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            platform TEXT NOT NULL DEFAULT 'other',
            url TEXT,
            currency TEXT DEFAULT 'INR',
            timezone TEXT DEFAULT 'UTC',
            industry TEXT DEFAULT 'general',
            description TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS import_history (
            id TEXT PRIMARY KEY,
            store_id TEXT NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
            data_type TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_name TEXT,
            source_path TEXT,
            file_hash TEXT,
            row_count_raw INTEGER DEFAULT 0,
            row_count_new INTEGER DEFAULT 0,
            row_count_updated INTEGER DEFAULT 0,
            row_count_skipped INTEGER DEFAULT 0,
            health_score INTEGER DEFAULT 0,
            health_details TEXT DEFAULT '[]',
            schema_mapping TEXT DEFAULT '[]',
            status TEXT NOT NULL DEFAULT 'completed',
            error_message TEXT,
            imported_at TEXT NOT NULL,
            duration_ms INTEGER
        );

        CREATE TABLE IF NOT EXISTS import_lineage (
            id TEXT PRIMARY KEY,
            import_id TEXT NOT NULL REFERENCES import_history(id) ON DELETE CASCADE,
            step_order INTEGER NOT NULL,
            description TEXT NOT NULL,
            rows_before INTEGER,
            rows_after INTEGER,
            timestamp TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id TEXT PRIMARY KEY,
            store_id TEXT REFERENCES stores(id) ON DELETE SET NULL,
            module TEXT NOT NULL,
            severity TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS import_snapshots (
            id TEXT PRIMARY KEY,
            store_id TEXT NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
            data_type TEXT NOT NULL,
            import_id TEXT,
            row_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS background_tasks (
            id TEXT PRIMARY KEY,
            store_id TEXT REFERENCES stores(id) ON DELETE SET NULL,
            task_type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            progress INTEGER DEFAULT 0,
            error TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS system_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS store_credentials (
            id TEXT PRIMARY KEY,
            store_id TEXT NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
            credential_type TEXT NOT NULL,
            credentials_encrypted TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS webhook_log (
            id TEXT PRIMARY KEY,
            store_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            topic TEXT NOT NULL,
            payload_hash TEXT,
            status TEXT DEFAULT 'received',
            error TEXT,
            received_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sync_schedules (
            id TEXT PRIMARY KEY,
            store_id TEXT NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
            connector_type TEXT NOT NULL,
            data_types TEXT NOT NULL,
            interval_minutes INTEGER NOT NULL DEFAULT 60,
            is_active INTEGER DEFAULT 1,
            last_sync_at TEXT,
            last_sync_status TEXT,
            last_sync_error TEXT,
            next_sync_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS import_errors (
            id TEXT PRIMARY KEY,
            import_id TEXT NOT NULL,
            row_number INTEGER,
            column_name TEXT,
            error_type TEXT NOT NULL,
            error_detail TEXT NOT NULL,
            original_value TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS copilot_feedback (
            id TEXT PRIMARY KEY,
            store_id TEXT NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
            message_id TEXT NOT NULL UNIQUE,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            source TEXT NOT NULL,
            model TEXT,
            rating INTEGER NOT NULL DEFAULT 0,
            correction TEXT,
            question_keywords TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_copilot_feedback_store
            ON copilot_feedback(store_id, rating);
        CREATE INDEX IF NOT EXISTS idx_copilot_feedback_keywords
            ON copilot_feedback(store_id, question_keywords);
    """)

    conn.execute(
        "INSERT OR IGNORE INTO system_meta (key, value) VALUES (?, ?)",
        ("schema_version", "2"),
    )
    conn.execute(
        "INSERT OR IGNORE INTO system_meta (key, value) VALUES (?, ?)",
        ("first_run_completed", "false"),
    )
    # Ensure default user profile exists
    conn.execute(
        "INSERT OR IGNORE INTO user_profile (id, name, created_at) VALUES (?, ?, ?)",
        ("default", "User", datetime.now().isoformat()),
    )

    # Migration: add avatar_photo column if missing
    cols = [r[1] for r in conn.execute("PRAGMA table_info(user_profile)").fetchall()]
    if "avatar_photo" not in cols:
        conn.execute("ALTER TABLE user_profile ADD COLUMN avatar_photo TEXT")

    # Migration: add expires_at column to sessions if missing
    session_cols = [r[1] for r in conn.execute("PRAGMA table_info(sessions)").fetchall()]
    if "expires_at" not in session_cols:
        conn.execute("ALTER TABLE sessions ADD COLUMN expires_at TEXT")

    conn.commit()

    logger.info("SQLite schema initialized")


def close_connections() -> None:
    global _duckdb_conn
    if _duckdb_conn is not None:
        try:
            _duckdb_conn.execute("CHECKPOINT")
            logger.info("DuckDB WAL flushed via checkpoint")
        except Exception as exc:
            logger.warning("DuckDB checkpoint on close failed: %s", exc)
        _duckdb_conn.close()
        _duckdb_conn = None
        logger.info("DuckDB connection closed")
    # Close thread-local SQLite connection for the current thread
    conn = getattr(_sqlite_local, "conn", None)
    if conn is not None:
        conn.close()
        _sqlite_local.conn = None
        logger.info("SQLite connection closed")
