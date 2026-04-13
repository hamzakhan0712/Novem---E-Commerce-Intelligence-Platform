"""
Revenue attribution engine — decomposes KPI changes into quantified drivers.

When revenue drops 18%, this tells you WHY:
  - Orders ↓10%  → impact: -$8,000
  - AOV ↓5%      → impact: -$3,000
  - Refunds ↑22% → impact: -$4,500
"""

import logging
from datetime import datetime, timedelta, timezone

from app.core.database import get_duckdb_connection
from app.services.dashboard.kpi_calculator import calculate_kpis
from app.services.currency.currency_helper import sym as _sym

logger = logging.getLogger(__name__)

_PERIOD_DAYS = {
    "7d": 7, "14d": 14, "30d": 30, "60d": 60, "90d": 90,
    "6m": 182, "12m": 365,
}


def _period_bounds(period: str) -> tuple[str, str, str, str]:
    """Return (cur_start, cur_end, prev_start, prev_end) as ISO date strings."""
    days = _PERIOD_DAYS.get(period, 30)
    now = datetime.now(timezone.utc)
    cur_end = now.strftime("%Y-%m-%d")
    cur_start = (now - timedelta(days=days)).strftime("%Y-%m-%d")
    prev_end = cur_start
    prev_start = (now - timedelta(days=days * 2)).strftime("%Y-%m-%d")
    return cur_start, cur_end, prev_start, prev_end


def get_metric_breakdown(store_id: str, metric: str = "revenue", period: str = "30d") -> dict:
    """Dispatch to metric-specific driver analysis."""
    if metric == "revenue":
        return get_revenue_drivers(store_id, period)
    # Future: orders, customers, aov breakdowns
    return get_revenue_drivers(store_id, period)


def get_revenue_drivers(store_id: str, period: str = "30d") -> dict:
    """Decompose revenue change into additive drivers with $ impact."""
    conn = get_duckdb_connection()
    kpis = calculate_kpis(store_id, period)
    cur = kpis["current"]
    prev = kpis["previous"]
    change_pct = kpis["changes"]["revenue"]

    cur_rev = cur["revenue"]
    prev_rev = prev["revenue"]
    delta = cur_rev - prev_rev

    if prev_rev == 0 and cur_rev == 0:
        return _empty_result("revenue", 0, 0, 0, "No revenue data in either period.")

    drivers: list[dict] = []

    # 1) Volume effect: ΔOrders × prev_AOV
    cur_orders = cur["order_count"]
    prev_orders = prev["order_count"]
    prev_aov = prev["aov"]
    cur_aov = cur["aov"]
    d_orders = cur_orders - prev_orders
    d_aov = cur_aov - prev_aov

    volume_impact = d_orders * prev_aov if prev_aov > 0 else 0
    price_impact = prev_orders * d_aov if prev_orders > 0 else 0
    interaction = d_orders * d_aov

    if abs(volume_impact) > 0.01:
        pct = (d_orders / prev_orders * 100) if prev_orders > 0 else 0
        drivers.append({
            "driver": "Order Volume",
            "impact": round(volume_impact, 2),
            "direction": "up" if volume_impact > 0 else "down",
            "detail": f"Orders {'↑' if d_orders > 0 else '↓'}{abs(pct):.0f}% ({prev_orders:,}→{cur_orders:,})",
        })

    if abs(price_impact) > 0.01:
        pct = (d_aov / prev_aov * 100) if prev_aov > 0 else 0
        drivers.append({
            "driver": "Avg Order Value",
            "impact": round(price_impact, 2),
            "direction": "up" if price_impact > 0 else "down",
            "detail": f"AOV {'↑' if d_aov > 0 else '↓'}{abs(pct):.0f}% ({_sym(store_id)}{prev_aov:,.2f}→{_sym(store_id)}{cur_aov:,.2f})",
        })

    if abs(interaction) > 1:
        drivers.append({
            "driver": "Volume × Price Interaction",
            "impact": round(interaction, 2),
            "direction": "up" if interaction > 0 else "down",
            "detail": "Combined effect of order count and AOV changes",
        })

    # 2) Refund effect
    cur_start, cur_end, prev_start, prev_end = _period_bounds(period)
    refund_drivers = _refund_impact(conn, store_id, cur_start, cur_end, prev_start, prev_end)
    drivers.extend(refund_drivers)

    # 3) Channel mix
    channel_drivers = _channel_mix_impact(conn, store_id, cur_start, cur_end, prev_start, prev_end)
    drivers.extend(channel_drivers)

    # 4) Category mix
    category_drivers = _category_mix_impact(conn, store_id, cur_start, cur_end, prev_start, prev_end)
    drivers.extend(category_drivers)

    # 5) Customer mix (new vs returning)
    customer_drivers = _customer_mix_impact(conn, store_id, cur_start, cur_end, prev_start, prev_end)
    drivers.extend(customer_drivers)

    # Sort by absolute impact
    drivers.sort(key=lambda d: abs(d["impact"]), reverse=True)

    # Build narrative
    narrative = _build_narrative(delta, change_pct, drivers)

    return {
        "metric": "revenue",
        "current_value": cur_rev,
        "previous_value": prev_rev,
        "change_amount": round(delta, 2),
        "change_pct": change_pct,
        "period": period,
        "drivers": drivers,
        "narrative": narrative,
    }


def _refund_impact(conn, store_id: str, cs: str, ce: str, ps: str, pe: str) -> list[dict]:
    """Compute the $ impact of refund changes between periods."""
    row = conn.execute(
        """SELECT
             COALESCE(SUM(CASE WHEN order_date >= ? AND order_date <= ? THEN refund_amount ELSE 0 END), 0) as cur_ref,
             COALESCE(SUM(CASE WHEN order_date >= ? AND order_date < ?  THEN refund_amount ELSE 0 END), 0) as prev_ref
           FROM orders WHERE store_id = ? AND status = 'refunded'""",
        [cs, ce, ps, pe, store_id],
    ).fetchone()
    if not row:
        return []
    cur_ref, prev_ref = float(row[0]), float(row[1])
    d_ref = cur_ref - prev_ref
    if abs(d_ref) < 1:
        return []
    pct = (d_ref / prev_ref * 100) if prev_ref > 0 else 0
    return [{
        "driver": "Refunds",
        "impact": round(-d_ref, 2),
        "direction": "down" if d_ref > 0 else "up",
        "detail": f"Refunds {'↑' if d_ref > 0 else '↓'}{abs(pct):.0f}% ({_sym(store_id)}{prev_ref:,.0f}→{_sym(store_id)}{cur_ref:,.0f})",
    }]


def _channel_mix_impact(conn, store_id: str, cs: str, ce: str, ps: str, pe: str) -> list[dict]:
    """Identify which channels gained/lost revenue."""
    rows = conn.execute(
        """SELECT
             COALESCE(channel, 'Unknown') as ch,
             COALESCE(SUM(CASE WHEN order_date >= ? AND order_date <= ? THEN total_price - discount_amount END), 0) as cur_rev,
             COALESCE(SUM(CASE WHEN order_date >= ? AND order_date < ?  THEN total_price - discount_amount END), 0) as prev_rev
           FROM orders WHERE store_id = ? AND status = 'completed'
             AND (order_date >= ? OR order_date >= ?)
           GROUP BY ch
           HAVING cur_rev > 0 OR prev_rev > 0
           ORDER BY ABS(cur_rev - prev_rev) DESC
           LIMIT 5""",
        [cs, ce, ps, pe, store_id, ps, cs],
    ).fetchall()
    drivers = []
    for r in rows:
        ch, cur_r, prev_r = str(r[0]), float(r[1]), float(r[2])
        d = cur_r - prev_r
        if abs(d) < 10:
            continue
        pct = (d / prev_r * 100) if prev_r > 0 else 100
        drivers.append({
            "driver": f"Channel: {ch}",
            "impact": round(d, 2),
            "direction": "up" if d > 0 else "down",
            "detail": f"{ch} {'↑' if d > 0 else '↓'}{abs(pct):.0f}% ({_sym(store_id)}{prev_r:,.0f}→{_sym(store_id)}{cur_r:,.0f})",
        })
    return drivers


def _category_mix_impact(conn, store_id: str, cs: str, ce: str, ps: str, pe: str) -> list[dict]:
    """Identify which categories gained/lost revenue."""
    rows = conn.execute(
        """SELECT
             COALESCE(category, 'Uncategorized') as cat,
             COALESCE(SUM(CASE WHEN order_date >= ? AND order_date <= ? THEN total_price - discount_amount END), 0) as cur_rev,
             COALESCE(SUM(CASE WHEN order_date >= ? AND order_date < ?  THEN total_price - discount_amount END), 0) as prev_rev
           FROM orders WHERE store_id = ? AND status = 'completed'
             AND (order_date >= ? OR order_date >= ?)
           GROUP BY cat
           HAVING cur_rev > 0 OR prev_rev > 0
           ORDER BY ABS(cur_rev - prev_rev) DESC
           LIMIT 5""",
        [cs, ce, ps, pe, store_id, ps, cs],
    ).fetchall()
    drivers = []
    for r in rows:
        cat, cur_r, prev_r = str(r[0]), float(r[1]), float(r[2])
        d = cur_r - prev_r
        if abs(d) < 10:
            continue
        pct = (d / prev_r * 100) if prev_r > 0 else 100
        drivers.append({
            "driver": f"Category: {cat}",
            "impact": round(d, 2),
            "direction": "up" if d > 0 else "down",
            "detail": f"{cat} {'↑' if d > 0 else '↓'}{abs(pct):.0f}% ({_sym(store_id)}{prev_r:,.0f}→{_sym(store_id)}{cur_r:,.0f})",
        })
    return drivers


def _customer_mix_impact(conn, store_id: str, cs: str, ce: str, ps: str, pe: str) -> list[dict]:
    """Compare new vs returning customer contribution between periods."""
    row = conn.execute(
        """WITH prev_customers AS (
             SELECT DISTINCT customer_id FROM orders
             WHERE store_id = ? AND order_date < ? AND status = 'completed'
           ),
           cur_orders AS (
             SELECT customer_id, SUM(total_price - discount_amount) as rev
             FROM orders WHERE store_id = ? AND order_date >= ? AND order_date <= ? AND status = 'completed'
             GROUP BY customer_id
           )
           SELECT
             COALESCE(SUM(CASE WHEN pc.customer_id IS NOT NULL THEN co.rev END), 0) as returning_rev,
             COALESCE(SUM(CASE WHEN pc.customer_id IS NULL THEN co.rev END), 0) as new_rev
           FROM cur_orders co
           LEFT JOIN prev_customers pc ON co.customer_id = pc.customer_id""",
        [store_id, cs, store_id, cs, ce],
    ).fetchone()

    prev_row = conn.execute(
        """WITH earlier_customers AS (
             SELECT DISTINCT customer_id FROM orders
             WHERE store_id = ? AND order_date < ? AND status = 'completed'
           ),
           prev_orders AS (
             SELECT customer_id, SUM(total_price - discount_amount) as rev
             FROM orders WHERE store_id = ? AND order_date >= ? AND order_date < ? AND status = 'completed'
             GROUP BY customer_id
           )
           SELECT
             COALESCE(SUM(CASE WHEN ec.customer_id IS NOT NULL THEN po.rev END), 0) as returning_rev,
             COALESCE(SUM(CASE WHEN ec.customer_id IS NULL THEN po.rev END), 0) as new_rev
           FROM prev_orders po
           LEFT JOIN earlier_customers ec ON po.customer_id = ec.customer_id""",
        [store_id, ps, store_id, ps, pe],
    ).fetchone()

    if not row or not prev_row:
        return []

    drivers = []
    cur_ret, cur_new = float(row[0]), float(row[1])
    prev_ret, prev_new = float(prev_row[0]), float(prev_row[1])

    d_ret = cur_ret - prev_ret
    if abs(d_ret) > 10:
        pct = (d_ret / prev_ret * 100) if prev_ret > 0 else 100
        drivers.append({
            "driver": "Returning Customers",
            "impact": round(d_ret, 2),
            "direction": "up" if d_ret > 0 else "down",
            "detail": f"Returning revenue {'↑' if d_ret > 0 else '↓'}{abs(pct):.0f}% ({_sym(store_id)}{prev_ret:,.0f}→{_sym(store_id)}{cur_ret:,.0f})",
        })

    d_new = cur_new - prev_new
    if abs(d_new) > 10:
        pct = (d_new / prev_new * 100) if prev_new > 0 else 100
        drivers.append({
            "driver": "New Customers",
            "impact": round(d_new, 2),
            "direction": "up" if d_new > 0 else "down",
            "detail": f"New customer revenue {'↑' if d_new > 0 else '↓'}{abs(pct):.0f}% ({_sym(store_id)}{prev_new:,.0f}→{_sym(store_id)}{cur_new:,.0f})",
        })

    return drivers


def _build_narrative(delta: float, change_pct: float, drivers: list[dict]) -> str:
    """Build a plain-language explanation from the driver breakdown."""
    if abs(delta) < 1:
        return "Revenue remained stable with no significant changes."

    direction = "increased" if delta > 0 else "decreased"
    narrative = f"Revenue {direction} {abs(change_pct):.1f}% ({_sym(store_id)}{abs(delta):,.0f})"

    negative = [d for d in drivers if d["impact"] < 0]
    positive = [d for d in drivers if d["impact"] > 0]

    parts = []
    if delta < 0 and negative:
        top = negative[:3]
        parts.append("primarily due to " + ", ".join(
            f"{d['driver'].lower()} (-{_sym(store_id)}{abs(d['impact']):,.0f})" for d in top
        ))
    elif delta > 0 and positive:
        top = positive[:3]
        parts.append("driven by " + ", ".join(
            f"{d['driver'].lower()} (+{_sym(store_id)}{d['impact']:,.0f})" for d in top
        ))

    if parts:
        narrative += " — " + parts[0] + "."
    else:
        narrative += "."

    return narrative


def _empty_result(metric: str, cur: float, prev: float, pct: float, msg: str) -> dict:
    return {
        "metric": metric,
        "current_value": cur,
        "previous_value": prev,
        "change_amount": 0,
        "change_pct": pct,
        "period": "",
        "drivers": [],
        "narrative": msg,
    }
