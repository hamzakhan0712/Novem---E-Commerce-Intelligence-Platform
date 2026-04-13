import logging
import re
from io import StringIO

import pandas as pd
import requests

logger = logging.getLogger(__name__)

EXPORT_CSV_PATTERN = re.compile(
    r"https://docs\.google\.com/spreadsheets/d/([a-zA-Z0-9_-]+)"
)


def extract_sheet_id(url: str) -> str:
    """Extract the Google Sheets spreadsheet ID from a URL."""
    match = EXPORT_CSV_PATTERN.search(url)
    if not match:
        raise ValueError(
            "Invalid Google Sheets URL. Expected format: "
            "https://docs.google.com/spreadsheets/d/<ID>/..."
        )
    return match.group(1)


def build_export_url(sheet_id: str, sheet_name: str | None = None) -> str:
    """Build a CSV export URL for a public Google Sheet."""
    base = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    if sheet_name:
        base += f"&sheet={requests.utils.quote(sheet_name)}"
    return base


def fetch_google_sheet(url: str, sheet_name: str | None = None) -> pd.DataFrame:
    """Fetch a public Google Sheet as a DataFrame.

    The sheet must be published to the web or shared with
    "Anyone with the link" for this to work without OAuth.
    """
    sheet_id = extract_sheet_id(url)
    export_url = build_export_url(sheet_id, sheet_name)

    logger.info("Fetching Google Sheet %s", sheet_id)
    response = requests.get(export_url, timeout=30)

    if response.status_code != 200:
        raise ConnectionError(
            f"Failed to fetch Google Sheet (HTTP {response.status_code}). "
            "Ensure the sheet is publicly shared."
        )

    content_type = response.headers.get("Content-Type", "")
    if "text/csv" not in content_type and "application/octet-stream" not in content_type:
        raise ValueError(
            "Google Sheets did not return CSV data. "
            "Make sure the spreadsheet is publicly accessible."
        )

    df = pd.read_csv(StringIO(response.text))
    if df.empty:
        raise ValueError("The Google Sheet returned no data")

    logger.info("Fetched %d rows from Google Sheet %s", len(df), sheet_id)
    return df
