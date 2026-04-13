"""Tests for the alert service."""

import json
from unittest.mock import MagicMock, patch, call

import pytest

from app.models.alerts import AlertOut
from app.services.alerts.alert_service import (
    _get_alert_thresholds,
    check_kpi_thresholds,
    create_alert,
    get_unread_count,
    mark_alerts_read,
)


class TestGetAlertThresholds:
    """Tests for configurable threshold loading."""

    @patch("app.services.alerts.alert_service.get_sqlite_connection")
    def test_returns_defaults_when_no_settings(self, mock_conn_fn):
        mock_conn = MagicMock()
        mock_conn_fn.return_value = mock_conn
        mock_conn.execute.return_value.fetchone.return_value = None

        thresholds = _get_alert_thresholds()

        assert thresholds["revenue_drop_pct"] == -20
        assert thresholds["order_drop_pct"] == -25
        assert thresholds["customer_drop_pct"] == -30
        assert thresholds["aov_spike_pct"] == 50

    @patch("app.core.database.get_sqlite_connection")
    def test_overrides_from_settings(self, mock_conn_fn):
        mock_conn = MagicMock()
        mock_conn_fn.return_value = mock_conn
        row = MagicMock()
        row.__getitem__ = lambda self, key: json.dumps({"revenue_drop_pct": -10, "aov_spike_pct": 30}) if key == "value" else None
        mock_conn.execute.return_value.fetchone.return_value = row

        thresholds = _get_alert_thresholds()

        assert thresholds["revenue_drop_pct"] == -10
        assert thresholds["aov_spike_pct"] == 30
        assert thresholds["order_drop_pct"] == -25

    @patch("app.core.database.get_sqlite_connection")
    def test_ignores_unknown_keys_in_settings(self, mock_conn_fn):
        mock_conn = MagicMock()
        mock_conn_fn.return_value = mock_conn
        row = MagicMock()
        row.__getitem__ = lambda self, key: json.dumps({"unknown_key": 999, "revenue_drop_pct": -15}) if key == "value" else None
        mock_conn.execute.return_value.fetchone.return_value = row

        thresholds = _get_alert_thresholds()

        assert "unknown_key" not in thresholds
        assert thresholds["revenue_drop_pct"] == -15


class TestCheckKpiThresholds:
    """Tests for KPI threshold checking logic."""

    @patch("app.services.alerts.alert_service._get_alert_thresholds")
    @patch("app.services.alerts.alert_service.create_alert")
    @patch("app.services.dashboard.kpi_calculator.get_duckdb_connection")
    def test_creates_revenue_alert_when_below_threshold(
        self, mock_duckdb, mock_create, mock_thresholds
    ):
        mock_thresholds.return_value = {
            "revenue_drop_pct": -20,
            "order_drop_pct": -25,
            "customer_drop_pct": -30,
            "aov_spike_pct": 50,
        }
        mock_conn = MagicMock()
        mock_duckdb.return_value = mock_conn
        # current period then previous period
        mock_conn.execute.return_value.fetchone.side_effect = [
            (7500.0, 100, 50),  # current - 25% drop
            (10000.0, 100, 50),  # previous
        ]
        mock_create.return_value = AlertOut(
            id="a1", module="dashboard", severity="warning",
            title="Revenue Drop Detected", message="test", created_at="2024-01-01",
        )

        alerts = check_kpi_thresholds("store-1")

        assert len(alerts) >= 1

    @patch("app.services.alerts.alert_service._get_alert_thresholds")
    @patch("app.services.alerts.alert_service.create_alert")
    @patch("app.services.dashboard.kpi_calculator.get_duckdb_connection")
    def test_no_alerts_when_within_thresholds(
        self, mock_duckdb, mock_create, mock_thresholds
    ):
        mock_thresholds.return_value = {
            "revenue_drop_pct": -20,
            "order_drop_pct": -25,
            "customer_drop_pct": -30,
            "aov_spike_pct": 50,
        }
        mock_conn = MagicMock()
        mock_duckdb.return_value = mock_conn
        # Stable periods — no big changes
        mock_conn.execute.return_value.fetchone.side_effect = [
            (10000.0, 100, 50),  # current
            (10000.0, 100, 50),  # previous — same
        ]

        alerts = check_kpi_thresholds("store-1")

        assert len(alerts) == 0
        mock_create.assert_not_called()

    @patch("app.services.alerts.alert_service._get_alert_thresholds")
    @patch("app.services.alerts.alert_service.create_alert")
    @patch("app.services.dashboard.kpi_calculator.get_duckdb_connection")
    def test_multiple_alerts_when_multiple_thresholds_breached(
        self, mock_duckdb, mock_create, mock_thresholds
    ):
        mock_thresholds.return_value = {
            "revenue_drop_pct": -20,
            "order_drop_pct": -25,
            "customer_drop_pct": -30,
            "aov_spike_pct": 50,
        }
        mock_conn = MagicMock()
        mock_duckdb.return_value = mock_conn
        # Big drops + AOV spike
        mock_conn.execute.return_value.fetchone.side_effect = [
            (5000.0, 50, 25),    # current — big drop
            (10000.0, 100, 50),  # previous
        ]
        mock_create.return_value = AlertOut(
            id="a1", module="dashboard", severity="warning",
            title="test", message="test", created_at="2024-01-01",
        )

        alerts = check_kpi_thresholds("store-1")

        # Revenue, orders, and customers all dropped >threshold
        assert len(alerts) >= 3


class TestCreateAlert:
    """Tests for alert creation."""

    @patch("app.services.alerts.alert_service.get_sqlite_connection")
    def test_returns_alert_out_model(self, mock_conn_fn):
        mock_conn = MagicMock()
        mock_conn_fn.return_value = mock_conn

        result = create_alert(
            store_id="store-1",
            module="dashboard",
            severity="warning",
            title="Test Alert",
            message="Something happened",
        )

        assert isinstance(result, AlertOut)
        assert result.title == "Test Alert"
        assert result.severity == "warning"
        assert result.is_read is False
        assert result.store_id == "store-1"

    @patch("app.services.alerts.alert_service.get_sqlite_connection")
    def test_inserts_into_sqlite(self, mock_conn_fn):
        mock_conn = MagicMock()
        mock_conn_fn.return_value = mock_conn

        create_alert(
            store_id="store-1",
            module="dashboard",
            severity="info",
            title="Test",
            message="msg",
        )

        mock_conn.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
