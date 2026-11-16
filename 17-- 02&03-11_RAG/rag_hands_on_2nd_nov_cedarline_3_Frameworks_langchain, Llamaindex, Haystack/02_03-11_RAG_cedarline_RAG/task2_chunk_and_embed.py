"""
TASK 2 - Chunk and embed
------------------------
1. Split both documents into chunks of 120 tokens with a 20-token overlap.
2. Print the number of chunks and one sample chunk.
3. Create embeddings with all-MiniLM-L6-v2 and show the vector size.
"""

import config
from rag_helpers import load_documents, chunk_all_documents, embed_texts


def main():
    documents = load_documents()
    chunks = chunk_all_documents(documents)

    # ----- Chunk counts -----
    print("=" * 70)
    print(f"CHUNKING  (chunk size = {config.CHUNK_SIZE} tokens, overlap = {config.CHUNK_OVERLAP} tokens)")
    print("=" * 70)
    for file_name in documents:
        count = sum(1 for c in chunks if c["source"] == file_name)
        print(f"{file_name:<35} {count} chunks")
    print(f"{'TOTAL':<35} {len(chunks)} chunks\n")

    # ----- Every chunk in one short line -----
    print("ALL CHUNKS (first 60 characters of each):")
    for c in chunks:
        preview = c["text"].replace("\n", " ")[:60]
        print(f"  {c['id']:<42} {c['token_count']:>3} tokens | {preview}...")
    print()

    # ----- One full sample chunk -----
    sample = chunks[0]
    print("=" * 70)
    print(f"SAMPLE CHUNK: {sample['id']}  ({sample['token_count']} tokens)")
    print("=" * 70)
    print(sample["text"])
    print("=" * 70 + "\n")

    # ----- Embeddings -----
    texts = [c["text"] for c in chunks]
    vectors = embed_texts(texts)

    print("=" * 70)
    print("EMBEDDINGS")
    print("=" * 70)
    print(f"Embedding model      : {config.EMBEDDING_MODEL_NAME}")
    print(f"Number of embeddings : {len(vectors)}  (one per chunk)")
    print(f"Vector size          : {len(vectors[0])}  numbers per chunk")
    first_five = ", ".join(f"{x:.4f}" for x in vectors[0][:5])
    print(f"First 5 numbers of '{chunks[0]['id']}':")
    print(f"  [{first_five}, ...]")


if __name__ == "__main__":
    main()
