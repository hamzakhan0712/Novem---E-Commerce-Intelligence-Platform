"""
SHAP-based model explainability for churn predictions and forecasting.

Trains a lightweight gradient boosting model on RFM features, then uses
SHAP TreeExplainer to produce feature importance and per-customer explanations.
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


def _build_feature_table(store_id: str, period: str) -> pd.DataFrame | None:
    """Build customer-level feature matrix from orders."""
    conn = get_duckdb_connection()
    start, end = _parse_period(period)

    df = conn.execute(
        """
        SELECT
            customer_id,
            COUNT(DISTINCT order_id)                          AS order_count,
            DATEDIFF('day', MIN(order_date), MAX(order_date)) AS recency_span,
            DATEDIFF('day', MAX(order_date), CURRENT_TIMESTAMP) AS days_since_last,
            DATEDIFF('day', MIN(order_date), CURRENT_TIMESTAMP) AS tenure_days,
            SUM(total_price - discount_amount)                AS total_spend,
            AVG(total_price - discount_amount)                AS avg_order_value,
            SUM(refund_amount)                                AS total_refunds,
            COUNT(DISTINCT category)                          AS category_breadth,
            COUNT(DISTINCT channel)                           AS channel_count,
            SUM(quantity)                                     AS total_items
        FROM orders
        WHERE store_id = ?
          AND order_date >= ?
          AND order_date <= ?
          AND status = 'completed'
        GROUP BY customer_id
        HAVING COUNT(DISTINCT order_id) >= 2
        """,
        [store_id, start.isoformat(), end.isoformat()],
    ).fetchdf()

    if df.empty or len(df) < 10:
        return None

    return df


def get_shap_explanation(store_id: str, period: str = "12m") -> dict:
    """Train a gradient-boosting churn model and explain with SHAP."""
    # SHAP needs a wide lookback window to see both active and churned customers.
    # Short periods (7d, 30d) only capture active buyers, making churn labels uniform.
    # Use at least 12 months regardless of the UI-selected period.
    min_periods = {"7d": "12m", "14d": "12m", "30d": "12m", "60d": "12m", "90d": "12m", "6m": "12m"}
    effective_period = min_periods.get(period, period)
    features_df = _build_feature_table(store_id, effective_period)

    if features_df is None:
        return {
            "model": "insufficient_data",
            "global_importance": [],
            "sample_explanations": [],
            "summary": {"total_customers": 0, "features_used": 0, "model_accuracy": 0},
            "message": "Need at least 10 repeat customers for SHAP analysis.",
        }

    feature_cols = [
        "order_count", "recency_span", "days_since_last", "tenure_days",
        "total_spend", "avg_order_value", "total_refunds",
        "category_breadth", "channel_count", "total_items",
    ]

    X = features_df[feature_cols].fillna(0).copy()

    # Label: churned vs active using percentile-based adaptive threshold.
    # Use the 65th percentile of days_since_last — this guarantees ~35% are
    # labeled as churned regardless of the absolute values, avoiding the
    # "all same class" failure that happens with short periods.
    days_since = features_df["days_since_last"].astype(float)
    p65 = float(days_since.quantile(0.65))
    threshold = max(p65, 14)  # at least 14 days
    y = (days_since > threshold).astype(int)

    if y.nunique() < 2:
        return {
            "model": "insufficient_variance",
            "global_importance": [],
            "sample_explanations": [],
            "summary": {"total_customers": len(features_df), "features_used": len(feature_cols), "model_accuracy": 0},
            "message": "All customers have similar activity patterns — cannot distinguish churned vs. active.",
        }

    try:
        from sklearn.ensemble import GradientBoostingClassifier
        from sklearn.model_selection import cross_val_score
        import shap

        model = GradientBoostingClassifier(
            n_estimators=100, max_depth=3, learning_rate=0.1, random_state=42
        )
        model.fit(X, y)

        # Cross-validated accuracy
        cv_scores = cross_val_score(model, X, y, cv=min(5, len(X) // 2), scoring="accuracy")
        accuracy = round(float(cv_scores.mean()), 4)

        # SHAP explanations
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X)

        # For binary classification, shap_values may be a list [class_0, class_1]
        if isinstance(shap_values, list):
            sv = shap_values[1]  # class 1 = churned
        else:
            sv = shap_values

        # Global feature importance (mean |SHAP|)
        mean_abs = pd.Series(abs(sv).mean(axis=0), index=feature_cols).sort_values(ascending=False)

        global_importance = [
            {
                "feature": feat,
                "importance": round(float(val), 4),
                "label": _feature_label(feat),
            }
            for feat, val in mean_abs.items()
        ]

        # Sample per-customer explanations (top 10 highest churn risk)
        churn_proba = model.predict_proba(X)[:, 1]
        features_df["churn_probability"] = churn_proba

        top_risk = features_df.nlargest(10, "churn_probability")
        sample_explanations = []

        for idx in top_risk.index:
            row_shap = sv[idx] if hasattr(idx, '__index__') else sv[top_risk.index.get_loc(idx)]
            drivers = sorted(
                zip(feature_cols, row_shap, X.loc[idx]),
                key=lambda t: abs(t[1]),
                reverse=True,
            )[:5]

            sample_explanations.append({
                "customer_id": str(features_df.loc[idx, "customer_id"]),
                "churn_probability": round(float(features_df.loc[idx, "churn_probability"]), 4),
                "top_drivers": [
                    {
                        "feature": d[0],
                        "label": _feature_label(d[0]),
                        "shap_value": round(float(d[1]), 4),
                        "feature_value": round(float(d[2]), 2),
                        "direction": "increases_churn" if d[1] > 0 else "decreases_churn",
                    }
                    for d in drivers
                ],
            })

        return {
            "model": "gradient_boosting + SHAP",
            "global_importance": global_importance,
            "sample_explanations": sample_explanations,
            "summary": {
                "total_customers": len(features_df),
                "features_used": len(feature_cols),
                "model_accuracy": accuracy,
                "churn_threshold_days": round(threshold, 1),
                "churned_count": int(y.sum()),
                "active_count": int(len(y) - y.sum()),
            },
        }

    except ImportError as e:
        logger.warning("scikit-learn or shap not installed: %s", e)
        return _fallback_importance(features_df, feature_cols, y)


def _fallback_importance(df: pd.DataFrame, feature_cols: list, y: pd.Series) -> dict:
    """Correlation-based importance when sklearn/shap unavailable."""
    importance = []
    for col in feature_cols:
        corr = float(df[col].corr(y)) if df[col].std() > 0 else 0.0
        importance.append({
            "feature": col,
            "importance": round(abs(corr), 4),
            "label": _feature_label(col),
        })

    importance.sort(key=lambda x: x["importance"], reverse=True)

    return {
        "model": "correlation_fallback",
        "global_importance": importance,
        "sample_explanations": [],
        "summary": {
            "total_customers": len(df),
            "features_used": len(feature_cols),
            "model_accuracy": 0,
        },
        "message": "SHAP unavailable — showing correlation-based feature importance.",
    }


_FEATURE_LABELS = {
    "order_count": "Number of Orders",
    "recency_span": "Time Between First & Last Order",
    "days_since_last": "Days Since Last Purchase",
    "tenure_days": "Customer Tenure",
    "total_spend": "Total Lifetime Spend",
    "avg_order_value": "Average Order Value",
    "total_refunds": "Total Refund Amount",
    "category_breadth": "Product Categories Explored",
    "channel_count": "Sales Channels Used",
    "total_items": "Total Items Purchased",
}


def _feature_label(feature: str) -> str:
    return _FEATURE_LABELS.get(feature, feature.replace("_", " ").title())
