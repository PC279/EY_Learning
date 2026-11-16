"""Part 2: a LangGraph workflow built from scratch - onboarding a new joiner.
No LLM needed: this shows state, reducers, nodes, edges and conditional edges.
Run: python -m part2.onboarding_graph
"""
import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from nimbus import systems as ns


# 1. STATE: the shared data every node reads and updates.
class OnboardingState(TypedDict):
    name: str                                    # input: the new joiner
    email: str
    role: str                                    # e.g. "engineer", "sales"
    start_date: str
    tickets: Annotated[list[str], operator.add]  # REDUCER: node outputs are APPENDED, not replaced
    log: Annotated[list[str], operator.add]      # an audit trail every node adds to
    welcome_sent: bool                           # no reducer: the last write wins


# 2. NODES: plain functions. Each receives the full state and returns ONLY the keys it changes.
def laptop_ticket(state: OnboardingState) -> dict:
    t = ns.create_it_ticket("HR", "hardware", f"Laptop for {state['name']} ({state['role']})")
    return {"tickets": [t["id"]], "log": [f"laptop ticket {t['id']}"]}


def code_access_ticket(state: OnboardingState) -> dict:
    t = ns.create_it_ticket("HR", "access", f"GitHub and CI access for {state['name']}")
    return {"tickets": [t["id"]], "log": [f"code access ticket {t['id']}"]}


def welcome_email(state: OnboardingState) -> dict:
    ns.send_email(state["email"], "Welcome to Nimbus!",
                  f"Hi {state['name']}, see you on {state['start_date']}. "
                  f"Your IT tickets: {', '.join(state['tickets'])}.")
    return {"welcome_sent": True, "log": ["welcome email sent"]}


def orientation(state: OnboardingState) -> dict:
    ns.schedule_meeting([state["email"], "hr@nimbus.example"], "Orientation", state["start_date"], "10:00")
    return {"log": ["orientation scheduled"]}


# 3. A ROUTING FUNCTION for a conditional edge: reads state, returns the name of the next node.
def needs_code_access(state: OnboardingState) -> str:
    return "code_access_ticket" if state["role"] == "engineer" else "welcome_email"


# 4. Wire the graph.
builder = StateGraph(OnboardingState)
builder.add_node("laptop_ticket", laptop_ticket)
builder.add_node("code_access_ticket", code_access_ticket)
builder.add_node("welcome_email", welcome_email)
builder.add_node("orientation", orientation)

builder.add_edge(START, "laptop_ticket")                       # always start here
builder.add_conditional_edges("laptop_ticket", needs_code_access,  # branch on the role
                              ["code_access_ticket", "welcome_email"])
builder.add_edge("code_access_ticket", "welcome_email")
builder.add_edge("welcome_email", "orientation")
builder.add_edge("orientation", END)

graph = builder.compile()                                       # validates the wiring

if __name__ == "__main__":
    arjun = {"name": "Arjun Mehta", "email": "arjun@nimbus.example", "role": "engineer",
             "start_date": "2026-12-01", "tickets": [], "log": [], "welcome_sent": False}
    final = graph.invoke(arjun)
    print(final["tickets"], final["log"])
    for step in graph.stream(arjun, stream_mode="updates"):    # one dict per finished node
        print(step)
    print(graph.get_graph().draw_mermaid())                    # the picture of the graph
