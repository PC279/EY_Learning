"""Run the 15 test questions against any version of Ask HR.

Usage (from the project root):
    python -m eval.run_eval part2_by_hand.ask
    python -m eval.run_eval part3_langchain.ask
Each module must expose  ask(question, office=None) -> {"answer": str, "sources": [str, ...]}
"""
import importlib
import json
import sys
from pathlib import Path

QUESTIONS = json.loads((Path(__file__).parent / "questions.json").read_text(encoding="utf-8"))


def check(item: dict, result: dict) -> tuple[bool, bool]:
    expected = set(item["expected_sources"])
    # retrieval hit: at least one expected source among the retrieved chunks
    # (for "not in the documents" questions there is nothing to retrieve, so count it as a hit)
    hit = (not expected) or bool(expected & set(result["sources"]))
    answer = result["answer"].lower().replace("\u2019", "'")
    correct = all(word.lower() in answer for word in item["must_include"])
    return hit, correct


def main(module_name: str):
    ask = importlib.import_module(module_name).ask
    hits = correct = 0
    for item in QUESTIONS:
        result = ask(item["question"], office=item["office"])
        hit, ok = check(item, result)
        hits += hit
        correct += ok
        flag = ("R" if hit else "r") + ("A" if ok else "a")
        print(f"{item['id']:>2} [{flag}] {item['question']}")
        print(f"        -> {result['answer'][:160]!r}")
        if not ok:
            print(f"        expected: {item['expected']}")
    n = len(QUESTIONS)
    print(f"\nRetrieval hit rate: {hits}/{n}   Answers with expected facts: {correct}/{n}")
    print("Legend: R/r = right source retrieved / missed, A/a = answer contains expected facts / not")


if __name__ == "__main__":
    main(sys.argv[1])
