"""Query pipeline: embed question -> retrieve -> prompt -> generate.
Run from the project root:  python -m part2_by_hand.ask
"""
import argparse

from openai import OpenAI

import config
from part2_by_hand.ingest import get_collection
from part2_by_hand.prompts import SYSTEM_PROMPT, build_user_message

client = OpenAI(api_key=config.OPENROUTER_API_KEY, base_url=config.OPENROUTER_BASE_URL)
collection = get_collection()


def retrieve(question: str, k: int = config.TOP_K, office: str | None = None) -> list[dict]:
    where = {"office": {"$in": [office, "all"]}} if office else None
    res = collection.query(
        query_texts=[question], n_results=k, where=where,
        include=["documents", "metadatas", "distances"],
    )
    return [
        {"text": doc, "metadata": meta, "distance": dist}
        for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0])
    ]


def generate(question: str, chunks: list[dict], office: str | None) -> str:
    response = client.chat.completions.create(
        model=config.CHAT_MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_message(question, chunks, office)},
        ],
    )
    return response.choices[0].message.content


def ask(question: str, office: str | None = None) -> dict:
    """The interface every version of Ask HR shares."""
    chunks = retrieve(question, office=office)
    return {
        "answer": generate(question, chunks, office),
        "sources": [c["metadata"]["source"] for c in chunks],
        "chunks": chunks,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--office", choices=["india", "germany"], default=None)
    parser.add_argument("--show-chunks", action="store_true")
    args = parser.parse_args()

    while True:
        question = input("\nAsk HR> ").strip()
        if question.lower() in {"", "exit", "quit"}:
            break
        result = ask(question, office=args.office)
        if args.show_chunks:
            for c in result["chunks"]:
                print(f"  {c['distance']:.3f}  {c['metadata']['source']}  {c['text'][:70]!r}")
        print(result["answer"])
