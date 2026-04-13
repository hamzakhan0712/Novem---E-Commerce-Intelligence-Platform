import logging
import re
from typing import Optional

import pandas as pd

from app.models.ingestion import DataType, IndustryTemplate

logger = logging.getLogger(__name__)

SCHEMA_PATTERNS: dict[DataType, list[str]] = {
    DataType.ORDERS: [
        "order_id", "order_date", "customer", "quantity", "price",
        "total", "status", "order", "transaction", "invoice",
        "invoiceno", "invoicedate", "unitprice", "stockcode",
        "description", "country", "lineitem", "fulfillment",
        "shipping", "discount", "refund",
    ],
    DataType.CUSTOMERS: [
        "customer_id", "email", "name", "first_order", "total_spend",
        "signup", "lifetime", "customer", "first_name", "last_name",
        "phone", "address", "tags", "total_orders", "total_spent",
        "accepts", "tax_exempt", "billing",
    ],
    DataType.PRODUCTS: [
        "product_id", "product_name", "sku", "category", "price",
        "stock", "product", "item", "handle", "title", "vendor",
        "variant", "variant_sku", "variant_price", "published",
        "option1", "type", "tags", "cost_per_item",
    ],
    DataType.AD_SPEND: [
        "date", "channel", "spend", "impressions", "clicks", "campaign",
        "ad", "marketing", "cost", "conversions", "roas",
    ],
    DataType.REVIEWS: [
        "review", "rating", "product", "text", "comment", "date",
        "star", "feedback", "body", "headline",
    ],
    DataType.STOCK_LEVELS: [
        "product_id", "stock", "quantity_on_hand", "warehouse",
        "inventory", "lead_time", "reorder", "safety_stock",
        "snapshot", "on_hand",
    ],
}

# Keywords that EXCLUSIVELY identify a data type — if these appear,
# they strongly signal that specific type over any other.
EXCLUSIVE_KEYWORDS: dict[DataType, set[str]] = {
    DataType.AD_SPEND: {
        "impressions", "clicks", "spend", "ad_spend", "campaign",
        "conversions", "roas", "cpc", "cpm", "ctr", "ad_group",
        "adset", "ad_name", "cost_per_click", "cost_per_conversion",
    },
    DataType.REVIEWS: {
        "rating", "stars", "star_rating", "review_text", "review_body",
        "review_headline", "review_id", "sentiment", "nps_score",
        "review_date", "reviewer",
    },
    DataType.CUSTOMERS: {
        "total_orders", "total_spend", "total_spent", "lifetime_value",
        "ltv", "clv", "first_order_date", "last_order_date",
        "avg_order_value", "order_count", "signup_date",
    },
    DataType.STOCK_LEVELS: {
        "quantity_on_hand", "lead_time", "reorder_point", "safety_stock",
        "warehouse", "inventory_quantity", "stock_on_hand", "bin_quantity",
        "snapshot_date",
    },
    DataType.ORDERS: {
        "order_id", "order_date", "order_number", "invoice_id",
        "fulfillment_status", "shipping_address", "line_item",
    },
    DataType.PRODUCTS: {
        "variant_sku", "variant_price", "cost_per_item", "product_type",
        "published_scope", "option1", "option2",
    },
}

FASHION_KEYWORDS = {
    "dress", "shirt", "shoes", "size", "color", "fabric", "cotton",
    "blouse", "jeans", "jacket", "sweater", "skirt", "pants",
    "denim", "leather", "silk", "wool", "polyester",
}

CANONICAL_COLUMNS: dict[DataType, list[str]] = {
    DataType.ORDERS: [
        "order_id", "order_date", "customer_id", "customer_email_hash",
        "customer_name_hash", "product_id", "product_name", "category",
        "quantity", "unit_price", "total_price", "discount_amount",
        "currency", "status", "refund_amount", "refund_reason",
        "channel", "region", "line_item_index",
    ],
    DataType.CUSTOMERS: [
        "customer_id", "email_hash", "name_hash", "first_order_date",
        "last_order_date", "total_orders", "total_spend",
        "avg_order_value", "region",
    ],
    DataType.PRODUCTS: [
        "product_id", "product_name", "category", "subcategory",
        "parent_product_id",
        "unit_cost", "current_stock", "status", "size", "color",
    ],
    DataType.AD_SPEND: [
        "date", "channel", "campaign_name", "impressions", "clicks",
        "spend", "currency", "conversions", "revenue_attributed",
    ],
    DataType.REVIEWS: [
        "review_id", "product_id", "customer_id", "review_date",
        "rating", "review_text",
    ],
    DataType.STOCK_LEVELS: [
        "product_id", "snapshot_date", "quantity_on_hand", "lead_time_days",
        "warehouse", "location",
    ],
}

# Mapping from type-column values to DataType
TYPE_COLUMN_MAP: dict[str, DataType] = {
    "order": DataType.ORDERS,
    "orders": DataType.ORDERS,
    "customer": DataType.CUSTOMERS,
    "customers": DataType.CUSTOMERS,
    "product": DataType.PRODUCTS,
    "products": DataType.PRODUCTS,
    "adspend": DataType.AD_SPEND,
    "ad_spend": DataType.AD_SPEND,
    "ads": DataType.AD_SPEND,
    "review": DataType.REVIEWS,
    "reviews": DataType.REVIEWS,
    "stock": DataType.STOCK_LEVELS,
    "stock_levels": DataType.STOCK_LEVELS,
    "inventory": DataType.STOCK_LEVELS,
}


def detect_schema(
    headers: list[str],
) -> tuple[DataType, float, IndustryTemplate]:
    normalized = [_normalize_header(h) for h in headers]
    headers_lower = [h.lower().strip().replace(" ", "_").replace("-", "_") for h in headers]

    # Phase 1: Standard pattern overlap scoring
    scores: dict[DataType, int] = {}
    for dtype, patterns in SCHEMA_PATTERNS.items():
        score = 0
        for header in normalized:
            for pattern in patterns:
                if pattern in header or header in pattern:
                    score += 1
                    break
        scores[dtype] = score

    # Phase 2: Exclusive keyword bonus — strong signal for disambiguation
    exclusive_hits: dict[DataType, int] = {}
    for dtype, excl_keywords in EXCLUSIVE_KEYWORDS.items():
        hits = 0
        for header in headers_lower:
            for kw in excl_keywords:
                if kw == header or kw in header:
                    hits += 1
                    break
        exclusive_hits[dtype] = hits

    # Apply exclusive bonus: each exclusive hit is worth 3x a normal pattern hit
    combined_scores: dict[DataType, float] = {}
    for dtype in scores:
        combined_scores[dtype] = scores[dtype] + exclusive_hits.get(dtype, 0) * 3.0

    best_type = max(combined_scores, key=lambda k: combined_scores[k])
    max_score = combined_scores[best_type]

    # Phase 3: Confidence calculation with tie-breaking
    sorted_scores = sorted(combined_scores.values(), reverse=True)
    total_patterns = len(SCHEMA_PATTERNS[best_type])
    raw_confidence = min(max_score / max(total_patterns * 0.5, 1), 1.0)

    # Reduce confidence when the top two types are close (ambiguous detection)
    if len(sorted_scores) >= 2 and sorted_scores[0] > 0:
        gap = (sorted_scores[0] - sorted_scores[1]) / sorted_scores[0]
        if gap < 0.3:
            raw_confidence *= 0.6  # Very ambiguous
        elif gap < 0.5:
            raw_confidence *= 0.8  # Somewhat ambiguous

    # Boost confidence when exclusive keywords dominate
    if exclusive_hits.get(best_type, 0) >= 2:
        raw_confidence = min(raw_confidence * 1.2, 1.0)

    confidence = round(min(max(raw_confidence, 0.0), 1.0), 2)

    template = _detect_template(headers)

    logger.info(
        "Schema detection: type=%s, confidence=%.2f, template=%s, exclusive_hits=%s",
        best_type.value, confidence, template.value, dict(exclusive_hits),
    )
    return best_type, confidence, template


def detect_type_column(df: pd.DataFrame) -> Optional[str]:
    """Check if the DataFrame has a column that distinguishes multiple data types.

    Returns the column name if found, else None.
    """
    for col in df.columns:
        normalized = col.lower().strip().replace(" ", "_")
        if normalized in ("record_type", "type", "data_type", "table_type", "row_type", "category_type"):
            unique_vals = df[col].dropna().astype(str).str.strip().str.lower().unique()
            matched = sum(1 for v in unique_vals if v in TYPE_COLUMN_MAP)
            if matched >= 2:
                return col
    return None


def split_by_type_column(
    df: pd.DataFrame,
    type_col: str,
) -> dict[DataType, pd.DataFrame]:
    """Split DataFrame into sub-DataFrames by the type column."""
    result: dict[DataType, pd.DataFrame] = {}
    df[type_col] = df[type_col].astype(str).str.strip().str.lower()
    for val, group in df.groupby(type_col):
        dtype = TYPE_COLUMN_MAP.get(str(val))
        if dtype:
            sub = group.drop(columns=[type_col]).reset_index(drop=True)
            sub = sub.dropna(axis=1, how="all")
            if not sub.empty:
                result[dtype] = sub
    return result


def infer_mixed_types(df: pd.DataFrame) -> dict[DataType, pd.DataFrame]:
    """Infer data types from row patterns when no explicit type column exists.

    Heuristics:
    - Orders: quantity+price columns are non-null
    - Reviews: rating OR review_text/comment columns are non-null
    - Stock: stock/inventory columns are non-null, no price/qty
    - Customers: email-like data, no product/qty columns
    """
    # Try ID prefix detection first (e.g. ORD-xxx, REV-xxx, STK-xxx)
    id_col = None
    for col in df.columns:
        if col.lower().strip() in ("id", "record_id"):
            id_col = col
            break

    if id_col:
        prefixes: dict[str, DataType] = {
            "ord": DataType.ORDERS,
            "rev": DataType.REVIEWS,
            "stk": DataType.STOCK_LEVELS,
            "cus": DataType.CUSTOMERS,
            "ads": DataType.AD_SPEND,
            "prd": DataType.PRODUCTS,
        }
        result: dict[DataType, list[int]] = {}
        for idx, val in df[id_col].items():
            val_str = str(val).strip().lower()
            prefix = val_str[:3] if len(val_str) >= 3 else ""
            dtype = prefixes.get(prefix)
            if dtype:
                result.setdefault(dtype, []).append(idx)

        if len(result) >= 2:
            splits: dict[DataType, pd.DataFrame] = {}
            for dtype, indices in result.items():
                sub = df.loc[indices].dropna(axis=1, how="all").reset_index(drop=True)
                if not sub.empty:
                    splits[dtype] = sub
            if splits:
                return splits

    # Fall back to column-value pattern matching
    result_dfs: dict[DataType, list[int]] = {}

    # Detect which columns look like qty, price, rating, stock
    qty_cols = [c for c in df.columns if c.lower().strip() in ("quantity", "qty", "units", "no_of_units")]
    price_cols = [c for c in df.columns if c.lower().strip() in ("price", "unit_price", "total", "total_price", "revenue")]
    rating_cols = [c for c in df.columns if c.lower().strip() in ("rating", "stars", "star_rating", "score")]
    comment_cols = [c for c in df.columns if c.lower().strip() in ("comment", "review_text", "body", "feedback", "review")]
    stock_cols = [c for c in df.columns if c.lower().strip() in ("stock", "stock_on_hand", "quantity_on_hand", "inventory")]

    for idx in df.index:
        row = df.loc[idx]
        has_qty = any(pd.notna(row.get(c)) and str(row.get(c)).strip() not in ("", "None") for c in qty_cols)
        has_price = any(pd.notna(row.get(c)) and str(row.get(c)).strip() not in ("", "None") for c in price_cols)
        has_rating = any(pd.notna(row.get(c)) and str(row.get(c)).strip() not in ("", "None") for c in rating_cols)
        has_comment = any(pd.notna(row.get(c)) and str(row.get(c)).strip() not in ("", "None") for c in comment_cols)
        has_stock = any(pd.notna(row.get(c)) and str(row.get(c)).strip() not in ("", "None") for c in stock_cols)

        if has_rating or has_comment:
            result_dfs.setdefault(DataType.REVIEWS, []).append(idx)
        elif has_qty and has_price:
            result_dfs.setdefault(DataType.ORDERS, []).append(idx)
        elif has_stock:
            result_dfs.setdefault(DataType.STOCK_LEVELS, []).append(idx)
        else:
            result_dfs.setdefault(DataType.ORDERS, []).append(idx)

    if len(result_dfs) >= 2:
        splits = {}
        for dtype, indices in result_dfs.items():
            sub = df.loc[indices].dropna(axis=1, how="all").reset_index(drop=True)
            if not sub.empty:
                splits[dtype] = sub
        return splits

    return {}


def _detect_template(headers: list[str]) -> IndustryTemplate:
    header_text = " ".join(headers).lower()
    fashion_hits = sum(1 for kw in FASHION_KEYWORDS if kw in header_text)
    if fashion_hits >= 2:
        return IndustryTemplate.FASHION
    return IndustryTemplate.GENERAL


def _normalize_header(header: str) -> str:
    return re.sub(r"[^a-z0-9]", "", header.lower().strip())
