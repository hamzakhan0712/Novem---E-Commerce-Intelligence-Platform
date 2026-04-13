import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException

from app.core.database import get_sqlite_connection
from app.core.encryption import decrypt_json, encrypt_json
from app.models.credentials import (
    CredentialOut,
    SaveCredentialRequest,
    TestCredentialResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/credentials", tags=["credentials"])

_VALID_TYPES = {
    "shopify_api",
    "google_sheets_api",
    "postgresql",
    "webhook_shopify_secret",
}


@router.post("")
def save_credential(req: SaveCredentialRequest):
    if req.credential_type not in _VALID_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid credential_type. Must be one of: {', '.join(sorted(_VALID_TYPES))}")

    conn = get_sqlite_connection()

    store = conn.execute("SELECT id FROM stores WHERE id = ?", (req.store_id,)).fetchone()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    existing = conn.execute(
        "SELECT id FROM store_credentials WHERE store_id = ? AND credential_type = ?",
        (req.store_id, req.credential_type),
    ).fetchone()

    now = datetime.now().isoformat()
    encrypted = encrypt_json(req.credentials)

    if existing:
        conn.execute(
            "UPDATE store_credentials SET credentials_encrypted = ?, updated_at = ? WHERE id = ?",
            (encrypted, now, existing["id"]),
        )
        conn.commit()
        cred_id = existing["id"]
    else:
        cred_id = uuid.uuid4().hex[:12]
        conn.execute(
            "INSERT INTO store_credentials (id, store_id, credential_type, credentials_encrypted, created_at) VALUES (?, ?, ?, ?, ?)",
            (cred_id, req.store_id, req.credential_type, encrypted, now),
        )
        conn.commit()

    return {
        "success": True,
        "data": {"id": cred_id, "credential_type": req.credential_type},
    }


@router.get("/{store_id}")
def list_credentials(store_id: str):
    conn = get_sqlite_connection()
    rows = conn.execute(
        "SELECT id, store_id, credential_type, created_at, updated_at FROM store_credentials WHERE store_id = ?",
        (store_id,),
    ).fetchall()

    return {
        "success": True,
        "data": [
            CredentialOut(
                id=r["id"],
                store_id=r["store_id"],
                credential_type=r["credential_type"],
                created_at=r["created_at"],
                updated_at=r["updated_at"],
            ).model_dump()
            for r in rows
        ],
    }


@router.delete("/{credential_id}")
def delete_credential(credential_id: str):
    conn = get_sqlite_connection()
    row = conn.execute("SELECT id FROM store_credentials WHERE id = ?", (credential_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Credential not found")

    conn.execute("DELETE FROM store_credentials WHERE id = ?", (credential_id,))
    conn.commit()
    return {"success": True, "data": None}


@router.post("/{credential_id}/test")
def test_credential(credential_id: str) -> dict:
    conn = get_sqlite_connection()
    row = conn.execute(
        "SELECT credential_type, credentials_encrypted FROM store_credentials WHERE id = ?",
        (credential_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Credential not found")

    cred_type = row["credential_type"]
    try:
        creds = decrypt_json(row["credentials_encrypted"])
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to decrypt credentials")

    try:
        if cred_type == "shopify_api":
            from app.services.connectors.shopify_connector import ShopifyConnector
            connector = ShopifyConnector(creds)
            ok = connector.test_connection()
        elif cred_type == "postgresql":
            from app.services.connectors.database_connector import DatabaseConnector
            connector = DatabaseConnector(creds)
            ok = connector.test_connection()
        else:
            return {"success": True, "data": TestCredentialResponse(success=True, message="Credential saved (no live test available)").model_dump()}

        msg = "Connection successful" if ok else "Connection failed"
        return {"success": True, "data": TestCredentialResponse(success=ok, message=msg).model_dump()}

    except Exception as exc:
        logger.warning("Credential test failed for %s: %s", credential_id, exc)
        return {
            "success": True,
            "data": TestCredentialResponse(success=False, message=str(exc)).model_dump(),
        }
