"""One place for settings. Every script imports this."""
import os

from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
CHAT_MODEL = os.getenv("CHAT_MODEL", "openai/gpt-oss-120b:free")       # must support tool calling
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "z-ai/glm-4.5-air:free")  # used by ModelFallbackMiddleware
TODAY = "2026-11-04"
