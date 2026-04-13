import logging
import re

logger = logging.getLogger(__name__)

CHANNEL_MAP: dict[str, str] = {
    "google ads": "google",
    "google_ads": "google",
    "google": "google",
    "adwords": "google",
    "facebook": "meta",
    "facebook ads": "meta",
    "fb": "meta",
    "meta": "meta",
    "meta ads": "meta",
    "instagram": "meta",
    "tiktok": "tiktok",
    "tiktok_ads": "tiktok",
    "tiktok ads": "tiktok",
    "email": "email",
    "email_marketing": "email",
    "newsletter": "email",
    "mailchimp": "email",
    "organic": "organic",
    "organic_search": "organic",
    "seo": "organic",
    "direct": "organic",
    # Shopify-specific channels
    "web": "web",
    "online_store": "web",
    "online store": "web",
    "pos": "pos",
    "point_of_sale": "pos",
    "shopify_draft_order": "draft_order",
    "draft_order": "draft_order",
    "buy_button": "buy_button",
    "shopify_app": "web",
    # WooCommerce-specific channels
    "affiliate": "affiliate",
    "referral": "affiliate",
}


def normalize_channels(
    values: list[str],
) -> dict[str, str]:
    """Return a mapping from raw channel value to normalized value."""
    result: dict[str, str] = {}
    for raw in values:
        if not raw or not raw.strip():
            continue
        key = re.sub(r"[^a-z0-9 ]", "", raw.strip().lower())
        normalized = CHANNEL_MAP.get(key, raw.strip().lower())
        result[raw] = normalized
    return result
