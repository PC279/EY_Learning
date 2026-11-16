"""LlamaIndex query engine for Ask HR.
Run:  python -m part4_llamaindex.ask
"""
from llama_index.core import ChatPromptTemplate, VectorStoreIndex
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core.vector_stores import FilterOperator, MetadataFilter, MetadataFilters

import config
from part2_by_hand.prompts import SYSTEM_PROMPT
from part4_llamaindex.settings import get_vector_store

# LlamaIndex labels each passage with its metadata (source, office), not with [1], [2]...
SYSTEM = SYSTEM_PROMPT.replace(
    "cite the passages it relies on, like [1] or [2][3].",
    "cite the source file it relies on, like [travel_policy.md].",
)

QA_TEMPLATE = ChatPromptTemplate(message_templates=[
    ChatMessage(role=MessageRole.SYSTEM, content=SYSTEM),
    ChatMessage(role=MessageRole.USER, content=(
        "Employee's office: {office}\n\n"
        "Context passages:\n{context_str}\n\n"
        "Question: {query_str}")),
])

index = VectorStoreIndex.from_vector_store(get_vector_store())   # no re-embedding


def make_query_engine(office: str | None = None):
    filters = None
    if office:
        filters = MetadataFilters(filters=[
            MetadataFilter(key="office", value=[office, "all"], operator=FilterOperator.IN)
        ])
    return index.as_query_engine(
        similarity_top_k=config.TOP_K,
        filters=filters,
        text_qa_template=QA_TEMPLATE.partial_format(office=office or "unknown"),
        response_mode="compact",       # stuff all retrieved chunks into one prompt
    )


def ask(question: str, office: str | None = None) -> dict:
    response = make_query_engine(office).query(question)
    return {"answer": str(response),
            "sources": [n.node.metadata["source"] for n in response.source_nodes]}


if __name__ == "__main__":
    engine = make_query_engine()
    while (q := input("\nAsk HR> ").strip()) not in {"", "exit", "quit"}:
        response = engine.query(q)
        for n in response.source_nodes:
            print(f"  {n.score:.3f}  {n.node.metadata['source']}  {n.node.get_content()[:60]!r}")
        print(response)
