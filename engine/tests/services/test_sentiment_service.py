"""Tests for the sentiment analysis service."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.services.sentiment.sentiment_service import (
    _parse_period,
    _parse_period_with_prev,
    _change_pct,
    get_sentiment_summary,
    get_rating_breakdown,
    get_sentiment_trend,
)


class TestParsePeriod:
    def test_days(self):
        start, end = _parse_period("30d")
        diff = (end - start).days
        assert 29 <= diff <= 31

    def test_months(self):
        start, end = _parse_period("6m")
        diff = (end - start).days
        assert 175 <= diff <= 185


class TestParsePeriodWithPrev:
    def test_returns_four_dates(self):
        cs, ce, ps, pe = _parse_period_with_prev("30d")
        assert ce > cs
        assert pe < cs
        assert pe > ps

    def test_previous_period_same_span(self):
        cs, ce, ps, pe = _parse_period_with_prev("30d")
        current_span = (ce - cs).days
        prev_span = (pe - ps).days
        assert abs(current_span - prev_span) <= 1


class TestChangePct:
    def test_normal_increase(self):
        assert _change_pct(120, 100) == 20.0

    def test_normal_decrease(self):
        assert _change_pct(80, 100) == -20.0

    def test_zero_previous(self):
        assert _change_pct(50, 0) == 100.0

    def test_both_zero(self):
        assert _change_pct(0, 0) == 0.0


class TestGetSentimentSummary:
    @patch("app.services.sentiment.sentiment_service.get_duckdb_connection")
    def test_empty_data_returns_zeros(self, mock_conn_fn):
        mock_conn = MagicMock()
        mock_conn_fn.return_value = mock_conn
        mock_conn.execute.return_value.fetchone.return_value = (0, None, 0, 0, 0, None)

        result = get_sentiment_summary("store-1", "30d")
        assert result["current"]["total_reviews"] == 0
        assert result["current"]["avg_score"] == 0

    @patch("app.services.sentiment.sentiment_service.get_duckdb_connection")
    def test_with_reviews_returns_stats(self, mock_conn_fn):
        mock_conn = MagicMock()
        mock_conn_fn.return_value = mock_conn
        mock_conn.execute.return_value.fetchone.side_effect = [
            (100, 0.75, 60, 20, 20, 4.2),   # current
            (80, 0.70, 45, 20, 15, 4.0),     # previous
        ]

        result = get_sentiment_summary("store-1", "30d")
        assert result["current"]["total_reviews"] == 100
        assert result["current"]["avg_score"] == 0.75
        assert "changes" in result


class TestGetRatingBreakdown:
    @patch("app.services.sentiment.sentiment_service.get_duckdb_connection")
    def test_returns_rating_distribution(self, mock_conn_fn):
        mock_conn = MagicMock()
        mock_conn_fn.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = [
            (5, 50, 0.9), (4, 30, 0.75), (3, 10, 0.5), (2, 5, 0.3), (1, 5, 0.1),
        ]

        result = get_rating_breakdown("store-1", "30d")
        assert len(result) == 5
        assert result[0]["count"] == 50
        assert result[0]["avg_sentiment"] == 0.9


class TestGetSentimentTrend:
    @patch("app.services.sentiment.sentiment_service.get_duckdb_connection")
    def test_returns_daily_data(self, mock_conn_fn):
        mock_conn = MagicMock()
        mock_conn_fn.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = [
            ("2024-01-01", 10, 0.8, 7, 2),
            ("2024-01-02", 15, 0.7, 10, 3),
            ("2024-01-03", 8, 0.9, 6, 1),
        ]

        result = get_sentiment_trend("store-1", "7d")
        assert len(result) == 3
        assert "date" in result[0]
        assert "avg_score" in result[0]
        assert "count" in result[0]

    @patch("app.services.sentiment.sentiment_service.get_duckdb_connection")
    def test_empty_trend(self, mock_conn_fn):
        mock_conn = MagicMock()
        mock_conn_fn.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = []

        result = get_sentiment_trend("store-1", "7d")
        assert result == []
