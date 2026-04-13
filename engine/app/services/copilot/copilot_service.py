"""
AI Copilot service — natural language business Q&A with RAG.

Pipeline:
1. Analytics engine provides precomputed insights (KPIs, segments, anomalies, forecasts).
2. RAG context builder selects relevant data based on user question.
3. LLM (via Ollama) receives filtered context and produces natural-language answers.
4. Falls back to rule-based answers when Ollama is unavailable.
"""

import logging
import re
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone

from app.config import OLLAMA_URL
from app.core.database import get_duckdb_connection, get_sqlite_connection
from app.services.copilot.context_cache import (
    build_store_context,
    format_cached_context,
    get_or_build_context,
    invalidate_cache,
)
from app.services.copilot.feedback_service import build_few_shot_context
from app.services.copilot.spell_corrector import correct_question
from app.services.currency.currency_helper import sym as _csym

logger = logging.getLogger(__name__)

# ── Ollama client setup ─────────────────────────────────────────

_HAS_OLLAMA = False
_client = None

try:
    from ollama import Client as OllamaClient
    _client = OllamaClient(host=OLLAMA_URL)
    _HAS_OLLAMA = True
    logger.info("Ollama client configured → %s", OLLAMA_URL)
except ImportError:
    logger.info("Ollama package not installed — rule-based copilot only")


# ── Ollama management ───────────────────────────────────────────

AVAILABLE_MODELS = [
    {"id": "llama3.2:latest", "name": "Llama 3.2", "size_gb": 2.0, "params": "3.2B", "tier": "starter",
     "description": "Default baseline — fast and lightweight"},
    {"id": "phi3:mini", "name": "Phi-3 Mini", "size_gb": 2.2, "params": "3.8B", "tier": "starter",
     "description": "Microsoft's compact reasoning model"},
    {"id": "qwen2.5:7b", "name": "Qwen 2.5 7B", "size_gb": 4.7, "params": "7.6B", "tier": "mid",
     "description": "Balanced reasoning and performance"},
    {"id": "qwen2.5-coder:7b", "name": "Qwen 2.5 Coder 7B", "size_gb": 4.7, "params": "7.6B", "tier": "mid",
     "description": "Optimized for structured/analytical reasoning"},
    {"id": "qwen2.5-coder:14b", "name": "Qwen 2.5 Coder 14B", "size_gb": 9.0, "params": "14.8B", "tier": "advanced",
     "description": "Highest capability — slower, resource-heavy"},
]

DEFAULT_MODEL = "llama3.2:latest"

# Model tiers for upgrade recommendations
_TIER_ORDER = {"starter": 0, "mid": 1, "advanced": 2}


def _get_installed_models_raw() -> list[str]:
    """Query Ollama for actually-installed model IDs."""
    if not _HAS_OLLAMA or not _client:
        return []
    try:
        response = _client.list()
        models = response.models if hasattr(response, "models") else []
        return [m.model for m in models]
    except Exception as e:
        logger.warning("Failed to list Ollama models: %s", e)
        return []


def get_ollama_status() -> dict:
    """Check Ollama connectivity and return status with detected models."""
    if not _HAS_OLLAMA or not _client:
        return {"available": False, "reason": "ollama package not installed"}
    try:
        response = _client.list()
        models = response.models if hasattr(response, "models") else []
        installed = []
        for m in models:
            installed.append({
                "id": m.model,
                "size_bytes": m.size,
                "family": m.details.family if hasattr(m.details, "family") else None,
                "params": m.details.parameter_size if hasattr(m.details, "parameter_size") else None,
                "quantization": m.details.quantization_level if hasattr(m.details, "quantization_level") else None,
            })
        return {
            "available": True,
            "url": OLLAMA_URL,
            "installed_count": len(installed),
            "installed_models": installed,
        }
    except Exception as e:
        return {"available": False, "reason": f"Cannot reach Ollama at {OLLAMA_URL}: {e}"}


def list_models() -> list[dict]:
    """Return available models with accurate install status from Ollama."""
    installed_ids = _get_installed_models_raw()
    result = []
    for m in AVAILABLE_MODELS:
        # Exact match: check if model id matches any installed model
        is_installed = m["id"] in installed_ids
        # Also check without tag for models that might have different tag format
        if not is_installed:
            base_name = m["id"].split(":")[0]
            is_installed = any(i == base_name or i.startswith(base_name + ":") for i in installed_ids)
        result.append({
            **m,
            "installed": is_installed,
        })
    return result


def get_model_recommendations() -> dict:
    """Generate install/upgrade suggestions based on what's currently installed."""
    models = list_models()
    installed = [m for m in models if m["installed"]]
    not_installed = [m for m in models if not m["installed"]]
    installed_ids = {m["id"] for m in installed}
    installed_tiers = {m["tier"] for m in installed}

    recommendations: list[dict] = []
    active = get_active_model()
    active_model = next((m for m in models if m["id"] == active), None)
    active_tier = active_model["tier"] if active_model else "starter"

    # Detect if Ollama is running
    status = get_ollama_status()
    if not status["available"]:
        return {
            "status": "offline",
            "message": f"Ollama is not reachable at {OLLAMA_URL}. Start it to manage AI models.",
            "recommendations": [],
            "installed_count": 0,
            "total_count": len(AVAILABLE_MODELS),
        }

    # If no models installed at all
    if not installed:
        recommendations.append({
            "type": "install",
            "priority": "high",
            "model_id": "llama3.2:latest",
            "title": "Get started with Llama 3.2",
            "description": "Install the default model (2.0 GB) for instant AI-powered answers.",
        })
        return {
            "status": "needs_setup",
            "message": "No models installed yet. Install one to enable AI-powered answers.",
            "recommendations": recommendations,
            "installed_count": 0,
            "total_count": len(AVAILABLE_MODELS),
        }

    # Suggest uninstalled models
    for m in not_installed:
        m_tier_val = _TIER_ORDER.get(m["tier"], 0)
        active_tier_val = _TIER_ORDER.get(active_tier, 0)

        if m_tier_val > active_tier_val:
            recommendations.append({
                "type": "upgrade",
                "priority": "medium",
                "model_id": m["id"],
                "title": f"Upgrade to {m['name']}",
                "description": f"{m['params']} parameters, {m['size_gb']} GB — {m['description'].lower()}.",
            })
        else:
            recommendations.append({
                "type": "install",
                "priority": "low",
                "model_id": m["id"],
                "title": f"Also available: {m['name']}",
                "description": f"{m['params']} parameters, {m['size_gb']} GB — {m['description'].lower()}.",
            })

    # Suggest active model upgrade if using a starter tier
    if active_tier == "starter" and "mid" in installed_tiers:
        mid_models = [m for m in installed if m["tier"] == "mid"]
        if mid_models:
            best_mid = mid_models[0]
            recommendations.insert(0, {
                "type": "switch",
                "priority": "high",
                "model_id": best_mid["id"],
                "title": f"Switch to {best_mid['name']} for better answers",
                "description": (
                    f"You have {best_mid['name']} installed but are using {active_model['name'] if active_model else active}. "
                    f"Switching will improve answer quality at the cost of slightly slower responses."
                ),
            })

    if active_tier in ("starter", "mid") and "advanced" in installed_tiers:
        adv = next((m for m in installed if m["tier"] == "advanced"), None)
        if adv and adv["id"] != active:
            recommendations.insert(0, {
                "type": "switch",
                "priority": "medium",
                "model_id": adv["id"],
                "title": f"Try {adv['name']} for highest quality",
                "description": (
                    f"{adv['params']} model with the best analytical capability. "
                    f"Slower but significantly more accurate for complex questions."
                ),
            })

    # Summary message
    if len(installed) == len(AVAILABLE_MODELS):
        message = "All recommended models are installed. You're fully set up!"
        rec_status = "complete"
    elif len(installed) >= 3:
        message = f"{len(installed)}/{len(AVAILABLE_MODELS)} models installed. Great coverage!"
        rec_status = "good"
    else:
        message = f"{len(installed)}/{len(AVAILABLE_MODELS)} models installed."
        rec_status = "partial"

    return {
        "status": rec_status,
        "message": message,
        "active_model": active,
        "active_tier": active_tier,
        "recommendations": recommendations,
        "installed_count": len(installed),
        "total_count": len(AVAILABLE_MODELS),
    }


def get_active_model(store_id: str | None = None) -> str:
    """Get the user's selected model, falling back to any installed model."""
    try:
        conn = get_sqlite_connection()
        row = conn.execute(
            "SELECT value FROM settings WHERE key = 'copilot_model'"
        ).fetchone()
        preferred = row[0] if row else DEFAULT_MODEL
    except Exception:
        preferred = DEFAULT_MODEL

    installed = _get_installed_models_raw()
    if not installed:
        return preferred

    if preferred in installed:
        return preferred
    # Check base name match (e.g. "llama3.2:latest" vs "llama3.2:3b")
    preferred_base = preferred.split(":")[0]
    for m in installed:
        if m == preferred_base or m.startswith(preferred_base + ":"):
            return m

    return installed[0]


def set_active_model(model_id: str) -> dict:
    """Set the active model in settings."""
    conn = get_sqlite_connection()
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES ('copilot_model', ?)",
        (model_id,),
    )
    conn.commit()
    return {"model": model_id, "status": "active"}


def pull_model(model_id: str) -> dict:
    """Download a model via Ollama. Returns status."""
    if not _HAS_OLLAMA or not _client:
        return {"success": False, "error": "Ollama is not available"}
    try:
        _client.pull(model_id)
        return {"success": True, "model": model_id}
    except Exception as e:
        return {"success": False, "error": str(e)}


def delete_model(model_id: str) -> dict:
    """Delete a downloaded model."""
    if not _HAS_OLLAMA or not _client:
        return {"success": False, "error": "Ollama is not available"}
    try:
        _client.delete(model_id)
        return {"success": True, "model": model_id}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── Intelligence Context for RAG ─────────────────────────────────

def _build_intelligence_context(store_id: str) -> str:
    """Gather pre-computed insights, health score, drivers, and missed revenue for RAG."""
    sections: list[str] = []

    # Health score
    try:
        from app.services.insights.health_score import calculate_health_score
        hs = calculate_health_score(store_id)
        sections.append(
            f"BUSINESS HEALTH SCORE: {hs['overall_score']}/100 ({hs['label']}). "
            f"Components — Revenue Growth: {hs['components']['revenue_growth']['score']}/100, "
            f"Customer Health: {hs['components']['customer_health']['score']}/100, "
            f"Operational Efficiency: {hs['components']['operational_efficiency']['score']}/100, "
            f"Growth Momentum: {hs['components']['growth_momentum']['score']}/100."
        )
    except Exception:
        pass

    # Causal revenue drivers
    try:
        from app.services.insights.causal_engine import get_revenue_drivers
        drv = get_revenue_drivers(store_id)
        if drv.get("narrative"):
            sections.append(f"REVENUE DRIVERS: {drv['narrative']}")
    except Exception:
        pass

    # Missed revenue
    try:
        from app.services.insights.missed_revenue import detect_missed_revenue
        mr = detect_missed_revenue(store_id)
        total = mr.get("total_missed_revenue", 0)
        if total > 0:
            bd = mr.get("breakdown", {})
            parts = []
            if bd.get("refunds", {}).get("total", 0) > 0:
                parts.append(f"refunds {_csym(store_id)}{bd['refunds']['total']:,.2f}")
            if bd.get("churned_customers", {}).get("total", 0) > 0:
                parts.append(f"churned customers {_csym(store_id)}{bd['churned_customers']['total']:,.2f}")
            if bd.get("stockout_signals", {}).get("total", 0) > 0:
                parts.append(f"potential stockouts {_csym(store_id)}{bd['stockout_signals']['total']:,.2f}")
            sections.append(
                f"MISSED REVENUE: {_csym(store_id)}{total:,.2f} total — {', '.join(parts)}."
            )
    except Exception:
        pass

    # Key insights and anomalies summary
    try:
        from app.services.insights.insight_engine import generate_insights, detect_anomalies
        insights = generate_insights(store_id)
        if insights:
            top = insights[:3]
            lines = [f"  - {i['message']}" for i in top]
            sections.append("KEY INSIGHTS:\n" + "\n".join(lines))

        anomalies = detect_anomalies(store_id)
        if anomalies:
            top_a = anomalies[:3]
            lines = [f"  - {a['message']}" for a in top_a]
            sections.append("ANOMALIES DETECTED:\n" + "\n".join(lines))
    except Exception:
        pass

    # Recommended actions
    try:
        from app.services.insights.insight_engine import get_recommended_actions
        actions = get_recommended_actions(store_id)
        if actions:
            top_act = actions[:3]
            lines = []
            for a in top_act:
                impact = f" (est. {_csym(store_id)}{a['impact_dollars']:,.0f})" if a.get("impact_dollars") else ""
                lines.append(f"  - {a['title']}: {a['description']}{impact}")
            sections.append("TOP RECOMMENDED ACTIONS:\n" + "\n".join(lines))
    except Exception:
        pass

    if not sections:
        return "INTELLIGENCE: No insights available yet."
    return "INTELLIGENCE SUMMARY:\n" + "\n".join(sections)


# ── RAG Context Builder ─────────────────────────────────────────

def _build_rag_context(store_id: str, question: str) -> str:
    """Build a rich analytics context for the LLM based on the question.

    Uses the context cache when available (Improvement #2) to avoid
    running SQL on every question.  Falls back to direct queries if
    the cache is empty.
    """
    # Try cache first
    cached_ctx = get_or_build_context(store_id)
    if cached_ctx:
        return format_cached_context(cached_ctx, question)

    # Fallback: direct DuckDB queries (cache miss / build failed)
    conn = get_duckdb_connection()
    q = question.lower()
    parts: list[str] = []

    # Always include basic store summary
    row = conn.execute(
        """SELECT COUNT(*) as orders, COALESCE(SUM(total_price - discount_amount), 0) as revenue,
                  COUNT(DISTINCT customer_id) as customers,
                  COUNT(DISTINCT product_id) as products,
                  MIN(order_date) as first_order, MAX(order_date) as last_order,
                  COALESCE(AVG(total_price - discount_amount), 0) as aov
           FROM orders WHERE store_id = ?""",
        [store_id],
    ).fetchone()

    if row and row[0] > 0:
        parts.append(
            f"STORE OVERVIEW: {int(row[0]):,} orders, {_csym(store_id)}{float(row[1]):,.2f} total revenue, "
            f"{int(row[2]):,} customers, {int(row[3]):,} products, "
            f"AOV {_csym(store_id)}{float(row[6]):,.2f}, data from {row[4]} to {row[5]}."
        )
    else:
        return "STORE OVERVIEW: No order data available yet."

    # Inject insights engine context for analytical questions
    if any(w in q for w in ["why", "explain", "insight", "anomal", "health", "driver", "cause",
                             "missed", "opportunity", "recommend", "action", "what happened",
                             "issue", "problem", "decline", "drop", "increase", "spike"]):
        parts.append(_build_intelligence_context(store_id))

    # Revenue / sales context
    if any(w in q for w in ["revenue", "sales", "income", "earning", "money", "monthly", "trend"]):
        rows = conn.execute(
            """SELECT strftime(order_date, '%Y-%m') as month, SUM(total_price - discount_amount) as rev,
                      COUNT(*) as cnt
               FROM orders WHERE store_id = ? GROUP BY month ORDER BY month DESC LIMIT 6""",
            [store_id],
        ).fetchall()
        if rows:
            lines = [f"  {r[0]}: {_csym(store_id)}{float(r[1]):,.2f} ({int(r[2]):,} orders)" for r in rows]
            parts.append("MONTHLY REVENUE (last 6):\n" + "\n".join(lines))

    # Customer context
    if any(w in q for w in ["customer", "retention", "repeat", "returning", "loyal", "churn", "segment"]):
        cust = conn.execute(
            """SELECT
                 COUNT(DISTINCT customer_id) as total,
                 COUNT(DISTINCT CASE WHEN oc > 1 THEN cid END) as repeat_c,
                 ROUND(COUNT(DISTINCT CASE WHEN oc > 1 THEN cid END) * 100.0 /
                   NULLIF(COUNT(DISTINCT cid), 0), 1) as repeat_rate
               FROM (
                 SELECT customer_id as cid, COUNT(*) as oc
                 FROM orders WHERE store_id = ? GROUP BY customer_id
               )""",
            [store_id],
        ).fetchone()
        if cust:
            parts.append(
                f"CUSTOMER METRICS: {int(cust[0]):,} total, {int(cust[1]):,} repeat, "
                f"{float(cust[2]):.1f}% repeat rate."
            )

        top_c = conn.execute(
            """SELECT customer_id, COUNT(*) as orders, SUM(total_price - discount_amount) as spent
               FROM orders WHERE store_id = ? GROUP BY customer_id ORDER BY spent DESC LIMIT 5""",
            [store_id],
        ).fetchall()
        if top_c:
            lines = [f"  {r[0]}: {int(r[1]):,} orders, {_csym(store_id)}{float(r[2]):,.2f}" for r in top_c]
            parts.append("TOP CUSTOMERS:\n" + "\n".join(lines))

    # Product context
    if any(w in q for w in ["product", "selling", "best", "top", "category", "item", "stock"]):
        top_p = conn.execute(
            """SELECT product_id, SUM(quantity) as qty, SUM(total_price - discount_amount) as rev
               FROM orders WHERE store_id = ?
               GROUP BY product_id ORDER BY rev DESC LIMIT 5""",
            [store_id],
        ).fetchall()
        if top_p:
            lines = [f"  {r[0]}: {int(r[1]):,} units, {_csym(store_id)}{float(r[2]):,.2f}" for r in top_p]
            parts.append("TOP PRODUCTS:\n" + "\n".join(lines))

        cats = conn.execute(
            """SELECT COALESCE(category, 'Uncategorized') as cat, SUM(total_price - discount_amount) as rev, COUNT(*) as cnt
               FROM orders WHERE store_id = ?
               GROUP BY cat ORDER BY rev DESC LIMIT 5""",
            [store_id],
        ).fetchall()
        if cats:
            lines = [f"  {r[0]}: {_csym(store_id)}{float(r[1]):,.2f} ({int(r[2]):,} orders)" for r in cats]
            parts.append("TOP CATEGORIES:\n" + "\n".join(lines))

    # Refund & order status context
    if any(w in q for w in ["refund", "return", "cancel", "status"]):
        status_rows = conn.execute(
            """SELECT status, COUNT(*) as cnt, SUM(total_price - discount_amount) as val
               FROM orders WHERE store_id = ? GROUP BY status""",
            [store_id],
        ).fetchall()
        if status_rows:
            lines = [f"  {r[0]}: {int(r[1]):,} orders ({_csym(store_id)}{float(r[2]):,.2f})" for r in status_rows]
            parts.append("ORDER STATUS BREAKDOWN:\n" + "\n".join(lines))

    # Time-based analysis
    if any(w in q for w in ["today", "week", "recent", "latest", "last"]):
        recent = conn.execute(
            """SELECT COUNT(*) as cnt, COALESCE(SUM(total_price - discount_amount), 0) as rev
               FROM orders WHERE store_id = ? AND order_date >= ?""",
            [store_id, (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)).isoformat()],
        ).fetchone()
        if recent:
            parts.append(f"LAST 7 DAYS: {int(recent[0]):,} orders, {_csym(store_id)}{float(recent[1]):,.2f} revenue.")

    # Review / sentiment context
    if any(w in q for w in ["review", "sentiment", "rating", "feedback", "opinion"]):
        rev = conn.execute(
            """SELECT COUNT(*) as cnt, AVG(rating) as avg_r,
                      AVG(sentiment_score) as avg_s,
                      COUNT(CASE WHEN sentiment_label = 'positive' THEN 1 END) as pos,
                      COUNT(CASE WHEN sentiment_label = 'negative' THEN 1 END) as neg
               FROM reviews WHERE store_id = ?""",
            [store_id],
        ).fetchone()
        if rev and rev[0] > 0:
            parts.append(
                f"REVIEWS: {int(rev[0]):,} total, avg rating {float(rev[1] or 0):.1f}★, "
                f"sentiment {float(rev[2] or 0) * 100:.0f}%, "
                f"{int(rev[3]):,} positive, {int(rev[4]):,} negative."
            )

    # Channel / region context
    if any(w in q for w in ["channel", "region", "where", "source", "marketing"]):
        channels = conn.execute(
            """SELECT COALESCE(channel, 'Unknown') as ch, COUNT(*) as cnt, SUM(total_price - discount_amount) as rev
               FROM orders WHERE store_id = ? GROUP BY ch ORDER BY rev DESC LIMIT 5""",
            [store_id],
        ).fetchall()
        if channels:
            lines = [f"  {r[0]}: {int(r[1]):,} orders, {_csym(store_id)}{float(r[2]):,.2f}" for r in channels]
            parts.append("CHANNELS:\n" + "\n".join(lines))

    return "\n\n".join(parts)


# ── Question patterns for rule-based fallback ───────────────────

QUERY_PATTERNS = [
    {
        "patterns": [r"total revenue", r"how much .* (made|earned|revenue)", r"sales total"],
        "query": """SELECT COALESCE(SUM(total_price - discount_amount), 0) as value FROM orders WHERE store_id = ?""",
        "template": "Total net revenue is **${value:,.2f}**.",
        "format": "currency",
    },
    {
        "patterns": [r"how many orders", r"total orders", r"order count", r"number of orders"],
        "query": """SELECT COUNT(*) as value FROM orders WHERE store_id = ?""",
        "template": "There are **{value:,}** orders in your store.",
        "format": "integer",
    },
    {
        "patterns": [r"how many customers", r"total customers", r"customer count", r"number of customers"],
        "query": """SELECT COUNT(DISTINCT customer_id) as value FROM orders WHERE store_id = ?""",
        "template": "You have **{value:,}** unique customers.",
        "format": "integer",
    },
    {
        "patterns": [r"average order", r"aov", r"average .* value"],
        "query": """SELECT COALESCE(AVG(total_price - discount_amount), 0) as value FROM orders WHERE store_id = ?""",
        "template": "Average order value (net) is **${value:,.2f}**.",
        "format": "currency",
    },
    {
        "patterns": [r"top (selling |)products?", r"best (selling |)products?"],
        "query": """SELECT product_id, SUM(quantity) as qty, SUM(total_price - discount_amount) as revenue
                     FROM orders WHERE store_id = ?
                     GROUP BY product_id ORDER BY revenue DESC LIMIT 5""",
        "template": "top_products",
        "format": "table",
    },
    {
        "patterns": [r"top customers?", r"best customers?", r"biggest (buyers?|spenders?)"],
        "query": """SELECT customer_id, COUNT(*) as orders, SUM(total_price - discount_amount) as spent
                     FROM orders WHERE store_id = ?
                     GROUP BY customer_id ORDER BY spent DESC LIMIT 5""",
        "template": "top_customers",
        "format": "table",
    },
    {
        "patterns": [r"refund", r"return rate"],
        "query": """SELECT
                       COUNT(CASE WHEN status = 'refunded' THEN 1 END) as refunds,
                       COUNT(*) as total,
                       ROUND(COUNT(CASE WHEN status = 'refunded' THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1) as rate
                     FROM orders WHERE store_id = ?""",
        "template": "refund_rate",
        "format": "table",
    },
    {
        "patterns": [r"(revenue|sales) (by|per) (month|monthly)", r"monthly (revenue|sales)"],
        "query": """SELECT strftime(order_date, '%Y-%m') as month, SUM(total_price - discount_amount) as revenue
                     FROM orders WHERE store_id = ?
                     GROUP BY month ORDER BY month DESC LIMIT 12""",
        "template": "monthly_revenue",
        "format": "table",
    },
    {
        "patterns": [r"repeat.*customer|returning.*customer|retention"],
        "query": """SELECT
                       COUNT(*) as total_customers,
                       COUNT(CASE WHEN order_count > 1 THEN 1 END) as repeat_customers,
                       ROUND(COUNT(CASE WHEN order_count > 1 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1) as repeat_rate
                     FROM (
                       SELECT customer_id, COUNT(*) as order_count
                       FROM orders WHERE store_id = ?
                       GROUP BY customer_id
                     )""",
        "template": "repeat_customers",
        "format": "table",
    },
    # ── Expanded patterns (improvement #3) ──────────────────
    {
        "patterns": [r"compare.*month", r"this month.*vs.*last", r"month.*over.*month", r"mom"],
        "query": """SELECT strftime(order_date, '%Y-%m') AS month,
                           SUM(total_price - discount_amount) AS revenue,
                           COUNT(*) AS orders
                    FROM orders WHERE store_id = ?
                    GROUP BY month ORDER BY month DESC LIMIT 2""",
        "template": "mom_comparison",
        "format": "table",
    },
    {
        "patterns": [r"profit margin", r"gross margin", r"net margin", r"margin"],
        "query": """SELECT COALESCE(SUM(total_price - discount_amount - COALESCE(refund_amount, 0)), 0) as net,
                           COALESCE(SUM(total_price - discount_amount), 0) as gross
                    FROM orders WHERE store_id = ?""",
        "template": "profit_margin",
        "format": "table",
    },
    {
        "patterns": [r"how many refund", r"refunded orders", r"cancel+ed orders", r"number of refund"],
        "query": """SELECT COUNT(*) as value FROM orders WHERE store_id = ? AND status IN ('refunded', 'cancelled')""",
        "template": "There are **{value:,}** refunded/cancelled orders.",
        "format": "integer",
    },
    {
        "patterns": [r"revenue (by|per) (category|categories)", r"category.*(revenue|sales|breakdown)",
                     r"sales (by|per) category"],
        "query": """SELECT COALESCE(category, 'Uncategorized') as cat,
                           SUM(total_price - discount_amount) as rev,
                           COUNT(*) as orders
                    FROM orders WHERE store_id = ?
                    GROUP BY cat ORDER BY rev DESC LIMIT 10""",
        "template": "category_revenue",
        "format": "table",
    },
    {
        "patterns": [r"new customer", r"first.time.*customer", r"customer acquisition"],
        "query": """SELECT COUNT(DISTINCT customer_id) as value
                    FROM (
                      SELECT customer_id, MIN(order_date) as first_order
                      FROM orders WHERE store_id = ? GROUP BY customer_id
                    ) WHERE first_order >= CURRENT_DATE - INTERVAL 30 DAY""",
        "template": "You have **{value:,}** new customers in the last 30 days.",
        "format": "integer",
    },
    {
        "patterns": [r"(best|worst|top|bottom) (day|date|time)", r"busiest day", r"peak day"],
        "query": """SELECT strftime(order_date, '%A') as day_of_week,
                           COUNT(*) as orders,
                           SUM(total_price - discount_amount) as revenue
                    FROM orders WHERE store_id = ?
                    GROUP BY day_of_week ORDER BY orders DESC""",
        "template": "day_performance",
        "format": "table",
    },
    {
        "patterns": [r"discount.*impact|how much.*discount|total.*discount"],
        "query": """SELECT COALESCE(SUM(discount_amount), 0) as total_discount,
                           ROUND(SUM(discount_amount) * 100.0 / NULLIF(SUM(total_price), 0), 1) as discount_pct,
                           COUNT(CASE WHEN discount_amount > 0 THEN 1 END) as discounted_orders,
                           COUNT(*) as total_orders
                    FROM orders WHERE store_id = ?""",
        "template": "discount_summary",
        "format": "table",
    },
    {
        "patterns": [r"revenue (this|last|current) week", r"weekly (revenue|sales|orders)"],
        "query": """SELECT strftime(order_date, '%Y-W%W') as week,
                           SUM(total_price - discount_amount) as revenue,
                           COUNT(*) as orders
                    FROM orders WHERE store_id = ?
                    GROUP BY week ORDER BY week DESC LIMIT 8""",
        "template": "weekly_revenue",
        "format": "table",
    },
]

# Patterns that use the intelligence engine (no SQL, computed from services)
INTELLIGENCE_PATTERNS = [
    {
        "patterns": [
            r"how.*business.*doing", r"business.*health", r"health.*score",
            r"overall.*performance", r"store.*performance", r"how.*my.*store",
            r"summary", r"overview",
        ],
        "handler": "_handle_health_score",
    },
    {
        "patterns": [
            r"what.*should.*focus", r"what.*do.*next", r"recommend",
            r"suggest", r"action.*item", r"priority", r"what.*improve",
        ],
        "handler": "_handle_recommended_actions",
    },
    {
        "patterns": [
            r"missed.*revenue", r"lost.*revenue", r"leaving.*money",
            r"revenue.*leak", r"losing.*money",
        ],
        "handler": "_handle_missed_revenue",
    },
    {
        "patterns": [
            r"anomal", r"unusual", r"weird", r"something.*wrong",
            r"problem", r"issue",
        ],
        "handler": "_handle_anomalies",
    },
    {
        "patterns": [r"trend", r"growth", r"growing", r"declining", r"direction"],
        "handler": "_handle_trends",
    },
]


def _handle_health_score(store_id: str) -> dict | None:
    try:
        from app.services.insights.health_score import calculate_health_score
        hs = calculate_health_score(store_id)
        comp = hs["components"]
        answer = (
            f"**Business Health Score: {hs['overall_score']}/100 ({hs['label']})**\n\n"
            f"- Revenue Growth: {comp['revenue_growth']['score']}/100\n"
            f"- Customer Health: {comp['customer_health']['score']}/100\n"
            f"- Operational Efficiency: {comp['operational_efficiency']['score']}/100\n"
            f"- Growth Momentum: {comp['growth_momentum']['score']}/100\n"
        )
        weakest = min(comp.items(), key=lambda x: x[1]["score"])
        answer += f"\n**Focus area:** {weakest[0].replace('_', ' ').title()} needs the most attention."
        return {"answer": answer, "source": "intelligence"}
    except Exception:
        return None


def _handle_recommended_actions(store_id: str) -> dict | None:
    try:
        from app.services.insights.insight_engine import get_recommended_actions
        actions = get_recommended_actions(store_id)
        if not actions:
            return None
        lines = ["**Recommended Actions:**\n"]
        for i, a in enumerate(actions[:5], 1):
            impact = f" (est. impact: {_csym(store_id)}{a['impact_dollars']:,.0f})" if a.get("impact_dollars") else ""
            lines.append(f"{i}. **{a['title']}** — {a['description']}{impact}")
        return {"answer": "\n".join(lines), "source": "intelligence"}
    except Exception:
        return None


def _handle_missed_revenue(store_id: str) -> dict | None:
    try:
        from app.services.insights.missed_revenue import detect_missed_revenue
        mr = detect_missed_revenue(store_id)
        total = mr.get("total_missed_revenue", 0)
        if total <= 0:
            return {"answer": "No significant missed revenue detected. Great job!", "source": "intelligence"}
        bd = mr.get("breakdown", {})
        lines = [f"**Missed Revenue: {_csym(store_id)}{total:,.2f}**\n"]
        if bd.get("refunds", {}).get("total", 0) > 0:
            lines.append(f"- Refunds/returns: {_csym(store_id)}{bd['refunds']['total']:,.2f}")
        if bd.get("churned_customers", {}).get("total", 0) > 0:
            lines.append(f"- Churned customers: {_csym(store_id)}{bd['churned_customers']['total']:,.2f}")
        if bd.get("stockout_signals", {}).get("total", 0) > 0:
            lines.append(f"- Potential stockouts: {_csym(store_id)}{bd['stockout_signals']['total']:,.2f}")
        return {"answer": "\n".join(lines), "source": "intelligence"}
    except Exception:
        return None


def _handle_anomalies(store_id: str) -> dict | None:
    try:
        from app.services.insights.insight_engine import detect_anomalies
        anomalies = detect_anomalies(store_id)
        if not anomalies:
            return {"answer": "No anomalies detected in your recent data.", "source": "intelligence"}
        lines = ["**Detected Anomalies:**\n"]
        for i, a in enumerate(anomalies[:5], 1):
            lines.append(f"{i}. {a['message']}")
        return {"answer": "\n".join(lines), "source": "intelligence"}
    except Exception:
        return None


def _handle_trends(store_id: str) -> dict | None:
    try:
        from app.services.insights.insight_engine import generate_insights
        insights = generate_insights(store_id)
        trend_insights = [i for i in insights if any(w in i.get("type", "").lower() for w in ("trend", "growth", "decline"))]
        if not trend_insights:
            trend_insights = insights[:5]
        if not trend_insights:
            return None
        lines = ["**Key Trends & Insights:**\n"]
        for i, ins in enumerate(trend_insights[:5], 1):
            lines.append(f"{i}. {ins['message']}")
        return {"answer": "\n".join(lines), "source": "intelligence"}
    except Exception:
        return None


_INTELLIGENCE_HANDLERS = {
    "_handle_health_score": _handle_health_score,
    "_handle_recommended_actions": _handle_recommended_actions,
    "_handle_missed_revenue": _handle_missed_revenue,
    "_handle_anomalies": _handle_anomalies,
    "_handle_trends": _handle_trends,
}


# ── Response Cache (LRU with TTL) ───────────────────────────────

_response_cache: dict[str, dict] = {}
_response_cache_lock = threading.Lock() if 'threading' in dir() else None
_RESPONSE_CACHE_TTL = 300  # 5 minutes
_RESPONSE_CACHE_MAX = 100  # max entries


def _get_cached_response(key: str) -> dict | None:
    """Return a cached response if it exists and hasn't expired."""
    entry = _response_cache.get(key)
    if entry and (time.monotonic() - entry["_cached_at"]) < _RESPONSE_CACHE_TTL:
        return entry["response"]
    return None


def _set_cached_response(key: str, response: dict) -> None:
    """Cache a response with TTL."""
    if len(_response_cache) >= _RESPONSE_CACHE_MAX:
        # Evict oldest entry
        oldest_key = min(_response_cache, key=lambda k: _response_cache[k]["_cached_at"])
        _response_cache.pop(oldest_key, None)
    _response_cache[key] = {"response": response, "_cached_at": time.monotonic()}


def clear_response_cache(store_id: str | None = None) -> None:
    """Clear response cache. If store_id given, only clear that store's entries."""
    if store_id:
        keys = [k for k in _response_cache if k.startswith(f"{store_id}:")]
        for k in keys:
            _response_cache.pop(k, None)
    else:
        _response_cache.clear()


# ── Main ask entry point ────────────────────────────────────────

def ask_copilot(store_id: str, question: str, conversation_history: list[dict] | None = None) -> dict:
    """Answer a business question using RAG + LLM or rule-based fallback.

    Every response includes a unique message_id that the frontend can use
    to submit feedback (thumbs up/down).  The feedback is stored and
    injected into future prompts as few-shot examples.

    Args:
        store_id: The store to query.
        question: The user's question (may contain typos).
        conversation_history: Optional list of recent messages for context.
    """
    question_lower = question.lower().strip()
    message_id = f"cop-{uuid.uuid4().hex[:12]}"

    if not question_lower:
        return {
            "answer": "Please ask me a question about your store data!",
            "source": "system",
            "message_id": message_id,
        }

    # Spell-correct before pattern matching (Improvement #1)
    corrected = correct_question(question_lower)
    was_corrected = corrected != question_lower
    if was_corrected:
        logger.info("Spell correction: '%s' → '%s'", question_lower, corrected)

    # Check response cache (Improvement #7)
    cache_key = f"{store_id}:{corrected}"
    cached = _get_cached_response(cache_key)
    if cached:
        result = {**cached, "message_id": message_id, "cached": True}
        if was_corrected:
            result["corrected_question"] = corrected
        return result

    # Try rule-based first (fast, zero-cost) — use corrected question
    for pattern_group in QUERY_PATTERNS:
        for pat in pattern_group["patterns"]:
            if re.search(pat, corrected):
                result = _execute_pattern(store_id, pattern_group, question)
                result["message_id"] = message_id
                if was_corrected:
                    result["corrected_question"] = corrected
                _set_cached_response(cache_key, result)
                return result

    # Try intelligence-based patterns (computed from insight services, no LLM needed)
    for pattern_group in INTELLIGENCE_PATTERNS:
        for pat in pattern_group["patterns"]:
            if re.search(pat, corrected):
                handler = _INTELLIGENCE_HANDLERS.get(pattern_group["handler"])
                if handler:
                    result = handler(store_id)
                    if result:
                        result["message_id"] = message_id
                        if was_corrected:
                            result["corrected_question"] = corrected
                        _set_cached_response(cache_key, result)
                        return result
                break

    # RAG + Ollama for open-ended questions
    if _HAS_OLLAMA:
        result = _ask_ollama_rag(store_id, question, corrected, conversation_history)
        result["message_id"] = message_id
        if was_corrected:
            result["corrected_question"] = corrected
        _set_cached_response(cache_key, result)
        return result

    # Last resort: helpful guidance
    return {
        "answer": (
            "I can answer questions like:\n"
            "- \"What's my total revenue?\"\n"
            "- \"How many orders do I have?\"\n"
            "- \"Show me top selling products\"\n"
            "- \"Who are my top customers?\"\n"
            "- \"What's my average order value?\"\n"
            "- \"How many repeat customers?\"\n"
            "- \"What's my refund rate?\"\n"
            "- \"Show monthly revenue\"\n"
            "- \"How is my business doing?\" (health score)\n"
            "- \"What should I focus on?\" (recommendations)\n"
            "- \"Any anomalies?\" (anomaly detection)\n"
            "- \"Show me trends\" (growth insights)\n"
            "- \"Missed revenue\" (revenue leak analysis)\n\n"
            "Install Ollama for free-form questions!"
        ),
        "source": "system",
        "message_id": message_id,
    }


def _execute_pattern(store_id: str, pattern_group: dict, original_question: str) -> dict:
    """Execute a matched pattern query and format the result."""
    conn = get_duckdb_connection()
    try:
        result = conn.execute(pattern_group["query"], [store_id]).fetchall()
    except Exception as e:
        logger.error("Copilot query error: %s", e)
        return {"answer": "Sorry, I couldn't fetch that data right now.", "source": "error"}

    user_ctx = _get_user_context()
    sym = _currency_symbol(user_ctx.get("currency", "USD"))

    fmt = pattern_group["format"]
    template = pattern_group["template"]

    if fmt == "currency":
        val = float(result[0][0]) if result and result[0][0] else 0
        answer = template.replace("$", sym).replace("{value:,.2f}", f"{val:,.2f}")
    elif fmt == "integer":
        val = int(result[0][0]) if result and result[0][0] else 0
        answer = template.replace("{value:,}", f"{val:,}")
    elif fmt == "table":
        answer = _format_table_answer(template, result, sym)
    else:
        answer = str(result)

    return {"answer": answer, "source": "analytics"}


def _format_table_answer(template: str, rows: list, sym: str = "$") -> str:
    """Format table query results into readable text."""
    if not rows:
        return "No data found for that query."

    if template == "top_products":
        lines = ["**Top Products by Revenue:**\n"]
        for i, r in enumerate(rows, 1):
            lines.append(f"{i}. Product `{r[0]}` — {int(r[1]):,} units, {sym}{float(r[2]):,.2f} revenue")
        return "\n".join(lines)

    if template == "top_customers":
        lines = ["**Top Customers by Spending:**\n"]
        for i, r in enumerate(rows, 1):
            lines.append(f"{i}. Customer `{r[0]}` — {int(r[1]):,} orders, {sym}{float(r[2]):,.2f} spent")
        return "\n".join(lines)

    if template == "refund_rate":
        r = rows[0]
        return (
            f"**Refund Analysis:**\n"
            f"- Total orders: {int(r[1]):,}\n"
            f"- Refunded: {int(r[0]):,}\n"
            f"- Refund rate: {float(r[2]):.1f}%"
        )

    if template == "monthly_revenue":
        lines = ["**Monthly Revenue (Last 12 Months):**\n"]
        for r in rows:
            lines.append(f"- {r[0]}: {sym}{float(r[1]):,.2f}")
        return "\n".join(lines)

    if template == "repeat_customers":
        r = rows[0]
        return (
            f"**Customer Retention:**\n"
            f"- Total customers: {int(r[0]):,}\n"
            f"- Repeat customers: {int(r[1]):,}\n"
            f"- Repeat rate: {float(r[2]):.1f}%"
        )

    if template == "mom_comparison":
        if len(rows) >= 2:
            curr, prev = rows[0], rows[1]
            curr_rev, prev_rev = float(curr[1]), float(prev[1])
            change = ((curr_rev - prev_rev) / prev_rev * 100) if prev_rev else 0
            direction = "up" if change >= 0 else "down"
            return (
                f"**Month-over-Month Comparison:**\n"
                f"- {curr[0]}: {sym}{curr_rev:,.2f} ({int(curr[2]):,} orders)\n"
                f"- {prev[0]}: {sym}{prev_rev:,.2f} ({int(prev[2]):,} orders)\n"
                f"- Change: **{direction} {abs(change):.1f}%**"
            )
        if rows:
            return f"**{rows[0][0]}**: {sym}{float(rows[0][1]):,.2f} ({int(rows[0][2]):,} orders). No prior month for comparison."
        return "No monthly data available."

    if template == "profit_margin":
        r = rows[0]
        net, gross = float(r[0]), float(r[1])
        margin_pct = (net / gross * 100) if gross else 0
        return (
            f"**Revenue Summary:**\n"
            f"- Gross revenue: {sym}{gross:,.2f}\n"
            f"- Net revenue (after refunds): {sym}{net:,.2f}\n"
            f"- Net margin: **{margin_pct:.1f}%**"
        )

    if template == "category_revenue":
        lines = ["**Revenue by Category:**\n"]
        for i, r in enumerate(rows, 1):
            lines.append(f"{i}. {r[0]} — {sym}{float(r[1]):,.2f} ({int(r[2]):,} orders)")
        return "\n".join(lines)

    if template == "day_performance":
        lines = ["**Orders by Day of Week:**\n"]
        for r in rows:
            lines.append(f"- {r[0]}: {int(r[1]):,} orders, {sym}{float(r[2]):,.2f}")
        return "\n".join(lines)

    if template == "discount_summary":
        r = rows[0]
        return (
            f"**Discount Analysis:**\n"
            f"- Total discounts given: {sym}{float(r[0]):,.2f}\n"
            f"- Discount as % of gross: {float(r[1]):.1f}%\n"
            f"- Discounted orders: {int(r[2]):,} / {int(r[3]):,} total"
        )

    if template == "weekly_revenue":
        lines = ["**Weekly Revenue (Last 8 Weeks):**\n"]
        for r in rows:
            lines.append(f"- {r[0]}: {sym}{float(r[1]):,.2f} ({int(r[2]):,} orders)")
        return "\n".join(lines)

    return str(rows)


def _get_user_context() -> dict:
    """Read user profile and settings for RAG enrichment."""
    conn = get_sqlite_connection()
    ctx: dict = {}
    try:
        rows = conn.execute(
            "SELECT key, value FROM settings WHERE key IN "
            "('currency', 'region', 'industry', 'business_name', 'platform')"
        ).fetchall()
        for key, value in rows:
            ctx[key] = value
    except Exception:
        pass
    return ctx


def _currency_symbol(currency: str) -> str:
    """Return the symbol for common currency codes, fallback to code itself."""
    symbols = {
        "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "CNY": "¥",
        "INR": "₹", "KRW": "₩", "BRL": "R$", "CAD": "CA$", "AUD": "A$",
        "CHF": "CHF", "SEK": "kr", "NOK": "kr", "DKK": "kr", "PLN": "zł",
        "TRY": "₺", "MXN": "MX$", "SGD": "S$", "HKD": "HK$", "NZD": "NZ$",
        "ZAR": "R", "THB": "฿", "MYR": "RM", "PHP": "₱",
    }
    return symbols.get(currency, currency)


def _ask_ollama_rag(
    store_id: str,
    question: str,
    corrected_question: str | None = None,
    conversation_history: list[dict] | None = None,
) -> dict:
    """Use RAG context + Ollama + feedback memory for open-ended questions.

    Args:
        store_id: Store to query data for.
        question: Original user question.
        corrected_question: Spell-corrected version (used for RAG keywords).
        conversation_history: Recent chat messages for multi-turn context.
    """
    # Use corrected question for RAG context building (better keyword extraction)
    q_for_rag = corrected_question or question
    context = _build_rag_context(store_id, q_for_rag)
    model = get_active_model()
    user_ctx = _get_user_context()

    user_profile_parts: list[str] = []
    if user_ctx.get("business_name"):
        user_profile_parts.append(f"Business: {user_ctx['business_name']}")
    if user_ctx.get("industry"):
        user_profile_parts.append(f"Industry: {user_ctx['industry']}")
    if user_ctx.get("region"):
        user_profile_parts.append(f"Region: {user_ctx['region']}")
    if user_ctx.get("platform"):
        user_profile_parts.append(f"Platform: {user_ctx['platform']}")
    currency = user_ctx.get("currency", "USD")
    sym = _currency_symbol(currency)
    user_profile_parts.append(f"Currency: {currency} ({sym})")

    user_profile_block = ""
    if user_profile_parts:
        user_profile_block = "\n--- USER PROFILE ---\n" + " | ".join(user_profile_parts) + "\n--- END PROFILE ---\n\n"

    # Build few-shot context from feedback memory
    few_shot_block = ""
    try:
        few_shot = build_few_shot_context(store_id, question)
        if few_shot:
            few_shot_block = f"\n{few_shot}\n\n"
    except Exception as exc:
        logger.warning("Failed to build few-shot context: %s", exc)

    system_prompt = (
        "You are Novem Copilot, an AI business analyst for e-commerce store owners. "
        "Answer questions about their business using ONLY the data context provided below. "
        "Be concise, use bullet points for lists, bold (**) for key numbers. "
        f"All monetary values should be presented in {currency} ({sym}). "
        "If the data doesn't contain enough information to answer, say so. "
        "Do not make up numbers or speculate beyond what the data shows.\n\n"
        f"{user_profile_block}"
        f"{few_shot_block}"
        f"--- DATA CONTEXT ---\n{context}\n--- END CONTEXT ---"
    )

    try:
        # Build message list with optional conversation history (Improvement #6)
        messages = [{"role": "system", "content": system_prompt}]
        if conversation_history:
            # Include last 5 turns max to keep context window manageable
            recent = conversation_history[-10:]  # 10 messages = ~5 turns
            for msg in recent:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": question})

        response = _client.chat(
            model=model,
            messages=messages,
        )
        return {
            "answer": response["message"]["content"],
            "source": "ollama",
            "model": model,
        }
    except Exception as e:
        logger.warning("Ollama call failed (%s): %s", model, e)
        # Fallback to rule-based patterns
        return {
            "answer": (
                "The AI model is currently unavailable. "
                "I can still answer specific questions about revenue, orders, customers, and products. "
                "Try asking something more specific!"
            ),
            "source": "fallback",
        }


def get_suggested_questions() -> list[str]:
    """Return a list of suggested questions for the user."""
    return [
        "What's my total revenue?",
        "How many orders do I have?",
        "Show me top selling products",
        "Who are my top customers?",
        "What's my average order value?",
        "How many repeat customers do I have?",
        "What's my refund rate?",
        "Show monthly revenue breakdown",
        "What's my business health score?",
        "Why did my revenue change?",
        "Where am I losing revenue?",
        "What actions should I take?",
    ]


def get_conversation_starters() -> list[dict]:
    """Return categorized conversation starters for the welcome screen."""
    return [
        {"category": "Revenue", "icon": "dollar", "questions": [
            "What's my total revenue?",
            "Show monthly revenue breakdown",
            "What's my average order value?",
        ]},
        {"category": "Customers", "icon": "team", "questions": [
            "How many customers do I have?",
            "Who are my top customers?",
            "How many repeat customers?",
        ]},
        {"category": "Products", "icon": "shopping", "questions": [
            "Show me top selling products",
            "What are my top categories?",
            "Which products have the most refunds?",
        ]},
        {"category": "Health", "icon": "pulse", "questions": [
            "What's my refund rate?",
            "How is customer sentiment?",
            "What happened last week?",
        ]},
    ]


# ── Model warmup (Improvement #5) ──────────────────────────────

def warmup_model() -> dict:
    """Pre-load the active Ollama model into memory with a minimal prompt.

    Called fire-and-forget when the user opens the Copilot page so the
    first real question doesn't incur a cold-start delay.
    """
    if not _HAS_OLLAMA or not _client:
        return {"success": False, "reason": "Ollama not available"}
    model = get_active_model()
    try:
        _client.chat(
            model=model,
            messages=[{"role": "user", "content": "hello"}],
        )
        logger.info("Model %s warmed up successfully", model)
        return {"success": True, "model": model}
    except Exception as e:
        logger.warning("Model warmup failed (%s): %s", model, e)
        return {"success": False, "reason": str(e), "model": model}
