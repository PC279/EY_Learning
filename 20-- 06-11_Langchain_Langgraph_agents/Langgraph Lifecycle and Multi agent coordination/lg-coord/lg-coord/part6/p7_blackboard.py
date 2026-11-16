"""Pattern 7 - Shared blackboard: specialists read and write one shared 'board'; a controller
picks whoever can make progress next, until the board is complete and consistent.
Run: python -m part6.p7_blackboard
"""
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from nimbus.model import get_model

BUDGET_INR = 400_000
MAX_STEPS = 8


class Venue(BaseModel):
    city: str
    venue: str
    cost_inr: int


class Travel(BaseModel):
    cost_inr: int
    notes: str


class Board(TypedDict, total=False):        # THE BLACKBOARD: every specialist reads and writes here
    goal: str
    venue: dict
    travel: dict
    budget_ok: bool
    rejected_venues: list[str]
    steps: int


model = get_model()


def venue_specialist(b: Board) -> dict:
    v = model.with_structured_output(Venue).invoke(
        f"Pick an offsite venue for: {b['goal']}. Avoid: {b.get('rejected_venues', [])}.")
    return {"venue": v.model_dump(), "travel": {}, "steps": b.get("steps", 0) + 1}   # new venue: travel is stale


def travel_specialist(b: Board) -> dict:
    t = model.with_structured_output(Travel).invoke(
        f"Estimate total travel cost for 12 people from Bengaluru and Berlin to {b['venue']['city']}.")
    return {"travel": t.model_dump(), "steps": b.get("steps", 0) + 1}


def budget_specialist(b: Board) -> dict:     # deterministic: a rule, not an LLM
    total = b["venue"]["cost_inr"] + b["travel"]["cost_inr"]
    if total <= BUDGET_INR:
        return {"budget_ok": True, "steps": b.get("steps", 0) + 1}
    return {"budget_ok": False, "venue": {}, "travel": {}, "steps": b.get("steps", 0) + 1,
            "rejected_venues": b.get("rejected_venues", []) + [b["venue"]["venue"]]}   # erase and retry


def controller(b: Board) -> str:
    """Looks at the board and picks who can contribute next. No LLM needed."""
    if b.get("steps", 0) >= MAX_STEPS:
        return END
    if not b.get("venue"):
        return "venue_specialist"
    if not b.get("travel"):
        return "travel_specialist"
    if not b.get("budget_ok"):
        return "budget_specialist"
    return END


g = StateGraph(Board)
for name, fn in [("venue_specialist", venue_specialist), ("travel_specialist", travel_specialist),
                 ("budget_specialist", budget_specialist)]:
    g.add_node(name, fn)
    g.add_conditional_edges(name, controller, ["venue_specialist", "travel_specialist", "budget_specialist", END])
g.add_conditional_edges(START, controller, ["venue_specialist", "travel_specialist", "budget_specialist", END])
offsite = g.compile()

if __name__ == "__main__":
    r = offsite.invoke({"goal": "2-day engineering offsite for 12 people in March", "steps": 0})
    print(r["venue"], r["travel"], "budget ok:", r.get("budget_ok"), "rejected:", r.get("rejected_venues"))
