"""Part 4.1: an agent that returns a typed result. Run: python -m part4.structured_agent"""
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from pydantic import BaseModel, Field

from nimbus.context import Employee
from nimbus.model import get_model
from nimbus.prompts import SYSTEM_PROMPT
from nimbus.tools import READ_TOOLS


class TripQuote(BaseModel):
    """A policy-compliant trip proposal (nothing is booked)."""
    outbound_flight: str = Field(description="Flight id, e.g. FL2")
    return_flight: str = Field(description="Flight id, e.g. FL4")
    hotel_id: str
    nights: int
    estimated_total_inr: int
    needs_manager_approval: bool
    notes: str = Field(description="One sentence explaining the choices")


agent = create_agent(
    model=get_model(),
    tools=READ_TOOLS,                       # read-only: it can plan but not book
    system_prompt=SYSTEM_PROMPT + "\nPropose trips; do not book. EUR to INR rate: 95.",
    context_schema=Employee,
    response_format=ToolStrategy(TripQuote),
)

if __name__ == "__main__":
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "Quote me a Berlin trip, 16 to 19 Nov, within policy."}]},
        context=Employee("E101", "india"),
    )
    quote: TripQuote = result["structured_response"]     # a TripQuote object
    print(quote.model_dump())
