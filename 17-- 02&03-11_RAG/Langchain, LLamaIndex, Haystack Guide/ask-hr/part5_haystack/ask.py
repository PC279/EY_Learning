"""Haystack query pipeline: embed -> retrieve -> build prompt -> generate.
Run:  python -m part5_haystack.ask
"""
from haystack import Pipeline
from haystack.components.builders import ChatPromptBuilder
from haystack.components.generators.chat import OpenAIChatGenerator
from haystack.dataclasses import ChatMessage
from haystack.utils import Secret
from haystack_integrations.components.embedders.sentence_transformers import (
    SentenceTransformersTextEmbedder)
from haystack_integrations.components.retrievers.chroma import ChromaEmbeddingRetriever

import config
from part2_by_hand.prompts import SYSTEM_PROMPT
from part5_haystack.store import get_document_store

USER_TEMPLATE = """Employee's office: {{ office }}

Context passages:
{% for doc in documents %}
[{{ loop.index }}] (source: {{ doc.meta.source }})
{% if doc.meta.question %}Q: {{ doc.meta.question }}
A: {% endif %}{{ doc.content }}
{% endfor %}
Question: {{ question }}"""


def build_query_pipeline() -> Pipeline:
    p = Pipeline()
    p.add_component("text_embedder", SentenceTransformersTextEmbedder(
        model=config.EMBED_MODEL, normalize_embeddings=True, progress_bar=False))
    p.add_component("retriever", ChromaEmbeddingRetriever(get_document_store(), top_k=config.TOP_K))
    p.add_component("prompt_builder", ChatPromptBuilder(
        template=[ChatMessage.from_system(SYSTEM_PROMPT), ChatMessage.from_user(USER_TEMPLATE)],
        required_variables=["question", "documents"],
    ))
    p.add_component("llm", OpenAIChatGenerator(
        api_key=Secret.from_env_var("OPENROUTER_API_KEY"),
        api_base_url=config.OPENROUTER_BASE_URL,
        model=config.CHAT_MODEL,
        generation_kwargs={"temperature": 0},
    ))
    p.connect("text_embedder.embedding", "retriever.query_embedding")
    p.connect("retriever.documents", "prompt_builder.documents")
    p.connect("prompt_builder.prompt", "llm.messages")
    return p


pipeline = build_query_pipeline()


def ask(question: str, office: str | None = None) -> dict:
    filters = ({"field": "meta.office", "operator": "in", "value": [office, "all"]}
               if office else None)
    result = pipeline.run(
        {"text_embedder": {"text": question},
         "retriever": {"filters": filters},
         "prompt_builder": {"question": question, "office": office or "unknown"}},
        include_outputs_from={"retriever"},             # also return the retrieved docs
    )
    docs = result["retriever"]["documents"]
    return {"answer": result["llm"]["replies"][0].text,
            "sources": [d.meta["source"] for d in docs]}


if __name__ == "__main__":
    while (q := input("\nAsk HR> ").strip()) not in {"", "exit", "quit"}:
        print(ask(q)["answer"])
