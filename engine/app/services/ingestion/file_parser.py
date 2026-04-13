import csv
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_MB = 500
PREVIEW_ROWS = 10


def parse_file(
    file_path: str,
    selected_sheet: str | None = None,
    has_header_row: bool = True,
) -> tuple[list[str], list[list], int]:
    """Parse a CSV, TSV, Excel, or TXT file and return (headers, preview_rows, total_rows)."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise ValueError(
            f"File size ({size_mb:.0f} MB) exceeds {MAX_FILE_SIZE_MB} MB limit"
        )

    suffix = path.suffix.lower()

    if suffix in (".xlsx", ".xls"):
        return _parse_excel(path, selected_sheet, has_header_row)
    if suffix in (".csv", ".tsv", ".txt"):
        return _parse_delimited(path, has_header_row)

    raise ValueError(f"Unsupported file format: {suffix}")


def get_excel_sheets(file_path: str) -> list[str]:
    """Return list of sheet names for an Excel file."""
    path = Path(file_path)
    xls = pd.ExcelFile(path)
    return xls.sheet_names


def _parse_excel(
    path: Path,
    selected_sheet: str | None,
    has_header_row: bool,
) -> tuple[list[str], list[list], int]:
    header = 0 if has_header_row else None
    sheet = selected_sheet or 0

    df = pd.read_excel(path, sheet_name=sheet, header=header, dtype=str)

    if not has_header_row:
        df.columns = [f"column_{i + 1}" for i in range(len(df.columns))]

    headers = df.columns.tolist()
    total_rows = len(df)
    preview = df.head(PREVIEW_ROWS).fillna("").values.tolist()

    logger.info("Parsed Excel %s: %d rows, %d columns", path.name, total_rows, len(headers))
    return headers, preview, total_rows


def _parse_delimited(
    path: Path,
    has_header_row: bool,
) -> tuple[list[str], list[list], int]:
    encoding = _detect_encoding(path)
    delimiter = _detect_delimiter(path, encoding)

    header = 0 if has_header_row else None
    df = pd.read_csv(
        path,
        sep=delimiter,
        header=header,
        encoding=encoding,
        dtype=str,
        on_bad_lines="skip",
    )

    if not has_header_row:
        df.columns = [f"column_{i + 1}" for i in range(len(df.columns))]

    headers = df.columns.tolist()
    total_rows = len(df)
    preview = df.head(PREVIEW_ROWS).fillna("").values.tolist()

    logger.info(
        "Parsed %s: %d rows, %d columns (delim=%r, enc=%s)",
        path.name, total_rows, len(headers), delimiter, encoding,
    )
    return headers, preview, total_rows


def read_full_dataframe(
    file_path: str,
    selected_sheet: str | None = None,
    has_header_row: bool = True,
) -> pd.DataFrame:
    """Read the entire file into a DataFrame for import processing."""
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix in (".xlsx", ".xls"):
        header = 0 if has_header_row else None
        sheet = selected_sheet or 0
        df = pd.read_excel(path, sheet_name=sheet, header=header, dtype=str)
    else:
        encoding = _detect_encoding(path)
        delimiter = _detect_delimiter(path, encoding)
        header = 0 if has_header_row else None
        df = pd.read_csv(
            path, sep=delimiter, header=header, encoding=encoding,
            dtype=str, on_bad_lines="skip",
        )

    if not has_header_row:
        df.columns = [f"column_{i + 1}" for i in range(len(df.columns))]

    return df


def _detect_encoding(path: Path) -> str:
    """Try UTF-8, fall back to Latin-1."""
    try:
        with open(path, encoding="utf-8") as f:
            f.read(8192)
        return "utf-8"
    except UnicodeDecodeError:
        return "latin-1"


def _detect_delimiter(path: Path, encoding: str) -> str:
    """Auto-detect delimiter using csv.Sniffer."""
    with open(path, encoding=encoding) as f:
        sample = f.read(8192)
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
        return dialect.delimiter
    except csv.Error:
        return ","
