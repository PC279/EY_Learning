"""1.3 Embeddings and cosine similarity on Nimbus sentences."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sentence_transformers import SentenceTransformer
import config

model = SentenceTransformer(config.EMBED_MODEL)  # downloads ~90 MB the first time

question = "I left my laptop in a taxi, what now?"
sentences = [
    "If a company device is lost or stolen, notify the IT helpdesk within one hour.",
    "Employees in India receive 21 working days of annual leave.",
    "Hotel stays in Berlin are capped at 150 euros per night.",
    "Salary is credited on the last working day of each month.",
]
q_vec = model.encode(question, normalize_embeddings=True)
s_vecs = model.encode(sentences, normalize_embeddings=True)
print(q_vec.shape, q_vec[:5])
scores = model.similarity(q_vec, s_vecs)[0]
for s, score in sorted(zip(sentences, scores), key=lambda x: -x[1]):
    print(f"{score:.2f}  {s}")
