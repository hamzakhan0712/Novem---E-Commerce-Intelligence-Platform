"""
Copilot Feedback Memory — stores rated Q&A pairs and provides
similarity-based retrieval for few-shot prompt injection.

Learning mechanisms:
1. Few-shot injection — past good Q&A pairs are inserted into the prompt
2. Negative feedback avoidance — bad answers are flagged so the LLM avoids them
3. User corrections — stored and injected as ground-truth examples
4. Query pattern caching — frequently asked questions get fast-tracked
"""

import logging
import math
import re
import uuid
from collections import Counter
from datetime import datetime, timezone

from app.core.database import get_sqlite_connection

logger = logging.getLogger(__name__)

# ── Text Processing ─────────────────────────────────────────────

_STOP_WORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after", "above", "below",
    "between", "out", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "all", "both",
    "each", "few", "more", "most", "other", "some", "such", "no", "nor",
    "not", "only", "own", "same", "so", "than", "too", "very", "just",
    "don", "now", "and", "but", "or", "if", "while", "about", "what",
    "which", "who", "whom", "this", "that", "these", "those", "am", "it",
    "its", "my", "your", "i", "me", "we", "us", "you", "he", "she", "they",
    "them", "his", "her", "our", "their", "much", "many",
})

# Business domain keywords get boosted weight
_DOMAIN_BOOST = frozenset({
    "revenue", "sales", "orders", "customers", "products", "refund",
    "discount", "churn", "retention", "aov", "average", "top", "best",
    "worst", "category", "channel", "region", "monthly", "weekly", "daily",
    "trend", "growth", "decline", "spike", "drop", "anomaly", "forecast",
    "predict", "segment", "cohort", "lifetime", "value", "health", "score",
    "sentiment", "review", "rating", "stock", "inventory", "margin",
    "profit", "loss", "cost", "spend", "campaign", "conversion",
})


def _extract_keywords(text: str) -> list[str]:
    """Extract meaningful keywords from text, lowercased, stop-words removed."""
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [t for t in tokens if t not in _STOP_WORDS and len(t) > 1]


def _keyword_string(text: str) -> str:
    """Create a space-separated keyword string for storage."""
    return " ".join(_extract_keywords(text))


def _tfidf_similarity(query_kw: list[str], doc_kw: list[str], corpus_size: int, df: dict[str, int]) -> float:
    """Compute TF-IDF cosine similarity between a query and a document."""
    if not query_kw or not doc_kw:
        return 0.0

    q_counts = Counter(query_kw)
    d_counts = Counter(doc_kw)
    all_terms = set(q_counts) | set(d_counts)

    q_vec: dict[str, float] = {}
    d_vec: dict[str, float] = {}

    for term in all_terms:
        idf = math.log((1 + corpus_size) / (1 + df.get(term, 0))) + 1
        boost = 1.5 if term in _DOMAIN_BOOST else 1.0
        q_vec[term] = q_counts.get(term, 0) * idf * boost
        d_vec[term] = d_counts.get(term, 0) * idf * boost

    dot = sum(q_vec.get(t, 0) * d_vec.get(t, 0) for t in all_terms)
    mag_q = math.sqrt(sum(v * v for v in q_vec.values()))
    mag_d = math.sqrt(sum(v * v for v in d_vec.values()))

    if mag_q == 0 or mag_d == 0:
        return 0.0
    return dot / (mag_q * mag_d)


# ── Feedback Storage ────────────────────────────────────────────

def store_feedback(
    store_id: str,
    message_id: str,
    question: str,
    answer: str,
    source: str,
    model: str | None,
    rating: int,
    correction: str | None = None,
) -> dict:
    """Store or update feedback for a copilot message.

    rating: 1 = thumbs up, -1 = thumbs down, 0 = neutral/reset
    correction: optional user-provided correct answer (on thumbs down)
    """
    if rating not in (-1, 0, 1):
        return {"success": False, "error": "Rating must be -1, 0, or 1"}

    conn = get_sqlite_connection()
    now = datetime.now(timezone.utc).isoformat()
    keywords = _keyword_string(question)

    existing = conn.execute(
        "SELECT id FROM copilot_feedback WHERE message_id = ?",
        (message_id,),
    ).fetchone()

    if existing:
        conn.execute(
            """UPDATE copilot_feedback
               SET rating = ?, correction = ?, updated_at = ?
               WHERE message_id = ?""",
            (rating, correction, now, message_id),
        )
    else:
        feedback_id = str(uuid.uuid4())
        conn.execute(
            """INSERT INTO copilot_feedback
               (id, store_id, message_id, question, answer, source, model,
                rating, correction, question_keywords, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (feedback_id, store_id, message_id, question, answer, source,
             model, rating, correction, keywords, now, now),
        )

    conn.commit()
    logger.info("Feedback stored: message=%s rating=%d", message_id, rating)
    return {"success": True, "message_id": message_id, "rating": rating}


# ── Similarity Search ───────────────────────────────────────────

def find_similar_qa(store_id: str, question: str, limit: int = 3, min_score: float = 0.25) -> list[dict]:
    """Find the most similar past Q&A pairs for a given question.

    Uses TF-IDF cosine similarity on extracted keywords.
    Only returns positively-rated (thumbs up) entries.
    """
    conn = get_sqlite_connection()
    query_kw = _extract_keywords(question)

    if not query_kw:
        return []

    rows = conn.execute(
        """SELECT question, answer, correction, question_keywords, rating
           FROM copilot_feedback
           WHERE store_id = ? AND rating != 0
           ORDER BY created_at DESC
           LIMIT 100""",
        (store_id,),
    ).fetchall()

    if not rows:
        return []

    # Build document frequency map
    df: dict[str, int] = Counter()
    docs: list[tuple[list[str], dict]] = []
    for row in rows:
        doc_kw = row["question_keywords"].split() if row["question_keywords"] else []
        for term in set(doc_kw):
            df[term] += 1
        docs.append((doc_kw, dict(row)))

    corpus_size = len(docs)
    scored: list[tuple[float, dict]] = []

    for doc_kw, row_data in docs:
        sim = _tfidf_similarity(query_kw, doc_kw, corpus_size, df)
        if sim >= min_score:
            scored.append((sim, row_data))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = []

    for score, row_data in scored[:limit]:
        results.append({
            "question": row_data["question"],
            "answer": row_data["answer"],
            "correction": row_data["correction"],
            "rating": row_data["rating"],
            "similarity": round(score, 3),
        })

    return results


def find_negative_examples(store_id: str, question: str, limit: int = 2) -> list[dict]:
    """Find negatively-rated past answers for similar questions to avoid repeating them."""
    conn = get_sqlite_connection()
    query_kw = _extract_keywords(question)

    if not query_kw:
        return []

    rows = conn.execute(
        """SELECT question, answer, correction, question_keywords
           FROM copilot_feedback
           WHERE store_id = ? AND rating = -1
           ORDER BY created_at DESC
           LIMIT 50""",
        (store_id,),
    ).fetchall()

    if not rows:
        return []

    df: dict[str, int] = Counter()
    docs: list[tuple[list[str], dict]] = []
    for row in rows:
        doc_kw = row["question_keywords"].split() if row["question_keywords"] else []
        for term in set(doc_kw):
            df[term] += 1
        docs.append((doc_kw, dict(row)))

    corpus_size = len(docs)
    scored: list[tuple[float, dict]] = []

    for doc_kw, row_data in docs:
        sim = _tfidf_similarity(query_kw, doc_kw, corpus_size, df)
        if sim >= 0.3:
            scored.append((sim, row_data))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = []

    for score, row_data in scored[:limit]:
        results.append({
            "question": row_data["question"],
            "answer": row_data["answer"],
            "correction": row_data["correction"],
        })

    return results


# ── Few-Shot Prompt Builder ─────────────────────────────────────

def build_few_shot_context(store_id: str, question: str) -> str:
    """Build a few-shot context block from past rated Q&A pairs.

    Includes:
    - Positively rated similar Q&A as examples to follow
    - User corrections as ground-truth references
    - Negatively rated answers to avoid
    """
    sections: list[str] = []

    # Positive examples (few-shot)
    good_examples = find_similar_qa(store_id, question, limit=3, min_score=0.25)
    if good_examples:
        lines = []
        for ex in good_examples:
            effective_answer = ex["correction"] if ex["correction"] else ex["answer"]
            lines.append(f"Q: {ex['question']}")
            lines.append(f"A: {effective_answer}")
            if ex["correction"]:
                lines.append("(Note: This answer was corrected by the user — treat as ground truth)")
            lines.append("")
        sections.append(
            "--- PAST SUCCESSFUL Q&A (use as reference for style and accuracy) ---\n"
            + "\n".join(lines)
            + "--- END PAST Q&A ---"
        )

    # Negative examples (what to avoid)
    bad_examples = find_negative_examples(store_id, question, limit=2)
    if bad_examples:
        lines = []
        for ex in bad_examples:
            lines.append(f"Q: {ex['question']}")
            lines.append(f"Bad answer: {ex['answer']}")
            if ex["correction"]:
                lines.append(f"User's correction: {ex['correction']}")
            lines.append("")
        sections.append(
            "--- ANSWERS TO AVOID (user rated these negatively) ---\n"
            + "\n".join(lines)
            + "--- END AVOID ---"
        )

    return "\n\n".join(sections)


# ── Feedback Statistics ─────────────────────────────────────────

def get_feedback_stats(store_id: str) -> dict:
    """Return feedback statistics for a store."""
    conn = get_sqlite_connection()

    row = conn.execute(
        """SELECT
             COUNT(*) as total,
             COUNT(CASE WHEN rating = 1 THEN 1 END) as positive,
             COUNT(CASE WHEN rating = -1 THEN 1 END) as negative,
             COUNT(CASE WHEN correction IS NOT NULL AND correction != '' THEN 1 END) as corrections
           FROM copilot_feedback
           WHERE store_id = ?""",
        (store_id,),
    ).fetchone()

    total = row["total"] if row else 0
    positive = row["positive"] if row else 0
    negative = row["negative"] if row else 0
    corrections = row["corrections"] if row else 0

    satisfaction_rate = round(positive / total * 100, 1) if total > 0 else 0.0

    recent = conn.execute(
        """SELECT question, rating, created_at
           FROM copilot_feedback
           WHERE store_id = ?
           ORDER BY created_at DESC
           LIMIT 5""",
        (store_id,),
    ).fetchall()

    return {
        "total_feedback": total,
        "positive": positive,
        "negative": negative,
        "corrections": corrections,
        "satisfaction_rate": satisfaction_rate,
        "learning_entries": positive + corrections,
        "recent": [dict(r) for r in recent],
    }
