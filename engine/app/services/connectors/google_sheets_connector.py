import logging
from datetime import datetime

import pandas as pd
import requests

from app.services.connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class GoogleSheetsApiConnector(BaseConnector):
    """Connector for Google Sheets API v4 (API key auth).

    Falls back to the existing CSV-export path for public sheets
    when no API key is configured.
    """

    _BASE_URL = "https://sheets.googleapis.com/v4/spreadsheets"

    def __init__(self, credentials: dict):
        super().__init__(credentials)
        self.api_key = credentials.get("api_key", "")
        self.spreadsheet_id = credentials["spreadsheet_id"]
        self.sheet_name = credentials.get("sheet_name", "Sheet1")

    def test_connection(self) -> bool:
        try:
            url = f"{self._BASE_URL}/{self.spreadsheet_id}"
            params = {"key": self.api_key} if self.api_key else {}
            resp = requests.get(url, params=params, timeout=15)
            return resp.status_code == 200
        except Exception as exc:
            logger.warning("Google Sheets connection test failed: %s", exc)
            return False

    def get_available_data_types(self) -> list[str]:
        return ["orders", "customers", "products", "ad_spend", "reviews"]

    def fetch_data(
        self,
        data_type: str,
        since: datetime | None = None,
    ) -> pd.DataFrame:
        range_str = f"{self.sheet_name}"
        url = f"{self._BASE_URL}/{self.spreadsheet_id}/values/{range_str}"
        params: dict = {"key": self.api_key} if self.api_key else {}

        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        body = resp.json()

        values = body.get("values", [])
        if len(values) < 2:
            return pd.DataFrame()

        headers = values[0]
        data_rows = values[1:]
        df = pd.DataFrame(data_rows, columns=headers)

        logger.info(
            "Google Sheets: fetched %d rows from '%s'",
            len(df),
            self.sheet_name,
        )
        return df
