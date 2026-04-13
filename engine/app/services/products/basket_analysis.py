"""
Market basket analysis using Apriori algorithm + association rules.

Uses mlxtend to discover product co-purchase patterns:
  - Frequent itemsets (products bought together)
  - Association rules (if X then Y, with confidence and lift)
"""

import logging
from datetime import datetime, timedelta, timezone

import pandas as pd

from app.core.database import get_duckdb_connection

logger = logging.getLogger(__name__)


def _parse_period(period: str) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    days = int(period[:-1]) * 30 if period.endswith("m") else int(period.rstrip("d"))
    start = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0)
    end = now.replace(hour=23, minute=59, second=59)
    return start, end


def get_basket_analysis(store_id: str, period: str = "90d", min_support: float = 0.02, min_confidence: float = 0.1) -> dict:
    """Run Apriori association rule mining on order baskets."""
    conn = get_duckdb_connection()
    start, end = _parse_period(period)

    df = conn.execute(
        """
        SELECT o.order_id, o.product_name
        FROM orders o
        INNER JOIN (
            SELECT order_id
            FROM orders
            WHERE store_id = ?
              AND order_date >= ?
              AND order_date <= ?
              AND status = 'completed'
              AND product_name IS NOT NULL
            GROUP BY order_id
            HAVING COUNT(DISTINCT product_name) >= 2
        ) multi ON o.order_id = multi.order_id
        WHERE o.store_id = ?
          AND o.order_date >= ?
          AND o.order_date <= ?
          AND o.status = 'completed'
          AND o.product_name IS NOT NULL
        """,
        [store_id, start.isoformat(), end.isoformat(),
         store_id, start.isoformat(), end.isoformat()],
    ).fetchdf()

    if df.empty:
        return _empty_result("No order data found")

    unique_orders = df["order_id"].nunique()
    if unique_orders < 10:
        return _empty_result("Need at least 10 orders for basket analysis")

    # Build transaction matrix (one-hot encoded)
    basket = df.groupby(["order_id", "product_name"]).size().unstack(fill_value=0)
    basket = (basket > 0).astype(bool)

    if basket.shape[1] < 2:
        return _empty_result("Need at least 2 distinct products")

    try:
        from mlxtend.frequent_patterns import apriori, association_rules

        # Adaptive min_support — lower threshold for large/diverse datasets
        adaptive_support = min(min_support, max(2 / unique_orders, 0.001))

        frequent_items = apriori(basket, min_support=adaptive_support, use_colnames=True)

        if frequent_items.empty:
            return _empty_result("No frequent itemsets found — try importing more orders")

        rules = association_rules(frequent_items, metric="confidence", min_threshold=min_confidence)

        if rules.empty:
            # Return frequent itemsets even if no rules
            top_pairs = _extract_pairs_from_itemsets(frequent_items, unique_orders)
            return {
                "model": "apriori",
                "rules": [],
                "frequent_pairs": top_pairs,
                "total_orders": unique_orders,
                "total_products": int(basket.shape[1]),
                "summary": {
                    "rules_found": 0,
                    "frequent_pairs_found": len(top_pairs),
                    "min_support_used": round(adaptive_support, 4),
                    "min_confidence_used": min_confidence,
                },
            }

        # Sort by lift (strongest associations first)
        rules = rules.sort_values("lift", ascending=False).head(50)

        rule_list = []
        for _, r in rules.iterrows():
            antecedents = list(r["antecedents"])
            consequents = list(r["consequents"])
            rule_list.append({
                "if_bought": ", ".join(antecedents),
                "then_also_bought": ", ".join(consequents),
                "support": round(float(r["support"]), 4),
                "confidence": round(float(r["confidence"]), 4),
                "lift": round(float(r["lift"]), 4),
                "conviction": round(float(r["conviction"]), 4) if pd.notna(r["conviction"]) and r["conviction"] != float("inf") else None,
                "order_count": int(r["support"] * unique_orders),
            })

        top_pairs = _extract_pairs_from_itemsets(frequent_items, unique_orders)

        return {
            "model": "apriori",
            "rules": rule_list,
            "frequent_pairs": top_pairs,
            "total_orders": unique_orders,
            "total_products": int(basket.shape[1]),
            "summary": {
                "rules_found": len(rule_list),
                "frequent_pairs_found": len(top_pairs),
                "min_support_used": round(adaptive_support, 4),
                "min_confidence_used": min_confidence,
            },
        }

    except ImportError:
        logger.warning("mlxtend not installed, using co-occurrence fallback")
        return _cooccurrence_fallback(df, unique_orders)


def _extract_pairs_from_itemsets(frequent_items: pd.DataFrame, total_orders: int) -> list[dict]:
    """Extract 2-item pairs from frequent itemsets."""
    pairs = frequent_items[frequent_items["itemsets"].apply(len) == 2].copy()
    if pairs.empty:
        return []

    pairs = pairs.sort_values("support", ascending=False).head(20)

    result = []
    for _, row in pairs.iterrows():
        items = sorted(row["itemsets"])
        result.append({
            "products": items,
            "support": round(float(row["support"]), 4),
            "order_count": int(row["support"] * total_orders),
        })
    return result


def _cooccurrence_fallback(df: pd.DataFrame, total_orders: int) -> dict:
    """Simple co-occurrence counting when mlxtend is unavailable."""
    from collections import Counter

    baskets = df.groupby("order_id")["product_name"].apply(list).values

    pair_counts: Counter = Counter()
    for items in baskets:
        unique = sorted(set(items))
        for i in range(len(unique)):
            for j in range(i + 1, len(unique)):
                pair_counts[(unique[i], unique[j])] += 1

    top_pairs = [
        {
            "products": list(pair),
            "support": round(count / total_orders, 4),
            "order_count": count,
        }
        for pair, count in pair_counts.most_common(20)
        if count >= 2
    ]

    return {
        "model": "cooccurrence_fallback",
        "rules": [],
        "frequent_pairs": top_pairs,
        "total_orders": total_orders,
        "total_products": df["product_name"].nunique(),
        "summary": {
            "rules_found": 0,
            "frequent_pairs_found": len(top_pairs),
            "min_support_used": 0,
            "min_confidence_used": 0,
        },
    }


def _empty_result(message: str) -> dict:
    return {
        "model": "none",
        "rules": [],
        "frequent_pairs": [],
        "total_orders": 0,
        "total_products": 0,
        "summary": {
            "rules_found": 0,
            "frequent_pairs_found": 0,
            "min_support_used": 0,
            "min_confidence_used": 0,
            "message": message,
        },
    }
