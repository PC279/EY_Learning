"""Part 8: evaluate the supervisor team with a REAL model.
For each scenario we check three things: which specialists were used (routing), what changed in the
systems (end state), and how many rounds it took (efficiency). Run: python -m part8.eval_coordination 3
"""
import copy
import sys

from nimbus import systems as ns
from nimbus.context import Employee
from part6.p2_supervisor import team

PRIYA = Employee("E101", "india")
BALANCE = copy.deepcopy(ns.LEAVE_BALANCE)

SCENARIOS = [  # (request, specialists that MUST be used, check on the systems' end state)
    ("How many leave days do I have?", {"leave"}, lambda: not ns.BOOKINGS),
    ("My laptop screen is cracked, please raise a ticket.", {"it"}, lambda: len(ns.TICKETS) == 1),
    ("Book my Berlin trip 16-19 Nov and apply for leave on 20 Nov.", {"travel", "leave"},
     lambda: len(ns.BOOKINGS) == 1 and len(ns.LEAVE_REQUESTS) == 1),
    ("What is Nimbus Corp's share price?", set(), lambda: not ns.BOOKINGS and not ns.TICKETS),
]


def reset():
    ns.LEAVE_BALANCE.clear()
    ns.LEAVE_BALANCE.update(copy.deepcopy(BALANCE))
    for s in (ns.BOOKINGS, ns.LEAVE_REQUESTS, ns.TICKETS, ns.EMAILS, ns.MEETINGS):
        s.clear()


def run_once(i: int, request: str) -> dict:
    cfg = {"configurable": {"thread_id": f"eval-{i}-{id(request)}"}}
    result = team.invoke({"messages": [{"role": "user", "content": request}], "rounds": 0}, cfg, context=PRIYA)
    used = {m.name for m in result["messages"] if m.type == "ai" and m.name not in (None, "supervisor")}
    return {"used": used, "rounds": result.get("rounds", 0)}


def main(repeats: int = 1):
    passed = 0
    for i, (request, expected, end_state_ok) in enumerate(SCENARIOS):
        ok_runs, rounds = 0, 0
        for r in range(repeats):
            reset()
            out = run_once(i * 100 + r, request)
            routing_ok = out["used"] == expected            # exactly the right specialists, no extras
            ok_runs += routing_ok and end_state_ok()
            rounds += out["rounds"]
        passed += ok_runs == repeats
        print(f"{'PASS' if ok_runs == repeats else 'FAIL'} {ok_runs}/{repeats}  avg rounds={rounds / repeats:.1f}  "
              f"expected={sorted(expected) or 'none'}  {request[:50]}")
    print(f"\nScenarios passing every run: {passed}/{len(SCENARIOS)}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
