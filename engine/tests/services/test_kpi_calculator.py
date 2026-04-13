"""Tests for the KPI calculator service."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.services.dashboard.kpi_calculator import _parse_period, calculate_kpis


class TestParsePeriod:
    """Tests for _parse_period helper."""

    def test_30d_returns_four_datetimes(self):
        cs, ce, ps, pe = _parse_period("30d")
        assert isinstance(cs, datetime)
        assert isinstance(ce, datetime)
        assert isinstance(ps, datetime)
        assert isinstance(pe, datetime)

    def test_current_period_span_matches_days(self):
        cs, ce, _, _ = _parse_period("7d")
        diff = (ce - cs).days
        assert 6 <= diff <= 8

    def test_previous_ends_before_current_starts(self):
        cs, _, _, pe = _parse_period("30d")
        assert pe < cs

    def test_invalid_period_defaults_to_30d(self):
        cs_invalid, _, _, _ = _parse_period("999x")
        cs_valid, _, _, _ = _parse_period("30d")
        assert (cs_invalid - cs_valid).total_seconds() < 2

    def test_months_period(self):
        cs, ce, ps, pe = _parse_period("12m")
        diff = (ce - cs).days
        assert 350 <= diff <= 370


class TestCalculateKpis:
    """Tests for calculate_kpis with mocked DuckDB."""

    @patch("app.services.dashboard.kpi_calculator.get_duckdb_connection")
    def test_returns_expected_shape(self, mock_conn_fn):
        mock_conn = MagicMock()
        mock_conn_fn.return_value = mock_conn
        # Mock two calls: current period and previous period
        mock_conn.execute.return_value.fetchone.side_effect = [
            (5000.0, 100, 50),   # current: revenue, orders, customers
            (4000.0, 80, 40),    # previous
        ]

        result = calculate_kpis("store-1", "30d")

        assert result["period"] == "30d"
        assert "current" in result
        assert "previous" in result
        assert "changes" in result

    @patch("app.services.dashboard.kpi_calculator.get_duckdb_connection")
    def test_current_values_calculated_correctly(self, mock_conn_fn):
        mock_conn = MagicMock()
        mock_conn_fn.return_value = mock_conn
        mock_conn.execute.return_value.fetchone.side_effect = [
            (10000.0, 200, 100),
            (8000.0, 160, 80),
        ]

        result = calculate_kpis("store-1", "30d")

        assert result["current"]["revenue"] == 10000.0
        assert result["current"]["order_count"] == 200
        assert result["current"]["unique_customers"] == 100
        assert result["current"]["aov"] == 50.0

    @patch("app.services.dashboard.kpi_calculator.get_duckdb_connection")
    def test_change_percentage_calculated(self, mock_conn_fn):
        mock_conn = MagicMock()
        mock_conn_fn.return_value = mock_conn
        mock_conn.execute.return_value.fetchone.side_effect = [
            (10000.0, 200, 100),  # current
            (8000.0, 160, 80),    # previous
        ]

        result = calculate_kpis("store-1", "30d")

        assert result["changes"]["revenue"] == 25.0  # (10000-8000)/8000 * 100
        assert result["changes"]["order_count"] == 25.0

    @patch("app.services.dashboard.kpi_calculator.get_duckdb_connection")
    def test_zero_previous_period(self, mock_conn_fn):
        mock_conn = MagicMock()
        mock_conn_fn.return_value = mock_conn
        mock_conn.execute.return_value.fetchone.side_effect = [
            (5000.0, 50, 25),
            (0.0, 0, 0),  # no previous data
        ]

        result = calculate_kpis("store-1", "30d")

        assert result["changes"]["revenue"] == 100.0
        assert result["previous"]["aov"] == 0.0

    @patch("app.services.dashboard.kpi_calculator.get_duckdb_connection")
    def test_zero_both_periods(self, mock_conn_fn):
        mock_conn = MagicMock()
        mock_conn_fn.return_value = mock_conn
        mock_conn.execute.return_value.fetchone.side_effect = [
            (0.0, 0, 0),
            (0.0, 0, 0),
        ]

        result = calculate_kpis("store-1", "30d")

        assert result["changes"]["revenue"] == 0.0
        assert result["current"]["aov"] == 0.0
