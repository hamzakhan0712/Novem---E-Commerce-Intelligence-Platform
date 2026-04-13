"""
Shared currency formatting helper.

Every service that generates human-readable money strings should call
``fmt(value, store_id)`` instead of hard-coding ``₹``.
"""

import logging
from functools import lru_cache

from app.core.database import get_sqlite_connection

logger = logging.getLogger(__name__)

_SYMBOLS: dict[str, str] = {
    "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "CNY": "¥",
    "INR": "₹", "KRW": "₩", "BRL": "R$", "CAD": "CA$", "AUD": "A$",
    "CHF": "CHF", "SEK": "kr", "NOK": "kr", "DKK": "kr", "PLN": "zł",
    "TRY": "₺", "MXN": "MX$", "SGD": "S$", "HKD": "HK$", "NZD": "NZ$",
    "ZAR": "R", "THB": "฿", "MYR": "RM", "PHP": "₱",
    "AED": "د.إ", "SAR": "﷼", "PKR": "₨", "BDT": "৳",
}


def symbol(currency_code: str = "INR") -> str:
    """Return display symbol for a currency code."""
    return _SYMBOLS.get(currency_code, currency_code)


def store_currency(store_id: str) -> str:
    """Look up the currency code for a store. Falls back to ``INR``."""
    try:
        conn = get_sqlite_connection()
        row = conn.execute(
            "SELECT currency FROM stores WHERE id = ?", [store_id],
        ).fetchone()
        return row[0] if row and row[0] else "INR"
    except Exception:
        return "INR"


def sym(store_id: str) -> str:
    """Shortcut: return the display symbol for a store's currency."""
    return symbol(store_currency(store_id))


def fmt(value: float, store_id: str, decimals: int = 0) -> str:
    """Format *value* with the store's currency symbol.

    Examples::

        fmt(12345.6, "store-1")          → "₹12,346"
        fmt(12345.6, "store-1", 2)       → "₹12,345.60"
    """
    s = sym(store_id)
    return f"{s}{value:,.{decimals}f}"
