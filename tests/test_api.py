"""
API tests for FastAPI endpoints in api/main.py.
"""

import os
import pytest
from fastapi.testclient import TestClient

from api.main import app
from ingest.parse import Chunk
from index.stores import save_chunks, DATA_DIR

client = TestClient(app)


@pytest.fixture(autouse=True)
def ensure_sample_chunks():
    """Ensure minimal chunks exist in data/ for API testing across clean CI environments."""
    os.makedirs(DATA_DIR, exist_ok=True)
    sample_chunk = Chunk(
        id="samples/sample_class.py::total:8",
        file_path="samples/sample_class.py",
        language="python",
        kind="method",
        name="total",
        parent="ShoppingCart",
        start_line=8,
        end_line=9,
        code="def total(self):\n    return sum(item.price for item in self.items)",
    )
    for fname in ["chunks_codebase-assistant.json", "chunks.json"]:
        fpath = os.path.join(DATA_DIR, fname)
        if not os.path.exists(fpath):
            save_chunks([sample_chunk], filename=fname)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data


def test_get_repos():
    response = client.get("/repos")
    assert response.status_code == 200
    data = response.json()
    assert "repos" in data
    assert len(data["repos"]) >= 1
    assert any(r["repo_id"] == "codebase-assistant" for r in data["repos"])


def test_get_repo_info_found():
    response = client.get("/repos/codebase-assistant")
    assert response.status_code == 200
    data = response.json()
    assert data["repo_id"] == "codebase-assistant"
    assert data["status"] == "ready"
    assert data["chunk_count"] > 0


def test_get_repo_info_not_found():
    response = client.get("/repos/nonexistent_repo_id_12345")
    assert response.status_code == 404


def test_invalid_github_url():
    response = client.post("/repos", json={"url": "not-a-valid-url"})
    assert response.status_code == 400


def test_get_chunk_detail():
    from index.stores import load_chunks
    chunks_file = "chunks_codebase-assistant.json"
    fpath = os.path.join(DATA_DIR, chunks_file)
    if not os.path.exists(fpath):
        sample_chunk = Chunk(
            id="samples/sample_class.py::total:8",
            file_path="samples/sample_class.py",
            language="python",
            kind="method",
            name="total",
            parent="ShoppingCart",
            start_line=8,
            end_line=9,
            code="def total(self):\n    return sum(item.price for item in self.items)",
        )
        save_chunks([sample_chunk], filename=chunks_file)

    chunks = load_chunks(chunks_file)
    cid = chunks[0]["id"]
    response = client.get(f"/repos/codebase-assistant/chunks/{cid}")
    assert response.status_code == 200
    data = response.json()
    assert "code" in data
    assert "file_path" in data
    assert "language" in data

