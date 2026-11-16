"""Part 5.2: built-in middleware. Run: python -m part5.builtin"""
from langchain.agents import create_agent
from langchain.agents.middleware import (ModelCallLimitMiddleware, ModelFallbackMiddleware,
                                         PIIMiddleware, SummarizationMiddleware,
                                         ToolCallLimitMiddleware, ToolErrorMiddleware,
                                         ToolRetryMiddleware)

import config
from nimbus.context import Employee
from nimbus.model import get_model
from nimbus.prompts import SYSTEM_PROMPT
from nimbus.tools import ALL_TOOLS



def friendly_tool_errors(exc: Exception, request) -> str | None:
    """Turn temporary failures into a message the model can act on; let everything else stop the run."""
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return f"{request.tool_call['name']} is temporarily unavailable. Try once more, then tell the user."
    return None                                   # None = re-raise


agent = create_agent(
    model=get_model(),
    tools=ALL_TOOLS,
    system_prompt=SYSTEM_PROMPT,
    context_schema=Employee,
    middleware=[
        ModelCallLimitMiddleware(run_limit=12, exit_behavior="end"),     # hard cap per run
        ToolCallLimitMiddleware(tool_name="book_trip", run_limit=2),      # at most 2 booking attempts
        ToolErrorMiddleware(friendly_tool_errors),                       # outer: catches what retries can't fix
        ToolRetryMiddleware(max_retries=2, tools=["search_flights", "search_hotels"],
                            on_failure="error"),                          # inner: retry flaky reads first
        ModelFallbackMiddleware(get_model(config.FALLBACK_MODEL)),       # if the main model fails
        PIIMiddleware("email", strategy="redact", apply_to_input=True),  # emails never reach the model
        SummarizationMiddleware(model=get_model(), trigger=("tokens", 6000), keep=("messages", 20)),
    ],
)
