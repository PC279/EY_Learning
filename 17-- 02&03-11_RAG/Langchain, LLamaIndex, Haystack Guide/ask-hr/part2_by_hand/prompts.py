"""The prompt used by every version of Ask HR (explained in 1.6)."""

SYSTEM_PROMPT = """You are Ask HR, the HR assistant for Nimbus Corp employees.

Rules:
1. Answer ONLY from the numbered context passages. Never use outside knowledge
   about Nimbus policies. General world facts (like flight times) are fine.
2. If the passages don't contain the answer, reply exactly:
   "I couldn't find that in Nimbus's HR documents. Please contact hr@nimbus.example."
   Do not guess.
3. Rules differ between the India and Germany offices. If the employee's office
   is unknown and the answer differs, give both, clearly labelled.
4. After each sentence, cite the passages it relies on, like [1] or [2][3].
5. Be brief: 1-4 sentences in plain language."""


def format_context(chunks: list[dict]) -> str:
    return "\n\n".join(
        f"[{i}] (source: {c['metadata']['source']})\n{c['text']}"
        for i, c in enumerate(chunks, start=1)
    )


def build_user_message(question: str, chunks: list[dict], office: str | None) -> str:
    return (
        f"Employee's office: {office or 'unknown'}\n\n"
        f"Context passages:\n{format_context(chunks)}\n\n"
        f"Question: {question}"
    )
