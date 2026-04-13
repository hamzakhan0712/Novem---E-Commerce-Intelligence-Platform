"""
Spell corrector for copilot questions — domain-specific fuzzy matching.

Uses a curated e-commerce/analytics dictionary with Levenshtein distance
to correct typos before pattern matching and RAG keyword extraction.
No external dependencies required.
"""

import re


# ── Domain Dictionary ───────────────────────────────────────────
# ~120 business terms that cover the copilot's vocabulary.
# Only words ≥ 3 chars are checked; short tokens are left alone.

DOMAIN_DICTIONARY: frozenset[str] = frozenset({
    # Core metrics
    "revenue", "sales", "orders", "customers", "products", "average",
    "total", "monthly", "weekly", "daily", "trend", "growth", "count",
    "value", "amount", "number", "rate", "percentage", "ratio",

    # Time
    "today", "yesterday", "week", "month", "year", "quarter",
    "recent", "latest", "last", "first", "period", "date",

    # Analytics
    "refund", "refunds", "refunded", "discount", "discounts",
    "retention", "churn", "segment", "segments", "forecast",
    "anomaly", "anomalies", "sentiment", "rating", "ratings",
    "review", "reviews", "conversion", "lifetime",

    # E-commerce
    "category", "categories", "channel", "channels", "region",
    "inventory", "stock", "margin", "margins", "profit", "profits",
    "campaign", "campaigns", "spend", "spending",
    "repeat", "returning", "loyal", "loyalty",
    "order", "customer", "product", "item", "items",

    # Descriptors
    "best", "worst", "selling", "top", "bottom", "highest", "lowest",
    "biggest", "smallest", "most", "least", "many", "much",
    "earning", "made", "earned", "spent", "bought", "purchased",
    "spenders", "buyers", "sellers",

    # Actions / question words
    "show", "tell", "give", "list", "find", "compare", "explain",
    "what", "which", "where", "when", "why", "how", "who", "whose",
    "does", "have", "whats", "hows",

    # Business health
    "health", "score", "driver", "drivers", "cause", "causes",
    "decline", "drop", "increase", "spike", "opportunity",
    "missed", "recommend", "action", "actions", "insight", "insights",

    # Status
    "cancelled", "canceled", "completed", "pending", "shipped",
    "delivered", "processing", "active", "inactive",

    # Misc
    "breakdown", "distribution", "performance", "summary", "overview",
    "analysis", "report", "versus", "between", "across",
    "new", "old", "current", "previous", "next",
})

# Pre-sorted by length for efficient matching
_SORTED_DICT = sorted(DOMAIN_DICTIONARY, key=len)

# Words to never touch (common English + short words)
_SKIP_WORDS: frozenset[str] = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "do", "did",
    "my", "me", "we", "us", "it", "in", "on", "to", "of", "or",
    "and", "but", "not", "no", "so", "if", "up", "at", "by", "as",
    "for", "has", "had", "its", "ive", "im", "id",
})


def _levenshtein(a: str, b: str) -> int:
    """Edit distance between two strings (Wagner–Fischer algorithm)."""
    if len(a) < len(b):
        return _levenshtein(b, a)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            cost = 0 if ca == cb else 1
            curr.append(min(
                curr[j] + 1,       # insert
                prev[j + 1] + 1,   # delete
                prev[j] + cost,    # substitute
            ))
        prev = curr
    return prev[-1]


def _best_match(token: str, max_distance: int = 2) -> str:
    """Find the closest dictionary word within max_distance, or return the token unchanged."""
    token_len = len(token)
    best = token
    best_dist = max_distance + 1

    for word in _SORTED_DICT:
        # Quick length pre-filter — if lengths differ by more than max_distance, skip
        if abs(len(word) - token_len) > max_distance:
            continue
        # Quick first-char heuristic — if first chars differ, need at least dist 1
        dist = _levenshtein(token, word)
        if dist < best_dist:
            best_dist = dist
            best = word
            if dist == 0:
                break  # exact match

    return best


def correct_question(question: str) -> str:
    """Correct spelling in a business question using the domain dictionary.

    Returns the corrected question (lowercased). Only tokens of length ≥ 3
    that aren't already in the dictionary are candidates for correction.
    """
    tokens = re.findall(r"[a-zA-Z]+|[^\s]+", question.lower())
    corrected: list[str] = []

    for token in tokens:
        # Skip short words, numbers, punctuation, and known words
        if (
            len(token) <= 2
            or token in _SKIP_WORDS
            or token in DOMAIN_DICTIONARY
            or not token.isalpha()
        ):
            corrected.append(token)
            continue

        # Allow max distance based on word length
        max_dist = 1 if len(token) <= 4 else 2
        fixed = _best_match(token, max_dist)
        corrected.append(fixed)

    return " ".join(corrected)
