"""
Customer churn prediction using BG/NBD (Beta-Geometric / Negative Binomial Distribution) model.

Uses the lifetimes library to compute:
  - P(alive): probability customer is still active
  - Expected purchases in next N days
  - CLV: Customer Lifetime Value via Gamma-Gamma model
"""

import logging
from datetime import datetime, timedelta, timezone

import pandas as pd

from app.core.database import get_duckdb_connection

logger = logging.getLogger(__name__)

_RISK_THRESHOLDS = {"high": 0.3, "medium": 0.6}


def _parse_period(period: str) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    days = int(period[:-1]) * 30 if period.endswith("m") else int(period.rstrip("d"))
    start = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0)
    end = now.replace(hour=23, minute=59, second=59)
    return start, end


def _build_rfm_table(store_id: str, period: str) -> pd.DataFrame | None:
    """Build recency-frequency-monetary table from orders for the lifetimes library."""
    conn = get_duckdb_connection()
    start, end = _parse_period(period)

    df = conn.execute(
        """
        SELECT
            customer_id,
            CAST(order_date AS DATE) AS order_date,
            SUM(total_price - discount_amount) AS monetary_value
        FROM orders
        WHERE store_id = ?
          AND order_date >= ?
          AND order_date <= ?
          AND status = 'completed'
        GROUP BY customer_id, CAST(order_date AS DATE)
        ORDER BY customer_id, order_date
        """,
        [store_id, start.isoformat(), end.isoformat()],
    ).fetchdf()

    if df.empty or len(df) < 5:
        return None

    df["order_date"] = pd.to_datetime(df["order_date"])
    observation_end = df["order_date"].max()

    rfm = df.groupby("customer_id").agg(
        frequency=("order_date", lambda x: x.nunique() - 1),
        recency=("order_date", lambda x: (x.max() - x.min()).days),
        T=("order_date", lambda x: (observation_end - x.min()).days),
        monetary_value=("monetary_value", "mean"),
    ).reset_index()

    rfm = rfm[rfm["frequency"] > 0].copy()
    rfm["monetary_value"] = rfm["monetary_value"].clip(lower=0.01)

    if rfm.empty or len(rfm) < 3:
        return None

    return rfm


def get_churn_predictions(store_id: str, period: str = "12m", horizon_days: int = 30) -> dict:
    """Run BG/NBD model and return churn risk per customer."""
    rfm = _build_rfm_table(store_id, period)

    if rfm is None:
        return {
            "model": "insufficient_data",
            "customers": [],
            "summary": {
                "total_scored": 0,
                "high_risk": 0,
                "medium_risk": 0,
                "low_risk": 0,
                "avg_alive_probability": 0,
            },
            "horizon_days": horizon_days,
        }

    try:
        from lifetimes import BetaGeoFitter, GammaGammaFitter

        bgf = BetaGeoFitter(penalizer_coef=0.01)
        bgf.fit(rfm["frequency"], rfm["recency"], rfm["T"])

        rfm["p_alive"] = bgf.conditional_probability_alive(
            rfm["frequency"], rfm["recency"], rfm["T"]
        )
        rfm["predicted_purchases"] = bgf.conditional_expected_number_of_purchases_up_to_time(
            horizon_days, rfm["frequency"], rfm["recency"], rfm["T"]
        )

        # Gamma-Gamma for CLV if enough variation
        clv_available = False
        if rfm["monetary_value"].std() > 0:
            try:
                ggf = GammaGammaFitter(penalizer_coef=0.01)
                ggf.fit(rfm["frequency"], rfm["monetary_value"])
                rfm["expected_avg_value"] = ggf.conditional_expected_average_profit(
                    rfm["frequency"], rfm["monetary_value"]
                )
                rfm["clv"] = ggf.customer_lifetime_value(
                    bgf, rfm["frequency"], rfm["recency"], rfm["T"],
                    rfm["monetary_value"], time=horizon_days / 30, discount_rate=0.01,
                )
                clv_available = True
            except Exception as e:
                logger.warning("Gamma-Gamma fit failed, skipping CLV: %s", e)

        model_name = "BG/NBD + Gamma-Gamma" if clv_available else "BG/NBD"

    except ImportError:
        logger.warning("lifetimes not installed, using heuristic fallback")
        return _heuristic_churn(rfm, horizon_days)

    # Classify risk
    def _classify(p_alive: float) -> str:
        if p_alive < _RISK_THRESHOLDS["high"]:
            return "high"
        if p_alive < _RISK_THRESHOLDS["medium"]:
            return "medium"
        return "low"

    rfm["churn_risk"] = rfm["p_alive"].apply(_classify)

    customers = []
    for _, row in rfm.iterrows():
        entry = {
            "customer_id": str(row["customer_id"]),
            "p_alive": round(float(row["p_alive"]), 4),
            "churn_risk": row["churn_risk"],
            "predicted_purchases": round(float(row["predicted_purchases"]), 2),
            "frequency": int(row["frequency"]),
            "recency_days": int(row["recency"]),
            "tenure_days": int(row["T"]),
            "avg_order_value": round(float(row["monetary_value"]), 2),
        }
        if clv_available:
            entry["expected_clv"] = round(float(row.get("clv", 0)), 2)
        customers.append(entry)

    customers.sort(key=lambda c: c["p_alive"])

    high = sum(1 for c in customers if c["churn_risk"] == "high")
    medium = sum(1 for c in customers if c["churn_risk"] == "medium")
    low = sum(1 for c in customers if c["churn_risk"] == "low")
    avg_alive = sum(c["p_alive"] for c in customers) / len(customers) if customers else 0

    return {
        "model": model_name,
        "customers": customers,
        "summary": {
            "total_scored": len(customers),
            "high_risk": high,
            "medium_risk": medium,
            "low_risk": low,
            "avg_alive_probability": round(avg_alive, 4),
        },
        "horizon_days": horizon_days,
    }


def _heuristic_churn(rfm: pd.DataFrame, horizon_days: int) -> dict:
    """Simple recency-based churn estimation when lifetimes is unavailable."""
    max_T = rfm["T"].max() if not rfm.empty else 1

    def _estimate_alive(row: pd.Series) -> float:
        if row["T"] == 0:
            return 0.5
        recency_ratio = row["recency"] / row["T"]
        freq_factor = min(row["frequency"] / 5, 1.0)
        return round(min(1.0, recency_ratio * 0.6 + freq_factor * 0.4), 4)

    rfm["p_alive"] = rfm.apply(_estimate_alive, axis=1)
    rfm["predicted_purchases"] = (rfm["frequency"] / (rfm["T"] / 30).clip(lower=1)) * (horizon_days / 30)
    rfm["churn_risk"] = rfm["p_alive"].apply(
        lambda p: "high" if p < 0.3 else ("medium" if p < 0.6 else "low")
    )

    customers = [
        {
            "customer_id": str(row["customer_id"]),
            "p_alive": float(row["p_alive"]),
            "churn_risk": row["churn_risk"],
            "predicted_purchases": round(float(row["predicted_purchases"]), 2),
            "frequency": int(row["frequency"]),
            "recency_days": int(row["recency"]),
            "tenure_days": int(row["T"]),
            "avg_order_value": round(float(row["monetary_value"]), 2),
        }
        for _, row in rfm.iterrows()
    ]
    customers.sort(key=lambda c: c["p_alive"])

    high = sum(1 for c in customers if c["churn_risk"] == "high")
    medium = sum(1 for c in customers if c["churn_risk"] == "medium")
    low = sum(1 for c in customers if c["churn_risk"] == "low")
    avg_alive = sum(c["p_alive"] for c in customers) / len(customers) if customers else 0

    return {
        "model": "heuristic_fallback",
        "customers": customers,
        "summary": {
            "total_scored": len(customers),
            "high_risk": high,
            "medium_risk": medium,
            "low_risk": low,
            "avg_alive_probability": round(avg_alive, 4),
        },
        "horizon_days": horizon_days,
    }
