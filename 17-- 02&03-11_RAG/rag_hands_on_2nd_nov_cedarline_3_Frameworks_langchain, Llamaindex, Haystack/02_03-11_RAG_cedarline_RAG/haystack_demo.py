"""Haystack version of the same RAG retrieval pipeline.

Reads every .txt file in Documents/, splits it with Haystack's token splitter, embeds with the
project's local all-MiniLM-L6-v2 model, stores the chunks in a SEPARATE collection inside the
project's chroma_db folder, then lets you search interactively.
Run:  python haystack_demo.py      (type 'exit' or press Enter on an empty line to stop)
"""
from dataclasses import replace

from haystack import Document, Pipeline, component
from haystack.components.preprocessors import DocumentSplitter
from haystack.components.writers import DocumentWriter
from haystack.document_stores.types import DuplicatePolicy
from haystack_integrations.components.retrievers.chroma import ChromaEmbeddingRetriever
from haystack_integrations.document_stores.chroma import ChromaDocumentStore

import config
from rag_helpers import load_documents, embed_texts

COLLECTION = "haystack_cedarline"   # separate collection, so the other versions' data is not touched
CHUNK_SIZE = 180
CHUNK_OVERLAP = 35
TOP_K = 3


# ---------------------------------------------------------------
# Custom components: small building blocks that plug into a Haystack Pipeline.
# Each one has a run() method and declares what it outputs.
# ---------------------------------------------------------------
@component
class ChunkLabeller:
    """Gives every chunk a readable ID: hs_chunk_001, hs_chunk_002, ..."""

    @component.output_types(documents=list[Document])
    def run(self, documents: list[Document]):
        labelled = []
        for i, doc in enumerate(documents, start=1):
            chunk_id = f"hs_chunk_{i:03d}"
            # Keep the labels, drop "_split_overlap" (a list ChromaDB cannot store), add chunk_id
            meta = {k: v for k, v in doc.meta.items() if k != "_split_overlap"}
            meta["chunk_id"] = chunk_id
            # replace() makes an updated COPY of the chunk (Haystack's recommended way)
            labelled.append(replace(doc, id=chunk_id, meta=meta))
        return {"documents": labelled}


@component
class LocalDocumentEmbedder:
    """Embeds many chunks with our local all-MiniLM-L6-v2 model (from rag_helpers.py)."""

    @component.output_types(documents=list[Document])
    def run(self, documents: list[Document]):
        vectors = embed_texts([doc.content for doc in documents])
        embedded = [replace(doc, embedding=vector) for doc, vector in zip(documents, vectors)]
        return {"documents": embedded}


@component
class LocalTextEmbedder:
    """Embeds one question with the SAME local model."""

    @component.output_types(embedding=list[float])
    def run(self, text: str):
        return {"embedding": embed_texts([text])[0]}


def get_document_store():
    """Open (or create) the collection inside the project's chroma_db folder."""
    return ChromaDocumentStore(
        collection_name=COLLECTION,
        persist_path=str(config.CHROMA_DIR),
        distance_function="cosine",
        client_settings={"anonymized_telemetry": False},
    )


def build_search_pipeline(document_store):
    """Question text -> embedding -> top K closest chunks."""
    pipeline = Pipeline()
    pipeline.add_component("text_embedder", LocalTextEmbedder())
    pipeline.add_component("retriever", ChromaEmbeddingRetriever(document_store, top_k=TOP_K))
    pipeline.connect("text_embedder.embedding", "retriever.query_embedding")
    return pipeline


def main():
    # STEP 1: READ DOCUMENTS
    documents = [
        Document(content=text, meta={"source": f"Documents/{filename}"})
        for filename, text in load_documents().items()
    ]
    for doc in documents:
        print("Document loaded:", doc.meta["source"])

    # STEP 2 + 3: CHUNK, EMBED AND STORE WITH AN INDEXING PIPELINE
    document_store = get_document_store()
    document_store.delete_all_documents(recreate_index=True)   # start fresh, never store chunks twice

    indexing = Pipeline()
    indexing.add_component("splitter", DocumentSplitter(
        split_by="token",
        split_length=CHUNK_SIZE,
        split_overlap=CHUNK_OVERLAP,
        tokenizer_encoding=config.TOKEN_ENCODING,
    ))
    indexing.add_component("labeller", ChunkLabeller())
    indexing.add_component("embedder", LocalDocumentEmbedder())
    indexing.add_component("writer", DocumentWriter(document_store, policy=DuplicatePolicy.OVERWRITE))

    indexing.connect("splitter.documents", "labeller.documents")
    indexing.connect("labeller.documents", "embedder.documents")
    indexing.connect("embedder.documents", "writer.documents")

    result = indexing.run(
        {"splitter": {"documents": documents}},
        include_outputs_from={"labeller"},   # also give back the chunks, so we can print them
    )
    chunks = result["labeller"]["documents"]

    print(f"\nChunk size: {CHUNK_SIZE} tokens | Overlap: {CHUNK_OVERLAP} tokens")
    print("Total chunks:", len(chunks))
    print("First chunk:", chunks[0].content[:130])
    print("Stored chunks:", document_store.count_documents(),
          f"in collection '{COLLECTION}' at {config.CHROMA_DIR.relative_to(config.PROJECT_DIR)}")

    # STEP 4: SEARCH AND RETRIEVE WITH A SEARCH PIPELINE
    search = build_search_pipeline(document_store)
    while True:
        try:
            question = input("\nEnter your question (exit to stop): ").strip()
        except EOFError:
            break
        if question.lower() in {"", "exit", "quit"}:
            break

        results = search.run({"text_embedder": {"text": question}})
        for doc in results["retriever"]["documents"]:
            print("\n" + "-" * 60)
            print("Chunk:", doc.meta["chunk_id"])
            print("Source:", doc.meta["source"])
            print("Cosine distance:", round(doc.score, 4))   # Chroma's distance, unchanged
            print("Text:", doc.content)


if __name__ == "__main__":
    main()