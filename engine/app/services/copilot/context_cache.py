"""
Context cache for copilot — precomputes and caches store data snapshots.

After a dataset is imported, this module builds a comprehensive context
snapshot so the copilot has instant knowledge without running SQL on
every question.  Thread-safe via threading.Lock per store.
"""

import logging
import threading
import time
from datetime import datetime, timedelta, timezone

from app.core.database import get_duckdb_connection
from app.services.currency.currency_helper import sym as _sym

logger = logging.getLogger(__name__)

# ── In-memory cache ─────────────────────────────────────────────

_cache: dict[str, dict] = {}
_cache_lock = threading.Lock()
_CACHE_TTL_SECONDS = 600  # 10 minutes


def invalidate_cache(store_id: str) -> None:
    """Remove cached context for a store (e.g. after import)."""
    with _cache_lock:
        _cache.pop(store_id, None)
    logger.info("Context cache invalidated for store %s", store_id)


def invalidate_all() -> None:
    """Clear the entire cache."""
    with _cache_lock:
        _cache.clear()
    logger.info("Context cache cleared for all stores")


def get_or_build_context(store_id: str) -> dict | None:
    """Return cached context if still valid, otherwise build it."""
    with _cache_lock:
        entry = _cache.get(store_id)
        if entry and (time.monotonic() - entry["_built_at"]) < _CACHE_TTL_SECONDS:
            return entry

    # Build outside the lock to avoid blocking other stores
    return build_store_context(store_id)


def build_store_context(store_id: str) -> dict | None:
    """Precompute a comprehensive data snapshot for a store.

    Returns None if no order data exists for the store.
    """
    conn = get_duckdb_connection()
    ctx: dict = {"store_id": store_id}

    try:
        # ── Overview ────────────────────────────────────────────
        overview = conn.execute(
            """SELECT
                 COUNT(*) as orders,
                 COALESCE(SUM(total_price - discount_amount), 0) as revenue,
                 COUNT(DISTINCT customer_id) as customers,
                 COUNT(DISTINCT product_id) as products,
                 MIN(order_date) as first_order,
                 MAX(order_date) as last_order,
                 COALESCE(AVG(total_price - discount_amount), 0) as aov
               FROM orders WHERE store_id = ?""",
            [store_id],
        ).fetchone()

        if not overview or overview[0] == 0:
            return None

        ctx["overview"] = {
            "orders": int(overview[0]),
            "revenue": float(overview[1]),
            "customers": int(overview[2]),
            "products": int(overview[3]),
            "first_order": str(overview[4]),
            "last_order": str(overview[5]),
            "aov": float(overview[6]),
        }

        # ── Monthly revenue (last 12) ──────────────────────────
        monthly = conn.execute(
            """SELECT strftime(order_date, '%Y-%m') as month,
                      SUM(total_price - discount_amount) as rev,
                      COUNT(*) as cnt
               FROM orders WHERE store_id = ?
               GROUP BY month ORDER BY month DESC LIMIT 12""",
            [store_id],
        ).fetchall()
        ctx["monthly_revenue"] = [
            {"month": r[0], "revenue": float(r[1]), "orders": int(r[2])}
            for r in monthly
        ]

        # ── Customer metrics ────────────────────────────────────
        cust = conn.execute(
            """SELECT
                 COUNT(DISTINCT cid) as total,
                 COUNT(DISTINCT CASE WHEN oc > 1 THEN cid END) as repeat_c,
                 ROUND(COUNT(DISTINCT CASE WHEN oc > 1 THEN cid END) * 100.0 /
                   NULLIF(COUNT(DISTINCT cid), 0), 1) as repeat_rate
               FROM (
                 SELECT customer_id as cid, COUNT(*) as oc
                 FROM orders WHERE store_id = ? GROUP BY customer_id
               )""",
            [store_id],
        ).fetchone()
        ctx["customer_metrics"] = {
            "total": int(cust[0]) if cust else 0,
            "repeat": int(cust[1]) if cust else 0,
            "repeat_rate": float(cust[2]) if cust and cust[2] else 0.0,
        }

        # ── Top customers ──────────────────────────────────────
        top_cust = conn.execute(
            """SELECT customer_id, COUNT(*) as orders, SUM(total_price - discount_amount) as spent
               FROM orders WHERE store_id = ?
               GROUP BY customer_id ORDER BY spent DESC LIMIT 10""",
            [store_id],
        ).fetchall()
        ctx["top_customers"] = [
            {"id": r[0], "orders": int(r[1]), "spent": float(r[2])}
            for r in top_cust
        ]

        # ── Top products ───────────────────────────────────────
        top_prod = conn.execute(
            """SELECT product_id, SUM(quantity) as qty, SUM(total_price - discount_amount) as rev
               FROM orders WHERE store_id = ?
               GROUP BY product_id ORDER BY rev DESC LIMIT 10""",
            [store_id],
        ).fetchall()
        ctx["top_products"] = [
            {"id": r[0], "qty": int(r[1]), "revenue": float(r[2])}
            for r in top_prod
        ]

        # ── Top categories ─────────────────────────────────────
        cats = conn.execute(
            """SELECT COALESCE(category, 'Uncategorized') as cat,
                      SUM(total_price - discount_amount) as rev,
                      COUNT(*) as cnt
               FROM orders WHERE store_id = ?
               GROUP BY cat ORDER BY rev DESC LIMIT 10""",
            [store_id],
        ).fetchall()
        ctx["top_categories"] = [
            {"name": r[0], "revenue": float(r[1]), "orders": int(r[2])}
            for r in cats
        ]

        # ── Order status breakdown ─────────────────────────────
        statuses = conn.execute(
            """SELECT status, COUNT(*) as cnt, SUM(total_price - discount_amount) as val
               FROM orders WHERE store_id = ? GROUP BY status""",
            [store_id],
        ).fetchall()
        ctx["order_statuses"] = [
            {"status": r[0], "count": int(r[1]), "value": float(r[2])}
            for r in statuses
        ]

        # ── Channel distribution ───────────────────────────────
        channels = conn.execute(
            """SELECT COALESCE(channel, 'Unknown') as ch,
                      COUNT(*) as cnt,
                      SUM(total_price - discount_amount) as rev
               FROM orders WHERE store_id = ?
               GROUP BY ch ORDER BY rev DESC LIMIT 10""",
            [store_id],
        ).fetchall()
        ctx["channels"] = [
            {"name": r[0], "orders": int(r[1]), "revenue": float(r[2])}
            for r in channels
        ]

        # ── Reviews summary ────────────────────────────────────
        try:
            rev = conn.execute(
                """SELECT COUNT(*) as cnt, AVG(rating) as avg_r,
                          AVG(sentiment_score) as avg_s,
                          COUNT(CASE WHEN sentiment_label = 'positive' THEN 1 END) as pos,
                          COUNT(CASE WHEN sentiment_label = 'negative' THEN 1 END) as neg
                   FROM reviews WHERE store_id = ?""",
                [store_id],
            ).fetchone()
            if rev and rev[0] > 0:
                ctx["reviews"] = {
                    "total": int(rev[0]),
                    "avg_rating": float(rev[1] or 0),
                    "avg_sentiment": float(rev[2] or 0),
                    "positive": int(rev[3]),
                    "negative": int(rev[4]),
                }
        except Exception:
            pass

        # ── Last 7 days snapshot ───────────────────────────────
        cutoff = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)).isoformat()
        recent = conn.execute(
            """SELECT COUNT(*) as cnt, COALESCE(SUM(total_price - discount_amount), 0) as rev
               FROM orders WHERE store_id = ? AND order_date >= ?""",
            [store_id, cutoff],
        ).fetchone()
        ctx["last_7_days"] = {
            "orders": int(recent[0]) if recent else 0,
            "revenue": float(recent[1]) if recent else 0.0,
        }

        # ── New customers (last 30 days) ───────────────────────
        cutoff_30 = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)).isoformat()
        new_cust = conn.execute(
            """SELECT COUNT(DISTINCT customer_id) as value
               FROM (
                 SELECT customer_id, MIN(order_date) as first_order
                 FROM orders WHERE store_id = ? GROUP BY customer_id
               ) WHERE first_order >= ?""",
            [store_id, cutoff_30],
        ).fetchone()
        ctx["new_customers_30d"] = int(new_cust[0]) if new_cust else 0

        # ── Table row counts ───────────────────────────────────
        table_counts: dict[str, int] = {}
        for table in ("orders", "customers", "products", "ad_spend", "reviews", "stock_levels"):
            try:
                row = conn.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE store_id = ?",
                    [store_id],
                ).fetchone()
                table_counts[table] = int(row[0]) if row else 0
            except Exception:
                table_counts[table] = 0
        ctx["table_counts"] = table_counts

        # Store in cache
        ctx["_built_at"] = time.monotonic()
        with _cache_lock:
            _cache[store_id] = ctx

        logger.info(
            "Context cache built for store %s: %d orders, $%.2f revenue",
            store_id, ctx["overview"]["orders"], ctx["overview"]["revenue"],
        )
        return ctx

    except Exception as exc:
        logger.error("Failed to build context cache for store %s: %s", store_id, exc)
        return None


# ── Context Formatting ──────────────────────────────────────────

def format_cached_context(ctx: dict, question: str) -> str:
    """Format a cached context dict into a text block for the LLM.

    Uses the question to decide which sections to include (same keyword
    logic as `_build_rag_context` but hitting the cache instead of SQL).
    """
    q = question.lower()
    parts: list[str] = []
    ov = ctx.get("overview", {})

    if not ov:
        return "STORE OVERVIEW: No order data available yet."

    # Always include overview + condensed core metrics
    parts.append(
        f"STORE OVERVIEW: {ov['orders']:,} orders, {_sym(store_id)}{ov['revenue']:,.2f} total revenue, "
        f"{ov['customers']:,} customers, {ov['products']:,} products, "
        f"AOV {_sym(store_id)}{ov['aov']:,.2f}, data from {ov['first_order']} to {ov['last_order']}."
    )

    # Always-include condensed core metrics (Improvement #4)
    cm = ctx.get("customer_metrics", {})
    if cm.get("total"):
        parts.append(
            f"CUSTOMERS: {cm['total']:,} total, {cm.get('repeat_rate', 0):.1f}% repeat rate."
        )

    top_p = ctx.get("top_products", [])
    if top_p:
        parts.append(
            f"TOP PRODUCT: {top_p[0]['id']} ({_sym(store_id)}{top_p[0]['revenue']:,.2f} revenue)"
        )

    top_cat = ctx.get("top_categories", [])
    if top_cat:
        parts.append(
            f"TOP CATEGORY: {top_cat[0]['name']} ({_sym(store_id)}{top_cat[0]['revenue']:,.2f} revenue)"
        )

    # Revenue / sales context
    if any(w in q for w in ["revenue", "sales", "income", "earning", "money", "monthly", "trend"]):
        monthly = ctx.get("monthly_revenue", [])
        if monthly:
            lines = [f"  {m['month']}: {_sym(store_id)}{m['revenue']:,.2f} ({m['orders']:,} orders)" for m in monthly[:6]]
            parts.append("MONTHLY REVENUE (last 6):\n" + "\n".join(lines))

    # Customer context
    if any(w in q for w in ["customer", "retention", "repeat", "returning", "loyal", "churn", "segment"]):
        if cm.get("total"):
            parts.append(
                f"CUSTOMER METRICS: {cm['total']:,} total, {cm.get('repeat', 0):,} repeat, "
                f"{cm.get('repeat_rate', 0):.1f}% repeat rate."
            )
        top_c = ctx.get("top_customers", [])
        if top_c:
            lines = [f"  {c['id']}: {c['orders']:,} orders, {_sym(store_id)}{c['spent']:,.2f}" for c in top_c[:5]]
            parts.append("TOP CUSTOMERS:\n" + "\n".join(lines))

    # Product context
    if any(w in q for w in ["product", "selling", "best", "top", "category", "item", "stock"]):
        if top_p:
            lines = [f"  {p['id']}: {p['qty']:,} units, {_sym(store_id)}{p['revenue']:,.2f}" for p in top_p[:5]]
            parts.append("TOP PRODUCTS:\n" + "\n".join(lines))
        if top_cat:
            lines = [f"  {c['name']}: {_sym(store_id)}{c['revenue']:,.2f} ({c['orders']:,} orders)" for c in top_cat[:5]]
            parts.append("TOP CATEGORIES:\n" + "\n".join(lines))

    # Refund & order status context
    if any(w in q for w in ["refund", "return", "cancel", "status"]):
        statuses = ctx.get("order_statuses", [])
        if statuses:
            lines = [f"  {s['status']}: {s['count']:,} orders ({_sym(store_id)}{s['value']:,.2f})" for s in statuses]
            parts.append("ORDER STATUS BREAKDOWN:\n" + "\n".join(lines))

    # Time-based analysis
    if any(w in q for w in ["today", "week", "recent", "latest", "last"]):
        last7 = ctx.get("last_7_days", {})
        if last7.get("orders"):
            parts.append(f"LAST 7 DAYS: {last7['orders']:,} orders, {_sym(store_id)}{last7['revenue']:,.2f} revenue.")

    # Review / sentiment context
    if any(w in q for w in ["review", "sentiment", "rating", "feedback", "opinion"]):
        reviews = ctx.get("reviews", {})
        if reviews.get("total"):
            parts.append(
                f"REVIEWS: {reviews['total']:,} total, avg rating {reviews['avg_rating']:.1f}★, "
                f"sentiment {reviews['avg_sentiment'] * 100:.0f}%, "
                f"{reviews['positive']:,} positive, {reviews['negative']:,} negative."
            )

    # Channel / region context
    if any(w in q for w in ["channel", "region", "where", "source", "marketing"]):
        channels = ctx.get("channels", [])
        if channels:
            lines = [f"  {ch['name']}: {ch['orders']:,} orders, {_sym(store_id)}{ch['revenue']:,.2f}" for ch in channels[:5]]
            parts.append("CHANNELS:\n" + "\n".join(lines))

    # New customers
    if any(w in q for w in ["new customer", "acquisition", "first time"]):
        nc = ctx.get("new_customers_30d", 0)
        parts.append(f"NEW CUSTOMERS (last 30 days): {nc:,}")

    return "\n\n".join(parts)
