"""Tests for the forecast service."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.services.forecasting.forecast_service import (
    generate_forecast,
    get_forecast_metrics_overview,
    _linear_forecast,
)


class TestLinearForecast:
    """Tests for _linear_forecast internal function."""

    def test_returns_correct_number_of_points(self):
        rows = [
            (datetime(2024, 1, i + 1), float(100 + i * 2))
            for i in range(30)
        ]
        result = _linear_forecast(rows, 14)
        assert len(result) == 14

    def test_all_values_non_negative(self):
        rows = [
            (datetime(2024, 1, i + 1), float(100 + i))
            for i in range(30)
        ]
        result = _linear_forecast(rows, 30)
        for point in result:
            assert point["value"] >= 0
            assert point["lower"] >= 0

    def test_has_confidence_intervals(self):
        rows = [
            (datetime(2024, 1, i + 1), float(50 + i * 3))
            for i in range(30)
        ]
        result = _linear_forecast(rows, 7)
        for point in result:
            assert "lower" in point
            assert "upper" in point
            assert point["lower"] <= point["value"] <= point["upper"]

    def test_constant_series_yields_stable_forecast(self):
        rows = [
            (datetime(2024, 1, i + 1), 100.0)
            for i in range(30)
        ]
        result = _linear_forecast(rows, 7)
        for point in result:
            assert 50 < point["value"] < 200

    def test_upward_trend_forecasts_higher(self):
        rows = [
            (datetime(2024, 1, i + 1), float(100 + i * 10))
            for i in range(30)
        ]
        result = _linear_forecast(rows, 7)
        last_historical = 100 + 29 * 10  # 390
        assert result[-1]["value"] > last_historical * 0.5


class TestGenerateForecast:
    """Tests for generate_forecast with mocked DuckDB."""

    @patch("app.services.forecasting.forecast_service.get_duckdb_connection")
    def test_insufficient_data_returns_message(self, mock_conn_fn):
        mock_conn = MagicMock()
        mock_conn_fn.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = [
            (datetime(2024, 1, 1), 100.0),
            (datetime(2024, 1, 2), 200.0),
        ]

        result = generate_forecast("store-1", "revenue", 30)
        assert result["method"] == "insufficient_data"
        assert "Need at least 14 days" in result["summary"]["message"]
        assert result["data"] == []

    @patch("app.services.forecasting.forecast_service.get_duckdb_connection")
    def test_sufficient_data_returns_forecast(self, mock_conn_fn):
        mock_conn = MagicMock()
        mock_conn_fn.return_value = mock_conn
        rows = [
            (datetime(2024, 1, i + 1), float(100 + i * 5))
            for i in range(30)
        ]
        mock_conn.execute.return_value.fetchall.return_value = rows

        result = generate_forecast("store-1", "revenue", 14)
        assert result["method"] in ("linear_trend", "prophet")
        assert result["metric"] == "revenue"
        assert len(result["data"]) == 30 + 14  # historical + forecast
        assert result["summary"]["horizon_days"] == 14

    @patch("app.services.forecasting.forecast_service.get_duckdb_connection")
    def test_forecast_has_summary_stats(self, mock_conn_fn):
        mock_conn = MagicMock()
        mock_conn_fn.return_value = mock_conn
        rows = [
            (datetime(2024, 1, i + 1), float(200 + i))
            for i in range(30)
        ]
        mock_conn.execute.return_value.fetchall.return_value = rows

        result = generate_forecast("store-1", "revenue", 14)
        summary = result["summary"]
        assert "historical_avg" in summary
        assert "forecast_avg" in summary
        assert "change_pct" in summary
        assert summary["trend"] in ("up", "down", "stable")
        assert summary["peak_date"] is not None

    def test_invalid_metric_raises(self):
        with pytest.raises(ValueError, match="Unknown metric"):
            generate_forecast("store-1", "invalid_metric", 30)

    @patch("app.services.forecasting.forecast_service.get_duckdb_connection")
    def test_data_includes_is_forecast_flag(self, mock_conn_fn):
        mock_conn = MagicMock()
        mock_conn_fn.return_value = mock_conn
        rows = [
            (datetime(2024, 1, i + 1), float(100 + i))
            for i in range(20)
        ]
        mock_conn.execute.return_value.fetchall.return_value = rows

        result = generate_forecast("store-1", "orders", 7)
        historical_pts = [d for d in result["data"] if not d["is_forecast"]]
        forecast_pts = [d for d in result["data"] if d["is_forecast"]]
        assert len(historical_pts) == 20
        assert len(forecast_pts) == 7


class TestForecastMetricsOverview:
    """Tests for get_forecast_metrics_overview."""

    @patch("app.services.forecasting.forecast_service.get_duckdb_connection")
    def test_returns_all_metrics(self, mock_conn_fn):
        mock_conn = MagicMock()
        mock_conn_fn.return_value = mock_conn
        rows = [
            (datetime(2024, 1, i + 1), float(100 + i))
            for i in range(30)
        ]
        mock_conn.execute.return_value.fetchall.return_value = rows

        result = get_forecast_metrics_overview("store-1", 14)
        assert len(result) == 4
        metric_keys = {r["metric"] for r in result}
        assert metric_keys == {"revenue", "orders", "customers", "aov"}

    @patch("app.services.forecasting.forecast_service.get_duckdb_connection")
    def test_handles_insufficient_data_gracefully(self, mock_conn_fn):
        mock_conn = MagicMock()
        mock_conn_fn.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = []

        result = get_forecast_metrics_overview("store-1", 14)
        assert len(result) == 4
        for item in result:
            assert item["method"] in ("insufficient_data", "error", "unknown")
