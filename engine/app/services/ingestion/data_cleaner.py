"""
Data cleaning pipeline for imported data.

Handles: type coercion, date parsing, currency normalization,
empty/whitespace stripping, numeric cleaning, and status normalization.
"""

import logging
import re
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)


def clean_dataframe(df: pd.DataFrame, data_type: str) -> tuple[pd.DataFrame, list[str]]:
    """Run the full cleaning pipeline. Returns (cleaned_df, list_of_actions)."""
    actions: list[str] = []

    df = _strip_whitespace(df, actions)
    df = _remove_empty_rows(df, actions)
    df = _normalize_nulls(df, actions)
    df = _strip_id_prefixes(df, actions)
    df = _strip_html_tags(df, actions)
    df = _concat_review_columns(df, data_type, actions)
    df = _combine_name_columns(df, data_type, actions)
    df = _forward_fill_variants(df, data_type, actions)
    df = _handle_cancellation_rows(df, data_type, actions)
    df = _filter_noise_rows(df, data_type, actions)
    df = _handle_negative_quantities(df, data_type, actions)
    df = _clean_dates(df, data_type, actions)
    df = _compute_total_price(df, data_type, actions)
    df = _clean_numerics(df, data_type, actions)
    df = _normalize_currency(df, actions)
    df = _normalize_status(df, data_type, actions)
    df = _normalize_product_status(df, data_type, actions)
    df = _normalize_strings(df, actions)

    return df, actions


def _strip_whitespace(df: pd.DataFrame, actions: list[str]) -> pd.DataFrame:
    """Strip leading/trailing whitespace from all string columns."""
    str_cols = df.select_dtypes(include=["object"]).columns
    if len(str_cols) > 0:
        for col in str_cols:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace({"nan": None, "None": None, "": None})
        actions.append(f"Stripped whitespace from {len(str_cols)} columns")
    return df


def _remove_empty_rows(df: pd.DataFrame, actions: list[str]) -> pd.DataFrame:
    """Remove rows where all values are null."""
    before = len(df)
    df = df.dropna(how="all")
    removed = before - len(df)
    if removed > 0:
        actions.append(f"Removed {removed} fully empty rows")
    return df


def _normalize_nulls(df: pd.DataFrame, actions: list[str]) -> pd.DataFrame:
    """Convert common null representations to actual None.

    Skips ID columns, name columns, and text/review columns to avoid
    corrupting legitimate values like 'N/A' in reviews or 'None' brand names.
    """
    null_patterns = {"n/a", "na", "null", "none", "-", "--", ".", "undefined", "missing"}
    # Columns that should NEVER be null-normalized (contain legitimate text)
    skip_keywords = ("id", "name", "text", "review", "body", "comment",
                     "title", "description", "email", "sku", "code",
                     "campaign", "reason", "channel", "region", "address")
    count = 0
    for col in df.columns:
        col_lower = col.lower()
        if any(kw in col_lower for kw in skip_keywords):
            continue
        mask = df[col].astype(str).str.lower().str.strip().isin(null_patterns)
        col_nullified = mask.sum()
        if col_nullified > 0:
            df.loc[mask, col] = None
            count += col_nullified
    if count > 0:
        actions.append(f"Normalized {count} null-like values (n/a, null, etc.)")
    return df


# Date columns per data type
_DATE_COLUMNS = {
    "orders": ["order_date"],
    "customers": ["first_order_date", "last_order_date"],
    "products": [],
    "ad_spend": ["date"],
    "reviews": ["review_date"],
    "stock_levels": ["snapshot_date"],
}


def _clean_dates(df: pd.DataFrame, data_type: str, actions: list[str]) -> pd.DataFrame:
    """Parse and normalize date columns to ISO 8601."""
    date_cols = _DATE_COLUMNS.get(data_type, [])
    for col in date_cols:
        if col not in df.columns:
            continue
        original_nulls = df[col].isna().sum()
        df[col] = pd.to_datetime(df[col], errors="coerce", format="mixed")
        new_nulls = df[col].isna().sum()
        unparsed = new_nulls - original_nulls
        if unparsed > 0:
            actions.append(f"Could not parse {unparsed} date values in '{col}'")
        else:
            actions.append(f"Parsed dates in '{col}'")
    return df


# Numeric columns per data type
_NUMERIC_COLUMNS = {
    "orders": {
        "integer": [],
        "decimal": ["quantity", "unit_price", "total_price", "discount_amount", "refund_amount"],
    },
    "customers": {
        "integer": ["total_orders"],
        "decimal": ["total_spend", "avg_order_value"],
    },
    "products": {
        "integer": ["current_stock"],
        "decimal": ["unit_cost"],
    },
    "ad_spend": {
        "integer": ["impressions", "clicks", "conversions"],
        "decimal": ["spend", "revenue_attributed"],
    },
    "reviews": {
        "integer": ["rating"],
        "decimal": ["sentiment_score"],
    },
    "stock_levels": {
        "integer": ["quantity_on_hand", "lead_time_days", "reorder_point", "safety_stock"],
        "decimal": [],
    },
}


def _clean_numerics(df: pd.DataFrame, data_type: str, actions: list[str]) -> pd.DataFrame:
    """Coerce numeric columns, strip currency symbols and commas."""
    config = _NUMERIC_COLUMNS.get(data_type, {"integer": [], "decimal": []})

    for col in config.get("integer", []):
        if col not in df.columns:
            continue
        df[col] = _to_numeric(df[col])
        df[col] = df[col].fillna(0).astype(int)

    for col in config.get("decimal", []):
        if col not in df.columns:
            continue
        df[col] = _to_numeric(df[col])
        df[col] = df[col].fillna(0).round(2)

    cleaned_cols = [c for c in config.get("integer", []) + config.get("decimal", []) if c in df.columns]
    if cleaned_cols:
        actions.append(f"Cleaned numeric values in {len(cleaned_cols)} columns")

    return df


def _to_numeric(series: pd.Series) -> pd.Series:
    """Strip currency symbols, commas, spaces; then coerce to numeric."""
    cleaned = series.astype(str).str.replace(r"Rs\.?\s?", "", regex=True)
    cleaned = cleaned.str.replace(r"[£€$¥₹,\s]", "", regex=True)
    cleaned = cleaned.str.replace(r"\(([0-9.]+)\)", r"-\1", regex=True)
    return pd.to_numeric(cleaned, errors="coerce")


_CURRENCY_ALIASES = {
    "usd": "USD", "dollar": "USD", "dollars": "USD", "$": "USD",
    "us dollar": "USD", "us dollars": "USD", "united states dollar": "USD",
    "eur": "EUR", "euro": "EUR", "euros": "EUR", "€": "EUR",
    "gbp": "GBP", "pound": "GBP", "pounds": "GBP", "£": "GBP",
    "british pound": "GBP", "pound sterling": "GBP",
    "inr": "INR", "rupee": "INR", "rupees": "INR", "₹": "INR",
    "indian rupee": "INR", "indian rupees": "INR",
    "jpy": "JPY", "yen": "JPY", "¥": "JPY", "japanese yen": "JPY",
    "cad": "CAD", "canadian dollar": "CAD",
    "aud": "AUD", "australian dollar": "AUD",
    "sgd": "SGD", "singapore dollar": "SGD",
    "aed": "AED", "dirham": "AED", "uae dirham": "AED",
    "sar": "SAR", "saudi riyal": "SAR", "riyal": "SAR",
    "myr": "MYR", "ringgit": "MYR", "malaysian ringgit": "MYR",
    "thb": "THB", "baht": "THB", "thai baht": "THB",
    "idr": "IDR", "indonesian rupiah": "IDR", "rupiah": "IDR",
    "php": "PHP", "philippine peso": "PHP", "peso": "PHP",
    "nzd": "NZD", "new zealand dollar": "NZD",
    "hkd": "HKD", "hong kong dollar": "HKD",
    "krw": "KRW", "won": "KRW", "korean won": "KRW",
    "cny": "CNY", "yuan": "CNY", "rmb": "CNY", "chinese yuan": "CNY",
    "brl": "BRL", "real": "BRL", "brazilian real": "BRL",
    "zar": "ZAR", "rand": "ZAR", "south african rand": "ZAR",
    "chf": "CHF", "swiss franc": "CHF", "franc": "CHF",
    "sek": "SEK", "swedish krona": "SEK", "krona": "SEK",
    "nok": "NOK", "norwegian krone": "NOK", "krone": "NOK",
    "dkk": "DKK", "danish krone": "DKK",
    "pln": "PLN", "zloty": "PLN", "polish zloty": "PLN",
    "try": "TRY", "lira": "TRY", "turkish lira": "TRY",
    "bdt": "BDT", "taka": "BDT", "bangladeshi taka": "BDT",
    "lkr": "LKR", "sri lankan rupee": "LKR",
    "pkr": "PKR", "pakistani rupee": "PKR",
    "npr": "NPR", "nepalese rupee": "NPR",
}


def _normalize_currency(df: pd.DataFrame, actions: list[str]) -> pd.DataFrame:
    """Standardize currency column to ISO 4217 codes."""
    if "currency" not in df.columns:
        return df

    before_unique = df["currency"].dropna().nunique()
    df["currency"] = df["currency"].astype(str).str.strip().str.lower().map(
        lambda v: _CURRENCY_ALIASES.get(v, v.upper() if isinstance(v, str) and len(v) == 3 else v)
    )
    # Fill missing currency with the mode (most common)
    mode = df["currency"].mode()
    if not mode.empty:
        df["currency"] = df["currency"].fillna(mode.iloc[0])

    after_unique = df["currency"].dropna().nunique()
    if before_unique != after_unique or before_unique > 0:
        actions.append(f"Normalized currency values to ISO 4217 ({after_unique} unique)")

    return df


_STATUS_MAP = {
    "completed": "completed", "complete": "completed", "paid": "completed",
    "fulfilled": "completed", "shipped": "completed", "delivered": "completed",
    "success": "completed", "closed": "completed", "done": "completed",
    "refunded": "refunded", "refund": "refunded", "returned": "refunded",
    "partially_refunded": "refunded", "partial_refund": "refunded",
    "cancelled": "cancelled", "canceled": "cancelled", "voided": "cancelled",
    "failed": "cancelled", "rejected": "cancelled", "expired": "cancelled",
    "trash": "cancelled", "trashed": "cancelled",
    "pending": "pending", "processing": "pending", "awaiting_payment": "pending",
    "awaiting payment": "pending", "unshipped": "pending",
    "on_hold": "pending", "on hold": "pending", "on-hold": "pending",
    "checkout_draft": "pending", "checkout-draft": "pending",
    "draft": "pending", "in_transit": "pending", "in transit": "pending",
    "dispatched": "pending", "packed": "pending", "ready_to_ship": "pending",
}


def _normalize_status(df: pd.DataFrame, data_type: str, actions: list[str]) -> pd.DataFrame:
    """Normalize order status values to a standard set."""
    if data_type != "orders" or "status" not in df.columns:
        return df

    # Fill missing status with 'completed' (common when CSV has no status column)
    null_status = df["status"].isna()
    null_count = null_status.sum()
    if null_count > 0:
        df.loc[null_status, "status"] = "completed"
        actions.append(f"Defaulted {null_count} missing order statuses to 'completed'")

    original = df["status"].dropna().unique().tolist()
    # Strip WooCommerce wc- prefix (e.g. wc-completed → completed)
    df["status"] = df["status"].astype(str).str.strip().str.lower()
    df["status"] = df["status"].str.replace(r"^wc[_-]", "", regex=True)
    df["status"] = df["status"].map(lambda v: _STATUS_MAP.get(v, v))
    # Default unknown statuses to 'completed'
    known = set(_STATUS_MAP.values())
    unknown_mask = ~df["status"].isin(known) & df["status"].notna()
    unknown_count = unknown_mask.sum()
    if unknown_count > 0:
        df.loc[unknown_mask, "status"] = "completed"
        actions.append(f"Mapped {unknown_count} unknown status values to 'completed'")
    else:
        actions.append("Normalized order status values")

    return df


def _normalize_strings(df: pd.DataFrame, actions: list[str]) -> pd.DataFrame:
    """Strip whitespace from product names and categories.

    Does NOT title-case — it breaks SKUs, abbreviations, brand names
    (e.g. 'SPF 50' → 'Spf 50', 'USB-C' → 'Usb-C').
    """
    for col in ["product_name", "category", "subcategory", "campaign_name"]:
        if col not in df.columns:
            continue
        mask = df[col].notna()
        if mask.any():
            df.loc[mask, col] = df.loc[mask, col].astype(str).str.strip()
    return df


# ── Real-world data cleaning steps ──────────────────────────────────────


def _strip_id_prefixes(df: pd.DataFrame, actions: list[str]) -> pd.DataFrame:
    """Strip leading apostrophes/quotes from ID and phone columns (Shopify export quirk)."""
    id_like_cols = [
        c for c in df.columns
        if any(kw in c.lower() for kw in ("id", "phone", "email", "sku", "code"))
    ]
    count = 0
    for col in id_like_cols:
        if not pd.api.types.is_string_dtype(df[col]):
            continue
        mask = df[col].astype(str).str.startswith("'")
        col_fixed = mask.sum()
        if col_fixed > 0:
            df[col] = df[col].astype(str).str.lstrip("'\"")
            count += col_fixed
    if count > 0:
        actions.append(f"Stripped leading quotes from {count} ID/phone values")
    return df


def _strip_html_tags(df: pd.DataFrame, actions: list[str]) -> pd.DataFrame:
    """Remove HTML tags from text columns."""
    text_cols = [
        c for c in df.columns
        if any(kw in c.lower() for kw in ("name", "description", "title", "text", "body", "review"))
    ]
    count = 0
    html_pattern = re.compile(r"<[^>]+>")
    for col in text_cols:
        if not pd.api.types.is_string_dtype(df[col]):
            continue
        has_html = df[col].astype(str).str.contains(r"<[^>]+>", regex=True, na=False)
        col_cleaned = has_html.sum()
        if col_cleaned > 0:
            df[col] = df[col].astype(str).apply(
                lambda v: html_pattern.sub("", v).strip() if pd.notna(v) and v != "None" else v
            )
            count += col_cleaned
    if count > 0:
        actions.append(f"Stripped HTML tags from {count} text values")
    return df


def _concat_review_columns(df: pd.DataFrame, data_type: str, actions: list[str]) -> pd.DataFrame:
    """Concatenate review_headline + review_body into review_text for review data.

    Many review datasets (Amazon) export headline and body as separate columns.
    Both map to review_text, but only one can win the column mapping.
    Concatenating them before mapping ensures we keep both.
    """
    if data_type != "reviews":
        return df

    headline_col = None
    body_col = None
    for col in df.columns:
        norm = col.lower().strip().replace(" ", "_")
        if norm in ("review_headline", "headline", "title", "summary"):
            headline_col = col
        elif norm in ("review_body", "body", "review_text", "text", "comment", "feedback"):
            body_col = col

    if headline_col and body_col:
        h = df[headline_col].fillna("").astype(str).str.strip()
        b = df[body_col].fillna("").astype(str).str.strip()
        combined = (h + " — " + b).str.strip(" —")
        combined = combined.replace("", None)
        df[body_col] = combined
        df = df.drop(columns=[headline_col], errors="ignore")
        actions.append(f"Concatenated '{headline_col}' + '{body_col}' into review text")

    return df


def _combine_name_columns(df: pd.DataFrame, data_type: str, actions: list[str]) -> pd.DataFrame:
    """Combine first_name + last_name into name_hash for customer data."""
    if data_type != "customers":
        return df

    has_first = "first_name" in df.columns
    has_last = "last_name" in df.columns
    has_name_hash = "name_hash" in df.columns

    if has_first or has_last:
        first = df.get("first_name", pd.Series([""] * len(df))).fillna("").astype(str)
        last = df.get("last_name", pd.Series([""] * len(df))).fillna("").astype(str)
        combined = (first + " " + last).str.strip()
        combined = combined.replace("", None)

        if has_name_hash:
            null_mask = df["name_hash"].isna()
            if null_mask.any():
                df.loc[null_mask, "name_hash"] = combined[null_mask]
        else:
            df["name_hash"] = combined

        if has_first:
            df = df.drop(columns=["first_name"], errors="ignore")
        if has_last:
            df = df.drop(columns=["last_name"], errors="ignore")

        actions.append("Combined first_name + last_name into name_hash")

    return df


def _forward_fill_variants(df: pd.DataFrame, data_type: str, actions: list[str]) -> pd.DataFrame:
    """Forward-fill product attributes for multi-row variant exports (Shopify/WooCommerce).

    In Shopify product exports, only the first variant row has the product title,
    category, etc. Subsequent variant rows leave these fields blank.
    """
    if data_type != "products":
        return df

    fill_cols = ["product_name", "category", "subcategory", "status"]
    fillable = [c for c in fill_cols if c in df.columns]
    if not fillable:
        return df

    group_col = None
    for candidate in ["product_id", "handle"]:
        if candidate in df.columns:
            group_col = candidate
            break

    if group_col is None:
        return df

    # Forward-fill the group column itself first (variant rows leave it blank)
    null_group_before = df[group_col].isna().sum()
    df[group_col] = df[group_col].ffill()
    null_group_after = df[group_col].isna().sum()
    group_filled = null_group_before - null_group_after

    filled_count = group_filled
    for col in fillable:
        null_before = df[col].isna().sum()
        df[col] = df.groupby(group_col)[col].transform(
            lambda g: g.ffill().bfill()
        )
        null_after = df[col].isna().sum()
        filled_count += null_before - null_after

    if filled_count > 0:
        actions.append(f"Forward-filled {filled_count} blank variant fields from parent product")

    return df


def _handle_cancellation_rows(df: pd.DataFrame, data_type: str, actions: list[str]) -> pd.DataFrame:
    """Detect cancellation-prefixed order IDs (e.g., C536379) and set status accordingly.

    Only triggers when both a C-prefixed ID and its non-C counterpart exist in the
    dataset. This avoids corrupting legitimate C-prefixed order IDs (BigCommerce,
    WooCommerce, ERP systems).
    """
    if data_type != "orders" or "order_id" not in df.columns:
        return df

    cancel_mask = df["order_id"].astype(str).str.match(r"^[Cc]\d+")
    cancel_count = cancel_mask.sum()
    if cancel_count == 0:
        return df

    # Only treat C-prefixed IDs as cancellations when the non-C version also exists
    all_ids = set(df["order_id"].astype(str))
    confirmed_cancels = pd.Series(False, index=df.index)
    for idx in df.index[cancel_mask]:
        c_id = str(df.at[idx, "order_id"])
        stripped_id = c_id[1:]  # Remove the C prefix
        if stripped_id in all_ids:
            confirmed_cancels.at[idx] = True

    actual_cancel_count = confirmed_cancels.sum()
    if actual_cancel_count == 0:
        return df

    df.loc[confirmed_cancels, "order_id"] = df.loc[confirmed_cancels, "order_id"].astype(str).str[1:]
    if "status" in df.columns:
        df.loc[confirmed_cancels, "status"] = "cancelled"
    if "refund_amount" in df.columns:
        null_refund = confirmed_cancels & df["refund_amount"].isna()
        if null_refund.any() and "total_price" in df.columns:
            tp = pd.to_numeric(df.loc[null_refund, "total_price"], errors="coerce").abs()
            df.loc[null_refund, "refund_amount"] = tp

    actions.append(f"Detected {actual_cancel_count} cancellation rows (C-prefixed order IDs with matching originals)")
    return df


def _filter_noise_rows(df: pd.DataFrame, data_type: str, actions: list[str]) -> pd.DataFrame:
    """Remove non-product rows: discounts, postage, shipping adjustments, etc.

    Uses ONLY exact matching to avoid removing legitimate products like
    'Discount Sunglasses', 'Shipping Container Toy', 'Postage Stamp Set'.
    """
    if data_type != "orders":
        return df

    before = len(df)
    noise_exact = {"d", "discount", "post", "postage", "shipping", "manual",
                   "adjust", "adjustment", "dot", "bank charges", "cruk",
                   "amazonfee", "amazon_fee", "m", "gift_wrap", "gift_wrapping",
                   "giftwrap", "promo_code", "promo", "coupon", "tax", "fee",
                   "tax_adjustment", "surcharge", "handling",
                   "shipping fee", "shipping charge", "delivery charge",
                   "gift wrapping", "gift wrap service",
                   "standard shipping", "express shipping", "free shipping",
                   "handling fee", "service fee", "platform fee"}

    for col in ["product_id", "product_name"]:
        if col not in df.columns:
            continue
        lower = df[col].astype(str).str.strip().str.lower()
        exact_mask = lower.isin(noise_exact)
        if exact_mask.any():
            df = df[~exact_mask]

    removed = before - len(df)
    if removed > 0:
        actions.append(f"Removed {removed} noise rows (discounts, postage, adjustments)")
    return df


def _handle_negative_quantities(df: pd.DataFrame, data_type: str, actions: list[str]) -> pd.DataFrame:
    """Handle negative quantities: mark as refunds and make quantities positive."""
    if data_type != "orders" or "quantity" not in df.columns:
        return df

    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    neg_mask = df["quantity"] < 0
    neg_count = neg_mask.sum()
    if neg_count == 0:
        return df

    if "status" in df.columns:
        already_cancelled = df["status"].astype(str).str.lower().isin({"cancelled", "refunded"})
        unmarked = neg_mask & ~already_cancelled
        df.loc[unmarked, "status"] = "refunded"

    df.loc[neg_mask, "quantity"] = df.loc[neg_mask, "quantity"].abs()

    if "total_price" in df.columns:
        df["total_price"] = pd.to_numeric(df["total_price"], errors="coerce")
        neg_total = neg_mask & (df["total_price"] < 0)
        df.loc[neg_total, "total_price"] = df.loc[neg_total, "total_price"].abs()

    if "unit_price" in df.columns:
        df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
        neg_price = neg_mask & (df["unit_price"] < 0)
        df.loc[neg_price, "unit_price"] = df.loc[neg_price, "unit_price"].abs()

    actions.append(f"Converted {neg_count} negative-quantity rows to refunds")
    return df


def _compute_total_price(df: pd.DataFrame, data_type: str, actions: list[str]) -> pd.DataFrame:
    """Compute total_price = quantity * unit_price when total_price is missing or all-null."""
    if data_type != "orders":
        return df
    if "total_price" not in df.columns:
        return df

    total_null_pct = df["total_price"].isna().sum() / max(len(df), 1)
    if total_null_pct < 0.9:
        return df

    if "quantity" in df.columns and "unit_price" in df.columns:
        qty = pd.to_numeric(df["quantity"], errors="coerce").fillna(0)
        price = pd.to_numeric(df["unit_price"], errors="coerce").fillna(0)
        df["total_price"] = (qty * price).round(2)
        actions.append("Computed total_price = quantity × unit_price (was missing)")

    return df


def _normalize_product_status(df: pd.DataFrame, data_type: str, actions: list[str]) -> pd.DataFrame:
    """Normalize product status values (active/draft/archived) from various formats."""
    if data_type != "products" or "status" not in df.columns:
        return df

    product_status_map = {
        "active": "active", "true": "active", "1": "active", "yes": "active",
        "published": "active", "enabled": "active", "visible": "active",
        "in stock": "active", "in_stock": "active", "live": "active",
        "draft": "draft", "false": "draft", "0": "draft", "no": "draft",
        "unpublished": "draft", "disabled": "draft", "hidden": "draft",
        "archived": "archived", "deleted": "archived", "discontinued": "archived",
        "out of stock": "archived", "out_of_stock": "archived",
    }

    original_vals = df["status"].dropna().unique().tolist()
    df["status"] = df["status"].astype(str).str.strip().str.lower().map(
        lambda v: product_status_map.get(v, "active")
    )
    mapped = len([v for v in original_vals if str(v).strip().lower() in product_status_map])
    if mapped > 0:
        actions.append(f"Normalized {len(original_vals)} product status values")

    return df
