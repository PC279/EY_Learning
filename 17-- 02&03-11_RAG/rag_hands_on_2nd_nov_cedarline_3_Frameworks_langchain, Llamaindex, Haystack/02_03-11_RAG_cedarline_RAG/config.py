"""
config.py
---------
All the settings for the project live in this one file.
If you want to change something (chunk size, AI model, folder names),
change it here and every task script will use the new value.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Hide two harmless warnings that confuse beginners (mostly on Windows).
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

# ---------------------------------------------------------------
# Folders
# ---------------------------------------------------------------
# PROJECT_DIR = the folder that contains this config.py file.
PROJECT_DIR = Path(__file__).resolve().parent

# Read secret values (API keys) from the .env file in the project folder.
load_dotenv(PROJECT_DIR / ".env")

DOCUMENTS_DIR = PROJECT_DIR / "Documents"   # where the .txt files are
CHROMA_DIR = PROJECT_DIR / "chroma_db"      # where ChromaDB saves its data
COLLECTION_NAME = "cedarline_docs"          # like a "table name" in ChromaDB

# ---------------------------------------------------------------
# Tokenizing and chunking (Task 1 and Task 2)
# ---------------------------------------------------------------
TOKEN_ENCODING = "cl100k_base"   # the tiktoken encoding used by GPT-4 style models
CHUNK_SIZE = 120                 # tokens per chunk
CHUNK_OVERLAP = 20               # tokens shared between neighbouring chunks

# ---------------------------------------------------------------
# Embeddings and search (Task 2 and Task 3)
# ---------------------------------------------------------------
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"  # runs locally, 384 numbers per text
TOP_K = 2                        # how many chunks to retrieve for each question

# ---------------------------------------------------------------
# AI model (Task 4)
# ---------------------------------------------------------------
# Choose ONE provider in your .env file: gemini, openai, anthropic or openrouter
AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").strip().lower()

# Default model for each provider. You can override it with AI_MODEL in .env
DEFAULT_MODELS = {
    "gemini": "gemini-flash-latest",
    "openai": "gpt-5-mini",
    "anthropic": "claude-haiku-5-5",
    "openrouter": "openrouter/free",   # picks any currently free model
}
AI_MODEL = os.getenv("AI_MODEL", "").strip() or DEFAULT_MODELS.get(AI_PROVIDER, "")

# ---------------------------------------------------------------
# The five test questions from the exercise PDF
# ---------------------------------------------------------------
TEST_QUESTIONS = [
    "How many annual leave days do employees receive?",
    "Which days must employees work from the office?",
    "How quickly should a lost company laptop be reported?",
    "How quickly are Priority 1 incidents acknowledged?",
    "What is the company travel allowance per day?",
]
