import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
CHAT_MODEL = os.getenv("CHAT_MODEL", "openai/gpt-oss-120b:free")   # must support tool calling
TODAY = "2026-11-04"           # fixed "today" so the test tasks always behave the same
MAX_STEPS = 10                 # hard limit on agent loop iterations
