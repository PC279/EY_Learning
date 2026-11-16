"""Part 3.4-3.6: checkpoints, threads, interrupts, time travel, retries, streaming.
Run: python -m part3.persistence
"""
import operator
from typing import Annotated, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, RetryPolicy, interrupt

from nimbus import systems as ns


class BookingState(TypedDict):
    employee_id: str
    plan: dict
    approved: bool
    booking: dict
    log: Annotated[list[str], operator.add]


ATTEMPTS = {"n": 0}


def make_plan(state: BookingState) -> dict:
    writer = get_stream_writer()                              # custom progress events
    writer({"progress": "looking up policy-compliant options"})
    ATTEMPTS["n"] += 1
    if ATTEMPTS["n"] == 1:
        raise ConnectionError("flight API timed out")         # transient failure: retried below
    return {"plan": {"flight_ids": ["FL2", "FL4"], "hotel_id": "HT1", "nights": 3}, "log": ["plan made"]}


def ask_approval(state: BookingState) -> dict:
    # interrupt() saves the state and PAUSES the run here; the value is shown to the human.
    answer = interrupt({"question": "Book this trip?", "plan": state["plan"]})
    return {"approved": answer == "yes", "log": [f"human said {answer}"]}


def book(state: BookingState) -> dict:
    if not state["approved"]:
        return {"log": ["not booked"]}
    p = state["plan"]
    return {"booking": ns.book_trip(state["employee_id"], p["flight_ids"], p["hotel_id"], p["nights"]),
            "log": ["booked"]}


builder = StateGraph(BookingState)
builder.add_node("make_plan", make_plan,
                 retry_policy=RetryPolicy(max_attempts=3, retry_on=ConnectionError))  # automatic retries
builder.add_node("ask_approval", ask_approval)
builder.add_node("book", book)
builder.add_edge(START, "make_plan")
builder.add_edge("make_plan", "ask_approval")
builder.add_edge("ask_approval", "book")
builder.add_edge("book", END)
graph = builder.compile(checkpointer=InMemorySaver())        # checkpoints: needed for interrupts

if __name__ == "__main__":
    cfg = {"configurable": {"thread_id": "priya-trip-1"}}
    for mode, chunk in graph.stream({"employee_id": "E101", "log": []}, cfg, stream_mode=["updates", "custom"]):
        print(mode, chunk)                                    # ends with an __interrupt__ update
    print("paused before:", graph.get_state(cfg).next)        # ('ask_approval',)
    result = graph.invoke(Command(resume="yes"), cfg)         # resume with the human's answer
    print(result["log"], result["booking"]["status"])

    # TIME TRAVEL: list checkpoints, pick one, and replay or fork from there.
    history = list(graph.get_state_history(cfg))              # newest first
    before_approval = next(s for s in history if s.next == ("ask_approval",))
    fork_cfg = graph.update_state(before_approval.config, {"log": ["forked: re-asking"]})
    forked = graph.invoke(None, fork_cfg)                     # runs again from that point -> pauses again
    print("fork paused at:", graph.get_state(fork_cfg).next)
