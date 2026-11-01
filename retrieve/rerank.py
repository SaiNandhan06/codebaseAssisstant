"""
Cross-encoder reranker: loads the model once at import, then reranks
candidate chunks by relevance to the query.

Includes a configurable low-confidence threshold: if the best rerank
score is below it, the result is flagged and an empty list is returned.
"""

import os
from sentence_transformers import CrossEncoder

# ── Model (loaded once at import) ─────────────────────────────────

RERANK_MODEL = os.getenv("RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L6-v2")
_reranker: CrossEncoder | None = None


def _get_reranker() -> CrossEncoder:
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoder(RERANK_MODEL)
    return _reranker


# ── Config ────────────────────────────────────────────────────────

LOW_CONFIDENCE_THRESHOLD = float(os.getenv("RERANK_THRESHOLD", "0.5"))


# ── Public API ────────────────────────────────────────────────────

def rerank(
    query: str,
    chunks: list[dict],
    top_n: int = 5,
    threshold: float | None = None,
) -> tuple[list[dict], bool]:
    """
    Rerank chunk dicts by cross-encoder relevance to the query.

    Returns:
        (top_n_chunks, low_confidence)
        If the best rerank score < threshold → low_confidence=True and chunks=[].
    """
    if threshold is None:
        threshold = LOW_CONFIDENCE_THRESHOLD

    reranker = _get_reranker()
    pairs = [(query, c["code"]) for c in chunks]
    scores = reranker.predict(pairs)

    # Attach rerank scores
    scored = []
    for score, chunk in zip(scores, chunks):
        cd = chunk.copy()
        cd["rerank_score"] = float(score)
        scored.append(cd)

    scored.sort(key=lambda c: c["rerank_score"], reverse=True)

    # Low-confidence check
    if scored and scored[0]["rerank_score"] < threshold:
        return [], True

    return scored[:top_n], False

