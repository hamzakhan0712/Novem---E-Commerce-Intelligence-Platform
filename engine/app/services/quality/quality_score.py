import json
import logging
from datetime import datetime, timezone

from app.core.database import get_duckdb_connection, get_sqlite_connection

logger = logging.getLogger(__name__)


def get_store_quality_score(store_id: str) -> dict:
    """
    Compute an overall data quality score for a store.

    Combines:
    - Import health scores (average of last 10 imports)
    - Data completeness (% of non-null key columns)
    - Data freshness (age of most recent order)
    - Volume adequacy (enough rows for reliable analytics)
    """
    import_score = _import_health_score(store_id)
    completeness = _data_completeness(store_id)
    freshness = _data_freshness(store_id)
    volume = _volume_adequacy(store_id)

    weights = {
        "import_health": 0.30,
        "completeness": 0.30,
        "freshness": 0.20,
        "volume": 0.20,
    }

    overall = (
        import_score["score"] * weights["import_health"]
        + completeness["score"] * weights["completeness"]
        + freshness["score"] * weights["freshness"]
        + volume["score"] * weights["volume"]
    )
    overall = min(100, max(0, int(round(overall))))

    return {
        "overall_score": overall,
        "components": {
            "import_health": import_score,
            "completeness": completeness,
            "freshness": freshness,
            "volume": volume,
        },
        "grade": _score_to_grade(overall),
    }


def _import_health_score(store_id: str) -> dict:
    conn = get_sqlite_connection()
    rows = conn.execute(
        """SELECT health_score, health_details FROM import_history
           WHERE store_id = ? AND status = 'completed'
           ORDER BY imported_at DESC LIMIT 10""",
        (store_id,),
    ).fetchall()

    if not rows:
        return {"score": 0, "detail": "No imports yet", "issues": []}

    scores = [r["health_score"] for r in rows if r["health_score"] is not None]
    avg = sum(scores) / len(scores) if scores else 0

    issues: list[str] = []
    for row in rows[:3]:
        try:
            details = json.loads(row["health_details"] or "[]")
            for check in details:
                if isinstance(check, dict) and check.get("score", 100) < 70:
                    for issue in check.get("issues", []):
                        if issue not in issues:
                            issues.append(issue)
        except (json.JSONDecodeError, TypeError):
            pass

    return {
        "score": int(round(avg)),
        "detail": f"Average of {len(scores)} recent imports",
        "issues": issues[:5],
    }


def _data_completeness(store_id: str) -> dict:
    conn = get_duckdb_connection()
    issues: list[str] = []

    key_columns = {
        "orders": ["order_date", "customer_id", "product_id", "total_price", "quantity"],
        "customers": ["customer_id", "total_orders", "total_spend"],
        "products": ["product_id", "product_name"],
    }

    total_checks = 0
    passed_checks = 0

    for table, columns in key_columns.items():
        row = conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE store_id = ?", [store_id]
        ).fetchone()
        total_rows = row[0] if row else 0

        if total_rows == 0:
            continue

        for col in columns:
            total_checks += 1
            null_row = conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE store_id = ? AND {col} IS NULL",
                [store_id],
            ).fetchone()
            null_count = null_row[0] if null_row else 0
            null_pct = (null_count / total_rows) * 100

            if null_pct < 5:
                passed_checks += 1
            elif null_pct < 20:
                passed_checks += 0.5
                issues.append(f"{table}.{col}: {null_pct:.0f}% null")
            else:
                issues.append(f"{table}.{col}: {null_pct:.0f}% null")

    if total_checks == 0:
        return {"score": 0, "detail": "No data to check", "issues": ["Import data first"]}

    score = (passed_checks / total_checks) * 100
    return {
        "score": int(round(score)),
        "detail": f"{int(passed_checks)}/{total_checks} key columns complete",
        "issues": issues[:5],
    }


def _data_freshness(store_id: str) -> dict:
    conn = get_duckdb_connection()
    row = conn.execute(
        "SELECT MAX(order_date) FROM orders WHERE store_id = ?", [store_id]
    ).fetchone()

    if not row or row[0] is None:
        return {"score": 0, "detail": "No orders data", "issues": ["No orders found"]}

    latest = row[0]
    if isinstance(latest, str):
        latest = datetime.fromisoformat(latest.replace("Z", "+00:00"))

    now = datetime.now(timezone.utc)
    if latest.tzinfo is None:
        from datetime import timezone as tz
        latest = latest.replace(tzinfo=tz.utc)

    days_old = (now - latest).days
    issues: list[str] = []

    if days_old <= 7:
        score = 100
    elif days_old <= 30:
        score = 90
    elif days_old <= 90:
        score = 70
        issues.append(f"Latest order is {days_old} days old")
    elif days_old <= 365:
        score = 40
        issues.append(f"Data is {days_old} days old — consider re-importing")
    else:
        score = 10
        issues.append(f"Data is over a year old ({days_old} days)")

    return {
        "score": score,
        "detail": f"Latest order: {days_old} days ago",
        "issues": issues,
    }


def _volume_adequacy(store_id: str) -> dict:
    conn = get_duckdb_connection()
    row = conn.execute(
        "SELECT COUNT(*) FROM orders WHERE store_id = ?", [store_id]
    ).fetchone()
    order_count = row[0] if row else 0

    issues: list[str] = []
    if order_count >= 1000:
        score = 100
    elif order_count >= 500:
        score = 90
    elif order_count >= 100:
        score = 70
        issues.append(f"Only {order_count} orders — some analytics may be limited")
    elif order_count >= 10:
        score = 40
        issues.append(f"Only {order_count} orders — need more data for reliable insights")
    elif order_count == 0:
        score = 0
        issues.append("No orders yet — import data first")
    else:
        score = 10
        issues.append(f"Only {order_count} orders — import more data")

    return {
        "score": score,
        "detail": f"{order_count} total orders",
        "issues": issues,
    }


def _score_to_grade(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 50:
        return "D"
    return "F"
