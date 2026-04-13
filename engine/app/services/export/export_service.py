import logging
import os
import shutil
import tempfile
import time
import zipfile
from datetime import datetime, timezone

from app.core.database import get_duckdb_connection, get_sqlite_connection

logger = logging.getLogger(__name__)

EXPORT_DIR = os.path.join(tempfile.gettempdir(), "novem_exports")
os.makedirs(EXPORT_DIR, exist_ok=True)

# Max age for exported files (1 hour)
_EXPORT_MAX_AGE_SECONDS = 3600


def cleanup_old_exports() -> None:
    """Remove exported files older than _EXPORT_MAX_AGE_SECONDS."""
    now = time.time()
    try:
        for filename in os.listdir(EXPORT_DIR):
            filepath = os.path.join(EXPORT_DIR, filename)
            if os.path.isfile(filepath):
                age = now - os.path.getmtime(filepath)
                if age > _EXPORT_MAX_AGE_SECONDS:
                    os.remove(filepath)
    except OSError:
        logger.debug("Could not clean up export directory")

TABLE_COLUMNS = {
    "orders": [
        "order_id", "order_date", "customer_id", "product_id", "product_name",
        "category", "quantity", "unit_price", "total_price", "discount_amount",
        "currency", "status", "refund_amount", "channel", "region",
    ],
    "customers": [
        "customer_id", "first_order_date", "last_order_date",
        "total_orders", "total_spend", "avg_order_value", "region",
    ],
    "products": [
        "product_id", "product_name", "category", "subcategory",
        "unit_cost", "current_stock", "status",
    ],
    "ad_spend": [
        "date", "channel", "campaign_name", "impressions", "clicks",
        "spend", "currency", "conversions", "revenue_attributed",
    ],
    "reviews": [
        "review_id", "product_id", "customer_id", "review_date",
        "rating", "review_text", "sentiment_score", "sentiment_label",
    ],
}


def export_to_csv(store_id: str, data_type: str, limit: int | None = None) -> tuple[str, int]:
    """Export store data to a CSV file. Returns (file_path, row_count)."""
    cleanup_old_exports()
    conn = get_duckdb_connection()
    columns = TABLE_COLUMNS.get(data_type)
    if not columns:
        raise ValueError(f"Unknown data type: {data_type}")

    col_list = ", ".join(columns)
    query = f"SELECT {col_list} FROM {data_type} WHERE store_id = ?"
    params: list[object] = [store_id]

    if limit:
        query += " LIMIT ?"
        params.append(limit)

    result = conn.execute(query, params)
    rows = result.fetchall()
    row_count = len(rows)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"{data_type}_{store_id[:8]}_{timestamp}.csv"
    filepath = os.path.join(EXPORT_DIR, filename)

    with open(filepath, "w", encoding="utf-8", newline="") as f:
        f.write(",".join(columns) + "\n")
        for row in rows:
            line = ",".join(
                _csv_escape(str(v) if v is not None else "")
                for v in row
            )
            f.write(line + "\n")

    logger.info("Exported %d rows of %s for store %s → %s", row_count, data_type, store_id, filepath)
    return filepath, row_count


def get_export_row_count(store_id: str, data_type: str) -> int:
    conn = get_duckdb_connection()
    row = conn.execute(
        f"SELECT COUNT(*) FROM {data_type} WHERE store_id = ?",
        [store_id],
    ).fetchone()
    return row[0] if row else 0


def generate_summary_report(store_id: str, period: str) -> dict:
    """Generate a summary report with key metrics for the given period."""
    from app.services.dashboard.kpi_calculator import calculate_kpis

    kpis = calculate_kpis(store_id, period)
    conn = get_duckdb_connection()

    # Top products
    top_products = conn.execute(
        """SELECT product_name, SUM(total_price - discount_amount) as revenue, SUM(quantity) as units_sold
           FROM orders WHERE store_id = ?
           GROUP BY product_name
           ORDER BY revenue DESC
           LIMIT 10""",
        [store_id],
    ).fetchall()

    # Top customers
    top_customers = conn.execute(
        """SELECT customer_id, COUNT(DISTINCT order_id) as orders, SUM(total_price - discount_amount) as spend
           FROM orders WHERE store_id = ?
           GROUP BY customer_id
           ORDER BY spend DESC
           LIMIT 10""",
        [store_id],
    ).fetchall()

    # Channel breakdown
    channels = conn.execute(
        """SELECT COALESCE(channel, 'Unknown') as channel,
                  COUNT(DISTINCT order_id) as orders, SUM(total_price - discount_amount) as revenue
           FROM orders WHERE store_id = ?
           GROUP BY channel
           ORDER BY revenue DESC""",
        [store_id],
    ).fetchall()

    return {
        "period": period,
        "kpis": kpis,
        "top_products": [
            {"name": r[0], "revenue": float(r[1]), "units_sold": int(r[2])}
            for r in top_products
        ],
        "top_customers": [
            {"customer_id": r[0], "orders": int(r[1]), "spend": float(r[2])}
            for r in top_customers
        ],
        "channels": [
            {"channel": r[0], "orders": int(r[1]), "revenue": float(r[2])}
            for r in channels
        ],
    }


def _csv_escape(value: str) -> str:
    if "," in value or '"' in value or "\n" in value:
        return '"' + value.replace('"', '""') + '"'
    return value


def export_bulk_csv(store_id: str) -> tuple[str, dict[str, int]]:
    """Export all data tables for a store as a single ZIP of CSVs.

    Returns (zip_path, counts_dict).
    """
    cleanup_old_exports()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    zip_name = f"novem_export_{store_id[:8]}_{timestamp}.zip"
    zip_path = os.path.join(EXPORT_DIR, zip_name)
    counts: dict[str, int] = {}

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for data_type in TABLE_COLUMNS:
            try:
                csv_path, row_count = export_to_csv(store_id, data_type)
                zf.write(csv_path, f"{data_type}.csv")
                counts[data_type] = row_count
                os.remove(csv_path)
            except Exception as exc:
                logger.warning("Bulk export skipped %s: %s", data_type, exc)
                counts[data_type] = 0

    logger.info("Bulk export for %s → %s (%s)", store_id, zip_path, counts)
    return zip_path, counts


def export_to_parquet(store_id: str, data_type: str) -> tuple[str, int]:
    """Export store data to Parquet. Returns (file_path, row_count)."""
    cleanup_old_exports()
    conn = get_duckdb_connection()
    columns = TABLE_COLUMNS.get(data_type)
    if not columns:
        raise ValueError(f"Unknown data type: {data_type}")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"{data_type}_{store_id[:8]}_{timestamp}.parquet"
    filepath = os.path.join(EXPORT_DIR, filename)

    col_list = ", ".join(columns)
    conn.execute(
        f"COPY (SELECT {col_list} FROM {data_type} WHERE store_id = ?) TO ? (FORMAT PARQUET)",
        [store_id, filepath],
    )

    row_count = get_export_row_count(store_id, data_type)
    logger.info("Exported %s to Parquet for store %s → %s", data_type, store_id, filepath)
    return filepath, row_count


def create_backup(store_id: str) -> tuple[str, dict]:
    """Create a full backup ZIP containing DuckDB data (CSVs) + SQLite metadata.

    Returns (zip_path, summary_dict).
    """
    cleanup_old_exports()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    zip_name = f"novem_backup_{store_id[:8]}_{timestamp}.zip"
    zip_path = os.path.join(EXPORT_DIR, zip_name)
    summary: dict = {"store_id": store_id, "timestamp": timestamp, "tables": {}}

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # DuckDB data tables
        for data_type in TABLE_COLUMNS:
            try:
                csv_path, row_count = export_to_csv(store_id, data_type)
                zf.write(csv_path, f"data/{data_type}.csv")
                summary["tables"][data_type] = row_count
                os.remove(csv_path)
            except Exception as exc:
                logger.warning("Backup skipped %s: %s", data_type, exc)

        # SQLite metadata
        sqlite_conn = get_sqlite_connection()
        meta_tables = ["stores", "settings", "user_profile", "import_history",
                       "import_snapshots", "alert_log"]
        for tbl in meta_tables:
            try:
                rows = sqlite_conn.execute(f"SELECT * FROM {tbl}").fetchall()
                cols = [d[0] for d in sqlite_conn.execute(f"SELECT * FROM {tbl} LIMIT 0").description]
                tmp = os.path.join(EXPORT_DIR, f"meta_{tbl}.csv")
                with open(tmp, "w", encoding="utf-8", newline="") as f:
                    f.write(",".join(cols) + "\n")
                    for row in rows:
                        f.write(",".join(_csv_escape(str(v) if v is not None else "") for v in row) + "\n")
                zf.write(tmp, f"metadata/{tbl}.csv")
                summary["tables"][f"meta_{tbl}"] = len(rows)
                os.remove(tmp)
            except Exception as exc:
                logger.debug("Backup metadata skip %s: %s", tbl, exc)

    size_bytes = os.path.getsize(zip_path)
    summary["size_bytes"] = size_bytes
    logger.info("Full backup for %s → %s (%d bytes)", store_id, zip_path, size_bytes)
    return zip_path, summary
