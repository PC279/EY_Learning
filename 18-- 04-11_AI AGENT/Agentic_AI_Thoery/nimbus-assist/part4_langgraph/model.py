from langchain_openai import ChatOpenAI

import config

llm = ChatOpenAI(model=config.CHAT_MODEL, api_key=config.OPENROUTER_API_KEY,
                 base_url=config.OPENROUTER_BASE_URL, temperature=0)
