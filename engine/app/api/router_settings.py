import logging
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import DATA_DIR, DUCKDB_PATH, SQLITE_PATH
from app.core.database import get_sqlite_connection
from app.models.common import ApiResponse
from app.services.currency.exchange_service import (
    get_exchange_rates,
    get_rate,
    get_supported_currencies,
)

router = APIRouter(prefix="/settings", tags=["settings"])

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Settings key-value API (reads/writes from the `settings` table)
# ---------------------------------------------------------------------------

_ALLOWED_SETTINGS = {
    "theme", "currency", "industry_template",
    "date_format", "fiscal_year_start", "zoom_level",
    "watch_folder_path", "pii_masking_enabled",
    "debug_mode", "region", "churn_threshold_days",
    "password_policy",
}


@router.get("/preferences")
def get_settings() -> ApiResponse:
    conn = get_sqlite_connection()
    rows = conn.execute(
        "SELECT key, value FROM settings"
    ).fetchall()
    settings_map = {r["key"]: r["value"] for r in rows}
    return ApiResponse(success=True, data=settings_map, error=None)


@router.put("/preferences")
def put_settings(body: dict) -> ApiResponse:
    conn = get_sqlite_connection()
    updates = {k: str(v) for k, v in body.items() if k in _ALLOWED_SETTINGS}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid settings keys provided")

    for key, value in updates.items():
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )
    conn.commit()

    return ApiResponse(success=True, data=updates, error=None)


# ---------------------------------------------------------------------------
# System info
# ---------------------------------------------------------------------------


def _dir_size(path: Path) -> int:
    """Total size in bytes of all files under *path*."""
    total = 0
    if not path.exists():
        return 0
    for entry in path.rglob("*"):
        if entry.is_file():
            total += entry.stat().st_size
    return total


@router.get("/system-info")
def get_system_info() -> ApiResponse:
    """Return storage usage and file paths for the Settings > System panel."""
    data_dir = DATA_DIR.resolve()
    cache_dir = data_dir / "cache"

    duckdb_size = DUCKDB_PATH.stat().st_size if DUCKDB_PATH.exists() else 0
    # Include WAL and SHM files for accurate SQLite size
    sqlite_size = SQLITE_PATH.stat().st_size if SQLITE_PATH.exists() else 0
    wal_path = SQLITE_PATH.with_suffix(".sqlite-wal")
    shm_path = SQLITE_PATH.with_suffix(".sqlite-shm")
    if wal_path.exists():
        sqlite_size += wal_path.stat().st_size
    if shm_path.exists():
        sqlite_size += shm_path.stat().st_size
    cache_size = _dir_size(cache_dir)
    total_storage = _dir_size(data_dir)

    return ApiResponse(
        success=True,
        data={
            "data_dir": str(data_dir),
            "duckdb_path": str(DUCKDB_PATH.resolve()),
            "sqlite_path": str(SQLITE_PATH.resolve()),
            "cache_dir": str(cache_dir),
            "duckdb_size": duckdb_size,
            "sqlite_size": sqlite_size,
            "cache_size": cache_size,
            "total_storage": total_storage,
        },
        error=None,
    )


@router.delete("/cache")
def clear_cache() -> ApiResponse:
    """Delete all files in the cache directory."""
    cache_dir = DATA_DIR.resolve() / "cache"
    removed = 0
    if cache_dir.exists():
        for entry in cache_dir.rglob("*"):
            if entry.is_file():
                entry.unlink()
                removed += 1
    return ApiResponse(
        success=True,
        data={"removed_files": removed},
        error=None,
    )


# ---------------------------------------------------------------------------
# Currency exchange rates
# ---------------------------------------------------------------------------


@router.get("/exchange-rates")
def get_exchange_rates_endpoint() -> ApiResponse:
    """Return current exchange rates (base: INR) and supported currencies."""
    rates = get_exchange_rates()
    return ApiResponse(
        success=True,
        data={
            "base": "INR",
            "rates": rates,
            "currencies": get_supported_currencies(),
        },
        error=None,
    )


@router.get("/exchange-rate/{currency}")
def get_single_rate(currency: str) -> ApiResponse:
    """Return the exchange rate for a single currency."""
    currency = currency.upper()
    rate = get_rate(currency)
    return ApiResponse(
        success=True,
        data={"currency": currency, "rate": rate},
        error=None,
    )
