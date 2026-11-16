"""Conversational Ask HR with a LlamaIndex chat engine.
Run:  python -m part4_llamaindex.chat
"""
from part4_llamaindex.ask import SYSTEM, index

chat_engine = index.as_chat_engine(
    chat_mode="condense_plus_context",   # rewrite follow-ups, then retrieve, then answer
    system_prompt=SYSTEM,
    similarity_top_k=4,
)

if __name__ == "__main__":
    while (q := input("\nYou> ").strip()) not in {"", "exit", "quit"}:
        print("Ask HR>", chat_engine.chat(q))
