"""
Insights API router — plain-language insights, anomaly detection, action recommendations.
"""

import logging

from fastapi import APIRouter, HTTPException, Query

from app.core.database import get_sqlite_connection
from app.models.common import ApiResponse
from app.services.insights.insight_engine import (
    detect_anomalies,
    generate_insights,
    get_insight_summary,
    get_recommended_actions,
)
from app.services.insights.causal_engine import get_metric_breakdown
from app.services.insights.missed_revenue import detect_missed_revenue
from app.services.insights.feed_service import build_insight_feed
from app.services.insights.health_score import calculate_health_score
from app.services.insights.explain_metric import explain_metric as explain_metric_service
from app.services.insights.shap_explainer import get_shap_explanation
from app.services.insights.scenario_simulator import run_scenario
from app.services.insights.business_dna import calculate_business_dna
from app.services.insights.root_cause_narrator import generate_root_cause_narrative

router = APIRouter(prefix="/insights", tags=["insights"])
logger = logging.getLogger(__name__)

VALID_PERIODS = {"7d", "14d", "30d", "60d", "90d", "6m", "12m"}


def _validate_store(store_id: str) -> None:
    conn = get_sqlite_connection()
    row = conn.execute("SELECT id FROM stores WHERE id = ?", (store_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Store not found")


@router.get("/summary")
def insight_summary(
    store_id: str = Query(...),
    period: str = Query("30d"),
) -> ApiResponse:
    """Return summary counts of insights, anomalies, and actions."""
    _validate_store(store_id)
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Use one of: {', '.join(sorted(VALID_PERIODS))}")

    try:
        summary = get_insight_summary(store_id, period)
    except Exception as exc:
        logger.error("Insight summary failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate insight summary")

    return ApiResponse(success=True, data=summary)


@router.get("")
def list_insights(
    store_id: str = Query(...),
    period: str = Query("30d"),
) -> ApiResponse:
    """Generate prioritized AI insights for a store."""
    _validate_store(store_id)
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Use one of: {', '.join(sorted(VALID_PERIODS))}")

    try:
        insights = generate_insights(store_id, period)
    except Exception as exc:
        logger.error("Insight generation failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate insights")

    return ApiResponse(success=True, data=insights)


@router.get("/anomalies")
def list_anomalies(
    store_id: str = Query(...),
    period: str = Query("30d"),
) -> ApiResponse:
    """Detect anomalies in store metrics."""
    _validate_store(store_id)
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Use one of: {', '.join(sorted(VALID_PERIODS))}")

    try:
        anomalies = detect_anomalies(store_id, period)
    except Exception as exc:
        logger.error("Anomaly detection failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to detect anomalies")

    return ApiResponse(success=True, data=anomalies)


@router.get("/actions")
def list_actions(
    store_id: str = Query(...),
    period: str = Query("30d"),
) -> ApiResponse:
    """Get recommended actions based on data analysis."""
    _validate_store(store_id)
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Use one of: {', '.join(sorted(VALID_PERIODS))}")

    try:
        actions = get_recommended_actions(store_id, period)
    except Exception as exc:
        logger.error("Action generation failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate actions")

    return ApiResponse(success=True, data=actions)


@router.get("/drivers")
def metric_drivers(
    store_id: str = Query(...),
    period: str = Query("30d"),
    metric: str = Query("revenue"),
) -> ApiResponse:
    """Decompose a KPI change into quantified attribution drivers."""
    _validate_store(store_id)
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Use one of: {', '.join(sorted(VALID_PERIODS))}")

    try:
        breakdown = get_metric_breakdown(store_id, metric, period)
    except Exception as exc:
        logger.error("Attribution breakdown failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate attribution breakdown")

    return ApiResponse(success=True, data=breakdown)


@router.get("/missed-revenue")
def missed_revenue(
    store_id: str = Query(...),
    period: str = Query("30d"),
) -> ApiResponse:
    """Detect missed revenue opportunities (refunds, stockouts, churn)."""
    _validate_store(store_id)
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Use one of: {', '.join(sorted(VALID_PERIODS))}")

    try:
        missed = detect_missed_revenue(store_id, period)
    except Exception as exc:
        logger.error("Missed revenue detection failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to detect missed revenue")

    return ApiResponse(success=True, data=missed)


@router.get("/feed")
def insight_feed(
    store_id: str = Query(...),
    period: str = Query("30d"),
) -> ApiResponse:
    """Return a unified, prioritized insight feed."""
    _validate_store(store_id)
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Use one of: {', '.join(sorted(VALID_PERIODS))}")

    try:
        feed = build_insight_feed(store_id, period)
    except Exception as exc:
        logger.error("Insight feed failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to build insight feed")

    return ApiResponse(success=True, data=feed)


@router.get("/health-score")
def health_score(
    store_id: str = Query(...),
    period: str = Query("30d"),
) -> ApiResponse:
    """Calculate the composite business health score."""
    _validate_store(store_id)
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Use one of: {', '.join(sorted(VALID_PERIODS))}")

    try:
        score = calculate_health_score(store_id, period)
    except Exception as exc:
        logger.error("Health score calculation failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to calculate health score")

    return ApiResponse(success=True, data=score)


@router.get("/explain")
def explain_metric(
    store_id: str = Query(...),
    metric: str = Query("revenue"),
    period: str = Query("30d"),
) -> ApiResponse:
    """Explain a metric in plain language with context and guidance."""
    _validate_store(store_id)
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Use one of: {', '.join(sorted(VALID_PERIODS))}")

    try:
        explanation = explain_metric_service(store_id, metric, period)
    except Exception as exc:
        logger.error("Metric explanation failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to explain metric")

    return ApiResponse(success=True, data=explanation)


@router.get("/business-dna")
def business_dna(
    store_id: str = Query(...),
    period: str = Query("12m"),
) -> ApiResponse:
    """Business DNA — store fingerprinting with 6-dimension radar profile."""
    _validate_store(store_id)
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Use one of: {', '.join(sorted(VALID_PERIODS))}")

    try:
        data = calculate_business_dna(store_id, period)
    except Exception as exc:
        logger.error("Business DNA failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to calculate Business DNA")

    return ApiResponse(success=True, data=data)


@router.get("/root-cause")
def root_cause(
    store_id: str = Query(...),
    period: str = Query("7d"),
) -> ApiResponse:
    """Root cause narrative — automated 1-sentence verdict on revenue changes."""
    _validate_store(store_id)
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Use one of: {', '.join(sorted(VALID_PERIODS))}")

    try:
        data = generate_root_cause_narrative(store_id, period)
    except Exception as exc:
        logger.error("Root cause narrative failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate root cause narrative")

    return ApiResponse(success=True, data=data)


@router.get("/shap")
def shap_explanation(
    store_id: str = Query(...),
    period: str = Query("12m"),
) -> ApiResponse:
    """SHAP-based model explainability — feature importance for churn drivers."""
    _validate_store(store_id)
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Use one of: {', '.join(sorted(VALID_PERIODS))}")

    try:
        data = get_shap_explanation(store_id, period)
    except Exception as exc:
        logger.error("SHAP explanation failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate SHAP explanation")

    return ApiResponse(success=True, data=data)


@router.post("/scenario")
def simulate_scenario(
    store_id: str = Query(...),
    period: str = Query("30d"),
    adjustments: dict | None = None,
) -> ApiResponse:
    """What-If scenario simulator — project impact of business lever changes."""
    _validate_store(store_id)
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Use one of: {', '.join(sorted(VALID_PERIODS))}")

    try:
        data = run_scenario(store_id, period, adjustments or {})
    except Exception as exc:
        logger.error("Scenario simulation failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to run scenario simulation")

    return ApiResponse(success=True, data=data)
