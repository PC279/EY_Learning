"""Pattern 5 - Parallel map-reduce: one worker agent per traveller, all at once, then combine.
Run: python -m part6.p5_map_reduce
"""
import operator
from typing import Annotated, TypedDict

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
from pydantic import BaseModel

from nimbus.context import Employee
from nimbus.model import get_model
from nimbus.prompts import SYSTEM_PROMPT
from nimbus.tools import READ_TOOLS


class Quote(BaseModel):
    employee_id: str
    flight_ids: list[str]
    hotel_id: str
    total_inr: int


quoter = create_agent(get_model(), READ_TOOLS, context_schema=Employee, response_format=ToolStrategy(Quote),
                      system_prompt=SYSTEM_PROMPT + "\nQuote (don't book) a policy-compliant trip. EUR to INR: 95.")


class QuotesState(TypedDict):
    request: str
    travellers: list[dict]                             # [{"employee_id": ..., "office": ...}]
    quotes: Annotated[list[dict], operator.add]        # REDUCE: each worker appends its quote
    total_inr: int


def fan_out(state: QuotesState) -> list[Send]:         # MAP: one worker per traveller
    return [Send("quote_one", {"request": state["request"], "traveller": t}) for t in state["travellers"]]


def quote_one(task: dict) -> dict:                     # runs in parallel; sees ONLY its own task
    who = Employee(task["traveller"]["employee_id"], task["traveller"]["office"])
    r = quoter.invoke({"messages": [{"role": "user", "content": task["request"]}]}, context=who)
    return {"quotes": [r["structured_response"].model_dump()]}


def combine(state: QuotesState) -> dict:               # REDUCE: runs once, after all workers
    return {"total_inr": sum(q["total_inr"] for q in state["quotes"])}


g = StateGraph(QuotesState)
g.add_node("quote_one", quote_one)
g.add_node("combine", combine)
g.add_conditional_edges(START, fan_out, ["quote_one"])
g.add_edge("quote_one", "combine")
g.add_edge("combine", END)
team_quotes = g.compile()

if __name__ == "__main__":
    people = [{"employee_id": "E101", "office": "india"}, {"employee_id": "E202", "office": "germany"},
              {"employee_id": "E303", "office": "india"}]
    r = team_quotes.invoke({"request": "Quote BLR->BER 16-19 Nov within policy.", "travellers": people, "quotes": []})
    print(len(r["quotes"]), "quotes, total INR", r["total_inr"])
