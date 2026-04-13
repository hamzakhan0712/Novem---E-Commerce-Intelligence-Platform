"""Tests for the copilot service pattern matching and fallbacks."""

import re
from unittest.mock import MagicMock, patch

import pytest

from app.services.copilot.copilot_service import (
    QUERY_PATTERNS,
    INTELLIGENCE_PATTERNS,
    ask_copilot,
)


class TestQueryPatterns:
    """Verify that QUERY_PATTERNS regex cover expected phrases."""

    def _matches(self, text: str) -> list[str]:
        """Return all pattern templates that match the given text."""
        matched = []
        for pg in QUERY_PATTERNS:
            for pat in pg["patterns"]:
                if re.search(pat, text.lower()):
                    matched.append(pg["template"])
                    break
        return matched

    def test_revenue_queries(self):
        assert self._matches("what is my total revenue")
        assert self._matches("how much have I earned")

    def test_order_queries(self):
        assert self._matches("how many orders do I have")
        assert self._matches("total orders")

    def test_customer_queries(self):
        assert self._matches("how many customers")
        assert self._matches("total customers")

    def test_aov_queries(self):
        assert self._matches("what is my average order value")
        assert self._matches("aov")

    def test_top_products(self):
        matches = self._matches("show me top selling products")
        assert "top_products" in matches

    def test_refund_rate(self):
        matches = self._matches("what is my refund rate")
        assert "refund_rate" in matches

    def test_monthly_revenue(self):
        matches = self._matches("show monthly revenue")
        assert "monthly_revenue" in matches

    def test_repeat_customers(self):
        matches = self._matches("how many repeat customers do I have")
        assert "repeat_customers" in matches

    def test_mom_comparison(self):
        matches = self._matches("compare this month vs last month")
        assert "mom_comparison" in matches

    def test_category_revenue(self):
        matches = self._matches("revenue by category")
        assert "category_revenue" in matches

    def test_discount_impact(self):
        matches = self._matches("how much discount have I given")
        assert "discount_summary" in matches


class TestIntelligencePatterns:
    """Verify intelligence pattern regex coverage."""

    def _matches_intelligence(self, text: str) -> list[str]:
        matched = []
        for pg in INTELLIGENCE_PATTERNS:
            for pat in pg["patterns"]:
                if re.search(pat, text.lower()):
                    matched.append(pg["handler"])
                    break
        return matched

    def test_health_score_queries(self):
        assert "_handle_health_score" in self._matches_intelligence("how is my business doing")
        assert "_handle_health_score" in self._matches_intelligence("health score")
        assert "_handle_health_score" in self._matches_intelligence("give me an overview")

    def test_recommended_actions(self):
        assert "_handle_recommended_actions" in self._matches_intelligence("what should I focus on")
        assert "_handle_recommended_actions" in self._matches_intelligence("recommend something")

    def test_missed_revenue(self):
        assert "_handle_missed_revenue" in self._matches_intelligence("am I losing money")
        assert "_handle_missed_revenue" in self._matches_intelligence("missed revenue")

    def test_anomalies(self):
        assert "_handle_anomalies" in self._matches_intelligence("any anomalies")
        assert "_handle_anomalies" in self._matches_intelligence("is something wrong")

    def test_trends(self):
        assert "_handle_trends" in self._matches_intelligence("show me trends")
        assert "_handle_trends" in self._matches_intelligence("am I growing")


class TestAskCopilot:
    """Integration tests for the ask_copilot entry point."""

    def test_empty_question_returns_system_message(self):
        result = ask_copilot("store-1", "")
        assert result["source"] == "system"
        assert "message_id" in result

    @patch("app.services.copilot.copilot_service._get_cached_response", return_value=None)
    @patch("app.services.copilot.copilot_service._set_cached_response")
    @patch("app.services.copilot.copilot_service.get_duckdb_connection")
    def test_pattern_match_returns_analytics(self, mock_conn_fn, mock_set_cache, mock_get_cache):
        mock_conn = MagicMock()
        mock_conn_fn.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = [(5000.0,)]

        result = ask_copilot("store-1", "total revenue")

        assert result["source"] == "analytics"
        assert "message_id" in result
