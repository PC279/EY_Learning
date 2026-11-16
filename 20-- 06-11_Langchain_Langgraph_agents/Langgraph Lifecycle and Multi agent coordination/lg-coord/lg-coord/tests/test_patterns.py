"""Part 6: every coordination pattern, with scripted model turns. Checks routing and end state."""
from nimbus import systems as ns
from nimbus.context import Employee
from tests.scripted import SCRIPT

PRIYA = Employee("E101", "india")
BOOK = ("book_trip", {"flight_ids": ["FL2", "FL4"], "hotel_id": "HT1", "nights": 3})
LEAVE = ("apply_leave", {"start_date": "2026-11-20", "end_date": "2026-11-20"})


def ask(graph, text, thread, **extra):
    return graph.invoke({"messages": [{"role": "user", "content": text}], **extra},
                        {"configurable": {"thread_id": thread}}, context=PRIYA)


def test_sequential_pipeline():
    from part6.p1_sequential import pipeline
    SCRIPT[:] = [[("TripPlan", {"flight_ids": ["FL2", "FL4"], "hotel_id": "HT1", "nights": 3})],
                 "Your Berlin trip is booked and awaiting manager approval."]
    r = pipeline.invoke({"request": "Berlin 16-19 Nov", "employee_id": "E101"})
    assert r["booking"]["status"] == "pending_manager_approval" and "approval" in r["message"]


def test_sequential_pipeline_stops_business_class():
    from part6.p1_sequential import pipeline
    SCRIPT[:] = [[("TripPlan", {"flight_ids": ["FL3", "FL4"], "hotel_id": "HT1", "nights": 3})]]
    r = pipeline.invoke({"request": "Berlin, business class", "employee_id": "E101"})
    assert r["message"].startswith("Plan rejected") and not ns.BOOKINGS


def test_supervisor_routes_and_finishes():
    from part6.p2_supervisor import team
    SCRIPT[:] = [[("Route", {"next": "travel", "instruction": "Book Berlin 16-19 Nov in policy."})],
                 [BOOK], "Booked BK1, pending approval.",
                 [("Route", {"next": "leave", "instruction": "Apply leave on 2026-11-20."})],
                 [LEAVE], "Leave LR1 submitted.",
                 [("Route", {"next": "FINISH", "instruction": ""})]]
    r = ask(team, "Trip and leave", "sup-1", rounds=0)
    assert [m.name for m in r["messages"] if m.type == "ai"] == ["supervisor", "travel", "supervisor", "leave"]
    assert ns.BOOKINGS and ns.LEAVE_REQUESTS


def test_supervisor_loop_guard():
    from part6.p2_supervisor import MAX_ROUNDS, team
    SCRIPT[:] = [[("Route", {"next": "it", "instruction": "again"})], "nothing to do"] * 10
    r = ask(team, "loop forever", "sup-2", rounds=0)
    assert r["rounds"] == MAX_ROUNDS and "too many rounds" in r["messages"][-1].content


def test_hierarchical_teams():
    from part6.p3_hierarchical import org
    SCRIPT[:] = [[("Route", {"next": "people_team", "instruction": "Order a monitor for Priya."})],
                 [("Route", {"next": "it", "instruction": "Open a hardware ticket for a monitor."})],
                 [("create_it_ticket", {"category": "hardware", "description": "New monitor"})], "Ticket IT1.",
                 [("Route", {"next": "FINISH", "instruction": ""})],     # the people team is done
                 [("Route", {"next": "FINISH", "instruction": ""})]]     # the top supervisor is done
    r = ask(org, "Order me a monitor", "hier-1", rounds=0)
    assert ns.TICKETS and any(m.name == "people_team" for m in r["messages"])


def test_swarm_handoff_keeps_active_agent():
    from part6.p4_swarm import swarm
    cfg = {"configurable": {"thread_id": "swarm-1"}}
    SCRIPT[:] = [[("get_leave_balance", {})], "You have 14 days."]
    r = swarm.invoke({"messages": [{"role": "user", "content": "leave balance?"}]}, cfg, context=PRIYA)
    assert r.get("active_agent", "leave_desk") == "leave_desk"   # set only after the first handoff
    SCRIPT[:] = [[("transfer_to_travel_desk", {})], [BOOK], "Booked, pending approval."]
    r = swarm.invoke({"messages": [{"role": "user", "content": "now book Berlin"}]}, cfg, context=PRIYA)
    assert r["active_agent"] == "travel_desk" and ns.BOOKINGS
    SCRIPT[:] = ["Anything else about your trip?"]                # next turn starts at the travel desk
    r = swarm.invoke({"messages": [{"role": "user", "content": "thanks"}]}, cfg, context=PRIYA)
    assert r["active_agent"] == "travel_desk"


def test_map_reduce_runs_all_workers():
    from part6.p5_map_reduce import team_quotes
    quote = lambda e: [("Quote", {"employee_id": e, "flight_ids": ["FL2", "FL4"], "hotel_id": "HT1", "total_inr": 190475})]
    SCRIPT[:] = [quote("E101"), quote("E202"), quote("E303")]
    people = [{"employee_id": e, "office": "india"} for e in ("E101", "E202", "E303")]
    r = team_quotes.invoke({"request": "quote", "travellers": people, "quotes": []})
    assert len(r["quotes"]) == 3 and r["total_inr"] == 3 * 190475


def test_critic_loop_revises_then_sends():
    from part6.p6_critic import email_loop
    SCRIPT[:] = ["Hey Arjun!!", [("Review", {"approved": False, "feedback": "Add start date and sign-off."})],
                 "Hi Arjun, ... The People Team", [("Review", {"approved": True, "feedback": ""})]]
    r = email_loop.invoke({"brief": "Arjun"})
    assert r["rounds"] == 2 and r["approved"] and ns.EMAILS


def test_critic_loop_gives_up_after_max_rounds():
    from part6.p6_critic import MAX_ROUNDS, email_loop
    SCRIPT[:] = ["draft", [("Review", {"approved": False, "feedback": "no"})]] * 5
    r = email_loop.invoke({"brief": "Arjun"})
    assert r["rounds"] == MAX_ROUNDS and not r["approved"] and ns.EMAILS


def test_blackboard_recovers_from_over_budget_venue():
    from part6.p7_blackboard import offsite
    SCRIPT[:] = [[("Venue", {"city": "Zurich", "venue": "Lakeside Palace", "cost_inr": 500000})],
                 [("Travel", {"cost_inr": 150000, "notes": "flights"})],
                 [("Venue", {"city": "Goa", "venue": "Beach Campus", "cost_inr": 180000})],
                 [("Travel", {"cost_inr": 120000, "notes": "flights"})]]
    r = offsite.invoke({"goal": "offsite", "steps": 0})
    assert r["budget_ok"] and r["venue"]["venue"] == "Beach Campus" and r["rejected_venues"] == ["Lakeside Palace"]
