"""Nimbus Assist as an explicit LangGraph graph: agent node <-> tools node, with memory and approvals.
Run:  python -m part4_langgraph.graph_agent --employee E101
"""
import argparse

from langchain_core.messages import SystemMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import Command

import config
from part3_by_hand.agent import SYSTEM_PROMPT
from part4_langgraph.lc_tools import ALL_TOOLS
from part4_langgraph.model import llm


class State(MessagesState):          # MessagesState already has `messages` (appended, not replaced)
    employee_id: str


llm_with_tools = llm.bind_tools(ALL_TOOLS)


def agent(state: State) -> dict:
    """REASON: the model reads everything so far and picks the next step."""
    system = SystemMessage(SYSTEM_PROMPT.format(employee_id=state["employee_id"]))
    return {"messages": [llm_with_tools.invoke([system] + state["messages"])]}


builder = StateGraph(State)
builder.add_node("agent", agent)
builder.add_node("tools", ToolNode(ALL_TOOLS))       # ACT: runs every requested tool call
builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", tools_condition)   # tool calls -> "tools", else -> END
builder.add_edge("tools", "agent")                        # OBSERVE: results go back to the model
graph = builder.compile(checkpointer=InMemorySaver())     # memory per thread_id


def run(task: str, employee_id: str, thread_id: str, approve=lambda req: "yes") -> str:
    cfg = {"configurable": {"thread_id": thread_id}, "recursion_limit": 2 * config.MAX_STEPS + 1}
    result = graph.invoke({"messages": [("user", task)], "employee_id": employee_id}, cfg)
    while "__interrupt__" in result:                          # paused, waiting for a human
        # one interrupt per risky tool call; answer each one by its id
        answers = {i.id: approve(i.value) for i in result["__interrupt__"]}
        result = graph.invoke(Command(resume=answers), cfg)
    return result["messages"][-1].content


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--employee", default="E101")
    args = parser.parse_args()
    ask = lambda req: input(f"  Allow {req['action']}({req['args']})? [y/N] ")
    while (task := input("\nYou> ").strip()) not in {"", "exit", "quit"}:
        print("Nimbus Assist>", run(task, args.employee, thread_id=f"{args.employee}-chat", approve=ask))
