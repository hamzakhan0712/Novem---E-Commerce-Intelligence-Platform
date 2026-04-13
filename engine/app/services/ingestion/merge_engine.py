"""
Merge engine for upserting imported data into store-scoped DuckDB tables.

Handles three strategies:
- UPSERT: insert new rows, update existing rows (matched by primary key)
- APPEND: insert all rows, skip exact duplicates
- REPLACE: delete all store data for this type, then insert
"""

import logging
from datetime import datetime, timezone

import duckdb
import pandas as pd

from app.core.database import get_duckdb_connection
from app.models.ingestion import MergeResult

logger = logging.getLogger(__name__)

# Natural primary keys per data type (excluding store_id which is always included)
TABLE_KEYS: dict[str, list[str]] = {
    "orders": ["order_id", "product_id", "line_item_index"],
    "customers": ["customer_id"],
    "products": ["product_id"],
    "ad_spend": ["date", "channel", "campaign_name"],
    "reviews": ["review_id"],
    "stock_levels": ["product_id", "snapshot_date"],
}

# NOT NULL columns per table with default values (None = required, no default → drop row)
TABLE_NOT_NULL_DEFAULTS: dict[str, dict[str, object | None]] = {
    "orders": {
        "order_id": None,
        "order_date": None,
        "customer_id": None,
        "product_id": None,
        "quantity": 1,
        "unit_price": 0,
        "total_price": 0,
        "currency": "INR",
        "status": "completed",
    },
    "customers": {
        "customer_id": None,
    },
    "products": {
        "product_id": None,
        "product_name": None,
    },
    "ad_spend": {
        "date": None,
        "channel": None,
        "spend": 0,
        "currency": "INR",
    },
    "reviews": {
        "review_id": None,
        "product_id": None,
        "review_date": None,
        "review_text": None,
    },
    "stock_levels": {
        "product_id": None,
        "snapshot_date": None,
        "quantity_on_hand": 0,
    },
}


ALLOWED_TABLES = frozenset(TABLE_KEYS.keys())


def _validate_table_name(data_type: str) -> str:
    """Validate data_type against allowlist before use in SQL."""
    if data_type not in ALLOWED_TABLES:
        raise ValueError(f"Invalid data type: {data_type!r}. Allowed: {', '.join(sorted(ALLOWED_TABLES))}")
    return data_type


def merge_into_store(
    df: pd.DataFrame,
    store_id: str,
    data_type: str,
    strategy: str = "upsert",
) -> MergeResult:
    """Merge a cleaned DataFrame into the store's DuckDB table."""
    _validate_table_name(data_type)
    if strategy == "replace":
        return _strategy_replace(df, store_id, data_type)
    if strategy == "append":
        return _strategy_append(df, store_id, data_type)
    return _strategy_upsert(df, store_id, data_type)


def _strategy_upsert(
    df: pd.DataFrame,
    store_id: str,
    data_type: str,
) -> MergeResult:
    """Insert new rows, update existing rows matched by natural keys."""
    conn = get_duckdb_connection()
    keys = TABLE_KEYS.get(data_type, [])

    if not keys:
        return _strategy_append(df, store_id, data_type)

    # Add store_id and timestamps
    df = df.copy()
    df["store_id"] = store_id
    now_ts = datetime.now(timezone.utc).isoformat()
    df["updated_at"] = pd.Timestamp(now_ts)
    if "created_at" not in df.columns:
        df["created_at"] = pd.Timestamp(now_ts)

    # Get existing keys for this store
    key_cols = ", ".join(keys)
    existing_df = conn.execute(
        f"SELECT {key_cols} FROM {data_type} WHERE store_id = ?",  # noqa: S608
        [store_id],
    ).fetchdf()

    if existing_df.empty:
        # No existing data — pure insert
        _insert_df(conn, df, data_type)
        return MergeResult(
            rows_new=len(df),
            rows_updated=0,
            rows_skipped=0,
            total_processed=len(df),
        )

    # Cast key columns to string for safe comparison
    for k in keys:
        if k in df.columns:
            df[k] = df[k].astype(str)
        if k in existing_df.columns:
            existing_df[k] = existing_df[k].astype(str)

    # Split into new vs existing
    merged = df.merge(existing_df, on=keys, how="left", indicator=True)
    new_rows = merged[merged["_merge"] == "left_only"].drop(columns=["_merge"])
    existing_rows = merged[merged["_merge"] == "both"].drop(columns=["_merge"])

    rows_new = len(new_rows)
    rows_updated = 0

    # Insert new rows
    if rows_new > 0:
        _insert_df(conn, new_rows, data_type)

    # Update existing rows
    if len(existing_rows) > 0:
        non_key_cols = [c for c in df.columns if c not in keys and c != "store_id" and c != "created_at"]
        if non_key_cols:
            rows_updated = _update_rows(conn, existing_rows, store_id, data_type, keys, non_key_cols)

    return MergeResult(
        rows_new=rows_new,
        rows_updated=rows_updated,
        rows_skipped=len(df) - rows_new - rows_updated,
        total_processed=len(df),
    )


def _strategy_append(
    df: pd.DataFrame,
    store_id: str,
    data_type: str,
) -> MergeResult:
    """Insert all rows, skip exact duplicates."""
    conn = get_duckdb_connection()
    keys = TABLE_KEYS.get(data_type, [])

    df = df.copy()
    df["store_id"] = store_id
    now_ts = datetime.now(timezone.utc).isoformat()
    df["created_at"] = pd.Timestamp(now_ts)
    df["updated_at"] = pd.Timestamp(now_ts)

    # Remove rows that already exist based on natural keys
    if keys:
        key_cols = ", ".join(keys)
        existing_df = conn.execute(
            f"SELECT {key_cols} FROM {data_type} WHERE store_id = ?",  # noqa: S608
            [store_id],
        ).fetchdf()

        if not existing_df.empty:
            for k in keys:
                if k in df.columns:
                    df[k] = df[k].astype(str)
                if k in existing_df.columns:
                    existing_df[k] = existing_df[k].astype(str)

            before = len(df)
            merged = df.merge(existing_df, on=keys, how="left", indicator=True)
            df = merged[merged["_merge"] == "left_only"].drop(columns=["_merge"])
            skipped = before - len(df)
        else:
            skipped = 0
    else:
        skipped = 0

    rows_new = len(df)
    if rows_new > 0:
        _insert_df(conn, df, data_type)

    return MergeResult(
        rows_new=rows_new,
        rows_updated=0,
        rows_skipped=skipped,
        total_processed=rows_new + skipped,
    )


def _strategy_replace(
    df: pd.DataFrame,
    store_id: str,
    data_type: str,
) -> MergeResult:
    """Delete all store data for this type, then insert."""
    conn = get_duckdb_connection()

    conn.execute(
        f"DELETE FROM {data_type} WHERE store_id = ?",  # noqa: S608
        [store_id],
    )

    df = df.copy()
    df["store_id"] = store_id
    now_ts = datetime.now(timezone.utc).isoformat()
    df["created_at"] = pd.Timestamp(now_ts)
    df["updated_at"] = pd.Timestamp(now_ts)

    _insert_df(conn, df, data_type)

    return MergeResult(
        rows_new=len(df),
        rows_updated=0,
        rows_skipped=0,
        total_processed=len(df),
    )


def _enforce_not_nulls(df: pd.DataFrame, table_name: str) -> tuple[pd.DataFrame, int, list[dict]]:
    """Fill defaults for NOT NULL columns and drop rows missing required values.

    Returns (cleaned_df, rows_dropped, error_details).
    error_details is a list of dicts with row_number, column_name, error_type.
    """
    not_null_spec = TABLE_NOT_NULL_DEFAULTS.get(table_name, {})
    if not not_null_spec:
        return df, 0, []

    df = df.copy()
    required_cols: list[str] = []

    for col, default_val in not_null_spec.items():
        if col not in df.columns:
            continue
        if default_val is not None:
            df[col] = df[col].fillna(default_val)
        else:
            required_cols.append(col)

    if not required_cols:
        return df, 0, []

    present = [c for c in required_cols if c in df.columns]
    if not present:
        return df, 0, []

    # Identify which rows will be dropped and why
    error_details: list[dict] = []
    null_mask = df[present].isna().any(axis=1)
    if null_mask.any():
        for idx in df.index[null_mask]:
            for col in present:
                if pd.isna(df.at[idx, col]):
                    error_details.append({
                        "row_number": int(idx) + 1,
                        "column_name": col,
                        "error_type": "NULL_REQUIRED_FIELD",
                        "error_detail": f"Required column '{col}' is NULL",
                        "original_value": None,
                    })

    before = len(df)
    df = df.dropna(subset=present)
    dropped = before - len(df)
    if dropped > 0:
        logger.warning(
            "Dropped %d rows from '%s' due to NULL values in required columns: %s",
            dropped, table_name, ", ".join(present),
        )
    return df, dropped, error_details


def _insert_df(conn, df: pd.DataFrame, table_name: str) -> None:
    """Insert a DataFrame into a DuckDB table, matching only existing columns."""
    # Enforce NOT NULL constraints before inserting
    df, dropped, _error_details = _enforce_not_nulls(df, table_name)
    if df.empty:
        logger.warning("No rows to insert into '%s' after NOT NULL enforcement", table_name)
        return

    # Get table columns to ensure alignment
    table_cols = [
        row[0] for row in conn.execute(
            f"SELECT column_name FROM information_schema.columns WHERE table_name = ?",
            [table_name],
        ).fetchall()
    ]

    # Only include columns that exist in the table
    insert_cols = [c for c in table_cols if c in df.columns]
    insert_df = df[insert_cols]

    conn.register("_merge_import_df", insert_df)
    col_list = ", ".join(insert_cols)
    try:
        conn.execute(f"INSERT INTO {table_name} ({col_list}) SELECT {col_list} FROM _merge_import_df")  # noqa: S608
    except duckdb.ConstraintException as exc:
        conn.unregister("_merge_import_df")
        raise RuntimeError(
            f"Data constraint violation inserting into '{table_name}': {exc}. "
            "Check that required columns (NOT NULL) have valid values."
        ) from exc
    except duckdb.TransactionException as exc:
        conn.unregister("_merge_import_df")
        if "being used by another process" in str(exc):
            raise RuntimeError(
                "DuckDB write failed — the database file is locked by another process. "
                "Stop any other running engine instances and try again."
            ) from exc
        raise
    conn.unregister("_merge_import_df")


def _update_rows(
    conn,
    df: pd.DataFrame,
    store_id: str,
    table_name: str,
    keys: list[str],
    update_cols: list[str],
) -> int:
    """Update existing rows using a temp table + UPDATE FROM pattern."""
    # Filter update_cols to only columns that exist in the actual table
    table_cols = {
        row[0] for row in conn.execute(
            f"SELECT column_name FROM information_schema.columns WHERE table_name = ?",
            [table_name],
        ).fetchall()
    }
    update_cols = [c for c in update_cols if c in table_cols and c in df.columns]

    if not update_cols:
        return 0

    temp_name = f"_tmp_update_{table_name}"
    conn.register(temp_name, df)

    set_clause = ", ".join(f"{c} = {temp_name}.{c}" for c in update_cols)
    key_clause = " AND ".join(
        f"{table_name}.{k} = {temp_name}.{k}" for k in keys
    )

    conn.execute(
        f"UPDATE {table_name} SET {set_clause} "  # noqa: S608
        f"FROM {temp_name} "
        f"WHERE {table_name}.store_id = ? AND {key_clause}",
        [store_id],
    )
    conn.unregister(temp_name)

    return len(df)


def delete_store_data(store_id: str, data_type: str | None = None) -> dict[str, int]:
    """Delete all data for a store, or just one data type. Returns counts deleted."""
    conn = get_duckdb_connection()
    tables = [data_type] if data_type else list(TABLE_KEYS.keys())
    result: dict[str, int] = {}

    for table in tables:
        try:
            count = conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE store_id = ?",  # noqa: S608
                [store_id],
            ).fetchone()[0]
            conn.execute(
                f"DELETE FROM {table} WHERE store_id = ?",  # noqa: S608
                [store_id],
            )
            result[table] = count
        except Exception as e:
            logger.warning("Failed to delete from %s for store %s: %s", table, store_id, e)
            result[table] = 0

    return result


def get_store_row_counts(store_id: str) -> dict[str, int]:
    """Get row counts for all tables for a given store."""
    conn = get_duckdb_connection()
    counts: dict[str, int] = {}
    for table in TABLE_KEYS:
        try:
            row = conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE store_id = ?",  # noqa: S608
                [store_id],
            ).fetchone()
            counts[table] = row[0] if row else 0
        except Exception:
            counts[table] = 0
    return counts


def save_import_errors(import_id: str, errors: list[dict]) -> None:
    """Persist row-level import errors to the SQLite import_errors table."""
    if not errors:
        return
    from app.core.database import get_sqlite_connection
    import uuid as _uuid

    conn = get_sqlite_connection()
    now = datetime.now(timezone.utc).isoformat()
    for err in errors:
        conn.execute(
            "INSERT INTO import_errors (id, import_id, row_number, column_name, "
            "error_type, error_detail, original_value, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(_uuid.uuid4()),
                import_id,
                err.get("row_number"),
                err.get("column_name"),
                err.get("error_type", "UNKNOWN"),
                err.get("error_detail", ""),
                str(err.get("original_value")) if err.get("original_value") is not None else None,
                now,
            ),
        )
    conn.commit()
    logger.info("Saved %d import errors for import %s", len(errors), import_id)
