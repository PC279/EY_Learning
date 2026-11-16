"""LlamaIndex indexing: readers -> IngestionPipeline (clean, split, embed) -> Chroma.
Run:  python -m part4_llamaindex.ingest
"""
from llama_index.core import Document, SimpleDirectoryReader
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TransformComponent

import config
from part2_by_hand.loaders import load_csv, load_html, office_from_name
from part4_llamaindex.settings import Settings, get_vector_store

# What the embedding model and the LLM get to "see" of each node's metadata.
HIDDEN_FROM_EMBEDDING = ["file_name", "file_path", "file_type", "file_size", "creation_date",
                         "last_modified_date", "last_accessed_date", "page_label", "row", "is_faq"]
HIDDEN_FROM_LLM = HIDDEN_FROM_EMBEDDING


def file_metadata(path: str) -> dict:
    """Called by SimpleDirectoryReader for every file: our extra metadata."""
    from pathlib import Path
    p = Path(path)
    return {"source": p.name, "office": office_from_name(p), "file_path": str(p)}


def load_documents() -> list[Document]:
    data = config.DATA_DIR
    docs = SimpleDirectoryReader(
        input_files=[data / "employee_handbook.pdf", data / "leave_policy_india.md",
                     data / "leave_policy_germany.md", data / "travel_policy.md"],
        file_metadata=file_metadata,
    ).load_data()                                   # PDF: one Document per page
    # Formats where our own Part 2 loaders do a better job:
    for rec in load_html(data / "it_security.html") + load_csv(data / "hr_faq.csv"):
        docs.append(Document(text=rec["text"], metadata=rec["metadata"]))

    for d in docs:
        d.excluded_embed_metadata_keys = HIDDEN_FROM_EMBEDDING
        d.excluded_llm_metadata_keys = HIDDEN_FROM_LLM
    return docs


class StripPdfHeaders(TransformComponent):
    """A custom pipeline step: remove the handbook's repeating header/footer lines."""

    def __call__(self, nodes, **kwargs):
        for node in nodes:
            lines = node.get_content().splitlines()
            node.set_content("\n".join(
                ln for ln in lines
                if not ln.startswith(("Nimbus Corp Employee Handbook - Internal", "Version 2026"))
            ))
        return nodes


def main():
    docs = load_documents()
    pipeline = IngestionPipeline(
        transformations=[
            StripPdfHeaders(),
            SentenceSplitter(chunk_size=200, chunk_overlap=30),   # TOKENS, not characters
            Settings.embed_model,                                  # embedding is a step too
        ],
        vector_store=get_vector_store(reset=True),
    )
    nodes = pipeline.run(documents=docs, show_progress=True)
    print(f"{len(docs)} documents -> {len(nodes)} nodes stored")


if __name__ == "__main__":
    main()
