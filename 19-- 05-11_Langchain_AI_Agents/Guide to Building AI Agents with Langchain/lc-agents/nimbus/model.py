"""How every script gets a chat model. Change providers here, nowhere else."""
from langchain.chat_models import init_chat_model

import config


def get_model(model: str | None = None, temperature: float = 0):
    """An OpenRouter model through the OpenAI-compatible API."""
    return init_chat_model(
        model or config.CHAT_MODEL,
        model_provider="openai",               # OpenRouter speaks the OpenAI API
        base_url=config.OPENROUTER_BASE_URL,
        api_key=config.OPENROUTER_API_KEY,
        temperature=temperature,
    )
