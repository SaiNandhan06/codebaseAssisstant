"""
clone.py — Clone a public GitHub repo by URL into data/repos/{owner}__{name}.

Validates the URL format, performs a shallow clone, and records the HEAD sha.
"""

import os
import re
import shutil

from git import Repo

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
REPOS_DIR = os.path.join(DATA_DIR, "repos")

# ── Configurable limits ──────────────────────────────────────────

MAX_FILES = int(os.getenv("MAX_FILES", "2000"))
MAX_CHUNKS = int(os.getenv("MAX_CHUNKS", "5000"))
MAX_REPO_SIZE_MB = int(os.getenv("MAX_REPO_SIZE_MB", "200"))

# ── URL validation ────────────────────────────────────────────────

_GITHUB_RE = re.compile(
    r"^https://github\.com/(?P<owner>[A-Za-z0-9._-]+)/(?P<name>[A-Za-z0-9._-]+?)(?:\.git)?$"
)


def parse_github_url(url: str) -> tuple[str, str]:
    """Extract (owner, name) from a GitHub URL. Raises ValueError if invalid."""
    m = _GITHUB_RE.match(url.strip())
    if not m:
        raise ValueError(
            f"Invalid GitHub URL: '{url}'. "
            "Expected format: https://github.com/owner/name"
        )
    return m.group("owner"), m.group("name")


def repo_id_from_url(url: str) -> str:
    """Get the repo_id (owner__name) from a GitHub URL."""
    owner, name = parse_github_url(url)
    return f"{owner}__{name}"


def clone_repo(url: str, force: bool = False) -> dict:
    """
    Shallow-clone a GitHub repo.

    Args:
        url: GitHub repository URL.
        force: If True, re-clone even if the directory exists.

    Returns:
        {"repo_id": str, "clone_path": str, "head_sha": str, "url": str}

    Raises:
        ValueError: If URL is invalid.
        RuntimeError: If repo exceeds size limits.
    """
    owner, name = parse_github_url(url)
    rid = f"{owner}__{name}"
    clone_path = os.path.join(REPOS_DIR, rid)

    if os.path.exists(clone_path):
        if force:
            shutil.rmtree(clone_path)
        else:
            # Already cloned — just get HEAD sha
            repo = Repo(clone_path)
            return {
                "repo_id": rid,
                "clone_path": clone_path,
                "head_sha": repo.head.commit.hexsha,
                "url": url,
            }

    os.makedirs(REPOS_DIR, exist_ok=True)

    # Shallow clone (depth=1)
    git_url = url if url.endswith(".git") else url + ".git"
    repo = Repo.clone_from(git_url, clone_path, depth=1)

    head_sha = repo.head.commit.hexsha

    # Check repo size
    total_size = 0
    for root, dirs, files in os.walk(clone_path):
        # Skip .git internals
        dirs[:] = [d for d in dirs if d != ".git"]
        for f in files:
            total_size += os.path.getsize(os.path.join(root, f))

    size_mb = total_size / (1024 * 1024)
    if size_mb > MAX_REPO_SIZE_MB:
        shutil.rmtree(clone_path)
        raise RuntimeError(
            f"Repository too large: {size_mb:.1f} MB (limit: {MAX_REPO_SIZE_MB} MB)"
        )

    return {
        "repo_id": rid,
        "clone_path": clone_path,
        "head_sha": head_sha,
        "url": url,
    }


def delete_clone(repo_id: str):
    """Delete a cloned repository."""
    clone_path = os.path.join(REPOS_DIR, repo_id)
    if os.path.exists(clone_path):
        shutil.rmtree(clone_path)

