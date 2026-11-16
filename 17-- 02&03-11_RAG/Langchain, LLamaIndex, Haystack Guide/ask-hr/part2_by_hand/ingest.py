"""Indexing pipeline: load -> chunk -> embed -> store.
Run from the project root:  python -m part2_by_hand.ingest
"""
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

import config
from part2_by_hand.chunking import chunk_records
from part2_by_hand.loaders import load_all

COLLECTION = "ask_hr_by_hand"


def get_collection():
    """Open (or create) the collection. Used by ingest AND by ask."""
    client = chromadb.PersistentClient(path=str(config.DB_DIR))
    embed_fn = SentenceTransformerEmbeddingFunction(
        model_name=config.EMBED_MODEL, normalize_embeddings=True
    )
    return client.get_or_create_collection(
        name=COLLECTION,
        embedding_function=embed_fn,
        configuration={"hnsw": {"space": "cosine"}},
        metadata={"embed_model": config.EMBED_MODEL},   # remember which model built it
    )


def make_id(meta: dict) -> str:
    """Deterministic id: same chunk -> same id on every run (no duplicates)."""
    position = meta.get("page", meta.get("row", 0))
    return f"{meta['source']}::{position}::{meta['chunk']}"


def main():
    records = load_all(config.DATA_DIR)
    chunks = chunk_records(records, config.CHUNK_SIZE, config.CHUNK_OVERLAP)
    print(f"Loaded {len(records)} records -> {len(chunks)} chunks")

    collection = get_collection()

    # A file may now produce fewer chunks than last time: clear its old chunks first.
    for source in sorted({c["metadata"]["source"] for c in chunks}):
        collection.delete(where={"source": source})

    collection.upsert(
        ids=[make_id(c["metadata"]) for c in chunks],
        documents=[c["text"] for c in chunks],
        metadatas=[c["metadata"] for c in chunks],
    )   # Chroma calls embed_fn on the documents for us
    print(f"Collection '{COLLECTION}' now holds {collection.count()} chunks")


if __name__ == "__main__":
    main()
