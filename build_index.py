"""
build_index.py — Full indexing pipeline: ingest → embed → store.

Usage:
    python build_index.py <repo_path>
    python build_index.py .              # index current directory
    python build_index.py samples        # index the samples folder

This script:
  1. Collects code chunks via tree-sitter (ingest/)
  2. Attaches git commit history to each chunk
  3. Embeds all chunks using Gemini (with disk cache)
  4. Stores vectors in Qdrant
  5. Saves chunks.json for BM25 rebuild at query time
"""

import os
import sys
import time
from collections import Counter

from ingest.pipeline import collect_chunks
from ingest.git_history import attach_history
from index.text import chunk_text
from index.stores import store_vectors, build_bm25, save_chunks


def main():
    repo_path = sys.argv[1] if len(sys.argv) > 1 else "."
    repo_path = os.path.abspath(repo_path)

    if not os.path.isdir(repo_path):
        sys.exit(f"Error: '{repo_path}' is not a folder")

    print(f"═══ build_index.py ═══")
    print(f"Repo path: {repo_path}\n")

    # ── Step 1: Ingest ────────────────────────────────────────────
    t0 = time.time()
    print("Step 1: Collecting chunks …")
    chunks, skipped = collect_chunks(repo_path)
    attach_history(chunks, repo_path)
    t1 = time.time()

    print(f"  Chunks: {len(chunks)}")
    print(f"  By kind: {dict(Counter(c.kind for c in chunks))}")
    print(f"  By language: {dict(Counter(c.language for c in chunks))}")
    print(f"  Skipped: {len(skipped)} files")
    for path, reason in skipped:
        print(f"    - {path}: {reason}")
    print(f"  Ingestion time: {t1-t0:.1f}s\n")

    if not chunks:
        sys.exit("No chunks found — nothing to index.")

    # ── Step 2: Save chunks.json ──────────────────────────────────
    print("Step 2: Saving chunks.json …")
    save_chunks(chunks)

    # ── Step 3: Build BM25 (sanity check) ─────────────────────────
    print("\nStep 3: Building BM25 index …")
    bm25 = build_bm25(chunks)
    print(f"  BM25 corpus size: {bm25.corpus_size}")

    # ── Step 4: Embed + store in Qdrant ───────────────────────────
    print("\nStep 4: Embedding and storing in Qdrant …")
    t2 = time.time()
    n = store_vectors(chunks)
    t3 = time.time()
    print(f"  Embedding + storage time: {t3-t2:.1f}s")

    # ── Done ──────────────────────────────────────────────────────
    print(f"\n═══ Done! {n} chunks indexed in {t3-t0:.1f}s total ═══")


if __name__ == "__main__":
    main()

