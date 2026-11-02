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
    lang = getattr(chunk, "language", None) or (chunk.get("language") if isinstance(chunk, dict) else "unknown")
    parent = getattr(chunk, "parent", None) if hasattr(chunk, "parent") else (chunk.get("parent") if isinstance(chunk, dict) else None)
    kind = getattr(chunk, "kind", None) or (chunk.get("kind") if isinstance(chunk, dict) else "code")
    name = getattr(chunk, "name", None) or (chunk.get("name") if isinstance(chunk, dict) else "")
    file_path = getattr(chunk, "file_path", None) or (chunk.get("file_path") if isinstance(chunk, dict) else "")
    start_line = getattr(chunk, "start_line", 0) if hasattr(chunk, "start_line") else (chunk.get("start_line", 0) if isinstance(chunk, dict) else 0)
    end_line = getattr(chunk, "end_line", 0) if hasattr(chunk, "end_line") else (chunk.get("end_line", 0) if isinstance(chunk, dict) else 0)

    parts = [str(lang)]
    if parent:
        parts.append(f"class {parent}")
    parts.append(f"{kind} {name}".strip())
    header = " | ".join(parts)
    loc = f"{file_path}  lines {start_line}-{end_line}"
    return f"{header}\n{loc}"


def chunk_text(chunk) -> str:
    """Full text representation used for both embedding and BM25."""
    code = getattr(chunk, "code", "") if hasattr(chunk, "code") else (chunk.get("code", "") if isinstance(chunk, dict) else "")
    return f"{context_header(chunk)}\n\n{code}"


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

