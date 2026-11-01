"""
FastAPI backend for Codebase Assistant.

Endpoints:
  POST   /repos                    — start ingestion of a GitHub repo
  GET    /repos                    — list all indexed repos
  GET    /repos/{repo_id}          — get repo status/info
  POST   /repos/{repo_id}/ask      — ask a question (non-streaming)
  POST   /repos/{repo_id}/ask/stream — ask with SSE streaming
  GET    /repos/{repo_id}/chunks/{chunk_id} — get full chunk details
  DELETE /repos/{repo_id}          — delete repo data
  GET    /health                   — health check
"""

import os
import sys
import time
import json
import logging
from collections import defaultdict

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.config import CORS_ORIGINS, RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW
from api.models import (
    IngestRequest, IngestResponse, AskRequest, AskResponse,
    RepoInfo, ChunkDetail, ErrorResponse,
)
from api.jobs import start_ingest, list_repos, get_repo, delete_repo, get_job

# ── Logging ───────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("codebase-assistant")


# ── App setup ─────────────────────────────────────────────────────

app = FastAPI(
    title="Codebase Assistant API",
    description="RAG-powered codebase Q&A with AST chunking, hybrid retrieval, and citations.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Rate limiting ─────────────────────────────────────────────────

_rate_limits: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(ip: str):
    """Simple in-memory per-IP rate limiting."""
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    _rate_limits[ip] = [t for t in _rate_limits[ip] if t > window_start]
    if len(_rate_limits[ip]) >= RATE_LIMIT_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW}s. Try again later.",
        )
    _rate_limits[ip].append(now)


# ── Endpoints ─────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": time.time()}


@app.post("/repos", response_model=IngestResponse)
async def ingest_repo(req: IngestRequest, request: Request):
    """Start indexing a GitHub repository."""
    _check_rate_limit(request.client.host)

    try:
        repo_id, job_id = start_ingest(req.url)
        logger.info(f"Started ingestion: {req.url} → {repo_id} (job: {job_id})")
        return IngestResponse(repo_id=repo_id, job_id=job_id, status="started")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        logger.error(f"Ingest error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/repos")
async def get_repos():
    """List all indexed repositories."""
    repos = list_repos()
    return {"repos": repos}


@app.get("/repos/{repo_id}")
async def get_repo_info(repo_id: str):
    """Get status and info for a specific repository."""
    info = get_repo(repo_id)
    if not info:
        raise HTTPException(status_code=404, detail=f"Repository '{repo_id}' not found")
    return info


@app.post("/repos/{repo_id}/ask", response_model=AskResponse)
async def ask_question(repo_id: str, req: AskRequest, request: Request):
    """Ask a question about an indexed repository."""
    _check_rate_limit(request.client.host)

    info = get_repo(repo_id)
    if not info:
        raise HTTPException(status_code=404, detail=f"Repository '{repo_id}' not found")
    if info.get("status") != "ready":
        raise HTTPException(status_code=400, detail="Repository is not ready yet. Current status: " + info.get("status", "unknown"))

    collection = f"code_{repo_id}"
    chunks_file = f"chunks_{repo_id}.json"

    t0 = time.time()
    try:
        from generate.answer import answer
        result = answer(
            question=req.question,
            collection=collection,
            chunks_path=chunks_file,
            history=req.history,
        )
        t1 = time.time()
        logger.info(f"Query [{repo_id}]: '{req.question[:50]}…' → {t1-t0:.2f}s")
        return AskResponse(**result)
    except Exception as e:
        logger.error(f"Answer error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/repos/{repo_id}/ask/stream")
async def ask_stream(repo_id: str, req: AskRequest, request: Request):
    """Ask with Server-Sent Events streaming."""
    _check_rate_limit(request.client.host)

    info = get_repo(repo_id)
    if not info:
        raise HTTPException(status_code=404, detail=f"Repository '{repo_id}' not found")
    if info.get("status") != "ready":
        raise HTTPException(status_code=400, detail="Repository is not ready yet")

    collection = f"code_{repo_id}"
    chunks_file = f"chunks_{repo_id}.json"

    def event_stream():
        from generate.answer import answer_stream
        try:
            for event in answer_stream(
                question=req.question,
                collection=collection,
                chunks_path=chunks_file,
                history=req.history,
            ):
                if "token" in event:
                    yield f"data: {json.dumps({'type': 'token', 'content': event['token']})}\n\n"
                elif "final" in event:
                    yield f"data: {json.dumps({'type': 'final', 'content': event['final']})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/repos/{repo_id}/chunks/{chunk_id:path}")
async def get_chunk(repo_id: str, chunk_id: str):
    """Get full details for a specific chunk."""
    chunks_file = f"chunks_{repo_id}.json"

    try:
        from index.stores import load_chunks
        chunk_dicts = load_chunks(chunks_file)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Chunks not found for this repository")

    for cd in chunk_dicts:
        if cd["id"] == chunk_id:
            # Build GitHub URL if we have repo info
            info = get_repo(repo_id)
            github_url = None
            if info and info.get("url"):
                url = info["url"].rstrip("/")
                sha = info.get("head_sha", "main")
                github_url = f"{url}/blob/{sha}/{cd['file_path']}#L{cd['start_line']}-L{cd['end_line']}"

            return ChunkDetail(
                github_url=github_url,
                **{k: cd[k] for k in ChunkDetail.model_fields if k in cd and k != "github_url"},
            )

    raise HTTPException(status_code=404, detail=f"Chunk '{chunk_id}' not found")


@app.delete("/repos/{repo_id}")
async def remove_repo(repo_id: str):
    """Delete a repository and all its data."""
    success = delete_repo(repo_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Repository '{repo_id}' not found")
    logger.info(f"Deleted repository: {repo_id}")
    return {"status": "deleted", "repo_id": repo_id}


# ── Error handlers ────────────────────────────────────────────────

@app.exception_handler(429)
async def rate_limit_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"detail": str(exc.detail), "error_type": "rate_limit", "retry_after": RATE_LIMIT_WINDOW},
    )


@app.exception_handler(500)
async def server_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error_type": "server_error"},
    )


# ── Run with uvicorn ──────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    from api.config import API_HOST, API_PORT
    uvicorn.run("api.main:app", host=API_HOST, port=API_PORT, reload=True)

