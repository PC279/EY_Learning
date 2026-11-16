"""Settings read from environment variables or a local .env file."""
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).parent
load_dotenv(PROJECT_DIR / ".env")  # real OS environment variables still take precedence

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
# Anchored to the project folder so PyCharm and the terminal always use the same file
DB_PATH = str(PROJECT_DIR / os.getenv("DB_PATH", "trips.db"))
