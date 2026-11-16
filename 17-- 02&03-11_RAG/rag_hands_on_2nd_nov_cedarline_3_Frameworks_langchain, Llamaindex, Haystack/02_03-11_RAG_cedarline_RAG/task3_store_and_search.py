"""
TASK 3 - Store and search in ChromaDB
-------------------------------------
1. Create a persistent ChromaDB database inside the project (folder: chroma_db).
2. Save every chunk, its embedding and its source filename.
3. Ask a question and show the top 2 chunks with their cosine distances.
"""

import config
from rag_helpers import load_documents, chunk_all_documents, embed_texts, get_collection, search


def build_database():
    """Chunk the documents, embed the chunks and save everything in ChromaDB."""
    documents = load_documents()
    chunks = chunk_all_documents(documents)
    vectors = embed_texts([c["text"] for c in chunks])

    collection = get_collection(reset=True)  # start fresh every time
    collection.add(
        ids=[c["id"] for c in chunks],                     # unique name for each chunk
        documents=[c["text"] for c in chunks],             # the chunk text
        embeddings=vectors,                                # the 384-number vector
        metadatas=[{"source": c["source"],                 # the source filename
                    "chunk_index": c["chunk_index"]} for c in chunks],
    )

    print("=" * 70)
    print("CHROMADB DATABASE")
    print("=" * 70)
    print(f"Database folder : {config.CHROMA_DIR}")
    print(f"Collection      : {config.COLLECTION_NAME}")
    print(f"Chunks stored   : {collection.count()}")

    # Read one record back to prove the text, embedding and source were saved.
    record = collection.get(ids=[chunks[0]["id"]], include=["documents", "metadatas", "embeddings"])
    print("\nExample stored record:")
    print(f"  id        : {record['ids'][0]}")
    print(f"  source    : {record['metadatas'][0]['source']}")
    print(f"  embedding : {len(record['embeddings'][0])} numbers")
    print(f"  text      : {record['documents'][0][:70].replace(chr(10), ' ')}...")
    print()


def show_search_results(question):
    """Search ChromaDB and print the top chunks with their cosine distances."""
    matches = search(question, top_k=config.TOP_K)

    print("=" * 70)
    print(f"QUESTION: {question}")
    print("=" * 70)
    for rank, m in enumerate(matches, start=1):
        print(f"\nResult {rank}")
        print(f"  Source          : {m['source']} (chunk {m['chunk_index']})")
        print(f"  Cosine distance : {m['distance']:.4f}   (smaller = more similar)")
        print("  Text:")
        for line in m["text"].strip().splitlines():
            print(f"    {line}")
    print()


def main():
    build_database()

    default_question = config.TEST_QUESTIONS[0]
    question = input(f"Type a question (or press Enter to use: '{default_question}')\n> ").strip()
    show_search_results(question or default_question)

    # Let the user try more questions.
    while True:
        question = input("Type another question, or press Enter to finish\n> ").strip()
        if not question:
            break
        show_search_results(question)

    print("Done. The database is saved in the chroma_db folder.")


if __name__ == "__main__":
    main()
