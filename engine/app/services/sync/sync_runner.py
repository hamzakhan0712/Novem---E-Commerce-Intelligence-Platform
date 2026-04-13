import logging
import uuid
from datetime import datetime

from app.core.database import get_sqlite_connection
from app.core.encryption import decrypt_json

logger = logging.getLogger(__name__)


def run_sync(
    store_id: str,
    data_types: list[str],
    schedule_id: str | None = None,
) -> dict:
    """Execute a full sync for a store: fetch from connector → normalize → merge.

    Returns a summary dict with per-data-type row counts.
    """
    conn = get_sqlite_connection()

    cred_row = conn.execute(
        "SELECT credential_type, credentials_encrypted FROM store_credentials "
        "WHERE store_id = ? AND credential_type NOT LIKE 'webhook_%' ORDER BY created_at DESC LIMIT 1",
        (store_id,),
    ).fetchone()

    if not cred_row:
        raise ValueError(f"No connector credentials for store {store_id}")

    cred_type = cred_row["credential_type"]
    creds = decrypt_json(cred_row["credentials_encrypted"])

    # Find last sync time for incremental
    last_sync_at = None
    if schedule_id:
        sched = conn.execute("SELECT last_sync_at FROM sync_schedules WHERE id = ?", (schedule_id,)).fetchone()
        if sched and sched["last_sync_at"]:
            last_sync_at = datetime.fromisoformat(sched["last_sync_at"])

    # Instantiate connector
    from app.api.router_connectors import _get_connector
    connector = _get_connector(cred_type, creds)

    # Import pipeline
    from app.services.ingestion.data_cleaner import clean_dataframe
    from app.services.ingestion.pii_masker import mask_pii
    from app.services.ingestion.merge_engine import merge_into_store

    results: dict[str, int] = {}
    now = datetime.now()

    for dt in data_types:
        try:
            df = connector.fetch_data(dt, since=last_sync_at)
            if df.empty:
                results[dt] = 0
                continue

            df, _actions = clean_dataframe(df, dt)
            # Build identity column mapping for PII masking (columns already canonical)
            col_map = {c: c for c in df.columns}
            df, _hashed = mask_pii(df, col_map)
            merge_into_store(df, store_id, dt, strategy="upsert")

            results[dt] = len(df)

            # Record import history
            conn.execute(
                "INSERT INTO import_history (id, store_id, data_type, source_type, source_name, "
                "row_count_raw, row_count_new, status, imported_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    uuid.uuid4().hex[:12],
                    store_id,
                    dt,
                    cred_type,
                    f"{cred_type}_sync",
                    len(df),
                    len(df),
                    "completed",
                    now.isoformat(),
                ),
            )

            logger.info("Synced %d %s rows for store %s", len(df), dt, store_id)

        except Exception as exc:
            logger.error("Sync failed for %s/%s: %s", store_id, dt, exc)
            results[dt] = -1

    conn.commit()

    # Update schedule record if applicable
    if schedule_id:
        status = "completed" if all(v >= 0 for v in results.values()) else "partial_error"
        error_msg = None
        if status == "partial_error":
            failed = [k for k, v in results.items() if v < 0]
            error_msg = f"Failed data types: {', '.join(failed)}"

        conn.execute(
            "UPDATE sync_schedules SET last_sync_at = ?, last_sync_status = ?, last_sync_error = ?, updated_at = ? WHERE id = ?",
            (now.isoformat(), status, error_msg, now.isoformat(), schedule_id),
        )
        conn.commit()

    return {"store_id": store_id, "results": results, "synced_at": now.isoformat()}
