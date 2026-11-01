"""
Text processing utilities for chunk indexing.

- context_header: builds a human-readable header for each chunk
  (used as prefix before the raw code when embedding/searching)
- tokenize: sub-word tokenizer that splits snake_case / camelCase
  identifiers so BM25 can match partial names
"""

import re


def context_header(chunk) -> str:
    """Build a short context string prepended to chunk code for embedding.

    Example output:
        python | class ShoppingCart | method add_item
        samples/sample_class.py  lines 5-6
    """
    parts = [chunk.language]
    if chunk.parent:
        parts.append(f"class {chunk.parent}")
    parts.append(f"{chunk.kind} {chunk.name}")
    header = " | ".join(parts)
    loc = f"{chunk.file_path}  lines {chunk.start_line}-{chunk.end_line}"
    return f"{header}\n{loc}"


def chunk_text(chunk) -> str:
    """Full text representation used for both embedding and BM25."""
    return f"{context_header(chunk)}\n\n{chunk.code}"


# ── Sub-word tokenizer ────────────────────────────────────────────

_CAMEL_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")  # split camelCase
_SEP_RE = re.compile(r"[_\-./\\]+")                 # split snake_case & paths
_WORD_RE = re.compile(r"[a-z0-9]+")                  # final token extraction


def tokenize(text: str) -> list[str]:
    """Tokenize text for BM25, splitting camelCase and snake_case identifiers.

    >>> tokenize("calculateTotal  get_user_name")
    ['calculate', 'total', 'get', 'user', 'name', 'calculatetotal', 'get_user_name']
    """
    text_lower = text.lower()
    # Split camelCase before lowering
    expanded = _CAMEL_RE.sub(" ", text)
    # Split on underscores/separators
    expanded = _SEP_RE.sub(" ", expanded)
    # Extract atomic words
    atoms = _WORD_RE.findall(expanded.lower())

    # Also keep the original unsplit tokens for exact-match boost
    originals = _WORD_RE.findall(_SEP_RE.sub(" ", text_lower))

    # Combine: atoms first (for sub-word matching), then originals (for exact)
    seen = set()
    tokens = []
    for t in atoms + originals:
        if t not in seen:
            seen.add(t)
            tokens.append(t)
    return tokens

