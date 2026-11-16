"""Indexing with structure-aware chunks and contextual headers.
Run:  python -m part7_pro.ingest_pro
"""
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

import config
from part2_by_hand.ingest import make_id
from part2_by_hand.loaders import load_all
from part7_pro.chunking_pro import chunk_records_pro

COLLECTION = "ask_hr_pro"


def get_collection():
    client = chromadb.PersistentClient(path=str(config.DB_DIR))
    return client.get_or_create_collection(
        name=COLLECTION,
        embedding_function=SentenceTransformerEmbeddingFunction(
            model_name=config.EMBED_MODEL, normalize_embeddings=True),
        configuration={"hnsw": {"space": "cosine"}},
    )


def main():
    chunks = chunk_records_pro(load_all(config.DATA_DIR), config.CHUNK_SIZE, config.CHUNK_OVERLAP)
    col = get_collection()
    for source in {c["metadata"]["source"] for c in chunks}:
        col.delete(where={"source": source})
    col.upsert(ids=[make_id(c["metadata"]) for c in chunks],
               documents=[c["text"] for c in chunks],
               metadatas=[c["metadata"] for c in chunks])
    print(f"{len(chunks)} chunks with contextual headers stored")


if __name__ == "__main__":
    main()
