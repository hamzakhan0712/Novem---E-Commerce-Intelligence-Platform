import logging
from datetime import datetime

import pandas as pd

from app.models.ingestion import HealthCheckDetail

logger = logging.getLogger(__name__)

QUALITY_CHECKS = [
    ("null_rate", 0.20),
    ("duplicate_rate", 0.15),
    ("date_validity", 0.15),
    ("negative_values", 0.10),
    ("currency_consistency", 0.10),
    ("schema_match", 0.15),
    ("row_count", 0.05),
    ("data_freshness", 0.10),
]


def run_quality_checks(
    df: pd.DataFrame,
    mapped_columns: dict[str, str],
    data_type: str,
) -> tuple[int, list[HealthCheckDetail]]:
    """Run all quality checks and return (health_score, details)."""
    details: list[HealthCheckDetail] = []

    for check_name, weight in QUALITY_CHECKS:
        checker = _CHECKERS.get(check_name)
        if checker:
            score, issues = checker(df, mapped_columns, data_type)
        else:
            score, issues = 100.0, []

        details.append(HealthCheckDetail(
            check=check_name,
            score=score,
            weight=weight,
            issues=issues,
        ))

    total_score = sum(d.score * d.weight for d in details)
    health_score = min(100, max(0, int(round(total_score))))

    logger.info("Quality check complete: score=%d", health_score)
    return health_score, details


def _check_null_rate(
    df: pd.DataFrame,
    mapped_columns: dict[str, str],
    _data_type: str,
) -> tuple[float, list[str]]:
    """Check NULL rates in mapped columns."""
    issues: list[str] = []
    if df.empty:
        return 0, ["No data rows"]

    total_cells = 0
    null_cells = 0
    for _src, target in mapped_columns.items():
        if target and target in df.columns:
            col = df[target]
            total_cells += len(col)
            nulls = col.isna().sum() + (col.astype(str).str.strip() == "").sum()
            null_cells += nulls
            pct = nulls / len(col) * 100
            if pct > 20:
                issues.append(f"{target}: {pct:.0f}% null values")

    if total_cells == 0:
        return 100, []

    null_pct = null_cells / total_cells * 100
    score = max(0, 100 - null_pct * 2)
    return score, issues


def _check_duplicate_rate(
    df: pd.DataFrame,
    _mapped_columns: dict[str, str],
    _data_type: str,
) -> tuple[float, list[str]]:
    """Check for duplicate rows."""
    if df.empty:
        return 0, ["No data rows"]

    dupe_count = df.duplicated().sum()
    dupe_pct = dupe_count / len(df) * 100
    issues = []
    if dupe_count > 0:
        issues.append(f"{dupe_count} duplicate rows ({dupe_pct:.1f}%)")

    score = max(0, 100 - dupe_pct * (100 / 15))
    return min(100, score), issues


def _check_date_validity(
    df: pd.DataFrame,
    mapped_columns: dict[str, str],
    _data_type: str,
) -> tuple[float, list[str]]:
    """Check date columns parse correctly and are in reasonable range."""
    date_cols = [
        t for t in mapped_columns.values()
        if t and any(kw in t for kw in ("date", "time", "at"))
    ]
    if not date_cols:
        return 100, []

    issues: list[str] = []
    valid_total = 0
    parsed_total = 0
    now = datetime.now()

    for col_name in date_cols:
        if col_name not in df.columns:
            continue
        col = pd.to_datetime(df[col_name], errors="coerce", format="mixed")
        total = len(col)
        valid = col.notna().sum()
        parsed_total += total
        valid_total += valid

        if valid < total:
            bad = total - valid
            issues.append(f"{col_name}: {bad} unparseable dates")

        future = (col.dropna() > now).sum()
        if future > 0:
            issues.append(f"{col_name}: {future} future dates")

        too_old = (col.dropna() < pd.Timestamp("2000-01-01")).sum()
        if too_old > 0:
            issues.append(f"{col_name}: {too_old} dates before 2000")

    if parsed_total == 0:
        return 100, []

    score = (valid_total / parsed_total) * 100
    return min(100, max(0, score)), issues


def _check_negative_values(
    df: pd.DataFrame,
    mapped_columns: dict[str, str],
    _data_type: str,
) -> tuple[float, list[str]]:
    """Check for unexpected negative values."""
    numeric_cols = [
        t for t in mapped_columns.values()
        if t and t not in ("refund_amount",) and any(
            kw in t for kw in (
                "price", "quantity", "qty", "amount",
                "spend", "total", "cost", "stock",
            )
        )
    ]
    if not numeric_cols:
        return 100, []

    issues: list[str] = []
    total = 0
    negatives = 0

    for col_name in numeric_cols:
        if col_name not in df.columns:
            continue
        col = pd.to_numeric(df[col_name], errors="coerce")
        total += col.notna().sum()
        neg = (col < 0).sum()
        if neg > 0:
            negatives += neg
            issues.append(f"{col_name}: {neg} negative values")

    if total == 0:
        return 100, []

    neg_pct = negatives / total * 100
    score = max(0, 100 - neg_pct * 10)
    return min(100, score), issues


def _check_currency_consistency(
    df: pd.DataFrame,
    mapped_columns: dict[str, str],
    _data_type: str,
) -> tuple[float, list[str]]:
    """Check currency field consistency."""
    currency_col = None
    for target in mapped_columns.values():
        if target and "currency" in target:
            currency_col = target
            break

    if not currency_col or currency_col not in df.columns:
        return 100, []

    values = df[currency_col].dropna().str.strip().str.upper()
    unique = values.unique()

    if len(unique) <= 1:
        return 100, []

    issues = [f"Multiple currencies found: {', '.join(unique[:5])}"]
    score = max(0, 100 - (len(unique) - 1) * 20)
    return min(100, score), issues


def _check_schema_match(
    df: pd.DataFrame,
    mapped_columns: dict[str, str],
    _data_type: str,
) -> tuple[float, list[str]]:
    """Check how well source columns mapped to canonical schema."""
    total = len(mapped_columns) if mapped_columns else 1
    mapped = sum(1 for v in mapped_columns.values() if v)
    pct = mapped / total * 100
    issues = []
    if pct < 50:
        issues.append(f"Only {mapped}/{total} columns mapped")
    return min(100, pct), issues


def _check_row_count(
    df: pd.DataFrame,
    _mapped_columns: dict[str, str],
    _data_type: str,
) -> tuple[float, list[str]]:
    """Check minimum viable row count."""
    rows = len(df)
    if rows >= 100:
        return 100, []
    if rows >= 10:
        return 70, [f"Only {rows} rows (recommend 100+)"]
    if rows > 0:
        return 30, [f"Only {rows} rows (recommend 100+)"]
    return 0, ["No data rows"]


def _check_data_freshness(
    df: pd.DataFrame,
    mapped_columns: dict[str, str],
    _data_type: str,
) -> tuple[float, list[str]]:
    """Check how recent the data is."""
    date_cols = [
        t for t in mapped_columns.values()
        if t and any(kw in t for kw in ("date", "time"))
    ]
    if not date_cols:
        return 100, []

    now = datetime.now()
    most_recent = None

    for col_name in date_cols:
        if col_name not in df.columns:
            continue
        col = pd.to_datetime(df[col_name], errors="coerce")
        max_date = col.dropna().max()
        if max_date and (most_recent is None or max_date > most_recent):
            most_recent = max_date

    if most_recent is None:
        return 50, ["Could not determine data freshness"]

    days_old = (now - most_recent).days
    if days_old <= 90:
        return 100, []
    if days_old <= 180:
        return 70, [f"Most recent data is {days_old} days old"]
    if days_old <= 365:
        return 40, [f"Most recent data is {days_old} days old"]
    return 10, [f"Most recent data is {days_old} days old (>1 year)"]


_CHECKERS = {
    "null_rate": _check_null_rate,
    "duplicate_rate": _check_duplicate_rate,
    "date_validity": _check_date_validity,
    "negative_values": _check_negative_values,
    "currency_consistency": _check_currency_consistency,
    "schema_match": _check_schema_match,
    "row_count": _check_row_count,
    "data_freshness": _check_data_freshness,
}
