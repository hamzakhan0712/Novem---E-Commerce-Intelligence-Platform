"""
Time-series forecasting service using linear regression fallback.
Uses Prophet when available, otherwise a simple trend extrapolation.
"""

import logging
from datetime import datetime, timedelta, timezone

from app.core.database import get_duckdb_connection

logger = logging.getLogger(__name__)

_HAS_PROPHET = False
try:
    from prophet import Prophet
    _HAS_PROPHET = True
    logger.info("Prophet available for forecasting")
except ImportError:
    logger.info("Prophet not installed — using linear trend fallback")

METRIC_SQL = {
    "revenue": "SUM(total_price - discount_amount)",
    "orders": "COUNT(DISTINCT order_id)",
    "customers": "COUNT(DISTINCT customer_id)",
    "aov": "SUM(total_price - discount_amount) / NULLIF(COUNT(DISTINCT order_id), 0)",
}

METRIC_LABELS = {
    "revenue": "Revenue",
    "orders": "Orders",
    "customers": "Customers",
    "aov": "Avg Order Value",
}


def generate_forecast(
    store_id: str,
    metric: str = "revenue",
    horizon_days: int = 30,
) -> dict:
    """Generate time-series forecast for a metric."""
    conn = get_duckdb_connection()
    agg = METRIC_SQL.get(metric)
    if not agg:
        raise ValueError(f"Unknown metric: {metric}")

    rows = conn.execute(
        f"""SELECT order_date::DATE as ds, {agg} as y
            FROM orders WHERE store_id = ? AND status = 'completed'
            GROUP BY ds ORDER BY ds""",
        [store_id],
    ).fetchall()

    if len(rows) < 14:
        return {
            "metric": metric,
            "method": "insufficient_data",
            "horizon_days": horizon_days,
            "data": [],
            "summary": {
                "historical_avg": 0,
                "forecast_avg": 0,
                "change_pct": 0,
                "trend": "insufficient_data",
                "horizon_days": horizon_days,
                "data_points": len(rows),
                "forecast_total": 0,
                "peak_date": None,
                "peak_value": 0,
                "min_date": None,
                "min_value": 0,
                "message": f"Need at least 14 days of data for forecasting. Currently have {len(rows)} days.",
            },
        }

    historical = [{"date": str(r[0]), "value": float(r[1]) if r[1] else 0} for r in rows]

    if _HAS_PROPHET:
        try:
            fc_points = _prophet_forecast(rows, horizon_days)
            method = "prophet"
        except Exception as exc:
            logger.warning("Prophet forecast failed, falling back to linear: %s", exc)
            fc_points = _linear_forecast(rows, horizon_days)
            method = "linear_trend"
    else:
        fc_points = _linear_forecast(rows, horizon_days)
        method = "linear_trend"

    # Build unified data array with is_forecast flag
    data = []
    for h in historical:
        data.append({
            "date": h["date"],
            "value": h["value"],
            "lower": None,
            "upper": None,
            "is_forecast": False,
        })
    for f in fc_points:
        data.append({
            "date": f["date"],
            "value": f["value"],
            "lower": f.get("lower"),
            "upper": f.get("upper"),
            "is_forecast": True,
        })

    # Summary stats
    hist_values = [h["value"] for h in historical[-30:]]
    fc_values = [f["value"] for f in fc_points]
    hist_avg = sum(hist_values) / len(hist_values) if hist_values else 0
    fc_avg = sum(fc_values) / len(fc_values) if fc_values else 0
    change_pct = ((fc_avg - hist_avg) / hist_avg * 100) if hist_avg > 0 else 0
    forecast_total = sum(fc_values)

    # Find peak and min forecast days
    peak_date = None
    peak_value = 0
    min_date = None
    min_value = float("inf")
    for f in fc_points:
        if f["value"] > peak_value:
            peak_value = f["value"]
            peak_date = f["date"]
        if f["value"] < min_value:
            min_value = f["value"]
            min_date = f["date"]

    return {
        "metric": metric,
        "method": method,
        "horizon_days": horizon_days,
        "data": data,
        "summary": {
            "horizon_days": horizon_days,
            "historical_avg": round(hist_avg, 2),
            "forecast_avg": round(fc_avg, 2),
            "change_pct": round(change_pct, 1),
            "trend": "up" if change_pct > 2 else "down" if change_pct < -2 else "stable",
            "data_points": len(historical),
            "forecast_total": round(forecast_total, 2),
            "peak_date": peak_date,
            "peak_value": round(peak_value, 2),
            "min_date": min_date,
            "min_value": round(min_value if min_value != float("inf") else 0, 2),
        },
    }


def get_forecast_metrics_overview(store_id: str, horizon_days: int = 30) -> list[dict]:
    """Quick overview of forecast trends for all metrics."""
    results = []
    for metric_key, label in METRIC_LABELS.items():
        try:
            fc = generate_forecast(store_id, metric_key, horizon_days)
            summary = fc.get("summary", {})
            results.append({
                "metric": metric_key,
                "label": label,
                "method": fc.get("method", "unknown"),
                "historical_avg": summary.get("historical_avg", 0),
                "forecast_avg": summary.get("forecast_avg", 0),
                "change_pct": summary.get("change_pct", 0),
                "trend": summary.get("trend", "unknown"),
                "forecast_total": summary.get("forecast_total", 0),
            })
        except Exception as exc:
            logger.warning("Failed to forecast %s: %s", metric_key, exc)
            results.append({
                "metric": metric_key,
                "label": label,
                "method": "error",
                "historical_avg": 0,
                "forecast_avg": 0,
                "change_pct": 0,
                "trend": "unknown",
                "forecast_total": 0,
            })
    return results


def _prophet_forecast(rows: list, horizon_days: int) -> list[dict]:
    import pandas as pd

    df = pd.DataFrame(rows, columns=["ds", "y"])
    df["ds"] = pd.to_datetime(df["ds"])
    df["y"] = df["y"].astype(float)

    model = Prophet(
        daily_seasonality=True,
        weekly_seasonality=True,
        yearly_seasonality=len(df) >= 365,
        changepoint_prior_scale=0.05,
    )
    model.fit(df)

    future = model.make_future_dataframe(periods=horizon_days)
    forecast = model.predict(future)

    fc_rows = forecast.tail(horizon_days)
    return [
        {
            "date": row["ds"].strftime("%Y-%m-%d"),
            "value": round(max(0, row["yhat"]), 2),
            "lower": round(max(0, row["yhat_lower"]), 2),
            "upper": round(max(0, row["yhat_upper"]), 2),
        }
        for _, row in fc_rows.iterrows()
    ]


def _linear_forecast(rows: list, horizon_days: int) -> list[dict]:
    """Simple linear trend extrapolation with seasonal adjustment."""
    n = len(rows)
    values = [float(r[1]) if r[1] else 0 for r in rows]

    # Linear regression: y = mx + b
    x_mean = (n - 1) / 2
    y_mean = sum(values) / n
    numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    slope = numerator / denominator if denominator != 0 else 0
    intercept = y_mean - slope * x_mean

    # Weekly seasonal factors (day-of-week adjustment)
    if n >= 14:
        dow_sums: dict[int, list[float]] = {d: [] for d in range(7)}
        for i, r in enumerate(rows):
            date = r[0] if isinstance(r[0], datetime) else datetime.fromisoformat(str(r[0]))
            dow_sums[date.weekday()].append(values[i])
        dow_avg = {d: sum(v) / len(v) if v else y_mean for d, v in dow_sums.items()}
        overall_avg = sum(dow_avg.values()) / 7
        seasonal = {d: (avg / overall_avg) if overall_avg > 0 else 1.0 for d, avg in dow_avg.items()}
    else:
        seasonal = {d: 1.0 for d in range(7)}

    last_date = rows[-1][0]
    if isinstance(last_date, str):
        last_date = datetime.fromisoformat(last_date)

    forecast: list[dict] = []
    for day in range(1, horizon_days + 1):
        fc_date = last_date + timedelta(days=day)
        trend_val = slope * (n - 1 + day) + intercept
        dow = fc_date.weekday() if isinstance(fc_date, datetime) else 0
        adjusted = max(0, trend_val * seasonal.get(dow, 1.0))

        # Confidence interval widens with distance
        uncertainty = abs(slope) * day * 0.3 + y_mean * 0.1
        forecast.append({
            "date": str(fc_date)[:10],
            "value": round(adjusted, 2),
            "lower": round(max(0, adjusted - uncertainty), 2),
            "upper": round(adjusted + uncertainty, 2),
        })

    return forecast
