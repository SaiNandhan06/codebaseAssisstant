"""
Hybrid retrieval: BM25 + Qdrant dense search fused with Reciprocal Rank Fusion (RRF).

hybrid_search(query, collection, chunks_path) → top-k Chunk dicts with scores.
"""

import os
import logging

from qdrant_client import QdrantClient
from rank_bm25 import BM25Okapi

from index.text import tokenize, chunk_text
from index.embed import embed_single
from index.stores import load_chunks, _db

logger = logging.getLogger(__name__)

RRF_K = 60  # RRF smoothing constant


def _rebuild_bm25(chunk_dicts: list[dict]):
    """Rebuild BM25 from chunk dicts (loaded from chunks.json)."""
    from ingest.parse import Chunk
    corpus = []
    for cd in chunk_dicts:
        # Reconstruct minimal Chunk for chunk_text()
        c = Chunk(
            id=cd["id"],
            file_path=cd["file_path"],
            language=cd["language"],
            kind=cd["kind"],
            name=cd["name"],
            parent=cd.get("parent"),
            start_line=cd["start_line"],
            end_line=cd["end_line"],
            code=cd["code"],
            commits=cd.get("commits", []),
        )
        corpus.append(tokenize(chunk_text(c)))
    return BM25Okapi(corpus)


def hybrid_search(
    query: str,
    collection: str = "code_chunks",
    chunks_path: str = "chunks.json",
    top_k: int = 20,
    rrf_k: int = RRF_K,
) -> list[dict]:
    """
    Hybrid BM25 + dense retrieval with RRF fusion.

    Returns top_k chunk dicts, each augmented with:
      - rrf_score
      - bm25_rank
      - dense_rank
    """
    # Load persisted chunks
    chunk_dicts = load_chunks(chunks_path)

    # ── BM25 ranking ──────────────────────────────────────────────
    bm25 = _rebuild_bm25(chunk_dicts)
    query_tokens = tokenize(query)
    bm25_scores = bm25.get_scores(query_tokens)
    bm25_ranked = sorted(range(len(chunk_dicts)), key=lambda i: bm25_scores[i], reverse=True)
    bm25_rank_of = {idx: rank for rank, idx in enumerate(bm25_ranked)}

    # ── Dense ranking (Qdrant) ────────────────────────────────────
    dense_rank_of = {}
    try:
        db = _db()
        if not db.collection_exists(collection):
            from index.stores import store_vectors
            logger.info(f"Collection '{collection}' not found in Qdrant. Auto-populating from {chunks_path}...")
            store_vectors(chunk_dicts, collection=collection)

        if db.collection_exists(collection):
            query_vector = embed_single(query)
            dense_results = db.query_points(
                collection_name=collection,
                query=query_vector,
                limit=len(chunk_dicts),
            ).points
            dense_rank_of = {r.id: rank for rank, r in enumerate(dense_results)}
    except Exception as e:
        logger.warning(f"Dense search warning for '{collection}': {e}. Continuing with BM25.")

    # ── RRF fusion ────────────────────────────────────────────────
    rrf_scores = {}
    for idx in range(len(chunk_dicts)):
        score = 0.0
        if idx in bm25_rank_of:
            score += 1.0 / (rrf_k + bm25_rank_of[idx])
        if idx in dense_rank_of:
            score += 1.0 / (rrf_k + dense_rank_of[idx])
        rrf_scores[idx] = score

    # Sort by RRF score descending
    ranked = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

    # Build results
    results = []
    for idx, rrf_score in ranked:
        cd = chunk_dicts[idx].copy()
        cd["rrf_score"] = rrf_score
        cd["bm25_rank"] = bm25_rank_of.get(idx, -1)
        cd["dense_rank"] = dense_rank_of.get(idx, -1)
        results.append(cd)

    return results

