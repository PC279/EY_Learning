"""Agent tests with a scripted model: check the agent's wiring and the systems' end state."""
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from nimbus import systems as ns
from nimbus.context import Employee
from nimbus.prompts import SYSTEM_PROMPT
from nimbus.tools import ALL_TOOLS
from part5.custom import travel_policy_guard
from tests.fake_model import ScriptedChatModel

PRIYA = Employee("E101", "india")


def make_agent(script, **kwargs):
    model = ScriptedChatModel(script=list(script), calls=[])
    return create_agent(model, ALL_TOOLS, system_prompt=SYSTEM_PROMPT, context_schema=Employee, **kwargs), model


def ask(agent, text, **kwargs):
    return agent.invoke({"messages": [{"role": "user", "content": text}]}, context=PRIYA, **kwargs)


def test_leave_balance_flows_back_to_the_model():
    agent, model = make_agent([[("get_leave_balance", {})], "You have 14 days left."])
    result = ask(agent, "How many leave days do I have left?")
    tool_result = model.calls[-1][-1]                      # the last thing the model read
    assert '"days_left": 14' in tool_result.content
    assert result["messages"][-1].content == "You have 14 days left."


def test_guard_blocks_business_class_before_the_system():
    agent, _ = make_agent([[("book_trip", {"flight_ids": ["FL3", "FL4"], "hotel_id": "HT1", "nights": 3})],
                           "Business class isn't allowed."], middleware=[travel_policy_guard])
    ask(agent, "Book business class to Berlin.")
    assert ns.BOOKINGS == []


def test_rejected_approval_changes_nothing():
    agent, _ = make_agent([[("apply_leave", {"start_date": "2026-11-20", "end_date": "2026-11-20"})], "OK."],
                          middleware=[HumanInTheLoopMiddleware(interrupt_on={"apply_leave": True})],
                          checkpointer=InMemorySaver())
    cfg = {"configurable": {"thread_id": "t1"}}
    result = ask(agent, "Leave on 20 Nov please.", config=cfg)
    assert "__interrupt__" in result
    agent.invoke(Command(resume={"decisions": [{"type": "reject", "message": "Not now"}]}), cfg, context=PRIYA)
    assert ns.LEAVE_REQUESTS == []
