"""
Ingestion pipeline: walks a repo, filters noise, parses code into Chunks,
collects doc chunks, and enforces configurable limits.
"""

import os
from .filters import should_skip_dir, skip_reason, looks_minified
from .parse import LANGUAGES, parse_file, Chunk
from .docs import collect_doc_chunks

# ── Configurable limits ──────────────────────────────────────────

MAX_FILES = int(os.getenv("MAX_FILES", "2000"))
MAX_CHUNKS = int(os.getenv("MAX_CHUNKS", "5000"))
MAX_CHUNK_CHARS = int(os.getenv("MAX_CHUNK_CHARS", "6000"))
OVERLAP_CHARS = 200  # overlap for split chunks


def _split_oversized(chunk: Chunk, max_chars: int = MAX_CHUNK_CHARS) -> list[Chunk]:
    """Split a chunk whose code exceeds max_chars into overlapping pieces."""
    code = chunk.code
    if len(code) <= max_chars:
        return [chunk]

    pieces = []
    start = 0
    part = 1
    while start < len(code):
        end = start + max_chars
        piece_code = code[start:end]

        # Count lines in piece
        piece_lines = piece_code.count("\n")
        piece_start_line = chunk.start_line + code[:start].count("\n")
        piece_end_line = piece_start_line + piece_lines

        pieces.append(Chunk(
            id=f"{chunk.id}:part{part}",
            file_path=chunk.file_path,
            language=chunk.language,
            kind=chunk.kind,
            name=f"{chunk.name} (part {part})",
            parent=chunk.parent,
            start_line=piece_start_line,
            end_line=piece_end_line,
            code=piece_code,
            commits=chunk.commits,
        ))

        start = end - OVERLAP_CHARS  # overlap
        part += 1

    return pieces


def collect_chunks(repo_path, respect_gitignore=True):
    """
    Walk a repo directory and extract code + doc chunks.

    Returns:
        (chunks, skipped) where:
        - chunks: list of Chunk objects
        - skipped: list of (rel_path, reason) tuples for filtered files
    """
    chunks, skipped = [], []
    file_count = 0

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if not should_skip_dir(d)]

        for file in files:
            ext = os.path.splitext(file)[1]
            if ext not in LANGUAGES:
                continue  # unsupported language: ignore silently

            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, repo_path).replace("\\", "/")

            reason = skip_reason(full_path)
            if reason:
                skipped.append((rel_path, reason))
                continue

            with open(full_path, "rb") as f:
                source = f.read()

            if looks_minified(source):
                skipped.append((rel_path, "minified (long lines)"))
                continue

            file_count += 1
            if file_count > MAX_FILES:
                skipped.append((rel_path, f"file limit exceeded ({MAX_FILES})"))
                continue

            file_chunks = parse_file(source, rel_path, ext)

            # Split oversized chunks
            split_chunks = []
            for c in file_chunks:
                split_chunks.extend(_split_oversized(c))

            chunks.extend(split_chunks)

            if len(chunks) > MAX_CHUNKS:
                skipped.append((rel_path, f"chunk limit exceeded ({MAX_CHUNKS})"))
                chunks = chunks[:MAX_CHUNKS]
                break

    # ── Collect doc chunks ────────────────────────────────────────
    doc_chunks = collect_doc_chunks(repo_path)
    remaining = MAX_CHUNKS - len(chunks)
    if remaining > 0:
        chunks.extend(doc_chunks[:remaining])

    return chunks, skipped
