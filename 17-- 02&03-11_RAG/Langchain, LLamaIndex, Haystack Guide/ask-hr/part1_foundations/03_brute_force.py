"""1.4 Retrieval in three lines: brute-force search over all Nimbus chunks."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from sentence_transformers import SentenceTransformer

import config
from part2_by_hand.chunking import chunk_records
from part2_by_hand.loaders import load_all

chunks = [c["text"] for c in chunk_records(load_all(config.DATA_DIR), config.CHUNK_SIZE, config.CHUNK_OVERLAP)]
model = SentenceTransformer(config.EMBED_MODEL)
chunk_vecs = model.encode(chunks, normalize_embeddings=True)          # shape (29, 384)
q_vec = model.encode("I left my laptop in a taxi, what now?", normalize_embeddings=True)

scores = chunk_vecs @ q_vec               # one dot product per chunk
top_k = np.argsort(-scores)[:4]
for i in top_k:
    print(round(float(scores[i]), 2), chunks[i][:80].replace("\n", " "))
