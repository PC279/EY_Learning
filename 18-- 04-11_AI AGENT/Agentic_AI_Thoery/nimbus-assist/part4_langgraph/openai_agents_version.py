"""Nimbus Assist (leave + IT only) with the OpenAI Agents SDK, using OpenRouter.
Install in a separate environment: pip install openai-agents
"""
from openai import AsyncOpenAI
from agents import Agent, OpenAIChatCompletionsModel, Runner, function_tool, set_tracing_disabled

import config
import nimbus_systems as ns

set_tracing_disabled(True)        # tracing uploads to OpenAI by default; off when using OpenRouter
model = OpenAIChatCompletionsModel(
    model=config.CHAT_MODEL,
    openai_client=AsyncOpenAI(api_key=config.OPENROUTER_API_KEY, base_url=config.OPENROUTER_BASE_URL),
)


@function_tool
def get_leave_balance(employee_id: str) -> dict:
    """Get remaining annual leave days and probation limits for an employee."""
    return ns.get_leave_balance(employee_id)


@function_tool
def create_it_ticket(employee_id: str, category: str, description: str) -> dict:
    """Open an IT support ticket. category: hardware, software, access, security."""
    return ns.create_it_ticket(employee_id, category, description)


assistant = Agent(
    name="Nimbus Assist",
    instructions=f"You help Nimbus employee E101. Today is {config.TODAY}. Use tools; never guess.",
    tools=[get_leave_balance, create_it_ticket],
    model=model,
)

if __name__ == "__main__":
    result = Runner.run_sync(assistant, "How many leave days do I have left?")
    print(result.final_output)
