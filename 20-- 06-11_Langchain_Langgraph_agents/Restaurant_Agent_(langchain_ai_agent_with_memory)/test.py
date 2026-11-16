import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()  # loads ALL variables from .env into the environment

model = ChatOpenAI(
    model="nvidia/nemotron-3.5-super-vl:free",
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),  # we fetch it, since ChatOpenAI doesn't know this name, it will look for OPEN_AI_API_KEY by default
)

response = model.invoke("Say hello in one short sentence.")
print(response.content)