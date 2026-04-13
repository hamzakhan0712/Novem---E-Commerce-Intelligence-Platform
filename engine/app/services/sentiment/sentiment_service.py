"""
Sentiment analysis service — analyzes review text to extract
sentiment scores, labels, and aspect-level breakdown.
Uses transformer model (distilbert) when available, with TextBlob
and keyword-based fallbacks for environments without torch.
"""

import logging
import re
from collections import Counter
from datetime import datetime, timedelta, timezone

from app.core.database import get_duckdb_connection

logger = logging.getLogger(__name__)

_HAS_TEXTBLOB = False
try:
    from textblob import TextBlob
    _HAS_TEXTBLOB = True
except ImportError:
    logger.info("TextBlob not installed — using keyword-based fallback")

_HAS_TRANSFORMER = False
_sentiment_pipeline = None

try:
    from transformers import pipeline as _hf_pipeline
    _sentiment_pipeline = _hf_pipeline(
        "sentiment-analysis",
        model="distilbert-base-uncased-finetuned-sst-2-english",
        truncation=True,
        max_length=512,
    )
    _HAS_TRANSFORMER = True
    logger.info("Transformer sentiment model loaded (distilbert-sst2)")
except Exception:
    logger.info("Transformers/torch not available — falling back to TextBlob/keywords")


# ── Period helpers ──────────────────────────────────────────────

def _parse_period(period: str) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if period.endswith("m"):
        days = int(period[:-1]) * 30
    else:
        days = int(period.rstrip("d"))
    start = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0)
    end = now.replace(hour=23, minute=59, second=59)
    return start, end


def _parse_period_with_prev(period: str) -> tuple[datetime, datetime, datetime, datetime]:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if period.endswith("m"):
        days = int(period[:-1]) * 30
    else:
        days = int(period.rstrip("d"))
    current_end = now.replace(hour=23, minute=59, second=59)
    current_start = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0)
    prev_end = current_start - timedelta(seconds=1)
    prev_start = (current_start - timedelta(days=days)).replace(hour=0, minute=0, second=0)
    return current_start, current_end, prev_start, prev_end


def _change_pct(curr: float, prev: float) -> float:
    if prev == 0:
        return 0.0 if curr == 0 else 100.0
    return round((curr - prev) / abs(prev) * 100, 1)


# ── Main summary ────────────────────────────────────────────────

def get_sentiment_summary(store_id: str, period: str = "30d") -> dict:
    """Sentiment KPIs with period-over-period comparison."""
    conn = get_duckdb_connection()
    cur_start, cur_end, prev_start, prev_end = _parse_period_with_prev(period)

    def _stats(start: datetime, end: datetime) -> dict:
        row = conn.execute(
            """SELECT
                 COUNT(*) as total,
                 AVG(CASE WHEN sentiment_score IS NOT NULL THEN sentiment_score END) as avg_score,
                 COUNT(CASE WHEN sentiment_label = 'positive' THEN 1 END) as pos,
                 COUNT(CASE WHEN sentiment_label = 'neutral'  THEN 1 END) as neu,
                 COUNT(CASE WHEN sentiment_label = 'negative' THEN 1 END) as neg,
                 AVG(rating) as avg_rating
               FROM reviews
               WHERE store_id = ? AND review_date >= ? AND review_date <= ?""",
            [store_id, str(start), str(end)],
        ).fetchone()
        if not row or row[0] == 0:
            return {"total_reviews": 0, "avg_score": 0, "avg_rating": 0,
                    "positive": 0, "neutral": 0, "negative": 0,
                    "positive_ratio": 0.0}
        return {
            "total_reviews": int(row[0]),
            "avg_score": round(float(row[1] or 0), 3),
            "avg_rating": round(float(row[5] or 0), 1),
            "positive": int(row[2]),
            "neutral": int(row[3]),
            "negative": int(row[4]),
            "positive_ratio": round(int(row[2]) / int(row[0]) * 100, 1) if int(row[0]) > 0 else 0.0,
        }

    current = _stats(cur_start, cur_end)
    previous = _stats(prev_start, prev_end)

    changes = {
        "total_reviews": _change_pct(current["total_reviews"], previous["total_reviews"]),
        "avg_score": _change_pct(current["avg_score"], previous["avg_score"]),
        "avg_rating": _change_pct(current["avg_rating"], previous["avg_rating"]),
        "positive": _change_pct(current["positive_ratio"], previous["positive_ratio"]),
    }

    distribution = {
        "positive": current["positive"],
        "neutral": current["neutral"],
        "negative": current["negative"],
    }

    return {
        "current": current,
        "previous": previous,
        "changes": changes,
        "distribution": distribution,
    }


# ── Rating breakdown ────────────────────────────────────────────

def get_rating_breakdown(store_id: str, period: str = "30d") -> list[dict]:
    conn = get_duckdb_connection()
    start, end = _parse_period(period)
    rows = conn.execute(
        """SELECT rating, COUNT(*) as count, AVG(sentiment_score) as avg_sent
           FROM reviews WHERE store_id = ? AND rating IS NOT NULL
             AND review_date >= ? AND review_date <= ?
           GROUP BY rating ORDER BY rating DESC""",
        [store_id, str(start), str(end)],
    ).fetchall()
    return [
        {"rating": int(r[0]), "count": int(r[1]),
         "avg_sentiment": round(float(r[2] or 0), 3)}
        for r in rows
    ]


# ── Sentiment trend over time ──────────────────────────────────

def get_sentiment_trend(store_id: str, period: str = "30d") -> list[dict]:
    """Daily sentiment score + review count over time."""
    conn = get_duckdb_connection()
    start, end = _parse_period(period)
    rows = conn.execute(
        """SELECT review_date::DATE as day,
                  COUNT(*) as count,
                  AVG(sentiment_score) as avg_score,
                  COUNT(CASE WHEN sentiment_label = 'positive' THEN 1 END) as pos,
                  COUNT(CASE WHEN sentiment_label = 'negative' THEN 1 END) as neg
           FROM reviews WHERE store_id = ?
             AND review_date >= ? AND review_date <= ?
           GROUP BY day ORDER BY day""",
        [store_id, str(start), str(end)],
    ).fetchall()
    return [
        {
            "date": str(r[0]),
            "count": int(r[1]),
            "avg_score": round(float(r[2] or 0), 3),
            "positive": int(r[3]),
            "negative": int(r[4]),
        }
        for r in rows
    ]


# ── Recent reviews ──────────────────────────────────────────────

def get_recent_reviews(store_id: str, period: str = "30d", limit: int = 50) -> list[dict]:
    conn = get_duckdb_connection()
    start, end = _parse_period(period)
    rows = conn.execute(
        """SELECT review_id, product_id, rating, review_text,
                  sentiment_score, sentiment_label, review_date
           FROM reviews WHERE store_id = ?
             AND review_date >= ? AND review_date <= ?
           ORDER BY review_date DESC LIMIT ?""",
        [store_id, str(start), str(end), limit],
    ).fetchall()
    return [
        {
            "review_id": r[0],
            "product_id": r[1],
            "rating": int(r[2]) if r[2] else None,
            "text": (r[3][:200] + "...") if r[3] and len(r[3]) > 200 else r[3],
            "sentiment_score": round(float(r[4]), 3) if r[4] else None,
            "sentiment_label": r[5],
            "date": str(r[6]),
        }
        for r in rows
    ]


# ── Products needing attention ──────────────────────────────────

def get_products_needing_attention(store_id: str, period: str = "30d", limit: int = 10) -> list[dict]:
    conn = get_duckdb_connection()
    start, end = _parse_period(period)
    rows = conn.execute(
        """SELECT product_id, COUNT(*) as review_count,
                  AVG(sentiment_score) as avg_sentiment, AVG(rating) as avg_rating
           FROM reviews WHERE store_id = ? AND product_id IS NOT NULL
             AND review_date >= ? AND review_date <= ?
           GROUP BY product_id
           HAVING COUNT(*) >= 2
           ORDER BY avg_sentiment ASC LIMIT ?""",
        [store_id, str(start), str(end), limit],
    ).fetchall()
    return [
        {
            "product_id": r[0],
            "review_count": int(r[1]),
            "avg_sentiment": round(float(r[2] or 0), 3),
            "avg_rating": round(float(r[3] or 0), 1),
        }
        for r in rows
    ]


# ── Keyword extraction ──────────────────────────────────────────

STOP_WORDS = {
    "the", "a", "an", "is", "it", "i", "my", "we", "to", "and", "of",
    "in", "for", "on", "was", "this", "that", "with", "but", "not", "have",
    "had", "has", "so", "just", "very", "are", "be", "been", "were", "they",
    "them", "from", "as", "at", "or", "by", "do", "did", "no", "all", "one",
    "would", "will", "can", "could", "if", "than", "its", "me", "you", "your",
    "also", "more", "some", "out", "up", "what", "when", "which", "who", "how",
    "about", "after", "our", "got", "get", "really", "much", "even", "like",
    "there", "their", "these", "those", "other", "only", "over", "any",
}

_WORD_RE = re.compile(r"[a-z]{3,}")


def get_top_keywords(store_id: str, period: str = "30d", top_n: int = 15) -> dict:
    """Extract most common words from positive and negative reviews."""
    conn = get_duckdb_connection()
    start, end = _parse_period(period)

    def _extract(label: str) -> list[dict]:
        rows = conn.execute(
            """SELECT review_text FROM reviews
               WHERE store_id = ? AND sentiment_label = ? AND review_text IS NOT NULL
                 AND review_date >= ? AND review_date <= ?
               LIMIT 500""",
            [store_id, label, str(start), str(end)],
        ).fetchall()
        counter: Counter[str] = Counter()
        for (text,) in rows:
            words = _WORD_RE.findall(text.lower())
            counter.update(w for w in words if w not in STOP_WORDS)
        return [{"word": w, "count": c} for w, c in counter.most_common(top_n)]

    return {
        "positive_keywords": _extract("positive"),
        "negative_keywords": _extract("negative"),
    }


# ── Analyze unscored reviews ───────────────────────────────────

def analyze_unscored_reviews(store_id: str, limit: int = 100) -> dict:
    """Analyze reviews that don't yet have sentiment scores.
    Uses batched inference with transformer when available for speed."""
    conn = get_duckdb_connection()

    rows = conn.execute(
        """SELECT review_id, review_text FROM reviews
           WHERE store_id = ? AND sentiment_score IS NULL AND review_text IS NOT NULL
           LIMIT ?""",
        [store_id, limit],
    ).fetchall()

    if not rows:
        return {"analyzed": 0, "message": "No unscored reviews found"}

    if _HAS_TRANSFORMER and _sentiment_pipeline is not None:
        return _batch_analyze_transformer(conn, store_id, rows)

    analyzed = 0
    for review_id, text in rows:
        score, label = _analyze_text(text)
        conn.execute(
            """UPDATE reviews SET sentiment_score = ?, sentiment_label = ?
               WHERE store_id = ? AND review_id = ?""",
            [score, label, store_id, review_id],
        )
        analyzed += 1

    engine_name = "transformer" if _HAS_TRANSFORMER else ("textblob" if _HAS_TEXTBLOB else "keyword")
    return {"analyzed": analyzed, "engine": engine_name, "message": f"Analyzed {analyzed} reviews"}


def _batch_analyze_transformer(conn, store_id: str, rows: list) -> dict:
    """Batch-process reviews through the transformer pipeline."""
    review_ids = [r[0] for r in rows]
    texts = [r[1][:512] for r in rows]

    try:
        results = _sentiment_pipeline(texts, batch_size=32)
    except Exception as exc:
        logger.warning("Batch transformer failed, falling back to single: %s", exc)
        analyzed = 0
        for review_id, text in rows:
            score, label = _analyze_text(text)
            conn.execute(
                """UPDATE reviews SET sentiment_score = ?, sentiment_label = ?
                   WHERE store_id = ? AND review_id = ?""",
                [score, label, store_id, review_id],
            )
            analyzed += 1
        return {"analyzed": analyzed, "engine": "transformer", "message": f"Analyzed {analyzed} reviews"}

    analyzed = 0
    for review_id, result in zip(review_ids, results):
        hf_label = result["label"]
        confidence = float(result["score"])
        if hf_label == "POSITIVE":
            score = 0.5 + confidence * 0.5
        else:
            score = 0.5 - confidence * 0.5

        if score >= 0.6:
            label = "positive"
        elif score <= 0.4:
            label = "negative"
        else:
            label = "neutral"

        conn.execute(
            """UPDATE reviews SET sentiment_score = ?, sentiment_label = ?
               WHERE store_id = ? AND review_id = ?""",
            [round(score, 3), label, store_id, review_id],
        )
        analyzed += 1

    return {"analyzed": analyzed, "engine": "transformer", "message": f"Analyzed {analyzed} reviews with transformer"}


# ── Text analysis helpers ───────────────────────────────────────

def _analyze_text(text: str) -> tuple[float, str]:
    """Analyze sentiment of a text. Returns (score, label).
    Priority: transformer (distilbert) → TextBlob → keyword fallback."""
    if _HAS_TRANSFORMER and _sentiment_pipeline is not None:
        try:
            result = _sentiment_pipeline(text[:512])[0]
            hf_label = result["label"]  # POSITIVE or NEGATIVE
            confidence = float(result["score"])  # 0..1
            if hf_label == "POSITIVE":
                score = 0.5 + confidence * 0.5  # Map to 0.5..1.0
            else:
                score = 0.5 - confidence * 0.5  # Map to 0.0..0.5
        except Exception:
            score = _textblob_or_keyword(text)
    else:
        score = _textblob_or_keyword(text)

    if score >= 0.6:
        label = "positive"
    elif score <= 0.4:
        label = "negative"
    else:
        label = "neutral"

    return round(score, 3), label


def _textblob_or_keyword(text: str) -> float:
    if _HAS_TEXTBLOB:
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity  # -1 to 1
        return (polarity + 1) / 2  # Normalize to 0-1
    return _keyword_sentiment(text)


POSITIVE_WORDS = {
    "great", "excellent", "amazing", "love", "perfect", "best", "good",
    "wonderful", "fantastic", "happy", "satisfied", "recommend", "quality",
    "awesome", "beautiful", "fast", "easy", "comfortable", "nice", "superb",
}

NEGATIVE_WORDS = {
    "bad", "terrible", "awful", "worst", "hate", "poor", "broken",
    "disappointed", "horrible", "defective", "cheap", "waste", "slow",
    "uncomfortable", "useless", "never", "return", "refund", "ugly", "wrong",
}


def _keyword_sentiment(text: str) -> float:
    """Simple keyword-based sentiment fallback."""
    words = set(text.lower().split())
    pos = len(words & POSITIVE_WORDS)
    neg = len(words & NEGATIVE_WORDS)
    total = pos + neg
    if total == 0:
        return 0.5
    return pos / total


# ── Engine status ───────────────────────────────────────────────

def get_sentiment_engine_status() -> dict:
    """Report which sentiment analysis engine is active."""
    if _HAS_TRANSFORMER:
        engine = "transformer"
        model = "distilbert-base-uncased-finetuned-sst-2-english"
    elif _HAS_TEXTBLOB:
        engine = "textblob"
        model = None
    else:
        engine = "keyword"
        model = None

    return {
        "engine": engine,
        "model": model,
        "transformer_available": _HAS_TRANSFORMER,
        "textblob_available": _HAS_TEXTBLOB,
    }
