"""Part 4.4: choose tools and model per request. Run: python -m part4.dynamic"""
from langchain.agents import create_agent
from langchain.agents.middleware import ModelRequest, ModelResponse, wrap_model_call

import config
from nimbus.context import Employee
from nimbus.model import get_model
from nimbus.prompts import SYSTEM_PROMPT
from nimbus.tools import ALL_TOOLS, READ_TOOLS

fast_model = get_model()
strong_model = get_model(config.FALLBACK_MODEL)      # any stronger model id you prefer


@wrap_model_call
def tools_and_model_by_situation(request: ModelRequest, handler) -> ModelResponse:
    who: Employee = request.runtime.context
    tools = request.tools
    if who.role == "guest":                          # guests may only read
        tools = [t for t in request.tools if t.name in {t2.name for t2 in READ_TOOLS}]
    model = strong_model if len(request.messages) > 8 else fast_model   # long tasks: stronger model
    return handler(request.override(tools=tools, model=model))


agent = create_agent(model=fast_model, tools=ALL_TOOLS, system_prompt=SYSTEM_PROMPT,
                     middleware=[tools_and_model_by_situation], context_schema=Employee)
