import logging
from datetime import datetime

import pandas as pd

from app.services.connectors.field_maps import SHOPIFY_STATUS_MAP

logger = logging.getLogger(__name__)


def process_order_event(payload: dict, store_id: str) -> pd.DataFrame:
    """Convert a Shopify order webhook payload into a canonical orders DataFrame."""
    o = payload
    line_items = o.get("line_items", [])

    rows = []
    for li in line_items:
        rows.append({
            "order_id": str(o.get("id", "")),
            "order_date": o.get("created_at", ""),
            "customer_id": str(o.get("customer", {}).get("id", "")),
            "customer_email_hash": "",
            "customer_name_hash": "",
            "product_id": str(li.get("product_id", "")),
            "product_name": li.get("title", ""),
            "category": li.get("product_type", ""),
            "quantity": li.get("quantity", 0),
            "unit_price": float(li.get("price", 0)),
            "total_price": float(li.get("price", 0)) * int(li.get("quantity", 0)),
            "discount_amount": sum(
                float(d.get("amount", 0))
                for d in li.get("discount_allocations", [])
            ),
            "currency": o.get("currency", "INR"),
            "status": SHOPIFY_STATUS_MAP.get(o.get("financial_status", ""), "pending"),
            "refund_amount": 0.0,
            "channel": o.get("source_name", ""),
            "region": (o.get("billing_address") or {}).get("province", ""),
        })

    return pd.DataFrame(rows) if rows else pd.DataFrame()


def process_customer_event(payload: dict, store_id: str) -> pd.DataFrame:
    """Convert a Shopify customer webhook payload into a canonical customers DataFrame."""
    c = payload
    return pd.DataFrame([{
        "customer_id": str(c.get("id", "")),
        "email_raw": c.get("email", ""),
        "name_raw": f"{c.get('first_name', '')} {c.get('last_name', '')}".strip(),
        "total_orders": c.get("orders_count", 0),
        "total_spend": float(c.get("total_spent", 0)),
        "region": (c.get("default_address") or {}).get("province", ""),
        "first_order_date": c.get("created_at", ""),
    }])


def process_product_event(payload: dict, store_id: str) -> pd.DataFrame:
    """Convert a Shopify product webhook payload into a canonical products DataFrame."""
    p = payload
    return pd.DataFrame([{
        "product_id": str(p.get("id", "")),
        "product_name": p.get("title", ""),
        "category": p.get("product_type", ""),
        "status": "active" if p.get("status") == "active" else "inactive",
    }])


TOPIC_HANDLERS = {
    "orders/create": ("orders", process_order_event),
    "orders/updated": ("orders", process_order_event),
    "orders/paid": ("orders", process_order_event),
    "customers/create": ("customers", process_customer_event),
    "customers/update": ("customers", process_customer_event),
    "products/create": ("products", process_product_event),
    "products/update": ("products", process_product_event),
}
