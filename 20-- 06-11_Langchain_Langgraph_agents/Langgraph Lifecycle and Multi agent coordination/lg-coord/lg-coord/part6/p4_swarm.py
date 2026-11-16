"""Pattern 4 - Handoffs (swarm): agents pass the CONVERSATION to each other; no central manager.
The active agent talks to the user directly and stays active until it hands off.
Run: python -m part6.p4_swarm
"""
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from langgraph_swarm import create_handoff_tool, create_swarm

from nimbus import tools as t
from nimbus.context import Employee
from nimbus.model import get_model
from nimbus.prompts import SYSTEM_PROMPT

model = get_model()

leave_desk = create_agent(
    model,
    [t.get_leave_balance, t.apply_leave, t.search_hr_policies,
     create_handoff_tool(agent_name="travel_desk", description="Transfer to the travel desk for flights and hotels")],
    system_prompt=SYSTEM_PROMPT + "\nYou are the leave desk. For anything about travel, transfer to travel_desk.",
    context_schema=Employee, name="leave_desk")

travel_desk = create_agent(
    model,
    [t.get_travel_policy, t.search_flights, t.search_hotels, t.book_trip,
     create_handoff_tool(agent_name="leave_desk", description="Transfer to the leave desk for time off")],
    system_prompt=SYSTEM_PROMPT + "\nYou are the travel desk. For anything about leave, transfer to leave_desk.",
    context_schema=Employee, name="travel_desk")

swarm = create_swarm([leave_desk, travel_desk], default_active_agent="leave_desk",
                     context_schema=Employee).compile(checkpointer=InMemorySaver())   # remembers who is active

if __name__ == "__main__":
    cfg, priya = {"configurable": {"thread_id": "c4"}}, Employee("E101", "india")
    for text in ["How many leave days do I have?", "Great. Now book me to Berlin 16-19 Nov."]:
        r = swarm.invoke({"messages": [{"role": "user", "content": text}]}, cfg, context=priya)
        active = r.get("active_agent", "leave_desk")      # the key appears after the first handoff
        print(active, ":", r["messages"][-1].content[:120])
