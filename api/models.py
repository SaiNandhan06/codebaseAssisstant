"""
Pydantic models for API request/response bodies.
"""

from pydantic import BaseModel, HttpUrl


class IngestRequest(BaseModel):
    url: str  # GitHub URL


class IngestResponse(BaseModel):
    repo_id: str
    job_id: str
    status: str = "started"


class RepoInfo(BaseModel):
    repo_id: str
    url: str | None = None
    status: str  # "indexing" | "ready" | "error"
    stage: str | None = None  # "cloning" | "parsing" | "embedding" | "storing" | "done"
    percent: float = 0.0
    chunk_count: int = 0
    file_count: int = 0
    head_sha: str | None = None
    error: str | None = None
    languages: dict = {}


class AskRequest(BaseModel):
    question: str
    history: list[dict] = []


class AskResponse(BaseModel):
    answer: str
    sources: list[dict] = []
    low_confidence: bool = False
    citations: list[dict] = []
    invalid_citations: list[dict] = []
    search_query: str = ""


class ChunkDetail(BaseModel):
    id: str
    file_path: str
    language: str
    kind: str
    name: str
    parent: str | None = None
    start_line: int
    end_line: int
    code: str
    commits: list[dict] = []
    github_url: str | None = None


class ErrorResponse(BaseModel):
    detail: str
    error_type: str = "general"
    retry_after: int | None = None

