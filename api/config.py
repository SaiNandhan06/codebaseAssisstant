"""
Configuration loaded from environment variables.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── API settings ──────────────────────────────────────────────────

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000"
).split(",")

# ── Qdrant ────────────────────────────────────────────────────────

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))

# ── Gemini ────────────────────────────────────────────────────────

GEN_MODEL = os.getenv("GEN_MODEL", "gemini-2.5-flash")
EMBED_MODEL = os.getenv("EMBED_MODEL", "gemini-embedding-001")

# ── Limits ────────────────────────────────────────────────────────

MAX_FILES = int(os.getenv("MAX_FILES", "2000"))
MAX_CHUNKS = int(os.getenv("MAX_CHUNKS", "5000"))
MAX_REPO_SIZE_MB = int(os.getenv("MAX_REPO_SIZE_MB", "200"))

# ── Rate limiting ─────────────────────────────────────────────────

RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "30"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # seconds

# ── Reranker ──────────────────────────────────────────────────────

RERANK_MODEL = os.getenv("RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L6-v2")
RERANK_THRESHOLD = float(os.getenv("RERANK_THRESHOLD", "-7.5"))

# ── Demo mode ─────────────────────────────────────────────────────

DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
DEMO_REPO_URL = os.getenv("DEMO_REPO_URL", "")
MAX_INGESTS_PER_IP = int(os.getenv("MAX_INGESTS_PER_IP", "1"))
MAX_DAILY_INGESTS = int(os.getenv("MAX_DAILY_INGESTS", "10"))

