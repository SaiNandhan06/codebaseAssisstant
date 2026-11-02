# Codebase Assistant — Architectural Overview

This document details the system design, components, and data pipeline of **Codebase Assistant**.

For the exhaustive all-in-one defense guide, file directory map, and presentation pitch, see [MASTER_PROJECT_GUIDE.md](../MASTER_PROJECT_GUIDE.md).

---

## 1. High-Level Architecture Diagram

```mermaid
graph TD
    User([Developer / Web Browser])

    subgraph Frontend ["Frontend (React 19 + Vite + Tailwind CSS)"]
        UI[Workspace & Home Views]
        SSE_Client[EventSource / Fetch SSE Client]
        Source_Viewer[Source Inspection Panel]
    end

    subgraph API_Layer ["API Layer (FastAPI)"]
        Router[API Endpoints: /repos, /ask, /ask/stream]
        JobManager[Background Job Manager]
    end

    subgraph RAG_Engine ["RAG Core Engine"]
        Parser[Tree-sitter AST Parser]
        GitEng[Git Commit History Parser]
        BM25_Eng[Sub-word Tokenized BM25]
        Embed_Eng[Gemini Embedder with Disk Cache]
        RRF_Fusion[Reciprocal Rank Fusion k=60]
        Reranker[Cross-Encoder ms-marco-MiniLM-L6-v2]
        Hallucination_Shield{Logit Score >= -7.5?}
        Generator[Gemini 2.5 Flash with Retry Wrapper]
        Validator[Interval Citation Validator]
    end

    subgraph Storage ["Persistent Storage"]
        Disk_Chunks[(data/chunks_*.json)]
        Embed_Cache[(data/embed_cache/*.json)]
        Qdrant_DB[(Qdrant Vector DB: Cosine 3072-d)]
    end

    User <--> UI
    UI <--> SSE_Client
    UI <--> Source_Viewer

    SSE_Client <--> Router
    Router <--> JobManager
    JobManager --> Parser
    Parser --> GitEng
    GitEng --> Disk_Chunks
    Disk_Chunks --> BM25_Eng
    Disk_Chunks --> Embed_Eng
    Embed_Eng <--> Embed_Cache
    Embed_Eng --> Qdrant_DB

    Router --> BM25_Eng
    Router --> Qdrant_DB
    BM25_Eng --> RRF_Fusion
    Qdrant_DB --> RRF_Fusion
    RRF_Fusion --> Reranker
    Reranker --> Hallucination_Shield
    Hallucination_Shield -->|Passed| Generator
    Hallucination_Shield -->|Failed| Router
    Generator --> Validator
    Validator --> SSE_Client
```

---

## 2. Component Specifications

### 2.1 Ingestion & Parsing (`ingest/`)
* **Tree-sitter AST Engine**: Recursively traverses the repository syntax tree. Breaks code into syntactically valid chunks (complete functions and class blocks) rather than fixed-token slices.
* **Metadata Attachment**: Enriches each chunk with repository URL, latest commit SHA, author attribution, and hierarchical context headers.

### 2.2 Storage & Search (`index/` & `retrieve/`)
* **Sub-word BM25**: Splits snake_case, camelCase, and file paths so exact symbol names can be discovered effortlessly.
* **Dense Semantic Vector Store**: Stores 3072-dimensional Gemini embeddings in Qdrant with Cosine distance metric.
* **Reciprocal Rank Fusion (RRF)**: Merges sparse and dense search rankings safely using $k=60$.
* **Cross-Encoder Gating**: Reranks top 20 candidates down to 5 using `cross-encoder/ms-marco-MiniLM-L6-v2`. Any query failing the logit threshold ($\tau = -7.5$) triggers an automatic low-confidence notice, preventing hallucination.

### 2.3 Generation & Citation Verification (`generate/`)
* **Prompt Injection**: Injects top reranked chunks into a markdown-structured prompt with system instructions enforcing `[file:start-end]` citations.
* **Streaming & Retries**: Emits SSE tokens while automatically retrying on 503/429 spikes using exponential backoff.
* **Citation Interval Validator**: Programmatically verifies that every cited line interval exists inside the retrieved chunks before the answer is rendered.

