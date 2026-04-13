import hashlib
import logging

import pandas as pd

logger = logging.getLogger(__name__)

PII_COLUMNS = {
    "customer_email_hash", "email_hash",
    "customer_name_hash", "name_hash",
}


def mask_pii(df: pd.DataFrame, mapped_columns: dict[str, str]) -> tuple[pd.DataFrame, int]:
    """SHA-256 hash PII fields. Returns (masked_df, count_of_hashed_values)."""
    df = df.copy()
    total_hashed = 0

    for _src, target in mapped_columns.items():
        if target not in PII_COLUMNS:
            continue
        if target not in df.columns:
            continue

        col = df[target]
        non_null = col.notna() & (col.astype(str).str.strip() != "")
        count = non_null.sum()

        if count > 0:
            df.loc[non_null, target] = col[non_null].astype(str).apply(
                lambda v: hashlib.sha256(v.strip().lower().encode()).hexdigest()
            )
            total_hashed += count
            logger.info("Hashed %d values in column %s", count, target)

    return df, total_hashed
