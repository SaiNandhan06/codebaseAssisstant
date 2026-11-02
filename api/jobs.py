"""
Background ingestion job manager.

Handles running ingest jobs asynchronously and tracking their progress.
"""

import os
import json
import time
import threading
import traceback
from collections import Counter
from dataclasses import asdict

from ingest.clone import clone_repo, parse_github_url, REPOS_DIR
from ingest.pipeline import collect_chunks
from ingest.git_history import attach_history
from index.stores import store_vectors, save_chunks

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

# ── Job state ─────────────────────────────────────────────────────

_jobs: dict[str, dict] = {
    "demo_codebase-assistant": {
        "job_id": "demo_codebase-assistant",
        "repo_id": "codebase-assistant",
        "url": "https://github.com/example/codebase-assistant",
        "status": "ready",
        "stage": "done",
        "percent": 100,
        "chunk_count": 121,
        "file_count": 15,
        "head_sha": "main",
        "error": None,
        "languages": {"python": 119, "markdown": 2},
        "created_at": time.time(),
    }
}
_job_lock = threading.Lock()
_ingest_lock = threading.Lock()  # one ingest at a time


def _discover_persisted_repos():
    """Discover previously indexed repos from disk chunks files."""
    if not os.path.exists(DATA_DIR):
        return
    for fname in os.listdir(DATA_DIR):
        if fname.startswith("chunks_") and fname.endswith(".json"):
            repo_id = fname[len("chunks_"):-len(".json")]
            job_id = f"persisted_{repo_id}"
            if job_id not in _jobs and not any(j.get("repo_id") == repo_id for j in _jobs.values()):
                try:
                    fpath = os.path.join(DATA_DIR, fname)
                    with open(fpath, "r", encoding="utf-8") as f:
                        chunks = json.load(f)
                    languages = dict(Counter(c.get("language", "unknown") for c in chunks))
                    files = len(set(c.get("file_path", "") for c in chunks))
                    url = chunks[0].get("repo_url", f"https://github.com/{repo_id.replace('__', '/')}") if chunks else f"https://github.com/{repo_id.replace('__', '/')}"
                    head_sha = chunks[0].get("commit_sha", "main") if chunks else "main"
                    _jobs[job_id] = {
                        "job_id": job_id,
                        "repo_id": repo_id,
                        "url": url,
                        "status": "ready",
                        "stage": "done",
                        "percent": 100,
                        "chunk_count": len(chunks),
                        "file_count": files,
                        "head_sha": head_sha,
                        "error": None,
                        "languages": languages,
                        "created_at": os.path.getmtime(fpath),
                    }
                except Exception:
                    pass

_discover_persisted_repos()


def get_job(job_id: str) -> dict | None:
    with _job_lock:
        _discover_persisted_repos()
        return _jobs.get(job_id, {}).copy() if job_id in _jobs else None


def list_repos() -> list[dict]:
    """List all indexed/indexing repos."""
    with _job_lock:
        _discover_persisted_repos()
        return [v.copy() for v in _jobs.values()]


def get_repo(repo_id: str) -> dict | None:
    """Get repo info by repo_id."""
    with _job_lock:
        _discover_persisted_repos()
        for job in _jobs.values():
            if job.get("repo_id") == repo_id:
                return job.copy()
    return None


def delete_repo(repo_id: str) -> bool:
    """Delete repo data (Qdrant collection, chunks, clone)."""
    from index.stores import _db

    collection = f"code_{repo_id}"

    # Delete Qdrant collection
    try:
        db = _db()
        if db.collection_exists(collection):
            db.delete_collection(collection)
    except Exception:
        pass

    # Delete chunks file
    chunks_file = os.path.join(DATA_DIR, f"chunks_{repo_id}.json")
    if os.path.exists(chunks_file):
        os.remove(chunks_file)

    # Delete clone
    clone_path = os.path.join(REPOS_DIR, repo_id)
    if os.path.exists(clone_path):
        import shutil
        shutil.rmtree(clone_path, ignore_errors=True)

    # Remove from jobs
    with _job_lock:
        to_remove = [k for k, v in _jobs.items() if v.get("repo_id") == repo_id]
        for k in to_remove:
            del _jobs[k]

    return bool(to_remove)


# ── Run ingestion in background ───────────────────────────────────

def _update_job(job_id: str, **kwargs):
    with _job_lock:
        if job_id in _jobs:
            _jobs[job_id].update(kwargs)


def _run_ingest(job_id: str, url: str, repo_id: str):
    """Background worker for ingestion."""
    collection = f"code_{repo_id}"
    chunks_file = f"chunks_{repo_id}.json"

    try:
        # Stage 1: Clone
        _update_job(job_id, stage="cloning", percent=5)
        info = clone_repo(url)
        clone_path = info["clone_path"]
        head_sha = info["head_sha"]
        _update_job(job_id, head_sha=head_sha, percent=15)

        # Stage 2: Parse
        _update_job(job_id, stage="parsing", percent=20)
        chunks, skipped = collect_chunks(clone_path)

        # Attach metadata
        for c in chunks:
            c.commit_sha = head_sha
            c.repo_url = url

        attach_history(chunks, clone_path)

        languages = dict(Counter(c.language for c in chunks))
        kinds = dict(Counter(c.kind for c in chunks))
        _update_job(
            job_id,
            chunk_count=len(chunks),
            file_count=len(set(c.file_path for c in chunks)),
            languages=languages,
            kinds=kinds,
            skipped_count=len(skipped),
            percent=40,
        )

        if not chunks:
            _update_job(job_id, status="error", error="No code chunks found in repository", stage="done")
            return

        # Stage 3: Embed
        _update_job(job_id, stage="embedding", percent=50)
        save_chunks(chunks, filename=chunks_file)

        # Stage 4: Store in Qdrant
        _update_job(job_id, stage="storing", percent=70)
        store_vectors(chunks, collection=collection)

        _update_job(
            job_id,
            status="ready",
            stage="done",
            percent=100,
        )

    except Exception as e:
        _update_job(
            job_id,
            status="error",
            error=str(e),
            stage="error",
            traceback=traceback.format_exc(),
        )
    finally:
        _ingest_lock.release()


def start_ingest(url: str) -> tuple[str, str]:
    """
    Start an ingestion job. Returns (repo_id, job_id).
    Raises RuntimeError if another ingest is already running.
    """
    from ingest.clone import repo_id_from_url
    repo_id = repo_id_from_url(url)
    job_id = f"{repo_id}_{int(time.time())}"

    if not _ingest_lock.acquire(blocking=False):
        raise RuntimeError("Another ingestion is in progress. Please wait.")

    with _job_lock:
        _jobs[job_id] = {
            "job_id": job_id,
            "repo_id": repo_id,
            "url": url,
            "status": "indexing",
            "stage": "starting",
            "percent": 0,
            "chunk_count": 0,
            "file_count": 0,
            "head_sha": None,
            "error": None,
            "languages": {},
            "created_at": time.time(),
        }

    thread = threading.Thread(
        target=_run_ingest,
        args=(job_id, url, repo_id),
        daemon=True,
    )
    thread.start()

    return repo_id, job_id

