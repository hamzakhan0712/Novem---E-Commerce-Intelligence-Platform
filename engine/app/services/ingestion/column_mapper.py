import logging
import re

from app.models.ingestion import ColumnMapping, DataType

logger = logging.getLogger(__name__)

SYNONYMS: dict[DataType, dict[str, list[str]]] = {
    DataType.ORDERS: {
        "order_id": [
            "order_number", "order_no", "order_ref", "transaction_id",
            "txn_id", "invoice_id", "invoice_number", "id",
            "invoice_no", "invoiceno", "invoice", "receipt_number",
            "receipt_no", "bill_no", "bill_number",
            "name", "order_name", "confirmation_number",
            "post_id", "wc_order_id",
            "amazon_order_id", "merchant_order_id", "purchase_order_id",
            "entity_id", "increment_id", "bc_order_id",
            "ref_no", "ref_number", "reference_no", "reference_number",
            "doc_no", "document_no", "so_number", "sales_order_no",
            "sub_order_id", "suborderid", "order_item_id",
            "flipkart_order_id", "meesho_order_id", "myntra_order_id",
        ],
        "order_date": [
            "date", "purchase_date", "created_at", "order_timestamp",
            "transaction_date", "ordered_at",
            "invoice_date", "invoicedate", "bill_date",
            "receipt_date", "sale_date", "sold_date",
            "processed_at", "closed_at",
            "date_created", "post_date", "date_completed",
            "purchase_date_time",
            "placed_at", "order_placed", "date_placed",
            "order_placed_on", "ordered_on", "booked_on",
            "dispatch_date_time", "dispatch_date",
        ],
        "customer_id": [
            "user_id", "buyer_id", "client_id", "customer_number",
            "cust_id", "shopper_id", "account_id", "member_id",
            "shopify_customer_id", "customer_user", "marketplace_buyer_id",
        ],
        "customer_email_hash": [
            "email", "customer_email", "buyer_email", "user_email",
            "contact_email", "e_mail",
            "billing_email", "notification_email",
            "cust_mail", "cust_email", "client_email", "mail",
        ],
        "customer_name_hash": [
            "customer_name", "buyer_name", "full_name",
            "user_name", "client_name",
            "billing_name", "shipping_name", "billing_first_name",
            "billing_last_name", "first_name", "last_name",
        ],
        "product_id": [
            "sku", "item_id", "product_sku", "item_sku", "product_code",
            "item_code", "variant_id", "upc", "asin",
            "stock_code", "stockcode", "item_number", "part_number",
            "barcode", "article_number", "article_no",
            "shopify_product_id", "variant_sku", "line_item_sku",
            "line_item_product_id", "lineitem_sku",
            "wc_product_id",
            "seller_sku", "fnsku", "listing_id", "marketplace_id",
            "bc_product_id",
            "prod_code", "prod_id", "material_code",
            "fsn", "seller_sku_code", "style_id",
            "supplier_sku", "meesho_sku",
        ],
        "product_name": [
            "item_name", "product_title", "item", "product_description",
            "item_title", "description", "item_description",
            "line_item", "goods", "article_name", "material_description",
            "line_item_name", "lineitem_name", "variant_title",
            "listing_title",
            "goods_description", "goods_desc", "product_desc",
        ],
        "category": [
            "product_category", "item_category", "department",
            "product_type", "item_type", "group",
            "collection", "product_type_shopify",
            "browse_node", "item_classification",
            "tax_class", "product_cat",
        ],
        "quantity": [
            "qty", "units", "items_ordered", "order_qty", "count",
            "line_item_quantity", "lineitem_quantity", "fulfillable_quantity",
            "quantity_ordered", "quantity_shipped",
            "qty_ordered", "product_qty",
            "no_of_units", "number_of_units", "pcs", "pieces",
        ],
        "unit_price": [
            "price", "item_price", "price_per_unit", "sale_price",
            "selling_price", "rate",
            "line_item_price", "lineitem_price", "variant_price",
            "item_price_amount", "your_price",
            "line_subtotal", "product_price",
            "rate_per_unit", "unit_rate", "unit_cost", "mrp",
            "your_selling_price", "meesho_selling_price",
        ],
        "total_price": [
            "total", "line_total", "subtotal", "order_total", "revenue",
            "gross", "order_value", "amount_paid", "amount",
            "total_price_shopify", "current_subtotal_price",
            "current_total_price", "subtotal_price",
            "order_total_wc", "cart_total",
            "item_total", "order_amount",
            "net_amount", "grand_total", "payment_amount", "net_value",
            "transaction_amount", "payment_total",
        ],
        "discount_amount": [
            "discount", "discount_value", "promo_amount",
            "coupon_amount", "savings",
            "total_discounts", "discount_code", "discount_applications",
            "cart_discount", "order_discount",
            "promotion_discount", "item_promotion_discount",
            "rebate", "rebate_amount", "concession",
        ],
        "currency": [
            "currency_code", "curr", "iso_currency",
            "presentment_currency", "shop_currency",
            "marketplace_currency",
        ],
        "status": [
            "order_status", "state", "fulfillment_status", "payment_status",
            "financial_status", "cancel_reason", "confirmed",
            "post_status", "wc_status",
            "order_status_amazon", "shipment_status",
            "order_condition", "delivery_status", "dispatch_status",
        ],
        "refund_amount": [
            "refund", "refund_value", "return_amount", "credit_amount",
            "total_refund", "refund_line_items_amount",
            "item_promotion_adjustment", "shipping_credit",
        ],
        "refund_reason": [
            "return_reason", "refund_reason_code", "cancellation_reason",
            "return_reason_code", "buyer_cancellation_reason",
        ],
        "channel": [
            "source", "traffic_source", "utm_source",
            "acquisition_channel", "marketing_channel", "medium",
            "referral_source",
            "source_name", "landing_site", "referring_site",
            "utm_medium", "utm_campaign",
            "sales_channel", "fulfillment_channel",
        ],
        "region": [
            "country", "location", "geo", "ship_country",
            "billing_country", "market",
            "shipping_country", "shipping_country_code",
            "billing_country_code", "shipping_province",
            "shipping_city", "shipping_state",
            "ship_service_level", "ship_state", "marketplace",
            "ship_to_country", "destination_country", "delivery_country",
        ],
    },
    DataType.CUSTOMERS: {
        "customer_id": [
            "user_id", "buyer_id", "client_id", "customer_number",
            "cust_id", "shopper_id", "account_id", "member_id",
            "id", "customer_no",
            "shopify_customer_id", "customer_user", "wc_customer_id",
        ],
        "email_hash": [
            "email", "customer_email", "user_email", "contact_email",
            "e_mail", "email_address", "e_mail_address",
            "billing_email", "notification_email",
            "cust_mail", "cust_email", "client_email", "mail",
        ],
        "name_hash": [
            "name", "full_name", "customer_name", "user_name",
            "display_name", "contact_name",
            "first_name", "last_name", "billing_name",
            "billing_first_name", "billing_last_name",
        ],
        "first_order_date": [
            "first_purchase", "signup_date", "created_at",
            "registered_at", "join_date",
            "accepts_marketing_updated_at",
            "date_registered", "user_registered",
        ],
        "last_order_date": [
            "last_purchase", "last_activity", "last_seen", "updated_at",
            "last_order_date_shopify", "last_login", "last_visit",
        ],
        "total_orders": [
            "order_count", "num_orders", "purchase_count", "transactions",
            "orders_count", "number_of_orders", "total_transactions",
        ],
        "total_spend": [
            "lifetime_value", "ltv", "total_revenue",
            "total_purchases", "clv",
            "total_spent", "revenue", "customer_value", "monetary_value",
        ],
        "avg_order_value": [
            "aov", "average_order", "avg_purchase",
            "avg_basket", "average_basket_size", "avg_transaction",
        ],
        "region": [
            "country", "location", "geo", "market",
            "default_address_country", "billing_country",
            "shipping_country", "country_code", "state", "city",
            "default_address_country_code", "default_address_province_code",
            "default_address_city",
        ],
    },
    DataType.PRODUCTS: {
        "product_id": [
            "sku", "item_id", "product_sku", "item_code",
            "product_code", "variant_id", "upc", "asin",
            "shopify_product_id", "handle", "variant_sku",
            "wc_product_id", "post_id",
            "fnsku", "seller_sku", "listing_id", "bc_product_id",
        ],
        "product_name": [
            "name", "title", "item_name", "item_title",
            "description", "product_title",
            "handle_title", "seo_title",
            "listing_title", "item_name_amazon",
        ],
        "category": [
            "product_category", "department", "product_type",
            "collection", "group", "type",
            "product_type_shopify", "collections",
            "product_cat", "tax_class",
            "browse_node", "item_type_keyword",
            "article_type",
        ],
        "subcategory": [
            "sub_category", "product_subcategory", "sub_type",
            "sub_department", "vendor",
            "tags", "product_tags",
            "item_classification", "browse_node_child",
        ],
        "parent_product_id": [
            "parent_sku", "parent_asin", "parent_product",
            "parent_id", "group_id", "product_group_id",
            "parent_handle", "main_product_id",
        ],
        "unit_cost": [
            "cost", "cogs", "cost_price", "purchase_price",
            "wholesale_price", "supplier_price",
            "variant_price", "price",
            "cost_per_item", "variant_cost", "variant_compare_at_price",
            "manufacturing_cost", "landed_cost", "buy_price",
            "selling_price", "retail_price", "msrp",
        ],
        "current_stock": [
            "stock", "inventory", "quantity_on_hand",
            "qty_available", "in_stock",
            "inventory_quantity", "variant_inventory_qty",
            "available_quantity",
            "stock_quantity", "wc_stock",
            "afn_fulfillable_quantity", "mfn_fulfillable_quantity",
        ],
        "status": [
            "product_status", "availability", "active",
            "published",
            "published_at", "published_scope",
            "post_status", "stock_status", "catalog_visibility",
            "is_active", "is_visible", "enabled",
        ],
        "size": [
            "product_size", "item_size", "variant_size",
            "option1", "option1_value", "option1_name",
            "option_size", "dimensions", "weight_unit",
        ],
        "color": [
            "product_color", "item_color", "variant_color", "colour",
            "option2", "option2_value", "option2_name", "option_color",
        ],
    },
    DataType.AD_SPEND: {
        "date": [
            "day", "report_date", "spend_date", "period",
            "date_start", "date_stop", "reporting_starts",
            "segments_date", "day_of_week",
            "campaign_date", "activity_date",
        ],
        "channel": [
            "source", "platform", "network", "ad_platform",
            "ad_source", "medium",
            "publisher_platform", "platform_position",
            "advertising_channel_type", "advertising_channel_sub_type",
            "traffic_source", "utm_source", "ad_network",
        ],
        "campaign_name": [
            "campaign", "campaign_id", "ad_campaign", "campaign_title",
            "campaign_name_fb", "adset_name", "ad_name",
            "campaign_name_google", "ad_group_name", "ad_group",
            "promotion_name", "promo_code", "marketing_campaign",
        ],
        "impressions": [
            "views", "impr", "ad_impressions", "reach",
            "unique_impressions", "display_impressions",
            "video_views", "estimated_impressions",
        ],
        "clicks": [
            "link_clicks", "ad_clicks", "click_count",
            "outbound_clicks", "unique_clicks", "inline_link_clicks",
            "interactions", "engagements",
        ],
        "spend": [
            "cost", "ad_spend", "amount_spent", "total_cost",
            "budget_spent",
            "spend_fb", "account_spend",
            "cost_micros", "cost_per_click", "average_cpc",
            "media_cost", "investment", "budget_used",
        ],
        "currency": [
            "currency_code", "curr", "account_currency",
        ],
        "conversions": [
            "purchases", "actions", "conversion_count", "results",
            "offsite_conversion_purchase", "unique_actions",
            "all_conversions", "conversions_google", "conversion_action",
            "total_conversions", "completed_purchases",
        ],
        "revenue_attributed": [
            "conversion_value", "purchase_value", "revenue", "value",
            "action_values", "purchase_roas",
            "all_conversions_value", "conversions_value",
            "attributed_revenue", "return_on_ad_spend", "roas_value",
        ],
    },
    DataType.REVIEWS: {
        "review_id": [
            "id", "review_number", "feedback_id",
            "shopify_review_id",
            "review_id_amazon", "marketplace_review_id",
            "comment_id", "testimonial_id",
        ],
        "product_id": [
            "sku", "item_id", "product_sku", "asin",
            "shopify_product_id", "handle",
            "parent_asin", "marketplace_product_id",
        ],
        "customer_id": [
            "user_id", "reviewer_id", "author_id",
            "reviewer_name", "profile_id",
            "buyer_id", "commenter_id",
        ],
        "review_date": [
            "date", "created_at", "posted_at", "submitted_at",
            "review_date_amazon",
            "publish_date", "date_published", "commented_at",
            "written_on",
        ],
        "rating": [
            "stars", "star_rating", "score", "review_rating",
            "overall_rating",
            "review_score", "satisfaction_score", "nps_score",
        ],
        "review_text": [
            "text", "comment", "body", "content", "feedback",
            "review_body", "description",
            "review_headline", "review_title",
            "summary", "opinion", "testimonial",
        ],
    },
    DataType.STOCK_LEVELS: {
        "product_id": [
            "sku", "item_id", "product_sku", "item_code",
            "shopify_product_id", "variant_id", "inventory_item_id",
            "asin", "fnsku", "seller_sku", "wc_product_id",
        ],
        "snapshot_date": [
            "date", "count_date", "stock_date", "inventory_date",
            "as_of_date",
            "report_date", "recorded_at", "timestamp",
            "checked_at", "last_updated",
        ],
        "quantity_on_hand": [
            "stock", "qty", "units", "inventory", "available",
            "on_hand", "in_stock",
            "inventory_quantity", "available_quantity",
            "afn_fulfillable_quantity", "mfn_fulfillable_quantity",
            "total_supply_quantity",
            "stock_quantity",
            "warehouse_qty", "bin_quantity", "physical_count",
            "stock_on_hand",
        ],
        "lead_time_days": [
            "lead_time", "supplier_lead_time", "restock_days",
            "delivery_days",
            "replenishment_days", "transit_days", "order_to_delivery",
            "procurement_lead_time",
        ],
        "warehouse": [
            "warehouse_name", "warehouse_code", "warehouse_id",
            "fulfillment_center", "fc_name", "storage_location",
            "depot", "distribution_center", "dc_name",
        ],
        "location": [
            "bin", "bin_location", "shelf", "aisle", "zone",
            "rack", "section", "storage_area", "bay",
        ],
    },
}

CONCAT_COLUMNS: dict[DataType, dict[str, list[str]]] = {
    DataType.REVIEWS: {
        "review_text": ["review_headline", "review_title", "review_body", "body", "comment"],
    },
}


def map_columns(
    headers: list[str],
    data_type: DataType,
) -> list[ColumnMapping]:
    synonym_map = SYNONYMS.get(data_type, {})
    mappings: list[ColumnMapping] = []
    used_targets: set[str] = set()

    for header in headers:
        normalized = _normalize(header)
        target, auto = _find_match(normalized, synonym_map, used_targets)
        if target:
            used_targets.add(target)
        mappings.append(ColumnMapping(
            source_column=header,
            target_column=target,
            auto_mapped=auto,
            data_type_hint=_guess_dtype(header),
        ))

    return mappings


def get_mapping_quality(
    headers: list[str],
    data_type: DataType,
) -> tuple[float, list[str]]:
    """Return (mapped_pct, unmapped_columns) for a set of headers against a data type."""
    mappings = map_columns(headers, data_type)
    total = len(mappings)
    if total == 0:
        return 0.0, []
    mapped = sum(1 for m in mappings if m.target_column)
    unmapped = [m.source_column for m in mappings if not m.target_column]
    return mapped / total, unmapped


def _find_match(
    normalized: str,
    synonym_map: dict[str, list[str]],
    used_targets: set[str],
) -> tuple[str | None, bool]:
    for canonical in synonym_map:
        if canonical in used_targets:
            continue
        if normalized == _normalize(canonical):
            return canonical, True

    for canonical, synonyms in synonym_map.items():
        if canonical in used_targets:
            continue
        for syn in synonyms:
            if normalized == _normalize(syn):
                return canonical, True

    if len(normalized) >= 7:
        for canonical, synonyms in synonym_map.items():
            if canonical in used_targets:
                continue
            all_names = [canonical, *synonyms]
            for name in all_names:
                norm_name = _normalize(name)
                if len(norm_name) >= 7 and _levenshtein(normalized, norm_name) <= 2:
                    return canonical, True

    return None, False


def _normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower().strip())


def _guess_dtype(header: str) -> str:
    h = header.lower()
    if any(kw in h for kw in ("date", "time", "created", "updated", "at")):
        return "date"
    if any(kw in h for kw in ("price", "amount", "cost", "spend", "revenue", "total", "value")):
        return "number"
    if any(kw in h for kw in ("count", "qty", "quantity", "stock", "units", "id", "rating")):
        return "number"
    return "string"


def _levenshtein(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return _levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            ins = prev_row[j + 1] + 1
            delete = curr_row[j] + 1
            sub = prev_row[j] + (c1 != c2)
            curr_row.append(min(ins, delete, sub))
        prev_row = curr_row
    return prev_row[-1]
