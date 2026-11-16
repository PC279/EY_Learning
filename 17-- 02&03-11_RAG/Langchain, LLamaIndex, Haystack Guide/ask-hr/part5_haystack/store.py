"""Shared Haystack pieces: the document store and the embedding model name."""
from haystack_integrations.document_stores.chroma import ChromaDocumentStore

import config

COLLECTION = "ask_hr_haystack"


def get_document_store() -> ChromaDocumentStore:
    return ChromaDocumentStore(
        collection_name=COLLECTION,
        persist_path=str(config.DB_DIR),
        distance_function="cosine",
    )
