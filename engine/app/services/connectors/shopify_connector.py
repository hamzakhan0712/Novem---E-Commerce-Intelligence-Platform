import logging
from datetime import datetime

import pandas as pd
import requests

from app.services.connectors.base import BaseConnector, RateLimiter
from app.services.connectors.field_maps import (
    SHOPIFY_CUSTOMER_MAP,
    SHOPIFY_ORDER_MAP,
    SHOPIFY_PRODUCT_MAP,
    SHOPIFY_STATUS_MAP,
)

logger = logging.getLogger(__name__)


class ShopifyConnector(BaseConnector):
    """Connector for Shopify REST Admin API."""

    def __init__(self, credentials: dict):
        super().__init__(credentials)
        self.shop_domain = credentials["shop_domain"].rstrip("/")
        self.api_key = credentials["api_key"]
        self.api_secret = credentials["api_secret"]
        self._base_url = f"https://{self.shop_domain}/admin/api/2024-01"
        self._session = requests.Session()
        self._session.headers.update({
            "X-Shopify-Access-Token": self.api_secret,
            "Content-Type": "application/json",
        })
        self._limiter = RateLimiter(requests_per_second=2.0)

    def test_connection(self) -> bool:
        try:
            self._limiter.wait()
            resp = self._session.get(f"{self._base_url}/shop.json", timeout=15)
            return resp.status_code == 200
        except Exception as exc:
            logger.warning("Shopify connection test failed: %s", exc)
            return False

    def get_available_data_types(self) -> list[str]:
        return ["orders", "customers", "products"]

    def fetch_data(
        self,
        data_type: str,
        since: datetime | None = None,
    ) -> pd.DataFrame:
        if data_type == "orders":
            return self._fetch_orders(since)
        elif data_type == "customers":
            return self._fetch_customers(since)
        elif data_type == "products":
            return self._fetch_products(since)
        else:
            raise ValueError(f"Unsupported data type: {data_type}")

    # ── Orders ──────────────────────────────────────

    def _fetch_orders(self, since: datetime | None) -> pd.DataFrame:
        params: dict = {"limit": 250, "status": "any"}
        if since:
            params["updated_at_min"] = since.isoformat()

        raw_orders = self._paginate(f"{self._base_url}/orders.json", "orders", params)

        rows = []
        for o in raw_orders:
            line_items = o.get("line_items", [])
            for li in line_items:
                row = {
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
                    "currency": o.get("currency", "USD"),
                    "status": SHOPIFY_STATUS_MAP.get(
                        o.get("financial_status", ""), "pending"
                    ),
                    "refund_amount": 0.0,
                    "channel": o.get("source_name", ""),
                    "region": (o.get("billing_address") or {}).get("province", ""),
                }
                rows.append(row)

        if not rows:
            return pd.DataFrame(columns=list(SHOPIFY_ORDER_MAP.values()))

        return pd.DataFrame(rows)

    # ── Customers ───────────────────────────────────

    def _fetch_customers(self, since: datetime | None) -> pd.DataFrame:
        params: dict = {"limit": 250}
        if since:
            params["updated_at_min"] = since.isoformat()

        raw = self._paginate(f"{self._base_url}/customers.json", "customers", params)

        rows = []
        for c in raw:
            rows.append({
                "customer_id": str(c.get("id", "")),
                "email_raw": c.get("email", ""),
                "name_raw": f"{c.get('first_name', '')} {c.get('last_name', '')}".strip(),
                "total_orders": c.get("orders_count", 0),
                "total_spend": float(c.get("total_spent", 0)),
                "region": (c.get("default_address") or {}).get("province", ""),
                "first_order_date": c.get("created_at", ""),
            })

        if not rows:
            return pd.DataFrame(columns=list(SHOPIFY_CUSTOMER_MAP.values()))

        return pd.DataFrame(rows)

    # ── Products ────────────────────────────────────

    def _fetch_products(self, since: datetime | None) -> pd.DataFrame:
        params: dict = {"limit": 250}
        if since:
            params["updated_at_min"] = since.isoformat()

        raw = self._paginate(f"{self._base_url}/products.json", "products", params)

        rows = []
        for p in raw:
            rows.append({
                "product_id": str(p.get("id", "")),
                "product_name": p.get("title", ""),
                "category": p.get("product_type", ""),
                "status": "active" if p.get("status") == "active" else "inactive",
            })

        if not rows:
            return pd.DataFrame(columns=list(SHOPIFY_PRODUCT_MAP.values()))

        return pd.DataFrame(rows)

    # ── Pagination (cursor-based via Link header) ───

    def _paginate(self, url: str, key: str, params: dict) -> list[dict]:
        all_items: list[dict] = []
        next_url: str | None = url

        while next_url:
            self._limiter.wait()
            resp = self._session.get(next_url, params=params if next_url == url else None, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            items = data.get(key, [])
            all_items.extend(items)

            link_header = resp.headers.get("Link", "")
            next_url = None
            if 'rel="next"' in link_header:
                for part in link_header.split(","):
                    if 'rel="next"' in part:
                        next_url = part.split(";")[0].strip().strip("<>")
                        break

            logger.debug("Fetched %d %s (total: %d)", len(items), key, len(all_items))

        return all_items
