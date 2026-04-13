"""Browse analytical data stored in DuckDB with pagination, sorting, and search."""

import logging

from fastapi import APIRouter, HTTPException, Query

from app.core.database import get_duckdb_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data-viewer", tags=["data-viewer"])

ALLOWED_TABLES = {"orders", "customers", "products", "ad_spend", "reviews", "stock_levels"}

SORT_DIRS = {"asc", "desc"}


@router.get("/browse")
def browse_table(
    store_id: str = Query(...),
    table: str = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    sort_by: str | None = Query(None),
    sort_dir: str = Query("desc"),
    search: str | None = Query(None),
):
    if table not in ALLOWED_TABLES:
        raise HTTPException(400, f"Invalid table. Allowed: {', '.join(sorted(ALLOWED_TABLES))}")
    if sort_dir.lower() not in SORT_DIRS:
        raise HTTPException(400, "sort_dir must be 'asc' or 'desc'")

    cur = get_duckdb_connection()

    # Get columns
    col_rows = cur.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = ?",
        [table],
    ).fetchall()
    columns = [r[0] for r in col_rows]
    if not columns:
        return {"success": True, "data": {"columns": [], "rows": [], "total": 0, "page": page, "page_size": page_size}}

    # Validate sort column
    safe_sort = sort_by if sort_by in columns else columns[0]
    direction = sort_dir.upper()

    # Build WHERE clause
    where = "WHERE store_id = ?"
    params: list = [store_id]

    if search:
        text_cols = []
        type_rows = cur.execute(
            "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = ?",
            [table],
        ).fetchall()
        for cname, dtype in type_rows:
            if "VARCHAR" in dtype.upper() or "TEXT" in dtype.upper():
                text_cols.append(cname)
        if text_cols:
            or_clauses = " OR ".join(f'CAST("{c}" AS VARCHAR) ILIKE ?' for c in text_cols)
            where += f" AND ({or_clauses})"
            params.extend([f"%{search}%"] * len(text_cols))

    # Count
    total = cur.execute(f'SELECT COUNT(*) FROM "{table}" {where}', params).fetchone()[0]

    # Fetch page
    offset = (page - 1) * page_size
    query = f'SELECT * FROM "{table}" {where} ORDER BY "{safe_sort}" {direction} LIMIT ? OFFSET ?'
    params.extend([page_size, offset])
    rows_raw = cur.execute(query, params).fetchall()

    rows = []
    for row in rows_raw:
        obj = {}
        for i, col in enumerate(columns):
            val = row[i]
            obj[col] = str(val) if val is not None and not isinstance(val, (int, float, bool)) else val
        rows.append(obj)

    return {
        "success": True,
        "data": {
            "columns": columns,
            "rows": rows,
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }


@router.get("/tables")
def list_tables(store_id: str = Query(...)):
    cur = get_duckdb_connection()
    result = {}
    for tbl in sorted(ALLOWED_TABLES):
        try:
            count = cur.execute(f'SELECT COUNT(*) FROM "{tbl}" WHERE store_id = ?', [store_id]).fetchone()[0]
            result[tbl] = count
        except Exception:
            result[tbl] = 0
    return {"success": True, "data": result}


@router.get("/columns")
def column_info(
    store_id: str = Query(...),
    table: str = Query(...),
):
    """Return column metadata + quick stats for a table."""
    if table not in ALLOWED_TABLES:
        raise HTTPException(400, f"Invalid table. Allowed: {', '.join(sorted(ALLOWED_TABLES))}")

    cur = get_duckdb_connection()
    type_rows = cur.execute(
        "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = ?",
        [table],
    ).fetchall()

    if not type_rows:
        return {"success": True, "data": []}

    total = cur.execute(f'SELECT COUNT(*) FROM "{table}" WHERE store_id = ?', [store_id]).fetchone()[0]
    cols = []
    for cname, dtype in type_rows:
        if cname == "store_id":
            continue
        info: dict = {"name": cname, "type": dtype, "null_count": 0, "distinct_count": 0}
        try:
            stats = cur.execute(
                f'SELECT COUNT(*) FILTER (WHERE "{cname}" IS NULL), '
                f'COUNT(DISTINCT "{cname}") '
                f'FROM "{table}" WHERE store_id = ?',
                [store_id],
            ).fetchone()
            info["null_count"] = stats[0]
            info["distinct_count"] = stats[1]
            info["null_pct"] = round(stats[0] / total * 100, 1) if total > 0 else 0
        except Exception:
            pass
        cols.append(info)
    return {"success": True, "data": cols}


@router.delete("/table-data")
def delete_table_data(
    store_id: str = Query(...),
    table: str = Query(...),
):
    """Delete all rows for a specific table and store."""
    if table not in ALLOWED_TABLES:
        raise HTTPException(400, f"Invalid table. Allowed: {', '.join(sorted(ALLOWED_TABLES))}")

    cur = get_duckdb_connection()
    try:
        count = cur.execute(f'SELECT COUNT(*) FROM "{table}" WHERE store_id = ?', [store_id]).fetchone()[0]
        cur.execute(f'DELETE FROM "{table}" WHERE store_id = ?', [store_id])
        logger.info("Deleted %d rows from %s for store %s", count, table, store_id)
        return {"success": True, "data": {"table": table, "deleted_rows": count}}
    except Exception as e:
        logger.error("Failed to delete data from %s: %s", table, e)
        raise HTTPException(500, f"Failed to delete data from {table}")


@router.delete("/all-data")
def delete_all_data(store_id: str = Query(...)):
    """Delete all analytical data for a store across all tables."""
    cur = get_duckdb_connection()
    results = {}
    total_deleted = 0
    for tbl in sorted(ALLOWED_TABLES):
        try:
            count = cur.execute(f'SELECT COUNT(*) FROM "{tbl}" WHERE store_id = ?', [store_id]).fetchone()[0]
            cur.execute(f'DELETE FROM "{tbl}" WHERE store_id = ?', [store_id])
            results[tbl] = count
            total_deleted += count
        except Exception as e:
            logger.error("Failed to delete data from %s: %s", tbl, e)
            results[tbl] = 0
    logger.info("Cleared all data for store %s: %d total rows deleted", store_id, total_deleted)
    return {"success": True, "data": {"tables": results, "total_deleted": total_deleted}}
