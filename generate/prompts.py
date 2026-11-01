"""
Prompt templates for grounded code-question answering.
"""

SYSTEM_PROMPT = """You are a precise code assistant. You answer questions about a codebase using ONLY the provided code chunks below.

RULES:
1. Answer ONLY from the provided chunks. Do NOT invent code or functionality not shown.
2. Cite EVERY claim using the format [file_path:start_line-end_line]. 
   Example: "The total is computed by summing item prices [utils/cart.py:8-9]."
3. If the chunks do not contain enough information to answer the question, say:
   "I can't find this in the code. The indexed chunks don't contain information about this topic."
4. When discussing implementation details, quote or paraphrase the actual code.
5. If commit history is available, use it to answer "why" or "when" questions.
6. Be concise but thorough. Prefer bullet points for multi-part answers.
7. Use Markdown formatting for code snippets and structure."""


def build_context(chunks: list[dict]) -> str:
    """Build the context block from ranked chunks for the LLM prompt."""
    parts = []
    for i, c in enumerate(chunks):
        header = (
            f"── Chunk {i+1}: [{c['kind']}] {c['name']} ──\n"
            f"File: {c['file_path']}  Lines: {c['start_line']}-{c['end_line']}  "
            f"Language: {c['language']}"
        )
        if c.get("parent"):
            header += f"  Parent class: {c['parent']}"

        # Add recent commits if available
        commits = c.get("commits", [])
        if commits:
            commit_lines = []
            for cm in commits[:3]:
                commit_lines.append(
                    f"  {cm['hash']} {cm['date']} — {cm['message']}"
                )
            header += "\nRecent commits:\n" + "\n".join(commit_lines)

        code = c["code"]
        parts.append(f"{header}\n\n```\n{code}\n```")

    return "\n\n".join(parts)


def build_prompt(question: str, chunks: list[dict], history: list[dict] | None = None) -> str:
    """Build the full user prompt with context and question."""
    context = build_context(chunks)

    prompt = f"""Here are the relevant code chunks from the repository:

{context}

───────────────────────────────────
Question: {question}
"""
    if history:
        conversation = "\n".join(
            f"{'User' if h['role'] == 'user' else 'Assistant'}: {h['content']}"
            for h in history[-4:]  # last 4 turns for context
        )
        prompt += f"\nPrevious conversation:\n{conversation}\n"

    return prompt


REWRITE_PROMPT = """Given the conversation history and a follow-up question, rewrite the follow-up into a standalone search query that captures the full intent. Return ONLY the rewritten query, nothing else.

Conversation:
{history}

Follow-up question: {question}

Standalone search query:"""

