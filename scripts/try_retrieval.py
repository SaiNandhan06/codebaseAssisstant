"""
try_retrieval.py — CLI to test the full hybrid retrieval + rerank pipeline.

Usage:
    python scripts/try_retrieval.py "How does the shopping cart calculate totals?"
"""

import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from retrieve.hybrid import hybrid_search
from retrieve.rerank import rerank


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/try_retrieval.py \"your question here\"")
        sys.exit(1)

    query = sys.argv[1]
    collection = os.getenv("QDRANT_COLLECTION", "code_chunks")

    print(f"Query: {query}\n")
    print("Step 1: Hybrid search (BM25 + dense, RRF fusion) → top 20")
    print("─" * 60)

    candidates = hybrid_search(query, collection=collection, top_k=20)
    for i, c in enumerate(candidates[:10]):  # show top 10
        print(f"  #{i+1:2d}  RRF={c['rrf_score']:.4f}  "
              f"BM25_rank={c['bm25_rank']:2d}  "
              f"Dense_rank={c['dense_rank']:2d}  "
              f"[{c['kind']}] {c['name']}  "
              f"{c['file_path']}:{c['start_line']}-{c['end_line']}")

    print(f"\nStep 2: Cross-encoder rerank → top 5")
    print("─" * 60)

    top_chunks, low_confidence = rerank(query, candidates, top_n=5)

    if low_confidence:
        print("  ⚠ LOW CONFIDENCE: best rerank score below threshold.")
        print("  Not enough evidence in the codebase to answer this question.")
        return

    for i, c in enumerate(top_chunks):
        print(f"  #{i+1}  rerank={c['rerank_score']:.4f}  "
              f"[{c['kind']}] {c['name']}  "
              f"{c['file_path']}:{c['start_line']}-{c['end_line']}")
        print(f"       Code: {c['code'][:100]}...")
        print()


if __name__ == "__main__":
    main()

