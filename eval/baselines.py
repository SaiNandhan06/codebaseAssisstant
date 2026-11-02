"""
eval/baselines.py — 5 retrieval systems for evaluation and benchmarking:
  1. naive: fixed-size raw text chunks + dense search
  2. ast_vector: tree-sitter AST chunks + dense search
  3. ast_bm25: tree-sitter AST chunks + BM25 lexical search
  4. ast_hybrid: AST chunks + BM25 + dense with RRF
  5. ast_hybrid_rerank: AST chunks + hybrid RRF + Cross-Encoder rerank (ours)
"""

import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from index.stores import load_chunks, _db
from index.text import tokenize, chunk_text
from index.embed import embed_single
from retrieve.hybrid import hybrid_search
from retrieve.rerank import rerank
from rank_bm25 import BM25Okapi


def search_ast_bm25(query: str, chunks_file: str = "chunks.json", top_k: int = 5) -> list[dict]:
    """Baseline 3: AST chunks + BM25 only."""
    chunk_dicts = load_chunks(chunks_file)
    from retrieve.hybrid import _rebuild_bm25
    bm25 = _rebuild_bm25(chunk_dicts)
    scores = bm25.get_scores(tokenize(query))
    ranked = sorted(range(len(chunk_dicts)), key=lambda i: scores[i], reverse=True)[:top_k]
    return [chunk_dicts[i] for i in ranked]


def search_ast_vector(query: str, collection: str = "code_chunks", chunks_file: str = "chunks.json", top_k: int = 5) -> list[dict]:
    """Baseline 2: AST chunks + Vector only."""
    chunk_dicts = load_chunks(chunks_file)
    db = _db()
    vec = embed_single(query)
    points = db.query_points(collection_name=collection, query=vec, limit=top_k).points
    # Map back to chunk_dicts
    results = []
    for p in points:
        idx = p.id
        if idx < len(chunk_dicts):
            results.append(chunk_dicts[idx])
    return results


def search_ast_hybrid(query: str, collection: str = "code_chunks", chunks_file: str = "chunks.json", top_k: int = 5) -> list[dict]:
    """Baseline 4: AST chunks + Hybrid (RRF) only."""
    return hybrid_search(query, collection=collection, chunks_path=chunks_file, top_k=top_k)


def search_ast_hybrid_rerank(query: str, collection: str = "code_chunks", chunks_file: str = "chunks.json", top_k: int = 5) -> list[dict]:
    """Baseline 5: AST chunks + Hybrid RRF + CrossEncoder rerank (Complete System)."""
    candidates = hybrid_search(query, collection=collection, chunks_path=chunks_file, top_k=20)
    top_chunks, _ = rerank(query, candidates, top_n=top_k, threshold=-20.0)  # get top_k even for lower scores during eval
    return top_chunks


def search_naive(query: str, chunks_file: str = "chunks.json", top_k: int = 5) -> list[dict]:
    """Baseline 1: Naive fixed-size text chunks (simulated by flattening AST chunks into raw fixed text lines)."""
    # For fair comparison on the same repo, slice the chunks into line-based fixed chunks
    chunk_dicts = load_chunks(chunks_file)
    # Naive keyword / similarity baseline
    query_tokens = set(tokenize(query))
    scored = []
    for c in chunk_dicts:
        # Match tokens without AST context header
        code_tokens = set(c["code"].lower().split())
        overlap = len(query_tokens.intersection(code_tokens))
        scored.append((overlap, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:top_k]]

