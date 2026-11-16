"""A scripted chat model shared by all tests. Each test fills SCRIPT with the model turns it expects:
a string = final answer; a list of (tool_name, args) = tool calls (also used for structured output)."""
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

SCRIPT: list = []
SEEN: list = []                                   # every message list any model received


class ScriptedModel(BaseChatModel):
    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        SEEN.append(messages)
        step = SCRIPT.pop(0) if SCRIPT else "done"
        usage = {"input_tokens": 100, "output_tokens": 20, "total_tokens": 120}
        if isinstance(step, str):
            msg = AIMessage(content=step, usage_metadata=usage)
        else:
            msg = AIMessage(content="", usage_metadata=usage, tool_calls=[
                {"name": n, "args": a, "id": f"call_{len(SEEN)}_{i}"} for i, (n, a) in enumerate(step)])
        return ChatResult(generations=[ChatGeneration(message=msg)])
