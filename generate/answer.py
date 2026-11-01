"""
answer.py — Grounded generation with citations, streaming support,
query rewriting for follow-ups, and citation validation.
"""

import os
import re

from dotenv import load_dotenv
from google import genai

from retrieve.hybrid import hybrid_search
from retrieve.rerank import rerank
from generate.prompts import (
    SYSTEM_PROMPT,
    build_prompt,
    REWRITE_PROMPT,
)

load_dotenv()

_client = genai.Client()
GEN_MODEL = os.getenv("GEN_MODEL", "gemini-3.5-flash")

# ── Citation regex ────────────────────────────────────────────────

_CITATION_RE = re.compile(r"\[([^\]]+?):(\d+)-(\d+)\]")


def _extract_citations(text: str) -> list[dict]:
    """Parse [file_path:start-end] citations from the answer text."""
    citations = []
    for m in _CITATION_RE.finditer(text):
        citations.append({
            "file_path": m.group(1),
            "start_line": int(m.group(2)),
            "end_line": int(m.group(3)),
            "raw": m.group(0),
        })
    return citations


def _validate_citations(citations: list[dict], chunks: list[dict]) -> tuple[list[dict], list[dict]]:
    """Check each citation against the retrieved chunks.

    Returns (valid_citations, invalid_citations).
    """
    valid, invalid = [], []
    for cit in citations:
        matched = False
        for c in chunks:
            if (cit["file_path"] == c["file_path"]
                    and cit["start_line"] >= c["start_line"]
                    and cit["end_line"] <= c["end_line"]):
                matched = True
                break
        if matched:
            valid.append(cit)
        else:
            invalid.append(cit)
    return valid, invalid


# ── Query rewriting for follow-ups ────────────────────────────────

def _rewrite_query(question: str, history: list[dict]) -> str:
    """Rewrite a follow-up question into a standalone query using chat history."""
    if not history:
        return question

    conversation = "\n".join(
        f"{'User' if h['role'] == 'user' else 'Assistant'}: {h['content']}"
        for h in history[-4:]
    )
    prompt = REWRITE_PROMPT.format(history=conversation, question=question)

    response = _client.models.generate_content(
        model=GEN_MODEL,
        contents=prompt,
    )
    rewritten = response.text.strip()
    return rewritten if rewritten else question


# ── Main answer function ──────────────────────────────────────────

def answer(
    question: str,
    collection: str = "code_chunks",
    chunks_path: str = "chunks.json",
    history: list[dict] | None = None,
    top_k: int = 20,
    top_n: int = 5,
) -> dict:
    """
    Full RAG pipeline: retrieve → rerank → generate → validate citations.

    Args:
        question: The user's question about the codebase.
        collection: Qdrant collection name.
        chunks_path: Path to chunks.json for BM25.
        history: List of {"role": "user"|"assistant", "content": "..."} dicts.
        top_k: Number of candidates from hybrid search.
        top_n: Number of chunks after reranking.

    Returns:
        {
            "answer": str,
            "sources": [chunk dicts with scores],
            "low_confidence": bool,
            "citations": [valid citations],
            "invalid_citations": [invalid citations],
            "search_query": str,  # the actual query used for retrieval
        }
    """
    # Rewrite follow-up questions
    search_query = _rewrite_query(question, history) if history else question

    # Retrieve
    candidates = hybrid_search(search_query, collection=collection,
                               chunks_path=chunks_path, top_k=top_k)

    # Rerank
    top_chunks, low_confidence = rerank(search_query, candidates, top_n=top_n)

    if low_confidence:
        return {
            "answer": "I can't find this in the code. The indexed chunks don't contain enough relevant information to answer this question confidently.",
            "sources": [],
            "low_confidence": True,
            "citations": [],
            "invalid_citations": [],
            "search_query": search_query,
        }

    # Generate
    user_prompt = build_prompt(question, top_chunks, history)

    response = _client.models.generate_content(
        model=GEN_MODEL,
        contents=user_prompt,
        config=genai.types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.1,
            max_output_tokens=2048,
        ),
    )
    answer_text = response.text

    # Validate citations
    all_citations = _extract_citations(answer_text)
    valid_cits, invalid_cits = _validate_citations(all_citations, top_chunks)

    return {
        "answer": answer_text,
        "sources": top_chunks,
        "low_confidence": False,
        "citations": valid_cits,
        "invalid_citations": invalid_cits,
        "search_query": search_query,
    }


# ── Streaming answer ─────────────────────────────────────────────

def answer_stream(
    question: str,
    collection: str = "code_chunks",
    chunks_path: str = "chunks.json",
    history: list[dict] | None = None,
    top_k: int = 20,
    top_n: int = 5,
):
    """
    Streaming version: yields dicts with either 'token' or 'final' key.

    Yields:
        {"token": "partial text"}  — streamed answer tokens
        {"final": {answer, sources, citations, ...}} — final result after stream ends
    """
    search_query = _rewrite_query(question, history) if history else question

    candidates = hybrid_search(search_query, collection=collection,
                               chunks_path=chunks_path, top_k=top_k)
    top_chunks, low_confidence = rerank(search_query, candidates, top_n=top_n)

    if low_confidence:
        msg = "I can't find this in the code. The indexed chunks don't contain enough relevant information."
        yield {"token": msg}
        yield {"final": {
            "answer": msg,
            "sources": [],
            "low_confidence": True,
            "citations": [],
            "invalid_citations": [],
            "search_query": search_query,
        }}
        return

    user_prompt = build_prompt(question, top_chunks, history)

    full_text = ""
    response = _client.models.generate_content_stream(
        model=GEN_MODEL,
        contents=user_prompt,
        config=genai.types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.1,
            max_output_tokens=2048,
        ),
    )

    for chunk in response:
        if chunk.text:
            full_text += chunk.text
            yield {"token": chunk.text}

    # Validate citations
    all_citations = _extract_citations(full_text)
    valid_cits, invalid_cits = _validate_citations(all_citations, top_chunks)

    yield {"final": {
        "answer": full_text,
        "sources": top_chunks,
        "low_confidence": False,
        "citations": valid_cits,
        "invalid_citations": invalid_cits,
        "search_query": search_query,
    }}

