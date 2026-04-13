"""
Import versioning — snapshot store data before each import for rollback.

Before every merge, we save a snapshot of the affected table for the store.
Users can list snapshots and roll back to any previous version.
"""

import json
import logging
import uuid
from datetime import datetime, timezone

from app.core.database import get_duckdb_connection, get_sqlite_connection

logger = logging.getLogger(__name__)

_SNAPSHOT_TABLE_PREFIX = "_snapshot_"
_MAX_SNAPSHOTS_PER_STORE = 10


def _snapshot_table_name(snapshot_id: str, data_type: str) -> str:
    """Build a deterministic snapshot table name."""
    safe_id = snapshot_id.replace("-", "")
    return f"{_SNAPSHOT_TABLE_PREFIX}{data_type}_{safe_id}"


def create_snapshot(store_id: str, data_type: str, import_id: str) -> str | None:
    """Snapshot the current state of a store's table before import.

    Returns the snapshot_id or None if the table is empty (nothing to snapshot).
    """
    conn = get_duckdb_connection()

    row_count = conn.execute(
        f"SELECT COUNT(*) FROM {data_type} WHERE store_id = ?",
        [store_id],
    ).fetchone()

    if not row_count or row_count[0] == 0:
        logger.info("No existing data in %s for store %s — skipping snapshot", data_type, store_id)
        return None

    snapshot_id = str(uuid.uuid4())
    snap_table = _snapshot_table_name(snapshot_id, data_type)

    conn.execute(
        f"CREATE TABLE {snap_table} AS SELECT * FROM {data_type} WHERE store_id = ?",
        [store_id],
    )

    sqlite = get_sqlite_connection()
    sqlite.execute(
        """INSERT INTO import_snapshots
           (id, store_id, data_type, import_id, row_count, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            snapshot_id,
            store_id,
            data_type,
            import_id,
            row_count[0],
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    sqlite.commit()

    logger.info(
        "Created snapshot %s for %s/%s (%d rows)",
        snapshot_id, store_id, data_type, row_count[0],
    )

    _prune_old_snapshots(store_id, data_type)
    return snapshot_id


def list_snapshots(store_id: str) -> list[dict]:
    """List all available snapshots for a store, newest first."""
    sqlite = get_sqlite_connection()
    rows = sqlite.execute(
        """SELECT id, data_type, import_id, row_count, created_at
           FROM import_snapshots
           WHERE store_id = ?
           ORDER BY created_at DESC""",
        (store_id,),
    ).fetchall()

    return [
        {
            "snapshot_id": r["id"],
            "data_type": r["data_type"],
            "import_id": r["import_id"],
            "row_count": r["row_count"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def rollback_to_snapshot(store_id: str, snapshot_id: str) -> dict:
    """Restore store data from a snapshot, replacing current data.

    Returns summary of the rollback operation.
    """
    sqlite = get_sqlite_connection()
    snap_row = sqlite.execute(
        "SELECT id, data_type, row_count FROM import_snapshots WHERE id = ? AND store_id = ?",
        (snapshot_id, store_id),
    ).fetchone()

    if not snap_row:
        raise ValueError(f"Snapshot {snapshot_id} not found for store {store_id}")

    data_type = snap_row["data_type"]
    snap_table = _snapshot_table_name(snapshot_id, data_type)

    conn = get_duckdb_connection()

    # Check snapshot table exists in DuckDB
    tables = conn.execute("SHOW TABLES").fetchall()
    table_names = [t[0] for t in tables]
    if snap_table not in table_names:
        raise ValueError(f"Snapshot data table {snap_table} no longer exists")

    # Get current row count before rollback
    current_count = conn.execute(
        f"SELECT COUNT(*) FROM {data_type} WHERE store_id = ?",
        [store_id],
    ).fetchone()[0]

    # Delete current data and replace with snapshot
    conn.execute(
        f"DELETE FROM {data_type} WHERE store_id = ?",
        [store_id],
    )
    conn.execute(
        f"INSERT INTO {data_type} SELECT * FROM {snap_table}"
    )

    restored_count = conn.execute(
        f"SELECT COUNT(*) FROM {data_type} WHERE store_id = ?",
        [store_id],
    ).fetchone()[0]

    logger.info(
        "Rolled back %s for store %s: %d rows → %d rows (snapshot %s)",
        data_type, store_id, current_count, restored_count, snapshot_id,
    )

    return {
        "snapshot_id": snapshot_id,
        "data_type": data_type,
        "rows_before_rollback": current_count,
        "rows_after_rollback": restored_count,
    }


def delete_snapshot(store_id: str, snapshot_id: str) -> None:
    """Delete a specific snapshot."""
    sqlite = get_sqlite_connection()
    snap_row = sqlite.execute(
        "SELECT data_type FROM import_snapshots WHERE id = ? AND store_id = ?",
        (snapshot_id, store_id),
    ).fetchone()

    if not snap_row:
        return

    snap_table = _snapshot_table_name(snapshot_id, snap_row["data_type"])
    conn = get_duckdb_connection()
    try:
        conn.execute(f"DROP TABLE IF EXISTS {snap_table}")
    except Exception as exc:
        logger.warning("Could not drop snapshot table %s: %s", snap_table, exc)

    sqlite.execute("DELETE FROM import_snapshots WHERE id = ?", (snapshot_id,))
    sqlite.commit()


def _prune_old_snapshots(store_id: str, data_type: str) -> None:
    """Keep only the most recent N snapshots per store+data_type."""
    sqlite = get_sqlite_connection()
    rows = sqlite.execute(
        """SELECT id FROM import_snapshots
           WHERE store_id = ? AND data_type = ?
           ORDER BY created_at DESC""",
        (store_id, data_type),
    ).fetchall()

    if len(rows) <= _MAX_SNAPSHOTS_PER_STORE:
        return

    to_delete = rows[_MAX_SNAPSHOTS_PER_STORE:]
    for r in to_delete:
        delete_snapshot(store_id, r["id"])
    logger.info(
        "Pruned %d old snapshots for %s/%s", len(to_delete), store_id, data_type,
    )
