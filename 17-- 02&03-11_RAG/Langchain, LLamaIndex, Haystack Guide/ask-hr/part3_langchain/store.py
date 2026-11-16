"""Shared pieces: the embedding model and the vector store (used by ingest and ask)."""
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

import config

COLLECTION = "ask_hr_langchain"


def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name=config.EMBED_MODEL,
        encode_kwargs={"normalize_embeddings": True},
    )


def get_vectorstore():
    return Chroma(
        collection_name=COLLECTION,
        embedding_function=get_embeddings(),
        persist_directory=str(config.DB_DIR),
        collection_configuration={"hnsw": {"space": "cosine"}},
    )
