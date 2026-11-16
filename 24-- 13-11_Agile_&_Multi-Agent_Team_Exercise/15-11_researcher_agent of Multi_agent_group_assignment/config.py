"""Shared settings for all three agents.

Loads API keys from the .env file and builds the LLM every agent uses,
so the model name and OpenRouter setup live in one place.
"""

import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Read OPENROUTER_API_KEY and TAVILY_API_KEY from .env into environment variables.
load_dotenv()

# Free NVIDIA model on OpenRouter. Change it here and every agent picks it up.
MODEL_NAME = "nvidia/nemotron-3.5-super-vl:free"


def get_llm() -> ChatOpenAI:
    """Return a chat model that talks to OpenRouter.

    OpenRouter speaks the same API as OpenAI, so we use ChatOpenAI and
    just point it at OpenRouter's URL.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        # Without this check, ChatOpenAI complains about OPENAI_API_KEY, which is confusing.
        raise ValueError("OPENROUTER_API_KEY is missing. Add it to your .env file.")

    return ChatOpenAI(
        model=MODEL_NAME,
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        timeout=60,      # free endpoints can be slow; give up after 60 seconds
        max_retries=2,   # retry a couple of times, since free endpoints sometimes fail
    )
