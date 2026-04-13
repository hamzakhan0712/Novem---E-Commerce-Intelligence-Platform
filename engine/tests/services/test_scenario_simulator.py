"""Tests for the scenario simulator service."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.insights.scenario_simulator import (
    _estimate_price_elasticity,
    _estimate_new_customer_aov_ratio,
    _DEFAULT_PRICE_ELASTICITY,
    _DEFAULT_NEW_CUSTOMER_AOV_RATIO,
    run_scenario,
)


class TestEstimatePriceElasticity:
    """Tests for data-driven price elasticity estimation."""

    @patch("app.services.insights.scenario_simulator.get_duckdb_connection")
    def test_returns_default_when_insufficient_data(self, mock_conn_fn):
        mock_conn = MagicMock()
        mock_conn_fn.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = [
            ("2024-01", 50.0, 30),
            ("2024-02", 55.0, 28),
        ]

        elasticity, is_data_driven = _estimate_price_elasticity("store-1")

        assert elasticity == _DEFAULT_PRICE_ELASTICITY
        assert is_data_driven is False

    @patch("app.services.insights.scenario_simulator.get_duckdb_connection")
    def test_returns_data_driven_with_sufficient_data(self, mock_conn_fn):
        mock_conn = MagicMock()
        mock_conn_fn.return_value = mock_conn
        # 6 months of data with meaningful AOV changes
        mock_conn.execute.return_value.fetchall.return_value = [
            ("2024-01", 50.0, 100),
            ("2024-02", 55.0, 90),
            ("2024-03", 52.0, 95),
            ("2024-04", 58.0, 85),
            ("2024-05", 54.0, 92),
            ("2024-06", 60.0, 80),
        ]

        elasticity, is_data_driven = _estimate_price_elasticity("store-1")

        assert is_data_driven is True
        assert -2.0 <= elasticity <= 0.0

    @patch("app.services.insights.scenario_simulator.get_duckdb_connection")
    def test_returns_default_on_exception(self, mock_conn_fn):
        mock_conn = MagicMock()
        mock_conn_fn.return_value = mock_conn
        mock_conn.execute.side_effect = Exception("DB error")

        elasticity, is_data_driven = _estimate_price_elasticity("store-1")

        assert elasticity == _DEFAULT_PRICE_ELASTICITY
        assert is_data_driven is False


class TestEstimateNewCustomerAovRatio:

    @patch("app.services.insights.scenario_simulator.get_duckdb_connection")
    def test_returns_data_driven_ratio(self, mock_conn_fn):
        mock_conn = MagicMock()
        mock_conn_fn.return_value = mock_conn
        mock_conn.execute.return_value.fetchone.return_value = (35.0, 50.0)

        ratio, is_data_driven = _estimate_new_customer_aov_ratio("store-1")

        assert is_data_driven is True
        assert ratio == 0.7

    @patch("app.services.insights.scenario_simulator.get_duckdb_connection")
    def test_returns_default_when_no_data(self, mock_conn_fn):
        mock_conn = MagicMock()
        mock_conn_fn.return_value = mock_conn
        mock_conn.execute.return_value.fetchone.return_value = (None, None)

        ratio, is_data_driven = _estimate_new_customer_aov_ratio("store-1")

        assert ratio == _DEFAULT_NEW_CUSTOMER_AOV_RATIO
        assert is_data_driven is False


class TestSimulateScenario:
    """Tests for the main run_scenario function."""

    @patch("app.services.insights.scenario_simulator._estimate_new_customer_aov_ratio")
    @patch("app.services.insights.scenario_simulator._estimate_price_elasticity")
    @patch("app.services.insights.scenario_simulator.calculate_kpis")
    @patch("app.services.insights.scenario_simulator.get_duckdb_connection")
    def test_returns_complete_structure(self, mock_conn_fn, mock_kpis, mock_elast, mock_aov_ratio):
        mock_conn = MagicMock()
        mock_conn_fn.return_value = mock_conn
        mock_conn.execute.return_value.fetchone.return_value = (500.0, 200.0)
        mock_kpis.return_value = {
            "current": {"revenue": 10000, "order_count": 200, "unique_customers": 100, "aov": 50},
        }
        mock_elast.return_value = (-0.3, False)
        mock_aov_ratio.return_value = (0.7, False)

        result = run_scenario("store-1", "30d", {})

        assert "baseline" in result
        assert "projected" in result
        assert "total_impact" in result
        assert "impacts" in result
        assert "assumptions" in result
        assert "disclaimer" in result
        assert isinstance(result["disclaimer"], str)

    @patch("app.services.insights.scenario_simulator._estimate_new_customer_aov_ratio")
    @patch("app.services.insights.scenario_simulator._estimate_price_elasticity")
    @patch("app.services.insights.scenario_simulator.calculate_kpis")
    @patch("app.services.insights.scenario_simulator.get_duckdb_connection")
    def test_price_increase_impacts_revenue(self, mock_conn_fn, mock_kpis, mock_elast, mock_aov_ratio):
        mock_conn = MagicMock()
        mock_conn_fn.return_value = mock_conn
        mock_conn.execute.return_value.fetchone.return_value = (500.0, 200.0)
        mock_kpis.return_value = {
            "current": {"revenue": 10000, "order_count": 200, "unique_customers": 100, "aov": 50},
        }
        mock_elast.return_value = (-0.5, True)
        mock_aov_ratio.return_value = (0.7, False)

        result = run_scenario("store-1", "30d", {"price_change_pct": 10})

        price_impact = [i for i in result["impacts"] if i["lever"] == "Price Change"]
        assert len(price_impact) == 1

    @patch("app.services.insights.scenario_simulator._estimate_new_customer_aov_ratio")
    @patch("app.services.insights.scenario_simulator._estimate_price_elasticity")
    @patch("app.services.insights.scenario_simulator.calculate_kpis")
    @patch("app.services.insights.scenario_simulator.get_duckdb_connection")
    def test_no_adjustments_returns_zero_impact(self, mock_conn_fn, mock_kpis, mock_elast, mock_aov_ratio):
        mock_conn = MagicMock()
        mock_conn_fn.return_value = mock_conn
        mock_conn.execute.return_value.fetchone.return_value = (500.0, 200.0)
        mock_kpis.return_value = {
            "current": {"revenue": 10000, "order_count": 200, "unique_customers": 100, "aov": 50},
        }
        mock_elast.return_value = (-0.3, False)
        mock_aov_ratio.return_value = (0.7, False)

        result = run_scenario("store-1", "30d", {})

        assert result["total_impact"] == 0
        assert len(result["impacts"]) == 0
