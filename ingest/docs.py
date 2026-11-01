"""
docs.py — Ingest Markdown documentation files (.md, .rst).

Splits by headings into Chunk objects with kind='doc'.
"""

import os
import re
from .parse import Chunk


def _split_by_headings(text: str, rel_path: str) -> list[Chunk]:
    """Split a markdown file by headings into doc chunks."""
    lines = text.split("\n")
    chunks = []
    current_heading = os.path.splitext(os.path.basename(rel_path))[0]
    current_lines = []
    current_start = 1

    heading_re = re.compile(r"^(#{1,3})\s+(.+)")

    for i, line in enumerate(lines, 1):
        m = heading_re.match(line)
        if m and current_lines:
            # Save previous section
            content = "\n".join(current_lines).strip()
            if content and len(content) > 20:  # skip tiny sections
                chunks.append(Chunk(
                    id=f"{rel_path}::doc:{current_heading}:{current_start}",
                    file_path=rel_path,
                    language="markdown",
                    kind="doc",
                    name=current_heading,
                    parent=None,
                    start_line=current_start,
                    end_line=i - 1,
                    code=content,
                ))
            current_heading = m.group(2).strip()
            current_lines = [line]
            current_start = i
        else:
            current_lines.append(line)

    # Save last section
    if current_lines:
        content = "\n".join(current_lines).strip()
        if content and len(content) > 20:
            chunks.append(Chunk(
                id=f"{rel_path}::doc:{current_heading}:{current_start}",
                file_path=rel_path,
                language="markdown",
                kind="doc",
                name=current_heading,
                parent=None,
                start_line=current_start,
                end_line=len(lines),
                code=content,
            ))

    return chunks


DOC_EXTENSIONS = {".md", ".rst", ".txt"}


def collect_doc_chunks(repo_path: str, skip_dirs: set | None = None) -> list[Chunk]:
    """Walk the repo and collect doc chunks from markdown/text files."""
    from .filters import should_skip_dir

    chunks = []
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if not should_skip_dir(d)]

        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext not in DOC_EXTENSIONS:
                continue

            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, repo_path).replace("\\", "/")

            try:
                with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except (OSError, UnicodeDecodeError):
                continue

            if len(content) < 30:  # skip near-empty files
                continue

            chunks.extend(_split_by_headings(content, rel_path))

    return chunks

