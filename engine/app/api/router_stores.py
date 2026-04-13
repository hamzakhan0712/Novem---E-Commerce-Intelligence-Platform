"""
Store management API router — CRUD for stores and user profile.
"""

import logging

from fastapi import APIRouter, HTTPException, Query

from app.models.common import ApiResponse
from app.models.stores import (
    CreateStoreRequest,
    StoreDataCounts,
    StoreOut,
    UpdateStoreRequest,
    UpdateUserProfileRequest,
    UserProfileOut,
)
from app.services.stores.store_manager import (
    create_store,
    deactivate_store,
    delete_store_permanently,
    get_store,
    get_store_data_counts,
    get_user_profile,
    list_stores,
    update_store,
    update_user_profile,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/stores", tags=["stores"])


# ─── User Profile ──────────────────────────────────────────────────────


@router.get("/profile")
async def get_profile() -> ApiResponse[UserProfileOut]:
    """Get the user profile."""
    profile = get_user_profile()
    return ApiResponse(success=True, data=profile)


@router.patch("/profile")
async def patch_profile(
    req: UpdateUserProfileRequest,
) -> ApiResponse[UserProfileOut]:
    """Update the user profile."""
    profile = update_user_profile(req)
    return ApiResponse(success=True, data=profile)


# ─── Store CRUD ─────────────────────────────────────────────────────────


@router.get("")
async def get_stores(
    include_inactive: bool = Query(False),
) -> ApiResponse[list[StoreOut]]:
    """List all stores."""
    stores = list_stores(include_inactive)
    return ApiResponse(success=True, data=stores)


@router.post("")
async def create_new_store(
    req: CreateStoreRequest,
) -> ApiResponse[StoreOut]:
    """Create a new store."""
    store = create_store(req)
    return ApiResponse(success=True, data=store)


@router.get("/{store_id}")
async def get_store_by_id(store_id: str) -> ApiResponse[StoreOut]:
    """Get a store by ID."""
    try:
        store = get_store(store_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Store not found")
    return ApiResponse(success=True, data=store)


@router.patch("/{store_id}")
async def patch_store(
    store_id: str,
    req: UpdateStoreRequest,
) -> ApiResponse[StoreOut]:
    """Update a store's settings."""
    try:
        store = update_store(store_id, req)
    except ValueError:
        raise HTTPException(status_code=404, detail="Store not found")
    return ApiResponse(success=True, data=store)


@router.post("/{store_id}/deactivate")
async def deactivate_store_route(store_id: str) -> ApiResponse[dict]:
    """Deactivate a store (soft delete — data preserved)."""
    try:
        deactivate_store(store_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Store not found")
    return ApiResponse(success=True, data={"id": store_id, "deactivated": True})


@router.post("/{store_id}/reactivate")
async def reactivate_store_route(store_id: str) -> ApiResponse[dict]:
    """Reactivate a deactivated store."""
    from app.core.database import get_sqlite_connection
    from datetime import datetime, timezone

    conn = get_sqlite_connection()
    row = conn.execute("SELECT id FROM stores WHERE id = ?", (store_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Store not found")

    conn.execute(
        "UPDATE stores SET is_active = 1, updated_at = ? WHERE id = ?",
        (datetime.now(timezone.utc).isoformat(), store_id),
    )
    conn.commit()
    return ApiResponse(success=True, data={"id": store_id, "reactivated": True})


@router.delete("/{store_id}")
async def delete_store_route(store_id: str) -> ApiResponse[dict]:
    """Permanently delete a store and all its data."""
    try:
        deleted_counts = delete_store_permanently(store_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Store not found")
    return ApiResponse(
        success=True,
        data={"id": store_id, "permanently_deleted": True, "rows_deleted": deleted_counts},
    )


@router.get("/{store_id}/data-counts")
async def get_data_counts(store_id: str) -> ApiResponse[StoreDataCounts]:
    """Get data row counts for a store."""
    try:
        counts = get_store_data_counts(store_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Store not found")
    return ApiResponse(success=True, data=counts)
