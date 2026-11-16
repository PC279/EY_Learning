"""Ask HR, professional edition: office detection + hybrid search + reranking.
Run:  python -m part7_pro.ask_pro
"""
import re

from openai import OpenAI
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder

import config
from part2_by_hand.prompts import SYSTEM_PROMPT, build_user_message
from part7_pro.ingest_pro import get_collection

client = OpenAI(api_key=config.OPENROUTER_API_KEY, base_url=config.OPENROUTER_BASE_URL)
collection = get_collection()
reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")   # ~90 MB, runs on CPU

CANDIDATES = 20        # how many each search method returns before fusion
OFFICE_WORDS = {"germany": ["germany", "german", "berlin"],
                "india": ["india", "indian", "bengaluru", "bangalore"]}


# --- 1. Understand the question -------------------------------------------------
def detect_office(question: str) -> str | None:
    q = question.lower()
    found = [office for office, words in OFFICE_WORDS.items() if any(w in q for w in words)]
    return found[0] if len(found) == 1 else None


def tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


# --- 2. Two ways to search --------------------------------------------------------
def vector_search(question: str, where: dict | None) -> list[str]:
    res = collection.query(query_texts=[question], n_results=CANDIDATES, where=where)
    return res["ids"][0]


def keyword_search(question: str, where: dict | None) -> list[str]:
    """BM25 over the same chunks. Built per query: fine for thousands of chunks."""
    data = collection.get(where=where)
    if not data["ids"]:
        return []
    bm25 = BM25Okapi([tokenize(doc) for doc in data["documents"]])
    scores = bm25.get_scores(tokenize(question))
    ranked = sorted(zip(data["ids"], scores), key=lambda x: -x[1])
    return [doc_id for doc_id, score in ranked[:CANDIDATES] if score > 0]


def reciprocal_rank_fusion(*rankings: list[str], k: int = 60) -> list[str]:
    """Merge rankings: an id scores 1/(k + rank) in every list it appears in."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores, key=lambda d: -scores[d])


# --- 3. Rerank the candidates with a cross-encoder --------------------------------
def rerank(question: str, ids: list[str], top_k: int) -> list[dict]:
    if not ids:
        return []
    data = collection.get(ids=ids)
    chunks = [{"id": i, "text": t, "metadata": m}
              for i, t, m in zip(data["ids"], data["documents"], data["metadatas"])]
    scores = reranker.predict([(question, c["text"]) for c in chunks])
    for c, s in zip(chunks, scores):
        c["score"] = float(s)
    return sorted(chunks, key=lambda c: -c["score"])[:top_k]


def retrieve(question: str, k: int = config.TOP_K, office: str | None = None) -> list[dict]:
    office = office or detect_office(question)
    where = {"office": {"$in": [office, "all"]}} if office else None
    fused = reciprocal_rank_fusion(vector_search(question, where), keyword_search(question, where))
    return rerank(question, fused[:CANDIDATES], top_k=k)


# --- 4. Generate -------------------------------------------------------------------
def ask(question: str, office: str | None = None) -> dict:
    chunks = retrieve(question, office=office)
    response = client.chat.completions.create(
        model=config.CHAT_MODEL, temperature=0,
        messages=[{"role": "system", "content": SYSTEM_PROMPT},
                  {"role": "user", "content": build_user_message(question, chunks, office)}],
    )
    return {"answer": response.choices[0].message.content,
            "sources": [c["metadata"]["source"] for c in chunks],
            "chunks": chunks}


if __name__ == "__main__":
    while (q := input("\nAsk HR> ").strip()) not in {"", "exit", "quit"}:
        r = ask(q)
        for c in r["chunks"]:
            print(f"  {c['score']:6.2f}  {c['id']}")
        print(r["answer"])
