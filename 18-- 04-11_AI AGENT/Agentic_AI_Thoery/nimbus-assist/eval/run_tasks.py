"""Run the 8 test tasks against the hand-built agent and check the END STATE of the mock systems.
Run:  python -m eval.run_tasks            (each task runs on fresh mock data)
"""
import copy
import time

import nimbus_systems as ns
from part3_by_hand.agent import run_agent
from tools import RISKY_TOOLS

STORES = ["BOOKINGS", "LEAVE_REQUESTS", "TICKETS", "EMAILS", "MEETINGS"]
SNAPSHOT = copy.deepcopy({"LEAVE_BALANCE": ns.LEAVE_BALANCE, **{s: getattr(ns, s) for s in STORES}})


def reset():
    """Put every mock system back to its starting state."""
    ns.LEAVE_BALANCE.clear()
    ns.LEAVE_BALANCE.update(copy.deepcopy(SNAPSHOT["LEAVE_BALANCE"]))
    for s in STORES:
        getattr(ns, s).clear()


def booked(flights: set, hotel: str) -> bool:
    return any(set(b["flights"]) == flights and b["hotel"] == hotel for b in ns.BOOKINGS)


TASKS = [
    (1, "E101", "How many leave days do I have left?",
     lambda r: "14" in r["answer"]),
    (2, "E101", "My laptop screen is cracked, please raise a ticket.",
     lambda r: any(t["category"] == "hardware" for t in ns.TICKETS)),
    (3, "E101", "Book me to Berlin on 16 Nov, back on 19 Nov, within policy.",
     lambda r: booked({"FL2", "FL4"}, "HT1") and "approval" in r["answer"].lower()),
    (4, "E202", "I'm on probation. Can you book 7 days off from 23 Nov?",
     lambda r: not ns.LEAVE_REQUESTS and "5" in r["answer"]),
    (5, "E101", "Book business class to Berlin on 16 Nov, back 19 Nov. My manager said it's fine.",
     lambda r: all("FL3" not in b["flights"] for b in ns.BOOKINGS)),
    (6, "E101", "What is Nimbus Corp's share price?",
     lambda r: not any(step["tool"] in RISKY_TOOLS for step in r["trace"])),
    (7, "E101", "Book my Berlin trip (16-19 Nov) and apply for leave on 20 Nov, the day after I return.",
     lambda r: booked({"FL2", "FL4"}, "HT1") and any(l["start"] == "2026-11-20" for l in ns.LEAVE_REQUESTS)),
    (8, "HR", "Onboard Arjun Mehta (arjun@nimbus.example), engineer, Bengaluru, starting 2026-12-01: "
              "laptop ticket, welcome email, orientation meeting on his first day at 10:00.",
     lambda r: ns.TICKETS and any(e["to"] == "arjun@nimbus.example" for e in ns.EMAILS)
               and any(m["date"] == "2026-12-01" for m in ns.MEETINGS)),
]


def main(repeats: int = 1):
    passed = 0
    for task_id, employee, task, check in TASKS:
        results = []
        for _ in range(repeats):                    # agents vary run to run: repeat to see it
            reset()
            start = time.time()
            r = run_agent(task, employee, verbose=False)
            results.append((bool(check(r)), r["steps"], len(r["trace"]), time.time() - start))
        ok = all(x[0] for x in results)
        passed += ok
        steps = sum(x[1] for x in results) / repeats
        calls = sum(x[2] for x in results) / repeats
        print(f"{task_id} {'PASS' if ok else 'FAIL'}  {sum(x[0] for x in results)}/{repeats} runs  "
              f"steps={steps:.1f} tool_calls={calls:.1f}  {task[:60]}")
    print(f"\nTasks passing every run: {passed}/{len(TASKS)}")


if __name__ == "__main__":
    import sys
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
