"""
config.py - reads all settings from backend/.env, so no password or key is ever written in code.
(Owned by Person B in the team plan; B can keep this or extend it.)
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Load values from the .env file in the folder you run commands from (backend/)
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str                       # required: the app stops with a clear error if missing
    AI_BASE_URL: str = "https://openrouter.ai/api/v1"
    AI_MODEL: str = ""                      # e.g. a free OpenRouter model id ending in :free
    AI_API_KEY: str = ""                    # never commit the real key
    AI_TIMEOUT_SECONDS: float = 30
    AI_ENABLED: bool = True


# One shared settings object that the rest of the app imports
settings = Settings()
