"""Part 3.1-3.2: Command (update + go to) and Send (parallel map-reduce).
Run: python -m part3.command_send
"""
import operator
from typing import Annotated, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, Send

from nimbus import systems as ns


# ---------- Command: a node decides where to go AND updates state, in one return ----------
class LeaveState(TypedDict):
    employee_id: str
    days: int
    outcome: str


def check_probation(state: LeaveState) -> Command[Literal["auto_approve", "manager_review"]]:
    emp = ns.get_employee(state["employee_id"])
    if emp["on_probation"] and state["days"] > 5:
        return Command(goto="manager_review", update={"outcome": "needs review: probation limit"})
    return Command(goto="auto_approve", update={"outcome": "ok"})


def auto_approve(state: LeaveState) -> dict:
    return {"outcome": state["outcome"] + " -> auto-approved"}


def manager_review(state: LeaveState) -> dict:
    return {"outcome": state["outcome"] + " -> sent to manager"}


leave = StateGraph(LeaveState)
leave.add_node("check_probation", check_probation)   # no add_conditional_edges needed:
leave.add_node("auto_approve", auto_approve)         # Command's type hint declares the targets
leave.add_node("manager_review", manager_review)
leave.add_edge(START, "check_probation")
leave.add_edge("auto_approve", END)
leave.add_edge("manager_review", END)
leave_graph = leave.compile()


# ---------- Send: fan out one task per item, run in parallel, gather with a reducer ----------
class QuoteState(TypedDict):
    travellers: list[str]                                 # input: employee ids
    quotes: Annotated[list[dict], operator.add]           # every worker appends here (the "reduce")
    cheapest: dict


class OneTraveller(TypedDict):                            # the private input of ONE worker
    employee_id: str


def fan_out(state: QuoteState) -> list[Send]:
    """Routing function returning Send objects: one 'quote_trip' run per traveller."""
    return [Send("quote_trip", {"employee_id": e}) for e in state["travellers"]]


def quote_trip(task: OneTraveller) -> dict:
    """Runs once per traveller, in parallel. Prices the policy-compliant BLR->BER trip."""
    flights = [f for f in ns.FLIGHTS if f["class"] == "premium_economy"]
    total = sum(f["price_inr"] for f in flights) + 3 * 135 * ns.EUR_TO_INR
    return {"quotes": [{"employee_id": task["employee_id"], "total_inr": total}]}


def pick_cheapest(state: QuoteState) -> dict:
    return {"cheapest": min(state["quotes"], key=lambda q: q["total_inr"])}


quotes = StateGraph(QuoteState)
quotes.add_node("quote_trip", quote_trip)
quotes.add_node("pick_cheapest", pick_cheapest)
quotes.add_conditional_edges(START, fan_out, ["quote_trip"])   # START -> N parallel workers
quotes.add_edge("quote_trip", "pick_cheapest")                 # waits for ALL workers, then runs once
quotes.add_edge("pick_cheapest", END)
quotes_graph = quotes.compile()

if __name__ == "__main__":
    print(leave_graph.invoke({"employee_id": "E202", "days": 7, "outcome": ""})["outcome"])
    print(leave_graph.invoke({"employee_id": "E101", "days": 7, "outcome": ""})["outcome"])
    r = quotes_graph.invoke({"travellers": ["E101", "E202"], "quotes": []})
    print(len(r["quotes"]), "quotes;", r["cheapest"])
