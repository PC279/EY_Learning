"""Part 6: memory that survives restarts, custom state, and trimming. Run: python -m part6.persistent"""
import sqlite3

from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import before_model
from langchain.messages import RemoveMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from typing_extensions import NotRequired

from nimbus.context import Employee
from nimbus.model import get_model
from nimbus.prompts import SYSTEM_PROMPT
from nimbus.tools import ALL_TOOLS


# 1. Extra fields carried through the conversation (and saved with it)
class NimbusState(AgentState):
    trip_booking_ids: NotRequired[list[str]]


# 2. Keep the first message and the last 10, drop the middle, before every model call
@before_model
def keep_recent_messages(state, runtime):
    messages = state["messages"]
    if len(messages) <= 11:
        return None                                        # nothing to do
    recent = messages[-10:]
    while recent and recent[0].type == "tool":             # never start on an orphan tool result
        recent = recent[1:]
    return {"messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES), messages[0], *recent]}


# 3. A checkpointer that writes to a file, so conversations survive restarts
conn = sqlite3.connect("memory.db", check_same_thread=False)
checkpointer = SqliteSaver(conn)

agent = create_agent(
    model=get_model(), tools=ALL_TOOLS, system_prompt=SYSTEM_PROMPT, context_schema=Employee,
    state_schema=NimbusState, middleware=[keep_recent_messages], checkpointer=checkpointer,
)

if __name__ == "__main__":
    cfg = {"configurable": {"thread_id": "priya-2026-11-05"}}
    priya = Employee("E101", "india")
    agent.invoke({"messages": [{"role": "user", "content": "How many leave days do I have?"}]}, cfg, context=priya)
    snapshot = agent.get_state(cfg)                        # what is saved for this thread
    print(len(snapshot.values["messages"]), "messages saved")
    for past in agent.get_state_history(cfg):              # every checkpoint, newest first
        print(past.config["configurable"]["checkpoint_id"], len(past.values.get("messages", [])))
