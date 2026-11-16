"""Pattern 3 - Hierarchical teams: a top supervisor manages TEAMS, each team has its own supervisor.
Run: python -m part6.p3_hierarchical
"""
from langgraph.checkpoint.memory import InMemorySaver

from nimbus.context import Employee
from nimbus.model import get_model
from nimbus.specialists import make_specialists
from part6.p2_supervisor import build_supervisor_graph

model = get_model()
s = make_specialists(model)

# Each team is a complete supervisor graph, compiled on its own (and testable on its own).
travel_team = build_supervisor_graph({"travel": s["travel"]}, model,
                                     "Travel bookings within policy.").compile(name="travel_team")
people_team = build_supervisor_graph({"leave": s["leave"], "it": s["it"], "comms": s["comms"]}, model,
                                     "Leave, IT equipment and communications.").compile(name="people_team")

# The top level treats each TEAM exactly like a single worker: same builder, one level up.
org = build_supervisor_graph({"travel_team": travel_team, "people_team": people_team}, model,
                             "Split the request between the travel team and the people team.").compile(
    checkpointer=InMemorySaver())

if __name__ == "__main__":
    r = org.invoke({"messages": [{"role": "user", "content":
                   "Book Berlin 16-19 Nov, leave on 20 Nov, and order me a new monitor."}], "rounds": 0},
                   {"configurable": {"thread_id": "c3"}}, context=Employee("E101", "india"))
    for m in r["messages"]:
        print(getattr(m, "name", None) or m.type, ":", m.content[:100])
