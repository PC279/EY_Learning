"""Global LlamaIndex settings + the shared vector store."""
import chromadb
from llama_index.core import Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openrouter import OpenRouter
from llama_index.vector_stores.chroma import ChromaVectorStore

import config

COLLECTION = "ask_hr_llamaindex"

Settings.embed_model = HuggingFaceEmbedding(model_name=config.EMBED_MODEL)  # normalises by default
Settings.llm = OpenRouter(
    model=config.CHAT_MODEL,
    api_key=config.OPENROUTER_API_KEY,
    temperature=0,
    max_tokens=1024,          # the default is only 256: long answers get cut off
)


def get_vector_store(reset: bool = False) -> ChromaVectorStore:
    client = chromadb.PersistentClient(path=str(config.DB_DIR))
    if reset and COLLECTION in [c.name for c in client.list_collections()]:
        client.delete_collection(COLLECTION)
    collection = client.get_or_create_collection(
        COLLECTION, configuration={"hnsw": {"space": "cosine"}}
    )
    return ChromaVectorStore(chroma_collection=collection)
