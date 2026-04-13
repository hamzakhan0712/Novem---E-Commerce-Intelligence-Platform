"""Tests for the ingestion merge engine."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from app.services.ingestion.merge_engine import (
    _enforce_not_nulls,
    _validate_table_name,
    merge_into_store,
    TABLE_KEYS,
    TABLE_NOT_NULL_DEFAULTS,
    ALLOWED_TABLES,
)


class TestValidateTableName:
    def test_valid_table_names(self):
        for name in ALLOWED_TABLES:
            assert _validate_table_name(name) == name

    def test_invalid_table_raises(self):
        with pytest.raises(ValueError, match="Invalid data type"):
            _validate_table_name("evil_table; DROP TABLE orders")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            _validate_table_name("")


class TestEnforceNotNulls:
    def test_fills_default_values(self):
        df = pd.DataFrame({
            "order_id": ["o1", "o2"],
            "order_date": ["2024-01-01", "2024-01-02"],
            "customer_id": ["c1", "c2"],
            "product_id": ["p1", "p2"],
            "quantity": [None, 3],
            "unit_price": [None, 10.0],
            "total_price": [None, 30.0],
            "currency": [None, "USD"],
            "status": [None, "pending"],
        })
        result, dropped, errors = _enforce_not_nulls(df, "orders")
        assert dropped == 0
        assert result.iloc[0]["quantity"] == 1
        assert result.iloc[0]["unit_price"] == 0
        assert result.iloc[0]["currency"] == "INR"
        assert result.iloc[0]["status"] == "completed"

    def test_drops_rows_missing_required(self):
        df = pd.DataFrame({
            "order_id": ["o1", None, "o3"],
            "order_date": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "customer_id": ["c1", "c2", None],
            "product_id": ["p1", "p2", "p3"],
            "quantity": [1, 2, 3],
            "unit_price": [10.0, 20.0, 30.0],
            "total_price": [10.0, 40.0, 90.0],
            "currency": ["INR", "INR", "INR"],
            "status": ["completed", "completed", "completed"],
        })
        result, dropped, errors = _enforce_not_nulls(df, "orders")
        assert dropped == 2
        assert len(result) == 1
        assert len(errors) > 0

    def test_unknown_table_returns_unchanged(self):
        df = pd.DataFrame({"a": [1, 2, 3]})
        result, dropped, errors = _enforce_not_nulls(df, "unknown_table")
        assert dropped == 0
        assert len(result) == 3

    def test_customer_table_requires_customer_id(self):
        df = pd.DataFrame({
            "customer_id": ["c1", None, "c3"],
        })
        result, dropped, errors = _enforce_not_nulls(df, "customers")
        assert dropped == 1
        assert len(result) == 2


class TestTableKeys:
    def test_all_tables_have_keys(self):
        for table in ALLOWED_TABLES:
            assert table in TABLE_KEYS
            assert len(TABLE_KEYS[table]) > 0

    def test_orders_has_composite_key(self):
        assert "order_id" in TABLE_KEYS["orders"]
        assert "product_id" in TABLE_KEYS["orders"]


class TestMergeIntoStore:
    @patch("app.services.ingestion.merge_engine.get_duckdb_connection")
    def test_upsert_pure_insert(self, mock_conn_fn):
        mock_conn = MagicMock()
        mock_conn_fn.return_value = mock_conn
        mock_conn.execute.return_value.fetchdf.return_value = pd.DataFrame()

        df = pd.DataFrame({
            "order_id": ["o1", "o2"],
            "product_id": ["p1", "p2"],
            "line_item_index": [0, 0],
            "order_date": ["2024-01-01", "2024-01-02"],
            "customer_id": ["c1", "c2"],
            "total_price": [100.0, 200.0],
        })

        result = merge_into_store(df, "store-1", "orders", "upsert")
        assert result.rows_new == 2
        assert result.rows_updated == 0

    @patch("app.services.ingestion.merge_engine.get_duckdb_connection")
    def test_replace_strategy(self, mock_conn_fn):
        mock_conn = MagicMock()
        mock_conn_fn.return_value = mock_conn

        df = pd.DataFrame({
            "customer_id": ["c1", "c2", "c3"],
        })

        result = merge_into_store(df, "store-1", "customers", "replace")
        assert result.rows_new == 3
        assert result.rows_updated == 0
        # Verify DELETE was called
        calls = [str(c) for c in mock_conn.execute.call_args_list]
        assert any("DELETE" in c for c in calls)

    @patch("app.services.ingestion.merge_engine.get_duckdb_connection")
    def test_append_skips_duplicates(self, mock_conn_fn):
        mock_conn = MagicMock()
        mock_conn_fn.return_value = mock_conn
        mock_conn.execute.return_value.fetchdf.return_value = pd.DataFrame({
            "customer_id": ["c1"],
        })

        df = pd.DataFrame({
            "customer_id": ["c1", "c2"],
        })

        result = merge_into_store(df, "store-1", "customers", "append")
        assert result.rows_new == 1
        assert result.rows_skipped == 1
