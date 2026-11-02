"""
Embedding helper: batched Gemini embeddings with retry + disk cache.

The cache avoids re-embedding unchanged chunks across runs, saving API quota.
"""

import hashlib
import json
import os
import re
import time

from dotenv import load_dotenv
from google import genai

load_dotenv()

_client = genai.Client()

EMBED_MODEL = os.getenv("EMBED_MODEL", "gemini-embedding-001")
EMBED_DIM = 3072          # gemini-embedding-001 output dimension
BATCH_SIZE = 100          # Gemini batch limit
MAX_RETRIES = 5
RETRY_BASE = 2            # exponential back-off base (seconds)

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "embed_cache")


def _cache_key(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _cache_path(key: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"{key}.json")


def _load_cached(key: str):
    path = _cache_path(key)
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return None


def _save_cache(key: str, vector: list[float]):
    path = _cache_path(key)
    with open(path, "w") as f:
        json.dump(vector, f)


def _calc_retry_delay(e: Exception, attempt: int) -> float:
    """Calculate back-off delay, honoring 429 quota retry-after suggestions if present."""
    msg = str(e)
    if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
        match = re.search(r"retry in ([\d\.]+)s", msg)
        if match:
            return float(match.group(1)) + 1.0
        match = re.search(r"retryDelay':\s*'(\d+)s'", msg)
        if match:
            return float(match.group(1)) + 1.0
        return max(32.0, RETRY_BASE ** (attempt + 1))
    return float(RETRY_BASE ** (attempt + 1))


def embed_single(text: str) -> list[float]:
    """Embed a single text string, with caching and retry."""
    key = _cache_key(text)
    cached = _load_cached(key)
    if cached is not None:
        return cached

    for attempt in range(MAX_RETRIES):
        try:
            result = _client.models.embed_content(
                model=EMBED_MODEL,
                contents=text,
            )
            vec = result.embeddings[0].values
            _save_cache(key, vec)
            return vec
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                raise
            wait = _calc_retry_delay(e, attempt)
            print(f"  Embed retry {attempt+1}/{MAX_RETRIES} after {wait:.1f}s: {e}")
            time.sleep(wait)


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts in batches, using the disk cache for each.

    Returns a list of vectors in the same order as *texts*.
    """
    results: list[list[float] | None] = [None] * len(texts)

    # Check cache first
    to_embed: list[tuple[int, str]] = []  # (original_index, text)
    for i, text in enumerate(texts):
        key = _cache_key(text)
        cached = _load_cached(key)
        if cached is not None:
            results[i] = cached
        else:
            to_embed.append((i, text))

    if not to_embed:
        return results  # all cached

    # Batch embed the misses
    for batch_start in range(0, len(to_embed), BATCH_SIZE):
        batch = to_embed[batch_start: batch_start + BATCH_SIZE]
        batch_texts = [t for _, t in batch]

        for attempt in range(MAX_RETRIES):
            try:
                result = _client.models.embed_content(
                    model=EMBED_MODEL,
                    contents=batch_texts,
                )
                for j, emb in enumerate(result.embeddings):
                    orig_idx = batch[j][0]
                    vec = emb.values
                    results[orig_idx] = vec
                    _save_cache(_cache_key(batch_texts[j]), vec)
                break
            except Exception as e:
                if attempt == MAX_RETRIES - 1:
                    raise
                wait = _calc_retry_delay(e, attempt)
                print(f"  Batch embed retry {attempt+1}/{MAX_RETRIES} after {wait:.1f}s: {e}")
                time.sleep(wait)

        # Small pause between batches to stay under rate limits
        if batch_start + BATCH_SIZE < len(to_embed):
            time.sleep(0.5)

    return results

