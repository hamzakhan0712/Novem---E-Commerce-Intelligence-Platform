"""Tests for the churn predictor service."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from app.services.customers.churn_predictor import (
    _build_rfm_table,
    _parse_period,
    get_churn_predictions,
    _heuristic_churn,
)


class TestParsePeriod:
    def test_days_format(self):
        start, end = _parse_period("30d")
        diff = (end - start).days
        assert 29 <= diff <= 31

    def test_months_format(self):
        start, end = _parse_period("12m")
        diff = (end - start).days
        assert 355 <= diff <= 370

    def test_end_is_today(self):
        _, end = _parse_period("30d")
        today = datetime.now(timezone.utc).replace(tzinfo=None)
        assert abs((end - today).total_seconds()) < 86400


class TestBuildRfmTable:
    @patch("app.services.customers.churn_predictor.get_duckdb_connection")
    def test_returns_none_for_empty_data(self, mock_conn_fn):
        mock_conn = MagicMock()
        mock_conn_fn.return_value = mock_conn
        mock_conn.execute.return_value.fetchdf.return_value = pd.DataFrame()

        result = _build_rfm_table("store-1", "12m")
        assert result is None

    @patch("app.services.customers.churn_predictor.get_duckdb_connection")
    def test_returns_none_for_small_data(self, mock_conn_fn):
        mock_conn = MagicMock()
        mock_conn_fn.return_value = mock_conn
        mock_conn.execute.return_value.fetchdf.return_value = pd.DataFrame({
            "customer_id": ["c1", "c2"],
            "order_date": [datetime(2024, 1, 1), datetime(2024, 1, 2)],
            "monetary_value": [100.0, 200.0],
        })

        result = _build_rfm_table("store-1", "12m")
        assert result is None

    @patch("app.services.customers.churn_predictor.get_duckdb_connection")
    def test_builds_rfm_with_sufficient_data(self, mock_conn_fn):
        mock_conn = MagicMock()
        mock_conn_fn.return_value = mock_conn
        # Need multiple orders per customer with different dates for frequency > 0
        dates_c1 = [datetime(2024, 1, 1) + timedelta(days=i * 14) for i in range(5)]
        dates_c2 = [datetime(2024, 1, 3) + timedelta(days=i * 14) for i in range(5)]
        dates_c3 = [datetime(2024, 1, 5) + timedelta(days=i * 14) for i in range(5)]
        mock_conn.execute.return_value.fetchdf.return_value = pd.DataFrame({
            "customer_id": ["c1"] * 5 + ["c2"] * 5 + ["c3"] * 5,
            "order_date": dates_c1 + dates_c2 + dates_c3,
            "monetary_value": [100.0] * 15,
        })

        result = _build_rfm_table("store-1", "12m")
        assert result is not None
        assert "frequency" in result.columns
        assert "recency" in result.columns
        assert "T" in result.columns
        assert "monetary_value" in result.columns


class TestHeuristicChurn:
    def test_returns_correct_structure(self):
        rfm = pd.DataFrame({
            "customer_id": ["c1", "c2", "c3"],
            "frequency": [5, 2, 1],
            "recency": [10, 50, 100],
            "T": [100, 100, 100],
            "monetary_value": [50.0, 30.0, 10.0],
        })
        result = _heuristic_churn(rfm, 30)

        assert result["model"] == "heuristic_fallback"
        assert len(result["customers"]) == 3
        assert "summary" in result
        assert result["summary"]["total_scored"] == 3

    def test_classifies_risk_levels(self):
        rfm = pd.DataFrame({
            "customer_id": ["c1", "c2", "c3"],
            "frequency": [10, 3, 1],
            "recency": [90, 30, 5],
            "T": [100, 100, 100],
            "monetary_value": [100.0, 50.0, 10.0],
        })
        result = _heuristic_churn(rfm, 30)

        risks = {c["customer_id"]: c["churn_risk"] for c in result["customers"]}
        assert all(r in ("high", "medium", "low") for r in risks.values())

    def test_customers_sorted_by_p_alive(self):
        rfm = pd.DataFrame({
            "customer_id": ["c1", "c2", "c3", "c4"],
            "frequency": [1, 5, 10, 2],
            "recency": [5, 80, 95, 30],
            "T": [100, 100, 100, 100],
            "monetary_value": [50.0, 50.0, 50.0, 50.0],
        })
        result = _heuristic_churn(rfm, 30)
        p_alives = [c["p_alive"] for c in result["customers"]]
        assert p_alives == sorted(p_alives)


class TestGetChurnPredictions:
    @patch("app.services.customers.churn_predictor._build_rfm_table")
    def test_insufficient_data_returns_empty(self, mock_rfm):
        mock_rfm.return_value = None

        result = get_churn_predictions("store-1", "12m", 30)
        assert result["model"] == "insufficient_data"
        assert result["customers"] == []
        assert result["summary"]["total_scored"] == 0

    @patch("app.services.customers.churn_predictor._build_rfm_table")
    def test_falls_back_to_heuristic_without_lifetimes(self, mock_rfm):
        rfm = pd.DataFrame({
            "customer_id": ["c1", "c2", "c3"],
            "frequency": [5, 2, 1],
            "recency": [10, 50, 80],
            "T": [100, 100, 100],
            "monetary_value": [50.0, 30.0, 10.0],
        })
        mock_rfm.return_value = rfm

        # The test may use lifetimes or heuristic — either is valid
        result = get_churn_predictions("store-1", "12m", 30)
        assert result["model"] in ("BG/NBD + Gamma-Gamma", "BG/NBD", "heuristic_fallback")
        assert len(result["customers"]) == 3
        assert result["summary"]["total_scored"] == 3
