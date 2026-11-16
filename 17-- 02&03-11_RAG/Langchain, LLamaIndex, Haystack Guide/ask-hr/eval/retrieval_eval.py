"""Retrieval-only metrics: hit rate@k and MRR. No LLM calls, so it's fast and free.
Usage:  python -m eval.retrieval_eval part2_by_hand.ask
        python -m eval.retrieval_eval part7_pro.ask_pro
The module must expose  retrieve(question, k, office) -> list of chunk dicts with metadata.
"""
import importlib
import sys

from eval.run_eval import QUESTIONS


def main(module_name: str, k: int = 4):
    retrieve = importlib.import_module(module_name).retrieve
    answerable = [q for q in QUESTIONS if q["expected_sources"]]
    hits, reciprocal_ranks = 0, []
    for item in answerable:
        sources = [c["metadata"]["source"] for c in retrieve(item["question"], k=k, office=item["office"])]
        rank = next((i for i, s in enumerate(sources, 1) if s in item["expected_sources"]), None)
        hits += rank is not None
        reciprocal_ranks.append(1 / rank if rank else 0.0)
        print(f"{item['id']:>2} rank={rank or '-'}  {item['question']}")
    n = len(answerable)
    print(f"\nHit rate@{k}: {hits}/{n} = {hits / n:.2f}   MRR: {sum(reciprocal_ranks) / n:.2f}")


if __name__ == "__main__":
    main(sys.argv[1])
