"""Pattern 1 - Sequential pipeline: plan -> policy check -> book -> notify, in a FIXED order.
An LLM agent does the open-ended step (planning); plain code does the steps that must never vary.
Run: python -m part6.p1_sequential
"""
from typing import TypedDict

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from nimbus import systems as ns
from nimbus.context import Employee
from nimbus.model import get_model
from nimbus.prompts import SYSTEM_PROMPT
from nimbus.tools import READ_TOOLS


class TripPlan(BaseModel):
    flight_ids: list[str]
    hotel_id: str
    nights: int


planner = create_agent(get_model(), READ_TOOLS, context_schema=Employee,
                       system_prompt=SYSTEM_PROMPT + "\nPlan a policy-compliant trip. Do not book.",
                       response_format=ToolStrategy(TripPlan))     # the planner's output is DATA


class PipelineState(TypedDict):
    request: str
    employee_id: str
    plan: dict
    problems: list[str]
    booking: dict
    message: str


def plan_step(state: PipelineState) -> dict:                       # stage 1: an agent
    result = planner.invoke({"messages": [{"role": "user", "content": state["request"]}]},
                            context=Employee(state["employee_id"], "india"))
    return {"plan": result["structured_response"].model_dump()}


def policy_step(state: PipelineState) -> dict:                     # stage 2: deterministic checks
    problems = [f"{f['id']} is {f['class']}" for f in ns.FLIGHTS
                if f["id"] in state["plan"]["flight_ids"] and f["class"] == "business"]
    return {"problems": problems}


def book_step(state: PipelineState) -> dict:                       # stage 3: code, never an LLM
    p = state["plan"]
    return {"booking": ns.book_trip(state["employee_id"], p["flight_ids"], p["hotel_id"], p["nights"])}


def notify_step(state: PipelineState) -> dict:                     # stage 4: a single LLM call
    text = get_model().invoke(f"In two sentences, tell the employee this booking result: {state['booking']}")
    return {"message": text.content}


def stop_if_problems(state: PipelineState) -> str:
    return "rejected" if state["problems"] else "book"


def rejected(state: PipelineState) -> dict:
    return {"message": "Plan rejected by policy check: " + "; ".join(state["problems"])}


g = StateGraph(PipelineState)
for name, fn in [("plan", plan_step), ("policy", policy_step), ("book", book_step),
                 ("notify", notify_step), ("rejected", rejected)]:
    g.add_node(name, fn)
g.add_edge(START, "plan")
g.add_edge("plan", "policy")
g.add_conditional_edges("policy", stop_if_problems, ["book", "rejected"])   # the only branch: a safety stop
g.add_edge("book", "notify")
g.add_edge("notify", END)
g.add_edge("rejected", END)
pipeline = g.compile()

if __name__ == "__main__":
    r = pipeline.invoke({"request": "Berlin 16-19 Nov", "employee_id": "E101"})
    print(r["booking"]["status"], "|", r["message"])
