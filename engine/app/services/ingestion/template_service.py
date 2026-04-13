"""
Template service — metadata, template CSV generation, schema reference,
platform guides, and feature-readiness thresholds.

Single source of truth for column metadata used across:
- Download template CSVs
- Schema reference panel
- Validation / dry-run reports
"""

import csv
import io
from typing import Optional

from app.services.ingestion.merge_engine import TABLE_NOT_NULL_DEFAULTS
from app.services.ingestion.schema_detector import CANONICAL_COLUMNS


# ── Column metadata (type hint, example value, human-readable notes) ────

COLUMN_METADATA: dict[str, dict[str, str]] = {
    # ── Orders ──
    "order_id": {"type": "text", "example": "ORD-001", "notes": "Unique order identifier"},
    "order_date": {"type": "date", "example": "2026-01-15", "notes": "ISO 8601 or common date formats"},
    "customer_id": {"type": "text", "example": "CUST-042", "notes": "Unique customer identifier"},
    "customer_email_hash": {"type": "text", "example": "customer@example.com", "notes": "Email — auto-hashed on import"},
    "customer_name_hash": {"type": "text", "example": "Rahul Sharma", "notes": "Name — auto-hashed on import"},
    "product_id": {"type": "text", "example": "SKU-100", "notes": "Unique product/SKU identifier"},
    "product_name": {"type": "text", "example": "Wireless Earbuds", "notes": "Product display name"},
    "category": {"type": "text", "example": "Electronics", "notes": "Product category"},
    "quantity": {"type": "number", "example": "2", "notes": "Quantity ordered (decimals OK for weight-based)"},
    "unit_price": {"type": "number", "example": "1499.00", "notes": "Price per unit"},
    "total_price": {"type": "number", "example": "2998.00", "notes": "Line item total (quantity × unit_price)"},
    "discount_amount": {"type": "number", "example": "150.00", "notes": "Discount applied to this line item"},
    "currency": {"type": "text", "example": "INR", "notes": "ISO 4217 code. Default: INR. Supports 35+ codes"},
    "status": {"type": "text", "example": "completed", "notes": "completed, pending, cancelled, refunded, etc."},
    "refund_amount": {"type": "number", "example": "0", "notes": "Refund amount (0 if none)"},
    "refund_reason": {"type": "text", "example": "", "notes": "Reason for refund (if applicable)"},
    "channel": {"type": "text", "example": "online", "notes": "Sales channel: online, store, marketplace, etc."},
    "region": {"type": "text", "example": "Maharashtra", "notes": "Geographic region or state"},
    "line_item_index": {"type": "number", "example": "0", "notes": "Auto-assigned; 0 for single item per order+product"},
    # ── Customers ──
    "email_hash": {"type": "text", "example": "priya@example.com", "notes": "Email — auto-hashed on import"},
    "name_hash": {"type": "text", "example": "Priya Patel", "notes": "Name — auto-hashed on import"},
    "first_order_date": {"type": "date", "example": "2025-03-10", "notes": "Date of first purchase"},
    "last_order_date": {"type": "date", "example": "2026-01-15", "notes": "Date of most recent purchase"},
    "total_orders": {"type": "number", "example": "12", "notes": "Total number of orders placed"},
    "total_spend": {"type": "number", "example": "45600.00", "notes": "Cumulative spending amount"},
    "avg_order_value": {"type": "number", "example": "3800.00", "notes": "Average order value"},
    # ── Products ──
    "subcategory": {"type": "text", "example": "True Wireless", "notes": "Product subcategory"},
    "parent_product_id": {"type": "text", "example": "PARENT-050", "notes": "Parent product for variants"},
    "unit_cost": {"type": "number", "example": "800.00", "notes": "Cost price per unit"},
    "current_stock": {"type": "number", "example": "150", "notes": "Current inventory count"},
    "size": {"type": "text", "example": "M", "notes": "Size variant (if applicable)"},
    "color": {"type": "text", "example": "Black", "notes": "Color variant (if applicable)"},
    # ── Ad Spend ──
    "date": {"type": "date", "example": "2026-01-15", "notes": "Campaign date"},
    "campaign_name": {"type": "text", "example": "Summer Sale 2026", "notes": "Campaign name or identifier"},
    "impressions": {"type": "number", "example": "15000", "notes": "Ad impressions count"},
    "clicks": {"type": "number", "example": "450", "notes": "Ad clicks count"},
    "spend": {"type": "number", "example": "5000.00", "notes": "Amount spent on ads"},
    "conversions": {"type": "number", "example": "28", "notes": "Number of conversions from ads"},
    "revenue_attributed": {"type": "number", "example": "84000.00", "notes": "Revenue attributed to this campaign"},
    # ── Reviews ──
    "review_id": {"type": "text", "example": "REV-001", "notes": "Unique review identifier"},
    "review_date": {"type": "date", "example": "2026-01-20", "notes": "Date review was posted"},
    "rating": {"type": "number", "example": "4", "notes": "Rating (1-5 stars)"},
    "review_text": {"type": "text", "example": "Great product, fast delivery!", "notes": "Full review text"},
    # ── Stock Levels ──
    "snapshot_date": {"type": "date", "example": "2026-01-15", "notes": "Date of inventory snapshot"},
    "quantity_on_hand": {"type": "number", "example": "250", "notes": "Units currently in stock"},
    "lead_time_days": {"type": "number", "example": "7", "notes": "Supplier lead time in days"},
    "warehouse": {"type": "text", "example": "WH-Mumbai", "notes": "Warehouse identifier"},
    "location": {"type": "text", "example": "Mumbai", "notes": "Warehouse city or location"},
}

# ── Template example rows per data type ─────────────────────────────────

TEMPLATE_ROWS: dict[str, list[dict[str, str]]] = {
    "orders": [
        {"order_id": "ORD-001", "order_date": "2026-01-15", "customer_id": "CUST-042", "customer_email_hash": "rahul@example.com", "customer_name_hash": "Rahul Sharma", "product_id": "SKU-100", "product_name": "Wireless Earbuds", "category": "Electronics", "quantity": "2", "unit_price": "1499.00", "total_price": "2998.00", "discount_amount": "0", "currency": "INR", "status": "completed", "refund_amount": "0", "refund_reason": "", "channel": "online", "region": "Maharashtra", "line_item_index": "0"},
        {"order_id": "ORD-002", "order_date": "2026-01-16", "customer_id": "CUST-043", "customer_email_hash": "priya@example.com", "customer_name_hash": "Priya Patel", "product_id": "SKU-101", "product_name": "USB-C Hub", "category": "Electronics", "quantity": "1", "unit_price": "1899.00", "total_price": "1899.00", "discount_amount": "100.00", "currency": "INR", "status": "completed", "refund_amount": "0", "refund_reason": "", "channel": "marketplace", "region": "Delhi", "line_item_index": "0"},
        {"order_id": "ORD-003", "order_date": "2026-01-17", "customer_id": "CUST-044", "customer_email_hash": "amit@example.com", "customer_name_hash": "Amit Kumar", "product_id": "SKU-102", "product_name": "Cotton T-Shirt (L)", "category": "Fashion", "quantity": "3", "unit_price": "599.00", "total_price": "1797.00", "discount_amount": "0", "currency": "INR", "status": "pending", "refund_amount": "0", "refund_reason": "", "channel": "store", "region": "Karnataka", "line_item_index": "0"},
    ],
    "customers": [
        {"customer_id": "CUST-042", "email_hash": "rahul@example.com", "name_hash": "Rahul Sharma", "first_order_date": "2025-03-10", "last_order_date": "2026-01-15", "total_orders": "12", "total_spend": "45600.00", "avg_order_value": "3800.00", "region": "Maharashtra"},
        {"customer_id": "CUST-043", "email_hash": "priya@example.com", "name_hash": "Priya Patel", "first_order_date": "2025-06-22", "last_order_date": "2026-01-16", "total_orders": "8", "total_spend": "28400.00", "avg_order_value": "3550.00", "region": "Delhi"},
        {"customer_id": "CUST-044", "email_hash": "amit@example.com", "name_hash": "Amit Kumar", "first_order_date": "2025-11-05", "last_order_date": "2026-01-17", "total_orders": "3", "total_spend": "5391.00", "avg_order_value": "1797.00", "region": "Karnataka"},
    ],
    "products": [
        {"product_id": "SKU-100", "product_name": "Wireless Earbuds", "category": "Electronics", "subcategory": "Audio", "parent_product_id": "", "unit_cost": "800.00", "current_stock": "150", "status": "active", "size": "", "color": "Black"},
        {"product_id": "SKU-101", "product_name": "USB-C Hub", "category": "Electronics", "subcategory": "Accessories", "parent_product_id": "", "unit_cost": "950.00", "current_stock": "75", "status": "active", "size": "", "color": "Silver"},
        {"product_id": "SKU-102", "product_name": "Cotton T-Shirt", "category": "Fashion", "subcategory": "Men Topwear", "parent_product_id": "PARENT-050", "unit_cost": "250.00", "current_stock": "300", "status": "active", "size": "L", "color": "White"},
    ],
    "ad_spend": [
        {"date": "2026-01-15", "channel": "Google Ads", "campaign_name": "Summer Sale 2026", "impressions": "15000", "clicks": "450", "spend": "5000.00", "currency": "INR", "conversions": "28", "revenue_attributed": "84000.00"},
        {"date": "2026-01-15", "channel": "Meta Ads", "campaign_name": "Retargeting - Jan", "impressions": "22000", "clicks": "680", "spend": "7500.00", "currency": "INR", "conversions": "45", "revenue_attributed": "112500.00"},
        {"date": "2026-01-16", "channel": "Google Ads", "campaign_name": "Brand Keywords", "impressions": "8000", "clicks": "320", "spend": "2400.00", "currency": "INR", "conversions": "18", "revenue_attributed": "54000.00"},
    ],
    "reviews": [
        {"review_id": "REV-001", "product_id": "SKU-100", "customer_id": "CUST-042", "review_date": "2026-01-20", "rating": "5", "review_text": "Amazing sound quality and battery life. Best purchase this year!"},
        {"review_id": "REV-002", "product_id": "SKU-101", "customer_id": "CUST-043", "review_date": "2026-01-21", "rating": "4", "review_text": "Good hub, all ports work well. Slightly warm during heavy use."},
        {"review_id": "REV-003", "product_id": "SKU-102", "customer_id": "CUST-044", "review_date": "2026-01-22", "rating": "3", "review_text": "Fabric is nice but sizing runs small. Order one size up."},
    ],
    "stock_levels": [
        {"product_id": "SKU-100", "snapshot_date": "2026-01-15", "quantity_on_hand": "150", "lead_time_days": "7", "warehouse": "WH-Mumbai", "location": "Mumbai"},
        {"product_id": "SKU-101", "snapshot_date": "2026-01-15", "quantity_on_hand": "75", "lead_time_days": "10", "warehouse": "WH-Mumbai", "location": "Mumbai"},
        {"product_id": "SKU-102", "snapshot_date": "2026-01-15", "quantity_on_hand": "300", "lead_time_days": "5", "warehouse": "WH-Delhi", "location": "Delhi"},
    ],
}


# ── Platform export guides ──────────────────────────────────────────────

PLATFORM_GUIDES: list[dict[str, str]] = [
    {
        "platform": "Shopify",
        "icon": "shopify",
        "steps": (
            "1. Go to **Orders** → **Export** → select **CSV for Excel**\n"
            "2. Choose **All orders** or a date range\n"
            "3. The exported CSV works directly with NOVEM — columns will auto-map\n"
            "4. For customers: **Customers** → **Export** → **CSV for Excel**\n"
            "5. For products: **Products** → **Export** → select all fields"
        ),
    },
    {
        "platform": "Amazon Seller Central",
        "icon": "amazon",
        "steps": (
            "1. Go to **Reports** → **Fulfillment** → **All Orders**\n"
            "2. Select the date range and click **Download**\n"
            "3. Choose **Tab-delimited** (.tsv) format — NOVEM reads TSV natively\n"
            "4. For reviews: **Reports** → **Customer Reviews** → download CSV\n"
            "5. For ad spend: **Campaign Manager** → **Reports** → download campaign report"
        ),
    },
    {
        "platform": "WooCommerce",
        "icon": "woocommerce",
        "steps": (
            "1. Go to **WooCommerce** → **Orders** → click **Export**\n"
            "2. Ensure the **Status** column is included in the export\n"
            "3. For products: **Products** → **Export** → select all columns\n"
            "4. Use the built-in WordPress CSV exporter or a plugin like WP All Export\n"
            "5. Date format should be YYYY-MM-DD for best compatibility"
        ),
    },
    {
        "platform": "Flipkart Seller Hub",
        "icon": "flipkart",
        "steps": (
            "1. Go to **Orders** → **Settlement Report** → download\n"
            "2. Use the **Order Item Level** report for line-item detail\n"
            "3. NOVEM recognizes Flipkart column names (FSN, sub_order_id, your_selling_price)\n"
            "4. For product catalog: **Products** → **Listings** → **Export**\n"
            "5. Meesho and Myntra exports also auto-map"
        ),
    },
    {
        "platform": "Generic / Custom",
        "icon": "generic",
        "steps": (
            "1. Download a **template CSV** for your data type and match your columns to it\n"
            "2. Save as CSV with **UTF-8 encoding** (File → Save As → CSV UTF-8)\n"
            "3. Use the first row for column headers — NOVEM auto-detects them\n"
            "4. Dates in any common format work (YYYY-MM-DD, DD/MM/YYYY, MM-DD-YYYY)\n"
            "5. Currency can be codes (INR, USD) or names (rupees, dollars) — auto-normalized"
        ),
    },
]


# ── Feature readiness thresholds ────────────────────────────────────────

FEATURE_THRESHOLDS: list[dict] = [
    {
        "feature": "Dashboard KPIs",
        "description": "Core revenue, order, and customer metrics",
        "requirements": {"orders": {"min_rows": 1}},
    },
    {
        "feature": "Revenue Forecasting",
        "description": "AI-powered revenue predictions",
        "requirements": {"orders": {"min_rows": 100, "min_days": 90}},
    },
    {
        "feature": "Customer Segmentation",
        "description": "RFM-based customer clusters",
        "requirements": {"customers": {"min_rows": 50}},
    },
    {
        "feature": "Churn Prediction",
        "description": "Identify at-risk customers",
        "requirements": {"orders": {"min_rows": 100, "min_days": 180}, "customers": {"min_rows": 50}},
    },
    {
        "feature": "Sentiment Analysis",
        "description": "Review sentiment and topic extraction",
        "requirements": {"reviews": {"min_rows": 10}},
    },
    {
        "feature": "Product Performance",
        "description": "Product-level analytics and rankings",
        "requirements": {"products": {"min_rows": 5}},
    },
    {
        "feature": "Ad Attribution",
        "description": "Marketing spend vs. revenue correlation",
        "requirements": {"orders": {"min_rows": 1}, "ad_spend": {"min_rows": 1}},
    },
    {
        "feature": "Stock Monitoring",
        "description": "Inventory alerts and reorder suggestions",
        "requirements": {"stock_levels": {"min_rows": 1}},
    },
]


# ── Helper functions ────────────────────────────────────────────────────


def generate_template_csv(data_type: str) -> str:
    """Generate a template CSV string for a data type with headers, hints, and example rows."""
    columns = CANONICAL_COLUMNS.get(data_type, [])
    if not columns:
        return ""

    not_null_map = TABLE_NOT_NULL_DEFAULTS.get(data_type, {})
    output = io.StringIO()
    writer = csv.writer(output)

    # Row 1: Headers
    writer.writerow(columns)

    # Row 2: Comment row with REQUIRED/optional + type hints
    hints: list[str] = []
    for col in columns:
        meta = COLUMN_METADATA.get(col, {})
        col_type = meta.get("type", "text")
        is_required = col in not_null_map and not_null_map[col] is None
        default = not_null_map.get(col)

        parts: list[str] = []
        parts.append("REQUIRED" if is_required else "optional")
        parts.append(f"({col_type})")
        if default is not None and not is_required:
            parts.append(f"default: {default}")
        if meta.get("notes"):
            parts.append(f"— {meta['notes']}")
        hints.append(" ".join(parts))
    writer.writerow(hints)

    # Rows 3-5: Example data
    example_rows = TEMPLATE_ROWS.get(data_type, [])
    for row_data in example_rows:
        writer.writerow([row_data.get(col, "") for col in columns])

    return output.getvalue()


def get_schema_reference(data_type: str) -> list[dict]:
    """Build schema reference info for a data type."""
    columns = CANONICAL_COLUMNS.get(data_type, [])
    not_null_map = TABLE_NOT_NULL_DEFAULTS.get(data_type, {})

    result: list[dict] = []
    for col in columns:
        meta = COLUMN_METADATA.get(col, {})
        is_required = col in not_null_map and not_null_map[col] is None
        default = not_null_map.get(col)

        result.append({
            "column": col,
            "required": is_required,
            "data_type": meta.get("type", "text"),
            "default_value": str(default) if default is not None else None,
            "example": meta.get("example", ""),
            "notes": meta.get("notes", ""),
        })
    return result


def evaluate_feature_readiness(
    row_counts: dict[str, int],
    date_spans: Optional[dict[str, int]] = None,
) -> list[dict]:
    """Evaluate which features are ready based on current store data."""
    if date_spans is None:
        date_spans = {}

    results: list[dict] = []
    for ft in FEATURE_THRESHOLDS:
        feature = ft["feature"]
        description = ft["description"]
        requirements = ft["requirements"]

        all_met = True
        warnings: list[str] = []
        blockers: list[str] = []

        for table, reqs in requirements.items():
            current_rows = row_counts.get(table, 0)
            min_rows = reqs.get("min_rows", 0)
            min_days = reqs.get("min_days", 0)

            if current_rows == 0:
                blockers.append(f"No {table} data — import {table} first")
                all_met = False
            elif current_rows < min_rows:
                deficit = min_rows - current_rows
                warnings.append(f"Need {deficit} more {table} rows (have {current_rows}, need {min_rows})")
                all_met = False

            if min_days > 0:
                current_days = date_spans.get(table, 0)
                if current_days < min_days:
                    deficit_days = min_days - current_days
                    warnings.append(f"Need {deficit_days} more days of {table} data (have {current_days}, need {min_days})")
                    all_met = False

        if blockers:
            status = "not_ready"
            detail = "; ".join(blockers)
        elif warnings:
            status = "warning"
            detail = "; ".join(warnings)
        else:
            status = "ready"
            detail = "All requirements met"

        # Build human-readable minimum requirement string
        req_parts: list[str] = []
        for table, reqs in requirements.items():
            if reqs.get("min_days"):
                req_parts.append(f"{reqs['min_days']} days of {table}")
            elif reqs.get("min_rows"):
                req_parts.append(f"{reqs['min_rows']}+ {table} rows")
            else:
                req_parts.append(f"{table} data")

        # Build current status string
        status_parts: list[str] = []
        for table in requirements:
            count = row_counts.get(table, 0)
            status_parts.append(f"{count:,} {table}")

        results.append({
            "feature": feature,
            "description": description,
            "minimum_required": " + ".join(req_parts),
            "current_value": ", ".join(status_parts),
            "status": status,
            "detail": detail,
        })

    return results
