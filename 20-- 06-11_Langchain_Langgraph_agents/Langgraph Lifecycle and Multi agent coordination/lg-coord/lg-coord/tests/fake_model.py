"""A scripted chat model for tests: no network, fully predictable.

Each item in `script` is one model turn: a string (final answer) or a list of
(tool_name, args) pairs (tool calls). Works with create_agent and middleware.
"""
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class ScriptedChatModel(BaseChatModel):
    script: list = []
    calls: list = []                       # every message list the model received

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools, **kwargs):
        return self                        # tools are ignored: the script decides

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.calls.append(messages)
        step = self.script.pop(0) if self.script else "done"
        usage = {"input_tokens": 100, "output_tokens": 20, "total_tokens": 120}
        if isinstance(step, str):
            msg = AIMessage(content=step, usage_metadata=usage)
        else:
            msg = AIMessage(content="", usage_metadata=usage, tool_calls=[
                {"name": name, "args": args, "id": f"call_{len(self.calls)}_{i}"}
                for i, (name, args) in enumerate(step)])
        return ChatResult(generations=[ChatGeneration(message=msg)])
