import os
from .filters import should_skip_dir, skip_reason, looks_minified
from .parse import LANGUAGES, parse_file


def collect_chunks(repo_path):
    chunks, skipped = [], []

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

            chunks.extend(parse_file(source, rel_path, ext))

    return chunks, skipped