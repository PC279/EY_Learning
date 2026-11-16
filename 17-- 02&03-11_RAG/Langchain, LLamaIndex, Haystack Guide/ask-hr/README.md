# Ask HR — companion code

Code for the doc "RAG from First Principles: Ask HR with LangChain, LlamaIndex & Haystack".

## Setup
    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env        # then put your OpenRouter key in .env

Run everything from this folder with `python -m ...`.

| Part | Build the index | Ask | Test |
|---|---|---|---|
| 1 | `python part1_foundations/04_chroma_basics.py` (and 01–03) | | |
| 2 by hand | `python -m part2_by_hand.ingest` | `python -m part2_by_hand.ask --show-chunks` | `python -m eval.run_eval part2_by_hand.ask` |
| 3 LangChain | `python -m part3_langchain.ingest` | `python -m part3_langchain.ask` / `.chat` / `.agent` | `python -m eval.run_eval part3_langchain.ask` |
| 4 LlamaIndex | `python -m part4_llamaindex.ingest` | `python -m part4_llamaindex.ask` / `.chat` | `python -m eval.run_eval part4_llamaindex.ask` |
| 5 Haystack | `python -m part5_haystack.ingest` | `python -m part5_haystack.ask` | `python -m eval.run_eval part5_haystack.ask` |
| 7 pro | `python -m part7_pro.ingest_pro` | `python -m part7_pro.ask_pro` | `python -m eval.retrieval_eval part7_pro.ask_pro`, `python -m eval.judge part7_pro.ask_pro` |

`data/` holds the fictional Nimbus Corp documents; `eval/questions.json` the 15 test questions.
