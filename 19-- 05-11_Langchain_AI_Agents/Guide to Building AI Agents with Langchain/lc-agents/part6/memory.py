"""Part 6: short-term memory (threads) and long-term memory (store). Run: python -m part6.memory"""
from langchain.agents import create_agent
from langchain.tools import ToolRuntime, tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

from nimbus.context import Employee
from nimbus.model import get_model
from nimbus.prompts import SYSTEM_PROMPT
from nimbus.tools import ALL_TOOLS


@tool
def remember_preference(preference: str, runtime: ToolRuntime[Employee]) -> str:
    """Save a lasting travel or work preference the employee stated (e.g. 'aisle seat')."""
    namespace = ("preferences", runtime.context.employee_id)
    key = preference.lower().replace(" ", "_")[:40]
    runtime.store.put(namespace, key, {"text": preference})
    return f"Saved: {preference}"


@tool
def recall_preferences(runtime: ToolRuntime[Employee]) -> list[str]:
    """List the employee's saved preferences. Check before booking travel."""
    items = runtime.store.search(("preferences", runtime.context.employee_id))
    return [item.value["text"] for item in items]


checkpointer = InMemorySaver()          # short-term: per conversation (thread_id)
store = InMemoryStore()                 # long-term: across all conversations

agent = create_agent(
    model=get_model(), tools=ALL_TOOLS + [remember_preference, recall_preferences],
    system_prompt=SYSTEM_PROMPT, context_schema=Employee,
    checkpointer=checkpointer, store=store,
)

if __name__ == "__main__":
    priya = Employee("E101", "india")
    chat_1 = {"configurable": {"thread_id": "priya-monday"}}
    agent.invoke({"messages": [{"role": "user", "content": "Remember: I always prefer aisle seats."}]},
                 chat_1, context=priya)
    agent.invoke({"messages": [{"role": "user", "content": "How many leave days do I have?"}]},
                 chat_1, context=priya)                    # same thread: sees the first message
    chat_2 = {"configurable": {"thread_id": "priya-friday"}}
    r = agent.invoke({"messages": [{"role": "user", "content": "What seat do I like?"}]},
                     chat_2, context=priya)                # new thread: only the STORE remembers
    print(r["messages"][-1].content)
