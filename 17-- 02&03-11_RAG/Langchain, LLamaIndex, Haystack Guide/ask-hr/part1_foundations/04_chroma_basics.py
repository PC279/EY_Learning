"""1.4 ChromaDB basics: collection, upsert, query, metadata filter."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
import config

client = chromadb.PersistentClient(path=str(config.DB_DIR))
embed_fn = SentenceTransformerEmbeddingFunction(model_name=config.EMBED_MODEL, normalize_embeddings=True)
collection = client.get_or_create_collection(
    name="nimbus_demo", embedding_function=embed_fn, configuration={"hnsw": {"space": "cosine"}})

collection.upsert(
    ids=["it::lost", "leave_in::annual", "travel::hotel_de"],
    documents=[
        "If a company device is lost or stolen, notify the IT helpdesk within one hour.",
        "Employees in India receive 21 working days of annual leave.",
        "Hotel stays in Germany are capped at 150 euros per night.",
    ],
    metadatas=[
        {"source": "it_security.html", "office": "all"},
        {"source": "leave_policy_india.md", "office": "india"},
        {"source": "travel_policy.md", "office": "germany"},
    ],
)

results = collection.query(query_texts=["I left my laptop in a taxi"], n_results=2,
                           include=["documents", "metadatas", "distances"])
for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
    print(f"{dist:.3f}  {meta['source']}: {doc}")

results_de = collection.query(query_texts=["hotel limit per night"], n_results=2,
                              where={"office": {"$in": ["germany", "all"]}})
print(results_de["documents"][0])
print("count:", collection.count())
