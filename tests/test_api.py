"""
API tests for FastAPI endpoints in api/main.py.
"""

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


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
    # Find chunk id from repos/codebase-assistant/chunks
    response = client.get("/repos/codebase-assistant/chunks/samples/sample_class.py::total:8")
    if response.status_code == 404:
        # Try finding any valid chunk
        from index.stores import load_chunks
        chunks = load_chunks("chunks.json")
        cid = chunks[0]["id"]
        response = client.get(f"/repos/codebase-assistant/chunks/{cid}")
    assert response.status_code == 200
    data = response.json()
    assert "code" in data
    assert "file_path" in data
    assert "language" in data

