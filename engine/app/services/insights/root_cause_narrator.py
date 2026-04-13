"""
Root Cause Narrator — Automated root cause narratives.

When revenue drops (or rises) week-over-week, runs a 5-layer drill-down
(category, channel, region, discount rate, return rate) then generates
a plain-English verdict via Ollama (with template fallback).
"""

import logging
from datetime import datetime, timedelta, timezone

from app.config import OLLAMA_URL
from app.core.database import get_duckdb_connection
from app.services.insights.causal_engine import get_revenue_drivers
from app.services.currency.currency_helper import sym as _sym

logger = logging.getLogger(__name__)

_PERIOD_DAYS = {
    "7d": 7, "14d": 14, "30d": 30, "60d": 60, "90d": 90,
    "6m": 182, "12m": 365,
}

_HAS_OLLAMA = False
_client = None
try:
    from ollama import Client as OllamaClient
    _client = OllamaClient(host=OLLAMA_URL)
    _HAS_OLLAMA = True
except ImportError:
    pass


def generate_root_cause_narrative(store_id: str, period: str = "7d") -> dict:
    """Run 5-layer drill-down and generate a 1-2 sentence verdict."""
    conn = get_duckdb_connection()
    days = _PERIOD_DAYS.get(period, 7)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    cur_end = now.strftime("%Y-%m-%d")
    cur_start = (now - timedelta(days=days)).strftime("%Y-%m-%d")
    prev_end = cur_start
    prev_start = (now - timedelta(days=days * 2)).strftime("%Y-%m-%d")

    try:
        drivers_data = get_revenue_drivers(store_id, period)
        change_pct = drivers_data.get("change_pct", 0) or 0
        change_amount = drivers_data.get("change_amount", 0) or 0

        if change_pct > 0.5:
            direction = "up"
        elif change_pct < -0.5:
            direction = "down"
        else:
            direction = "flat"

        drill_downs = []
        drill_downs.append(_drill_by_category(conn, store_id, cur_start, cur_end, prev_start, prev_end))
        drill_downs.append(_drill_by_channel(conn, store_id, cur_start, cur_end, prev_start, prev_end))
        drill_downs.append(_drill_by_region(conn, store_id, cur_start, cur_end, prev_start, prev_end))
        drill_downs.append(_drill_by_discount(conn, store_id, cur_start, cur_end, prev_start, prev_end))
        drill_downs.append(_drill_by_returns(conn, store_id, cur_start, cur_end, prev_start, prev_end))

        valid_drills = [d for d in drill_downs if d.get("impact") is not None]
        valid_drills.sort(key=lambda d: abs(d.get("impact", 0)), reverse=True)
        primary = valid_drills[0] if valid_drills else None

        primary_cause = None
        if primary:
            primary_cause = {
                "dimension": primary["dimension"],
                "contributor": primary["top_contributor"],
                "impact": primary["impact"],
                "impact_pct": round(primary["impact"] / abs(change_amount) * 100, 1) if change_amount else 0,
                "detail": primary["detail"],
            }

        verdict = _generate_verdict(
            direction, change_pct, change_amount, primary_cause, drill_downs
        )

        return {
            "verdict": verdict["text"],
            "direction": direction,
            "change_pct": round(change_pct, 2),
            "change_amount": round(change_amount, 2),
            "primary_cause": primary_cause,
            "drill_downs": drill_downs,
            "period": period,
            "generated_by": verdict["source"],
        }

    except Exception as exc:
        logger.error("Root cause narrative failed: %s", exc)
        return {
            "verdict": "Unable to generate root cause analysis.",
            "direction": "flat",
            "change_pct": 0,
            "change_amount": 0,
            "primary_cause": None,
            "drill_downs": [],
            "period": period,
            "generated_by": "error",
            "message": str(exc),
        }


def _drill_by_category(conn, store_id, cs, ce, ps, pe) -> dict:
    """Find the category with the biggest revenue change."""
    return _drill_by_dimension(conn, store_id, cs, ce, ps, pe, "category", "Category")


def _drill_by_channel(conn, store_id, cs, ce, ps, pe) -> dict:
    return _drill_by_dimension(conn, store_id, cs, ce, ps, pe, "channel", "Channel")


def _drill_by_region(conn, store_id, cs, ce, ps, pe) -> dict:
    return _drill_by_dimension(conn, store_id, cs, ce, ps, pe, "region", "Region")


def _drill_by_dimension(conn, store_id, cs, ce, ps, pe, column: str, label: str) -> dict:
    """Generic drill-down by a dimension column."""
    try:
        rows = conn.execute(
            f"""
            SELECT
                COALESCE({column}, 'Unknown') AS dim_val,
                SUM(CASE WHEN order_date >= ? AND order_date <= ? THEN total_price - discount_amount ELSE 0 END) AS cur_rev,
                SUM(CASE WHEN order_date >= ? AND order_date < ? THEN total_price - discount_amount ELSE 0 END) AS prev_rev
            FROM orders
            WHERE store_id = ? AND status = 'completed'
              AND order_date >= ? AND order_date <= ?
            GROUP BY COALESCE({column}, 'Unknown')
            ORDER BY ABS(cur_rev - prev_rev) DESC
            LIMIT 1
            """,
            [cs, ce, ps, pe, store_id, ps, ce],
        ).fetchone()

        if not rows:
            return {"dimension": label, "top_contributor": "N/A", "impact": None, "detail": "No data"}

        dim_val = rows[0]
        cur = float(rows[1])
        prev = float(rows[2])
        delta = cur - prev
        pct = ((cur - prev) / prev * 100) if prev > 0 else 0

        dir_arrow = "↑" if delta > 0 else "↓"
        detail = f"{label}: {dim_val} {dir_arrow} {_sym(store_id)}{abs(delta):,.0f} ({pct:+.1f}%)"

        return {
            "dimension": label,
            "top_contributor": str(dim_val),
            "impact": round(delta, 2),
            "detail": detail,
        }
    except Exception:
        return {"dimension": label, "top_contributor": "N/A", "impact": None, "detail": "Query failed"}


def _drill_by_discount(conn, store_id, cs, ce, ps, pe) -> dict:
    """Compare high-discount vs low-discount order revenue shift."""
    try:
        row = conn.execute(
            """
            WITH orders_bucketed AS (
                SELECT
                    CASE WHEN discount_amount > total_price * 0.1 THEN 'high_discount' ELSE 'low_discount' END AS bucket,
                    CASE WHEN order_date >= ? AND order_date <= ? THEN 'current' ELSE 'previous' END AS period_label,
                    total_price - discount_amount AS net_rev
                FROM orders
                WHERE store_id = ? AND status = 'completed'
                  AND order_date >= ? AND order_date <= ?
            )
            SELECT
                SUM(CASE WHEN period_label = 'current' AND bucket = 'high_discount' THEN net_rev ELSE 0 END) AS cur_high,
                SUM(CASE WHEN period_label = 'previous' AND bucket = 'high_discount' THEN net_rev ELSE 0 END) AS prev_high,
                SUM(CASE WHEN period_label = 'current' AND bucket = 'low_discount' THEN net_rev ELSE 0 END) AS cur_low,
                SUM(CASE WHEN period_label = 'previous' AND bucket = 'low_discount' THEN net_rev ELSE 0 END) AS prev_low
            FROM orders_bucketed
            """,
            [cs, ce, store_id, ps, ce],
        ).fetchone()

        if not row:
            return {"dimension": "Discount Impact", "top_contributor": "N/A", "impact": None, "detail": "No data"}

        cur_high, prev_high = float(row[0] or 0), float(row[1] or 0)
        cur_low, prev_low = float(row[2] or 0), float(row[3] or 0)

        high_delta = cur_high - prev_high
        low_delta = cur_low - prev_low

        if abs(high_delta) > abs(low_delta):
            contributor = "Heavily discounted orders"
            impact = high_delta
        else:
            contributor = "Regular-priced orders"
            impact = low_delta

        dir_arrow = "↑" if impact > 0 else "↓"
        detail = f"{contributor} {dir_arrow} {_sym(store_id)}{abs(impact):,.0f}"

        return {
            "dimension": "Discount Impact",
            "top_contributor": contributor,
            "impact": round(impact, 2),
            "detail": detail,
        }
    except Exception:
        return {"dimension": "Discount Impact", "top_contributor": "N/A", "impact": None, "detail": "Query failed"}


def _drill_by_returns(conn, store_id, cs, ce, ps, pe) -> dict:
    """Compare refund volume between periods."""
    try:
        row = conn.execute(
            """
            SELECT
                SUM(CASE WHEN order_date >= ? AND order_date <= ? THEN refund_amount ELSE 0 END) AS cur_refunds,
                SUM(CASE WHEN order_date >= ? AND order_date < ? THEN refund_amount ELSE 0 END) AS prev_refunds
            FROM orders
            WHERE store_id = ? AND order_date >= ? AND order_date <= ?
            """,
            [cs, ce, ps, pe, store_id, ps, ce],
        ).fetchone()

        if not row:
            return {"dimension": "Returns", "top_contributor": "N/A", "impact": None, "detail": "No data"}

        cur = float(row[0] or 0)
        prev = float(row[1] or 0)
        delta = -(cur - prev)

        dir_text = "increased" if cur > prev else "decreased"
        detail = f"Refunds {dir_text}: {_sym(store_id)}{cur:,.0f} vs {_sym(store_id)}{prev:,.0f} prior"

        return {
            "dimension": "Returns",
            "top_contributor": f"Refunds {dir_text}",
            "impact": round(delta, 2),
            "detail": detail,
        }
    except Exception:
        return {"dimension": "Returns", "top_contributor": "N/A", "impact": None, "detail": "Query failed"}


def _generate_verdict(
    direction: str, change_pct: float, change_amount: float,
    primary_cause: dict | None, drill_downs: list[dict],
) -> dict:
    """Generate a verdict sentence via Ollama, with template fallback."""
    if _HAS_OLLAMA and _client and primary_cause:
        try:
            context_lines = []
            for d in drill_downs:
                if d.get("impact") is not None:
                    context_lines.append(f"- {d['detail']}")

            prompt = (
                f"Revenue {'fell' if direction == 'down' else 'rose' if direction == 'up' else 'stayed flat'} "
                f"{abs(change_pct):.1f}% ({_sym(store_id)}{abs(change_amount):,.0f}) this period.\n\n"
                f"Drill-down findings:\n"
                + "\n".join(context_lines) + "\n\n"
                f"The single biggest factor: {primary_cause['dimension']}: {primary_cause['contributor']} "
                f"({_sym(store_id)}{abs(primary_cause['impact']):,.0f} impact, {abs(primary_cause.get('impact_pct', 0)):.0f}% of total change).\n\n"
                "Write exactly ONE sentence (max 40 words) summarizing why revenue changed. "
                "Be specific with category/channel/region names and rupee amounts. "
                "Do not use bullet points. Start with 'Revenue...'."
            )

            from app.services.copilot.copilot_service import get_active_model, DEFAULT_MODEL
            model = get_active_model(None) or DEFAULT_MODEL

            response = _client.chat(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a business analyst. Write one concise sentence."},
                    {"role": "user", "content": prompt},
                ],
            )
            text = response["message"]["content"].strip()
            if text:
                return {"text": text, "source": "ollama"}
        except Exception as exc:
            logger.warning("Ollama verdict generation failed, using template: %s", exc)

    return {"text": _template_verdict(direction, change_pct, change_amount, primary_cause), "source": "template"}


def _template_verdict(
    direction: str, change_pct: float, change_amount: float,
    primary_cause: dict | None,
) -> str:
    """Template-based verdict when Ollama is unavailable."""
    if direction == "flat":
        return f"Revenue remained relatively flat ({change_pct:+.1f}%) this period with no significant shifts across categories, channels, or regions."

    verb = "decreased" if direction == "down" else "increased"
    base = f"Revenue {verb} {abs(change_pct):.1f}% ({_sym(store_id)}{abs(change_amount):,.0f})"

    if not primary_cause:
        return f"{base} with no single dominant factor identified."

    return (
        f"{base}, primarily because {primary_cause['dimension']}: "
        f"{primary_cause['contributor']} accounted for "
        f"{_sym(store_id)}{abs(primary_cause['impact']):,.0f} of the change "
        f"({abs(primary_cause.get('impact_pct', 0)):.0f}% of total shift)."
    )
