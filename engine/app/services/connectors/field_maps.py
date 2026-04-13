"""Platform → canonical column mapping for API connectors."""

SHOPIFY_ORDER_MAP = {
    "id": "order_id",
    "created_at": "order_date",
    "financial_status": "status",
    "total_price": "total_price",
    "total_discounts": "discount_amount",
    "currency": "currency",
    "source_name": "channel",
    "billing_address.province": "region",
    "refunds_amount": "refund_amount",
    "cancel_reason": "refund_reason",
}

SHOPIFY_CUSTOMER_MAP = {
    "id": "customer_id",
    "email": "email_raw",
    "first_name": "first_name_raw",
    "last_name": "last_name_raw",
    "created_at": "first_order_date",
    "orders_count": "total_orders",
    "total_spent": "total_spend",
    "default_address.province": "region",
}

SHOPIFY_PRODUCT_MAP = {
    "id": "product_id",
    "title": "product_name",
    "product_type": "category",
    "status": "status",
    "created_at": "created_at",
}

SHOPIFY_STATUS_MAP = {
    "paid": "completed",
    "partially_paid": "pending",
    "pending": "pending",
    "refunded": "refunded",
    "partially_refunded": "completed",
    "voided": "cancelled",
    "authorized": "pending",
}


