"""
rag_helpers.py
--------------
Small reusable functions. Each task script imports what it needs from here,
so the same code is not copied into four files.

    load_documents()        -> read every .txt file in the Documents folder
    count_tokens(text)      -> how many tokens a text has
    chunk_text(text)        -> split one text into overlapping token chunks
    chunk_all_documents()   -> chunk every document and label each chunk
    embed_texts(texts)      -> turn texts into embedding vectors
    get_collection()        -> open (or create) the ChromaDB collection
    search(question)        -> find the closest chunks for a question
"""

import tiktoken

import config

# Load the tokenizer once and reuse it everywhere.
encoder = tiktoken.get_encoding(config.TOKEN_ENCODING)


# ---------------------------------------------------------------
# Task 1: reading and tokenizing
# ---------------------------------------------------------------
def load_documents():
    """Read every .txt file in the Documents folder.

    Returns a dictionary:  { "file_name.txt": "full text of the file", ... }
    """
    documents = {}
    for file_path in sorted(config.DOCUMENTS_DIR.glob("*.txt")):
        documents[file_path.name] = file_path.read_text(encoding="utf-8")

    if not documents:
        raise FileNotFoundError(
            f"No .txt files found in {config.DOCUMENTS_DIR}. "
            "Copy the two supplied documents into the Documents folder."
        )
    return documents


def count_tokens(text):
    """Return the number of tokens in a piece of text."""
    return len(encoder.encode(text))


# ---------------------------------------------------------------
# Task 2: chunking
# ---------------------------------------------------------------
def chunk_text(text, chunk_size=config.CHUNK_SIZE, overlap=config.CHUNK_OVERLAP):
    """Split text into chunks of `chunk_size` tokens.

    Each new chunk starts (chunk_size - overlap) tokens after the previous one,
    so neighbouring chunks share `overlap` tokens.
    Example with 120 / 20:  chunk 1 = tokens 0-119, chunk 2 = tokens 100-219, ...
    """
    tokens = encoder.encode(text)          # text  -> list of token IDs
    step = chunk_size - overlap            # 120 - 20 = 100
    chunks = []

    for start in range(0, len(tokens), step):
        end = start + chunk_size
        chunk_tokens = tokens[start:end]           # take 120 token IDs
        chunks.append(encoder.decode(chunk_tokens))  # token IDs -> text
        if end >= len(tokens):                     # reached the end of the text
            break

    return chunks


def chunk_all_documents(documents):
    """Chunk every document and attach labels to each chunk.

    Returns a list of dictionaries, one per chunk, for example:
    {
        "id": "Employee_Workplace_Policy.txt_chunk_0",
        "text": "CEDARLINE SYSTEMS - EMPLOYEE ...",
        "source": "Employee_Workplace_Policy.txt",
        "chunk_index": 0,
        "token_count": 120,
    }
    """
    all_chunks = []
    for file_name, text in documents.items():
        for index, chunk in enumerate(chunk_text(text)):
            all_chunks.append({
                "id": f"{file_name}_chunk_{index}",
                "text": chunk,
                "source": file_name,
                "chunk_index": index,
                "token_count": count_tokens(chunk),
            })
    return all_chunks


# ---------------------------------------------------------------
# Task 2: embeddings
# ---------------------------------------------------------------
_embedding_model = None  # loaded the first time it is needed, then reused


def get_embedding_model():
    """Load the all-MiniLM-L6-v2 model (downloaded automatically the first time)."""
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        print(f"Loading embedding model '{config.EMBEDDING_MODEL_NAME}' ...")
        _embedding_model = SentenceTransformer(config.EMBEDDING_MODEL_NAME)
    return _embedding_model


def embed_texts(texts):
    """Turn a list of texts into a list of vectors (each vector = 384 numbers)."""
    model = get_embedding_model()
    vectors = model.encode(texts, normalize_embeddings=True)
    return vectors.tolist()  # convert from a NumPy array to plain Python lists


# ---------------------------------------------------------------
# Task 3: ChromaDB
# ---------------------------------------------------------------
def get_collection(reset=False):
    """Open the persistent ChromaDB collection.

    reset=True deletes the old collection first, so re-running Task 3
    never stores the same chunk twice.
    """
    import chromadb
    from chromadb.config import Settings

    client = chromadb.PersistentClient(
        path=str(config.CHROMA_DIR),
        settings=Settings(anonymized_telemetry=False),
    )

    if reset:
        try:
            client.delete_collection(config.COLLECTION_NAME)
        except Exception:
            pass  # it did not exist yet, which is fine

    return client.get_or_create_collection(
        name=config.COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},  # measure closeness with cosine distance
    )


def search(question, top_k=config.TOP_K):
    """Find the top_k chunks whose meaning is closest to the question.

    Returns a list like:
    [ {"text": ..., "source": ..., "chunk_index": ..., "distance": 0.31}, ... ]
    """
    collection = get_collection()
    if collection.count() == 0:
        raise RuntimeError("The ChromaDB collection is empty. Run task3_store_and_search.py first.")

    question_vector = embed_texts([question])  # the question is embedded with the SAME model

    results = collection.query(
        query_embeddings=question_vector,
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    # ChromaDB returns one list per question. We asked one question, so take item [0].
    matches = []
    for text, metadata, distance in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        matches.append({
            "text": text,
            "source": metadata["source"],
            "chunk_index": metadata["chunk_index"],
            "distance": distance,
        })
    return matches
