"""LLM-as-judge: grade each answer for correctness and faithfulness.
Usage:  python -m eval.judge part7_pro.ask_pro
"""
import importlib
import json
import re
import sys

from openai import OpenAI

import config
from eval.run_eval import QUESTIONS

JUDGE_MODEL = config.CHAT_MODEL       # ideally a stronger model than the one being judged
client = OpenAI(api_key=config.OPENROUTER_API_KEY, base_url=config.OPENROUTER_BASE_URL)

JUDGE_PROMPT = """You are grading an HR assistant. Reply with JSON only:
{{"correct": true|false, "faithful": true|false, "reason": "<one sentence>"}}

- correct: the answer agrees with the reference answer (wording may differ;
  for "Not in the documents", the assistant must say it couldn't find it).
- faithful: every claim in the answer is supported by the passages
  (general world knowledge such as flight durations is allowed).

Question: {question}
Reference answer: {expected}
Passages the assistant saw:
{passages}
Assistant's answer: {answer}"""


def judge(item: dict, result: dict) -> dict:
    passages = "\n---\n".join(c["text"] for c in result.get("chunks", [])) or "(not available)"
    reply = client.chat.completions.create(
        model=JUDGE_MODEL, temperature=0,
        messages=[{"role": "user", "content": JUDGE_PROMPT.format(
            question=item["question"], expected=item["expected"],
            passages=passages, answer=result["answer"])}],
    ).choices[0].message.content
    match = re.search(r"\{.*\}", reply, re.S)          # tolerate text around the JSON
    return json.loads(match.group(0)) if match else {"correct": False, "faithful": False,
                                                     "reason": f"unparseable: {reply[:80]}"}


def main(module_name: str):
    ask = importlib.import_module(module_name).ask
    correct = faithful = 0
    for item in QUESTIONS:
        verdict = judge(item, ask(item["question"], office=item["office"]))
        correct += verdict["correct"]
        faithful += verdict["faithful"]
        print(f"{item['id']:>2} correct={verdict['correct']!s:5} faithful={verdict['faithful']!s:5} "
              f"{verdict['reason']}")
    n = len(QUESTIONS)
    print(f"\nCorrect: {correct}/{n}   Faithful: {faithful}/{n}")


if __name__ == "__main__":
    main(sys.argv[1])
