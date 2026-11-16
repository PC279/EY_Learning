"""Part 7.1: approvals with HumanInTheLoopMiddleware. Run: python -m part7.hitl"""
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from nimbus.context import Employee
from nimbus.model import get_model
from nimbus.prompts import SYSTEM_PROMPT
from nimbus.tools import ALL_TOOLS

agent = create_agent(
    model=get_model(), tools=ALL_TOOLS, system_prompt=SYSTEM_PROMPT, context_schema=Employee,
    middleware=[HumanInTheLoopMiddleware(interrupt_on={
        "book_trip": {"allowed_decisions": ["approve", "edit", "reject"],
                      "description": "Please confirm this booking"},
        "apply_leave": {"allowed_decisions": ["approve", "reject"]},
        "send_email": True,                       # True = all decisions allowed
        "search_flights": False,                  # never interrupt reads
    })],
    checkpointer=InMemorySaver(),                 # REQUIRED: the paused run must be saved
)


def ask_human(action: dict) -> dict:
    """Turn one pending action into a decision. In a real app this is a UI card."""
    print(f"\n{action.get('description', '')}\n  {action['name']}({action['args']})")
    answer = input("  approve / edit / reject? ").strip().lower()
    if answer.startswith("e"):
        nights = int(input("  new number of nights: "))
        return {"type": "edit", "edited_action": {"name": action["name"],
                                                  "args": {**action["args"], "nights": nights}}}
    if answer.startswith("r"):
        return {"type": "reject", "message": input("  reason: ")}
    return {"type": "approve"}


def run(task: str, employee: Employee, thread_id: str, decide=ask_human):
    cfg = {"configurable": {"thread_id": thread_id}}
    result = agent.invoke({"messages": [{"role": "user", "content": task}]}, cfg, context=employee)
    while "__interrupt__" in result:                       # the run is paused
        request = result["__interrupt__"][0].value         # {'action_requests': [...], 'review_configs': [...]}
        decisions = [decide(a) for a in request["action_requests"]]   # one decision per action, in order
        result = agent.invoke(Command(resume={"decisions": decisions}), cfg, context=employee)
    return result["messages"][-1].content


if __name__ == "__main__":
    print(run("Book me to Berlin 16-19 Nov within policy.", Employee("E101", "india"), "trip-1"))
