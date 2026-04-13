import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.database import get_sqlite_connection
from app.core.encryption import decrypt_json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/connectors", tags=["connectors"])


class SyncRequest(BaseModel):
    store_id: str
    data_types: list[str] = ["orders", "customers", "products"]


class TestConnectionRequest(BaseModel):
    credential_type: str
    credentials: dict


class PreviewQueryRequest(BaseModel):
    store_id: str
    query: str
    limit: int = 50


class ImportTablesRequest(BaseModel):
    store_id: str
    tables: list[dict]  # [{"table": "orders_raw", "data_type": "orders"}, ...]


def _get_connector(cred_type: str, creds: dict):
    if cred_type == "shopify_api":
        from app.services.connectors.shopify_connector import ShopifyConnector
        return ShopifyConnector(creds)
    elif cred_type == "google_sheets_api":
        from app.services.connectors.google_sheets_connector import GoogleSheetsApiConnector
        return GoogleSheetsApiConnector(creds)
    elif cred_type == "postgresql":
        from app.services.connectors.database_connector import DatabaseConnector
        return DatabaseConnector(creds)
    else:
        raise ValueError(f"Unknown connector type: {cred_type}")


def _load_store_connector(store_id: str):
    """Load the connector for a store from its saved credentials."""
    conn = get_sqlite_connection()
    row = conn.execute(
        "SELECT credential_type, credentials_encrypted FROM store_credentials "
        "WHERE store_id = ? AND credential_type NOT LIKE 'webhook_%' ORDER BY created_at DESC LIMIT 1",
        (store_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="No connector credentials found for this store")

    creds = decrypt_json(row["credentials_encrypted"])
    return _get_connector(row["credential_type"], creds), row["credential_type"]


@router.post("/sync")
def trigger_sync(req: SyncRequest):
    """Trigger an immediate sync for a store's configured connector."""
    from app.services.sync.sync_runner import run_sync

    try:
        result = run_sync(req.store_id, req.data_types)
        return {"success": True, "data": result}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Sync failed for store %s: %s", req.store_id, exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/status/{store_id}")
def get_connector_status(store_id: str):
    """Return last sync status and next scheduled sync for a store."""
    conn = get_sqlite_connection()

    creds = conn.execute(
        "SELECT credential_type, created_at FROM store_credentials "
        "WHERE store_id = ? AND credential_type NOT LIKE 'webhook_%'",
        (store_id,),
    ).fetchall()

    schedule = conn.execute(
        "SELECT * FROM sync_schedules WHERE store_id = ? AND is_active = 1",
        (store_id,),
    ).fetchone()

    return {
        "success": True,
        "data": {
            "connected": len(creds) > 0,
            "connector_types": [r["credential_type"] for r in creds],
            "schedule": dict(schedule) if schedule else None,
        },
    }


@router.post("/test-connection")
def test_connection(req: TestConnectionRequest):
    """Test connector credentials without saving them."""
    try:
        connector = _get_connector(req.credential_type, req.credentials)
        ok = connector.test_connection()
        msg = "Connection successful" if ok else "Connection failed — check credentials"
        return {"success": True, "data": {"connected": ok, "message": msg}}
    except Exception as exc:
        return {"success": True, "data": {"connected": False, "message": str(exc)}}


@router.get("/available-data/{store_id}")
def get_available_data(store_id: str):
    """List data types available from the store's connector."""
    connector, cred_type = _load_store_connector(store_id)
    return {
        "success": True,
        "data": {
            "connector_type": cred_type,
            "data_types": connector.get_available_data_types(),
        },
    }


@router.get("/{store_id}/tables")
def list_tables(store_id: str):
    """List tables from a database connector."""
    connector, cred_type = _load_store_connector(store_id)

    if cred_type not in ("postgresql",):
        raise HTTPException(status_code=400, detail="Table listing is only available for database connectors")

    tables = connector.list_tables()
    return {"success": True, "data": {"tables": tables}}


@router.post("/{store_id}/preview-query")
def preview_query(store_id: str, req: PreviewQueryRequest):
    """Preview results of a SQL query against the store's database connector."""
    connector, cred_type = _load_store_connector(store_id)

    if cred_type not in ("postgresql",):
        raise HTTPException(status_code=400, detail="Query preview is only available for database connectors")

    try:
        df = connector.preview_query(req.query, req.limit)
        return {
            "success": True,
            "data": {
                "columns": list(df.columns),
                "rows": df.head(req.limit).values.tolist(),
                "total_rows": len(df),
            },
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Query failed: {exc}")


@router.post("/{store_id}/import-tables")
def import_tables(store_id: str, req: ImportTablesRequest):
    """Import multiple tables from a database connector, each mapped to a data type."""
    import pandas as pd

    from app.services.ingestion.column_mapper import map_columns
    from app.services.ingestion.schema_detector import detect_schema
    from app.models.ingestion import DataType as DataTypeEnum

    connector, cred_type = _load_store_connector(store_id)

    if cred_type not in ("postgresql",):
        raise HTTPException(status_code=400, detail="Table import is only available for database connectors")

    if len(req.tables) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 tables per batch")

    results = []
    for entry in req.tables:
        table_name = entry.get("table")
        data_type = entry.get("data_type")

        if not table_name:
            continue

        try:
            df = connector.preview_query(f'SELECT * FROM "{table_name}"', limit=None)  # noqa: S608

            if df.empty:
                results.append({
                    "table": table_name,
                    "status": "skipped",
                    "message": "Table is empty",
                })
                continue

            headers = list(df.columns)

            if not data_type:
                detected_type, _, _ = detect_schema(headers)
                data_type = detected_type.value if hasattr(detected_type, "value") else detected_type

            dt_enum = DataTypeEnum(data_type) if isinstance(data_type, str) else data_type
            suggested_mappings = map_columns(headers, dt_enum)

            from app.api.router_ingestion import _process_dataframe_import
            import asyncio

            resp = asyncio.get_event_loop().run_until_complete(
                _process_dataframe_import(
                    df=df,
                    store_id=store_id,
                    data_type=data_type if isinstance(data_type, str) else data_type.value,
                    mappings=suggested_mappings,
                    source_type="postgresql",
                    source_name=f"Table: {table_name}",
                    source_path=f"postgresql://{table_name}",
                )
            )

            results.append({
                "table": table_name,
                "data_type": data_type if isinstance(data_type, str) else data_type.value,
                "status": "completed",
                "import_id": resp.data.import_id if resp.data else None,
                "rows": resp.data.merge_result.total_processed if resp.data else 0,
            })
        except Exception as exc:
            logger.error("Failed to import table %s: %s", table_name, exc)
            results.append({
                "table": table_name,
                "status": "failed",
                "message": str(exc),
            })

    return {"success": True, "data": {"results": results}}
