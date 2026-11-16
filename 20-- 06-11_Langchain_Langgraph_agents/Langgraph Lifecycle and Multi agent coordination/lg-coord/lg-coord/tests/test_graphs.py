"""Parts 2-4: graphs with no model, plus the lifecycle tracer."""
from langgraph.types import Command

from nimbus import systems as ns
from nimbus.context import Employee
from tests.scripted import SCRIPT


def test_onboarding_branches_on_role():
    from part2.onboarding_graph import graph
    base = {"name": "Arjun", "email": "a@n.example", "start_date": "2026-12-01", "tickets": [], "log": [],
            "welcome_sent": False}
    assert len(graph.invoke({**base, "role": "engineer"})["tickets"]) == 2
    assert len(graph.invoke({**base, "role": "sales"})["tickets"]) == 1


def test_send_runs_one_worker_per_traveller():
    from part3.command_send import quotes_graph
    r = quotes_graph.invoke({"travellers": ["E101", "E202"], "quotes": []})
    assert len(r["quotes"]) == 2 and r["cheapest"]


def test_retry_interrupt_resume_and_fork():
    from part3 import persistence as p
    p.ATTEMPTS["n"] = 0
    cfg = {"configurable": {"thread_id": "t-fork"}}
    p.graph.invoke({"employee_id": "E101", "log": []}, cfg)
    assert p.ATTEMPTS["n"] == 2                                   # failed once, retried once
    assert p.graph.get_state(cfg).next == ("ask_approval",)       # paused
    assert p.graph.invoke(Command(resume="no"), cfg)["log"][-1] == "not booked"
    before = next(s for s in p.graph.get_state_history(cfg) if s.next == ("ask_approval",))
    fork = p.graph.update_state(before.config, {"log": ["fork"]})
    p.graph.invoke(None, fork)
    assert p.graph.get_state(fork).next == ("ask_approval",)      # the fork paused again


def test_lifecycle_records_every_stage():
    from part4 import lifecycle as lc
    lc.EVENTS.clear()
    SCRIPT[:] = [[("book_trip", {"flight_ids": ["FL2", "FL4"], "hotel_id": "HT1", "nights": 3})], "Booked."]
    lc.run_with_pause("Book Berlin", Employee("E101", "india"), "life-test")
    stages = [e.split()[1] for e in lc.EVENTS]
    # after_* hooks run in REVERSE list order: the approval pause (inside HITL's after_model) happens
    # before the tracer's after_model, so DECIDE is logged only once the run resumes.
    assert stages == ["START", "THINK", "PAUSED", "RESUME", "DECIDE", "ACT", "OBSERVE", "THINK", "DECIDE", "COMPLETE"]
    assert ns.BOOKINGS
