"""LlamaIndex version of the same RAG retrieval pipeline.

Reads every .txt file in Documents/, splits it with LlamaIndex's sentence splitter, embeds with the
project's local all-MiniLM-L6-v2 model, stores the chunks in a SEPARATE collection inside the
project's chroma_db folder, then lets you search interactively.
Run:  python llamaindex_demo.py      (type 'exit' or press Enter on an empty line to stop)
"""
import math

import chromadb
import tiktoken
from chromadb.config import Settings
from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.chroma import ChromaVectorStore

import config
from rag_helpers import load_documents, embed_texts

COLLECTION = "llamaindex_cedarline"   # separate collection, so Task 3 and LangChain data are not touched
CHUNK_SIZE = 180
CHUNK_OVERLAP = 35
TOP_K = 3


# Reuse our existing local embedding model (all-MiniLM-L6-v2) from rag_helpers.py
class LocalEmbeddings(BaseEmbedding):

    def _get_text_embedding(self, text: str) -> list[float]:          # one chunk
        return embed_texts([text])[0]

    def _get_text_embeddings(self, texts: list[str]) -> list[list[float]]:  # many chunks at once
        return embed_texts(texts)

    def _get_query_embedding(self, query: str) -> list[float]:        # one question
        return embed_texts([query])[0]

    async def _aget_query_embedding(self, query: str) -> list[float]:  # async version (required)
        return self._get_query_embedding(query)


def get_client():
    """Open the same persistent chroma_db folder that Task 3 uses."""
    return chromadb.PersistentClient(
        path=str(config.CHROMA_DIR),
        settings=Settings(anonymized_telemetry=False),
    )


def score_to_distance(score: float) -> float:
    """LlamaIndex's Chroma connector reports similarity = e^(-distance).
    This undoes it, so we can print the same cosine distance as the other versions."""
    return -math.log(score)


def main():
    # STEP 1: READ DOCUMENTS
    documents = [
        Document(text=text, metadata={"source": f"Documents/{filename}"})
        for filename, text in load_documents().items()
    ]
    for doc in documents:
        print("Document loaded:", doc.metadata["source"])

    # STEP 2: CHUNK DOCUMENTS (LlamaIndex calls chunks "nodes")
    splitter = SentenceSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        tokenizer=tiktoken.get_encoding(config.TOKEN_ENCODING).encode,
        include_prev_next_rel=False,
    )
    nodes = splitter.get_nodes_from_documents(documents)
    for i, node in enumerate(nodes, start=1):
        node.id_ = f"li_chunk_{i:03d}"
        node.metadata["chunk_id"] = node.id_
        # Embed only the chunk text (not the labels), just like the other versions
        node.excluded_embed_metadata_keys = ["source", "chunk_id"]

    print(f"\nChunk size: {CHUNK_SIZE} tokens | Overlap: {CHUNK_OVERLAP} tokens")
    print("Total chunks:", len(nodes))
    print("First chunk:", nodes[0].text[:130])

    # STEP 3: STORE IN CHROMADB (same persistent folder as Task 3, separate collection)
    client = get_client()
    try:
        client.delete_collection(COLLECTION)   # start fresh, so chunks are never stored twice
    except Exception:
        pass                                   # it did not exist yet, which is fine

    collection = client.get_or_create_collection(
        COLLECTION, metadata={"hnsw:space": "cosine"}
    )
    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    index = VectorStoreIndex(
        nodes,
        storage_context=storage_context,
        embed_model=LocalEmbeddings(),
    )
    print("Stored chunks:", collection.count(),
          f"in collection '{COLLECTION}' at {config.CHROMA_DIR.relative_to(config.PROJECT_DIR)}")

    # STEP 4: SEARCH AND RETRIEVE
    retriever = index.as_retriever(similarity_top_k=TOP_K)
    while True:
        try:
            question = input("\nEnter your question (exit to stop): ").strip()
        except EOFError:
            break
        if question.lower() in {"", "exit", "quit"}:
            break

        results = retriever.retrieve(question)
        for result in results:
            print("\n" + "-" * 60)
            print("Chunk:", result.node.metadata["chunk_id"])
            print("Source:", result.node.metadata["source"])
            print("Cosine distance:", round(score_to_distance(result.score), 4))
            print("Text:", result.node.get_content())


if __name__ == "__main__":
    main()