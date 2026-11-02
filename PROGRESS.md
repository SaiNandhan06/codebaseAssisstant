# Engineering Progress Log — Codebase Assistant

## Initial Checks (Pre-Milestone 1)
- [x] Verified `python run_ingest.py samples`: Successfully extracted 5 chunks (`ShoppingCart` class, 3 methods, 1 standalone helper) with git commit history attached.
- [x] Verified `python build_index.py .`: Collected 121 code and doc chunks from codebase-assistant repo, saved `chunks.json`, built BM25 index, generated cached embeddings via Gemini, and indexed into Qdrant in 8.8s.

## Milestone 1: Retrieval Core on Real Data
- [x] Implemented `retrieve/hybrid.py`: Hybrid search fusing BM25 lexical rank with Qdrant dense vector rank using Reciprocal Rank Fusion ($k=60$).
- [x] Implemented `retrieve/rerank.py`: Cross-Encoder reranker (`cross-encoder/ms-marco-MiniLM-L6-v2`) with context headers (`# language kind parent.name in file_path\ncode`).
- [x] Tuned low-confidence threshold (`RERANK_THRESHOLD = -5.0` default logit threshold) to separate relevant code from completely ungrounded or off-topic questions.
- [x] CLI testing script `scripts/try_retrieval.py` validated with top-5 chunk outputs and score breakdowns.

## Milestone 2: Grounded Generation with Citations
- [x] Implemented `generate/prompts.py`: Strict system prompt enforcing citations in `[path:start-end]` format and fallback to "I can't find this in the code" when evidence is lacking.
- [x] Implemented `generate/answer.py`: Grounded RAG answer generation using `gemini-2.5-flash` with commit history context.
- [x] Implemented query rewriting for follow-up conversational questions.
- [x] Implemented post-generation regex citation extraction and chunk boundary validation returning `invalid_citations`.
- [x] Added streaming generator `answer_stream` for Server-Sent Events.

## Milestone 3: Ingestion Upgrades
- [x] Implemented `ingest/clone.py`: Safe shallow cloning of GitHub URLs (`https://github.com/owner/name`), HEAD commit SHA extraction, and size limit enforcement.
- [x] Per-repo Qdrant collection isolation (`code_{repo_id}`) and per-repo `chunks_{repo_id}.json`.
- [x] Configurable limits for `MAX_FILES`, `MAX_CHUNKS`, and `MAX_REPO_SIZE_MB`.
- [x] Noise filtering: Skip vendored, lockfiles (`package-lock.json`, `poetry.lock`), minified JS/CSS, long-line heuristics, and respect `.gitignore`.
- [x] Oversized function splitting (> 6000 chars) with 200 char overlap.
- [x] Markdown document ingestion (`ingest/docs.py`) split by headings into doc chunks.
- [x] Multi-language Tree-sitter table: Python, JavaScript, TypeScript, TSX, Java, Go.
- [x] Commit SHA and repository URL metadata attached to each chunk.

## Milestone 4: FastAPI Backend
- [x] Created `api/main.py`, `api/models.py`, `api/jobs.py`, `api/config.py`.
- [x] Endpoints: `POST /repos`, `GET /repos`, `GET /repos/{id}`, `POST /repos/{id}/ask`, `POST /repos/{id}/ask/stream`, `GET /repos/{id}/chunks/{chunk_id}`, `DELETE /repos/{id}`, `GET /health`.
- [x] Background asynchronous job processing with single-ingest mutex lock and rate limiting per IP.
- [x] Full Pytest test suite in `tests/test_core.py` and `tests/test_api.py` (25 tests passing 100%).

## Milestone 5: Frontend (React + Vite + TypeScript + Tailwind)
- [x] Built developer dark-themed UI matching specifications:
  - `HomePage`: Hero section, GitHub URL input, analyze button, quick example repos, list of indexed repos with status badges.
  - `ProgressBar`: 4 stages (Clone -> AST Parse -> Embedding -> Vector Store) with percentage tracking and live chunk counter.
  - `WorkspacePage`: 3-column layout with repo metadata, suggested questions, chat conversation with live SSE streaming, and interactive code viewer.
  - `AnswerCard`: Markdown answer display, copy button, low-confidence warning banner, and interactive citation chips.
  - `SourcePanel`: Syntax line-numbered code viewer highlighting cited line spans, commit history, and GitHub links.
- [x] Successfully verified production build (`npm run build` exits 0).

## Milestone 6: Evaluation
- [x] Created evaluation dataset `eval/questions/codebase_assistant.json` (20 verified questions across `where-is`, `how-does`, `why`, `usage`).
- [x] Created `eval/baselines.py` with 5 retrieval configurations (Naive, AST Vector, AST BM25, AST Hybrid, AST Hybrid + Rerank).
- [x] Executed `eval/run_eval.py`:
  - Naive baseline: 70.0% Hit@5, 0.602 MRR
  - AST Hybrid + Rerank: **100.0% Hit@5**, **0.879 MRR**, 97.5% Recall@5.
- [x] Results report saved in `eval/results/eval_report.md`.

## Milestone 7: Deployment
- [x] Pinned `requirements.txt`.
- [x] Dockerfile with health check.
- [x] `docker-compose.yml` for unified backend and Qdrant orchestration.
- [x] Verified local fallback storage and graceful shutdown.

