"""The same agent with LangChain's prebuilt create_agent (a LangGraph graph under the hood)."""
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

from part3_by_hand.agent import SYSTEM_PROMPT
from part4_langgraph.lc_tools import ALL_TOOLS
from part4_langgraph.model import llm

agent = create_agent(
    model=llm,
    tools=ALL_TOOLS,
    system_prompt=SYSTEM_PROMPT.format(employee_id="E101"),
    checkpointer=InMemorySaver(),
)

if __name__ == "__main__":
    cfg = {"configurable": {"thread_id": "demo"}}
    for chunk in agent.stream({"messages": [("user", "How many leave days do I have left?")]},
                              cfg, stream_mode="updates"):
        print(chunk)                      # one update per node: model step, tool step, ...
