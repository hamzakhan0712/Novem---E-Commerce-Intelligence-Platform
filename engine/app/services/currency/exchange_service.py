"""
Currency exchange rate service — fetches and caches exchange rates
for converting monetary values from the base currency (INR) to
the user's selected currency.

Uses the free frankfurter.app API (ECB data, no key required).
Falls back to static rates if offline.
"""

import logging
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_CACHE: dict[str, float] = {}
_CACHE_TIMESTAMP: float = 0
_CACHE_TTL_SECONDS: int = 3600  # 1 hour

_FALLBACK_RATES: dict[str, float] = {
    "INR": 1.0,
    "USD": 0.012,
    "EUR": 0.011,
    "GBP": 0.0095,
    "CAD": 0.016,
    "AUD": 0.018,
    "JPY": 1.856,
    "CNY": 0.087,
    "BRL": 0.060,
    "MXN": 0.206,
    "KRW": 15.928,
    "SGD": 0.016,
    "HKD": 0.094,
    "TRY": 0.383,
    "ZAR": 0.222,
    "SEK": 0.126,
    "NOK": 0.128,
    "DKK": 0.082,
    "CHF": 0.0105,
    "NZD": 0.020,
    "AED": 0.044,
    "SAR": 0.045,
    "PKR": 3.329,
    "BDT": 1.317,
}

API_URL = "https://api.frankfurter.app/latest?from=INR"


def get_exchange_rates(force_refresh: bool = False) -> dict[str, float]:
    """Return exchange rates with USD as the base currency.

    Rates are cached for 1 hour. Falls back to static rates on error.
    """
    global _CACHE, _CACHE_TIMESTAMP

    now = time.time()
    if _CACHE and not force_refresh and (now - _CACHE_TIMESTAMP) < _CACHE_TTL_SECONDS:
        return _CACHE

    try:
        response = httpx.get(API_URL, timeout=5.0, follow_redirects=True)
        response.raise_for_status()
        data = response.json()
        rates = data.get("rates", {})
        rates["INR"] = 1.0
        _CACHE = rates
        _CACHE_TIMESTAMP = now
        logger.info("Fetched %d exchange rates from frankfurter.app", len(rates))
        return _CACHE
    except Exception as e:
        logger.warning("Failed to fetch exchange rates: %s — using fallback", e)
        if _CACHE:
            return _CACHE
        return _FALLBACK_RATES.copy()


def get_rate(target_currency: str) -> float:
    """Get the exchange rate from INR to the target currency."""
    if target_currency == "INR":
        return 1.0
    rates = get_exchange_rates()
    rate = rates.get(target_currency)
    if rate is None:
        logger.warning("No rate for %s — returning 1.0", target_currency)
        return 1.0
    return float(rate)


def convert(amount: float, target_currency: str) -> float:
    """Convert an INR amount to the target currency."""
    return round(amount * get_rate(target_currency), 2)


def get_supported_currencies() -> list[dict]:
    """Return list of supported currencies with their current rates."""
    rates = get_exchange_rates()
    return [
        {"code": code, "rate": rate}
        for code, rate in sorted(rates.items())
    ]
