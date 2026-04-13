import hashlib
import hmac
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request

from app.core.database import get_sqlite_connection
from app.core.encryption import decrypt_json, encrypt_json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _verify_shopify_hmac(body: bytes, secret: str, header_hmac: str) -> bool:
    computed = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    import base64
    computed_b64 = base64.b64encode(computed).decode("utf-8")
    return hmac.compare_digest(computed_b64, header_hmac)


def _log_webhook(store_id: str, platform: str, topic: str, payload_hash: str, status: str, error: str | None = None):
    conn = get_sqlite_connection()
    conn.execute(
        "INSERT INTO webhook_log (id, store_id, platform, topic, payload_hash, status, error, received_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (uuid.uuid4().hex[:12], store_id, platform, topic, payload_hash, status, error, datetime.now().isoformat()),
    )
    conn.commit()


def _process_webhook_data(df, store_id: str, data_type: str, platform: str):
    """Run the webhook DataFrame through the existing normalization + merge pipeline."""
    if df is None or df.empty:
        return

    from app.services.ingestion.data_cleaner import clean_dataframe
    from app.services.ingestion.pii_masker import mask_pii
    from app.services.ingestion.merge_engine import merge_into_store

    df, _actions = clean_dataframe(df, data_type)
    col_map = {c: c for c in df.columns}
    df, _hashed = mask_pii(df, col_map)
    merge_into_store(df, store_id, data_type, strategy="upsert")

    # Record in import history
    conn = get_sqlite_connection()
    conn.execute(
        "INSERT INTO import_history (id, store_id, data_type, source_type, source_name, "
        "row_count_raw, row_count_new, status, imported_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            uuid.uuid4().hex[:12],
            store_id,
            data_type,
            "webhook",
            f"{platform}_webhook",
            len(df),
            len(df),
            "completed",
            datetime.now().isoformat(),
        ),
    )
    conn.commit()


@router.post("/shopify/{store_id}")
async def receive_shopify_webhook(store_id: str, request: Request):
    body = await request.body()
    hmac_header = request.headers.get("X-Shopify-Hmac-SHA256", "")
    topic = request.headers.get("X-Shopify-Topic", "")
    payload_hash = hashlib.sha256(body).hexdigest()[:16]

    conn = get_sqlite_connection()
    secret_row = conn.execute(
        "SELECT credentials_encrypted FROM store_credentials "
        "WHERE store_id = ? AND credential_type = 'webhook_shopify_secret'",
        (store_id,),
    ).fetchone()

    if secret_row:
        secret_data = decrypt_json(secret_row["credentials_encrypted"])
        if not _verify_shopify_hmac(body, secret_data["secret"], hmac_header):
            _log_webhook(store_id, "shopify", topic, payload_hash, "rejected", "HMAC verification failed")
            raise HTTPException(status_code=401, detail="Invalid HMAC signature")

    import json
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        _log_webhook(store_id, "shopify", topic, payload_hash, "error", "Invalid JSON")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    from app.services.webhooks.shopify_handler import TOPIC_HANDLERS
    handler_info = TOPIC_HANDLERS.get(topic)
    if not handler_info:
        _log_webhook(store_id, "shopify", topic, payload_hash, "ignored", f"Unhandled topic: {topic}")
        return {"success": True, "data": {"status": "ignored", "topic": topic}}

    data_type, handler_fn = handler_info
    try:
        df = handler_fn(payload, store_id)
        _process_webhook_data(df, store_id, data_type, "shopify")
        _log_webhook(store_id, "shopify", topic, payload_hash, "processed")
        return {"success": True, "data": {"status": "processed", "topic": topic, "rows": len(df)}}
    except Exception as exc:
        _log_webhook(store_id, "shopify", topic, payload_hash, "error", str(exc))
        logger.error("Shopify webhook processing failed: %s", exc)
        raise HTTPException(status_code=500, detail="Webhook processing failed")


@router.get("/status/{store_id}")
def webhook_status(store_id: str):
    conn = get_sqlite_connection()
    logs = conn.execute(
        "SELECT * FROM webhook_log WHERE store_id = ? ORDER BY received_at DESC LIMIT 20",
        (store_id,),
    ).fetchall()

    secrets = conn.execute(
        "SELECT credential_type FROM store_credentials "
        "WHERE store_id = ? AND credential_type LIKE 'webhook_%'",
        (store_id,),
    ).fetchall()

    return {
        "success": True,
        "data": {
            "configured_platforms": [r["credential_type"].replace("webhook_", "").replace("_secret", "") for r in secrets],
            "recent_events": [dict(r) for r in logs],
        },
    }


@router.post("/test/{store_id}")
def test_webhook(store_id: str, topic: str = "products/create"):
    """Send a mock Shopify webhook payload through the real processing pipeline to verify everything works."""
    import json

    conn = get_sqlite_connection()
    store = conn.execute("SELECT id FROM stores WHERE id = ?", (store_id,)).fetchone()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    now = datetime.now().isoformat()

    # Build a realistic mock payload for the requested topic
    test_payloads = {
        "products/create": {
            "id": 9999000001,
            "title": "NOVEM Test Product",
            "product_type": "Test",
            "status": "active",
            "created_at": now,
            "updated_at": now,
        },
        "orders/create": {
            "id": 9999000001,
            "created_at": now,
            "currency": "INR",
            "financial_status": "paid",
            "source_name": "web",
            "customer": {"id": 9999000001},
            "billing_address": {"province": "Test Region"},
            "line_items": [{
                "product_id": 9999000001,
                "title": "NOVEM Test Product",
                "product_type": "Test",
                "quantity": 1,
                "price": "9.99",
                "discount_allocations": [],
            }],
        },
        "customers/create": {
            "id": 9999000001,
            "email": "test@novem-webhook-test.local",
            "first_name": "NOVEM",
            "last_name": "Test",
            "orders_count": 0,
            "total_spent": "0.00",
            "created_at": now,
            "default_address": {"province": "Test Region"},
        },
    }

    payload = test_payloads.get(topic)
    if not payload:
        raise HTTPException(status_code=400, detail=f"Unsupported test topic: {topic}. Use: {', '.join(test_payloads.keys())}")

    from app.services.webhooks.shopify_handler import TOPIC_HANDLERS
    handler_info = TOPIC_HANDLERS.get(topic)
    if not handler_info:
        raise HTTPException(status_code=400, detail=f"No handler for topic: {topic}")

    data_type, handler_fn = handler_info
    payload_hash = hashlib.sha256(json.dumps(payload).encode()).hexdigest()[:16]

    try:
        df = handler_fn(payload, store_id)
        _process_webhook_data(df, store_id, data_type, "shopify")
        _log_webhook(store_id, "shopify", f"test:{topic}", payload_hash, "processed")
        return {
            "success": True,
            "data": {
                "status": "processed",
                "topic": topic,
                "rows": len(df),
                "message": f"Test {topic} webhook processed successfully — {len(df)} row(s) inserted into {data_type}.",
            },
        }
    except Exception as exc:
        _log_webhook(store_id, "shopify", f"test:{topic}", payload_hash, "error", str(exc))
        logger.error("Webhook test failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Test webhook processing failed: {exc}")


@router.post("/configure/{store_id}")
def configure_webhook(store_id: str, platform: str = "shopify"):
    """Generate a webhook secret and return the URL + secret for the user to configure."""
    import secrets as sec

    conn = get_sqlite_connection()
    store = conn.execute("SELECT id FROM stores WHERE id = ?", (store_id,)).fetchone()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    webhook_secret = sec.token_urlsafe(32)
    cred_type = f"webhook_{platform}_secret"

    existing = conn.execute(
        "SELECT id FROM store_credentials WHERE store_id = ? AND credential_type = ?",
        (store_id, cred_type),
    ).fetchone()

    encrypted = encrypt_json({"secret": webhook_secret})
    now = datetime.now().isoformat()

    if existing:
        conn.execute(
            "UPDATE store_credentials SET credentials_encrypted = ?, updated_at = ? WHERE id = ?",
            (encrypted, now, existing["id"]),
        )
    else:
        conn.execute(
            "INSERT INTO store_credentials (id, store_id, credential_type, credentials_encrypted, created_at) VALUES (?, ?, ?, ?, ?)",
            (uuid.uuid4().hex[:12], store_id, cred_type, encrypted, now),
        )
    conn.commit()

    webhook_url = f"/webhooks/{platform}/{store_id}"

    from app.config import ENGINE_PORT
    local_url = f"http://127.0.0.1:{ENGINE_PORT}{webhook_url}"

    return {
        "success": True,
        "data": {
            "webhook_url": webhook_url,
            "full_url": local_url,
            "webhook_secret": webhook_secret,
            "platform": platform,
            "instructions": (
                f"1. Open your {platform.title()} Admin → Settings → Notifications → Webhooks.\n"
                f"2. Click 'Create webhook'.\n"
                f"3. Select a topic (e.g. 'Order creation', 'Customer creation').\n"
                f"4. Set Format to JSON.\n"
                f"5. Paste the Webhook URL below — your server must be publicly accessible.\n"
                f"   If running locally, use a tunnel like ngrok: ngrok http {ENGINE_PORT}\n"
                f"   Then use: https://YOUR_NGROK_DOMAIN{webhook_url}\n"
                f"6. Repeat for each event you want to track (orders/create, customers/create, products/update, etc.).\n"
                f"7. Shopify will use the secret to sign each request with HMAC-SHA256. NOVEM verifies it automatically."
            ),
        },
    }
