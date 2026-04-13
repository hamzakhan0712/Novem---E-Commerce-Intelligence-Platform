"""
Store management service — CRUD for stores and user profile.

All store metadata lives in SQLite. Analytical data (DuckDB) is keyed by store_id.
"""

import logging
import uuid
from datetime import datetime, timezone

from app.core.database import get_duckdb_connection, get_sqlite_connection
from app.models.stores import (
    CreateStoreRequest,
    StoreDataCounts,
    StoreOut,
    UpdateStoreRequest,
    UpdateUserProfileRequest,
    UserProfileOut,
)
from app.services.ingestion.merge_engine import delete_store_data, get_store_row_counts

logger = logging.getLogger(__name__)


# ── User Profile ────────────────────────────────────────────────────────


def get_user_profile() -> UserProfileOut:
    conn = get_sqlite_connection()
    row = conn.execute("SELECT * FROM user_profile WHERE id = 'default'").fetchone()
    if not row:
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO user_profile (id, name, created_at) VALUES ('default', 'User', ?)",
            (now,),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM user_profile WHERE id = 'default'").fetchone()
    return UserProfileOut(
        id=row["id"],
        name=row["name"],
        avatar_seed=row["avatar_seed"],
        email=row["email"],
        currency=row["currency"],
        region=row["region"],
        date_format=row["date_format"],
        fiscal_year_start=row["fiscal_year_start"],
        timezone=row["timezone"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def update_user_profile(req: UpdateUserProfileRequest) -> UserProfileOut:
    conn = get_sqlite_connection()
    updates: list[str] = []
    params: list = []

    for field in ["name", "avatar_seed", "email", "currency", "region",
                   "date_format", "fiscal_year_start", "timezone"]:
        value = getattr(req, field)
        if value is not None:
            updates.append(f"{field} = ?")
            params.append(value)

    if not updates:
        return get_user_profile()

    updates.append("updated_at = ?")
    params.append(datetime.now(timezone.utc).isoformat())
    params.append("default")

    conn.execute(
        f"UPDATE user_profile SET {', '.join(updates)} WHERE id = ?",
        params,
    )
    conn.commit()
    return get_user_profile()


# ── Store CRUD ──────────────────────────────────────────────────────────


def create_store(req: CreateStoreRequest) -> StoreOut:
    conn = get_sqlite_connection()
    store_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    conn.execute(
        """INSERT INTO stores (id, name, platform, url, currency, timezone, industry,
           description, is_active, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)""",
        (
            store_id, req.name, req.platform.value, req.url,
            req.currency, req.timezone, req.industry.value,
            req.description, now, now,
        ),
    )
    conn.commit()
    logger.info("Created store: %s (%s)", req.name, store_id)
    return get_store(store_id)


def get_store(store_id: str) -> StoreOut:
    conn = get_sqlite_connection()
    row = conn.execute("SELECT * FROM stores WHERE id = ?", (store_id,)).fetchone()
    if not row:
        raise ValueError(f"Store not found: {store_id}")
    return _row_to_store(row, include_data_summary=True)


def list_stores(include_inactive: bool = False) -> list[StoreOut]:
    conn = get_sqlite_connection()
    if include_inactive:
        rows = conn.execute("SELECT * FROM stores ORDER BY created_at DESC").fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM stores WHERE is_active = 1 ORDER BY created_at DESC",
        ).fetchall()
    return [_row_to_store(r, include_data_summary=True) for r in rows]


def update_store(store_id: str, req: UpdateStoreRequest) -> StoreOut:
    conn = get_sqlite_connection()
    existing = conn.execute("SELECT id FROM stores WHERE id = ?", (store_id,)).fetchone()
    if not existing:
        raise ValueError(f"Store not found: {store_id}")

    updates: list[str] = []
    params: list = []

    for field in ["name", "platform", "url", "currency", "timezone", "industry", "description"]:
        value = getattr(req, field)
        if value is not None:
            if hasattr(value, "value"):
                value = value.value
            updates.append(f"{field} = ?")
            params.append(value)

    if not updates:
        return get_store(store_id)

    updates.append("updated_at = ?")
    params.append(datetime.now(timezone.utc).isoformat())
    params.append(store_id)

    conn.execute(
        f"UPDATE stores SET {', '.join(updates)} WHERE id = ?",
        params,
    )
    conn.commit()
    return get_store(store_id)


def deactivate_store(store_id: str) -> None:
    """Soft-deactivate a store (keeps data for potential reactivation)."""
    conn = get_sqlite_connection()
    conn.execute(
        "UPDATE stores SET is_active = 0, updated_at = ? WHERE id = ?",
        (datetime.now(timezone.utc).isoformat(), store_id),
    )
    conn.commit()
    logger.info("Deactivated store: %s", store_id)


def delete_store_permanently(store_id: str) -> dict[str, int]:
    """Permanently delete a store and all its data from both databases."""
    conn = get_sqlite_connection()

    # Delete analytical data from DuckDB
    deleted_counts = delete_store_data(store_id)

    # Delete metadata from SQLite (cascades handle child records)
    conn.execute("DELETE FROM stores WHERE id = ?", (store_id,))
    conn.commit()
    logger.info("Permanently deleted store: %s", store_id)

    return deleted_counts


def get_store_data_counts(store_id: str) -> StoreDataCounts:
    """Get data counts and import stats for a store."""
    counts = get_store_row_counts(store_id)

    conn = get_sqlite_connection()
    import_row = conn.execute(
        "SELECT COUNT(*) as cnt, MAX(imported_at) as last_at "
        "FROM import_history WHERE store_id = ? AND status = 'completed'",
        (store_id,),
    ).fetchone()

    return StoreDataCounts(
        orders=counts.get("orders", 0),
        customers=counts.get("customers", 0),
        products=counts.get("products", 0),
        ad_spend=counts.get("ad_spend", 0),
        reviews=counts.get("reviews", 0),
        stock_levels=counts.get("stock_levels", 0),
        total_imports=import_row["cnt"] if import_row else 0,
        last_import_at=import_row["last_at"] if import_row else None,
    )


def _row_to_store(row, include_data_summary: bool = False) -> StoreOut:
    store = StoreOut(
        id=row["id"],
        name=row["name"],
        platform=row["platform"],
        url=row["url"],
        currency=row["currency"],
        timezone=row["timezone"],
        industry=row["industry"],
        description=row["description"],
        is_active=bool(row["is_active"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )

    if include_data_summary:
        try:
            store.data_summary = get_store_data_counts(row["id"])
        except Exception:
            pass

    return store
