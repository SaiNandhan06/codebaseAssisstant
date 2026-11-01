"""
Storage layer: Qdrant vector store + BM25 index builder + chunks.json persistence.
"""

import json
import os

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from rank_bm25 import BM25Okapi

from .embed import EMBED_DIM, embed_batch
from .text import chunk_text, tokenize

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION = os.getenv("QDRANT_COLLECTION", "code_chunks")
QDRANT_MODE = os.getenv("QDRANT_MODE", "auto")  # "server", "local", or "auto"

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
QDRANT_LOCAL_DIR = os.path.join(DATA_DIR, "qdrant_local")

_qdrant_instance = None


def _db():
    """Get Qdrant client, auto-detecting server vs local mode."""
    global _qdrant_instance
    if _qdrant_instance is not None:
        return _qdrant_instance

    mode = QDRANT_MODE

    if mode == "server":
        _qdrant_instance = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        return _qdrant_instance

    if mode == "local":
        os.makedirs(QDRANT_LOCAL_DIR, exist_ok=True)
        _qdrant_instance = QdrantClient(path=QDRANT_LOCAL_DIR)
        return _qdrant_instance

    # auto: try server first, fall back to local
    try:
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=3)
        client.get_collections()  # test connection
        _qdrant_instance = client
        print(f"  Qdrant: connected to server at {QDRANT_HOST}:{QDRANT_PORT}")
    except Exception:
        os.makedirs(QDRANT_LOCAL_DIR, exist_ok=True)
        _qdrant_instance = QdrantClient(path=QDRANT_LOCAL_DIR)
        print(f"  Qdrant: using local storage at {QDRANT_LOCAL_DIR}")

    return _qdrant_instance


# ── Qdrant helpers ────────────────────────────────────────────────

def store_vectors(chunks, collection: str = COLLECTION):
    """Embed all chunks and upsert into Qdrant.  Returns the number of points stored."""
    db = _db()

    texts = [chunk_text(c) for c in chunks]
    print(f"  Embedding {len(texts)} chunks …")
    vectors = embed_batch(texts)

    # (Re)create collection
    if db.collection_exists(collection):
        db.delete_collection(collection)
    db.create_collection(
        collection_name=collection,
        vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
    )

    # Build points
    points = []
    for i, (chunk, vec) in enumerate(zip(chunks, vectors)):
        points.append(PointStruct(
            id=i,
            vector=vec,
            payload={
                "chunk_id": chunk.id,
                "file_path": chunk.file_path,
                "language": chunk.language,
                "kind": chunk.kind,
                "name": chunk.name,
                "parent": chunk.parent,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
            },
        ))

    # Upsert in batches of 100
    batch_size = 100
    for start in range(0, len(points), batch_size):
        db.upsert(collection_name=collection, points=points[start:start + batch_size])

    print(f"  Stored {len(points)} vectors in Qdrant collection '{collection}'")
    return len(points)


# ── BM25 builder ──────────────────────────────────────────────────

def build_bm25(chunks) -> BM25Okapi:
    """Build and return a BM25 index from chunk texts using the sub-word tokenizer."""
    corpus = [tokenize(chunk_text(c)) for c in chunks]
    return BM25Okapi(corpus)


# ── Chunks JSON persistence ──────────────────────────────────────

def save_chunks(chunks, filename: str = "chunks.json"):
    """Serialize chunks to data/chunks.json for BM25 rebuild at query time."""
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, filename)
    data = [c.to_dict() for c in chunks]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  Saved {len(data)} chunks to {path}")
    return path


def load_chunks(filename: str = "chunks.json"):
    """Load chunks from data/chunks.json.  Returns a list of dicts."""
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

