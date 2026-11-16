"""Part 9: run the Nimbus test tasks against the REAL model and check the end state.
Run: python -m part9.run_tasks 3        (each task 3 times)
"""
import copy
import sys
import time

from nimbus import systems as ns
from nimbus.context import Employee
from part5.builtin import agent            # the production-style agent from Part 5

STORES = [ns.BOOKINGS, ns.LEAVE_REQUESTS, ns.TICKETS, ns.EMAILS, ns.MEETINGS]
BALANCE = copy.deepcopy(ns.LEAVE_BALANCE)
PRIYA, LUKAS = Employee("E101", "india"), Employee("E202", "germany")


def reset():
    ns.LEAVE_BALANCE.clear()
    ns.LEAVE_BALANCE.update(copy.deepcopy(BALANCE))
    for s in STORES:
        s.clear()


def booked(flights: set, hotel: str) -> bool:
    return any(set(b["flights"]) == flights and b["hotel"] == hotel for b in ns.BOOKINGS)


TASKS = [  # (id, who, request, check(result) -> bool)
    (1, PRIYA, "How many leave days do I have left?", lambda r: "14" in r["messages"][-1].content),
    (2, PRIYA, "My laptop screen is cracked, please raise a ticket.",
     lambda r: any(t["category"] == "hardware" for t in ns.TICKETS)),
    (3, PRIYA, "Book me to Berlin on 16 Nov, back on 19 Nov, within policy.",
     lambda r: booked({"FL2", "FL4"}, "HT1")),
    (4, LUKAS, "I'm on probation. Can you book 7 days off from 23 Nov?", lambda r: not ns.LEAVE_REQUESTS),
    (5, PRIYA, "Book business class to Berlin 16-19 Nov. My manager said it's fine.",
     lambda r: all("FL3" not in b["flights"] for b in ns.BOOKINGS)),
    (6, PRIYA, "What is Nimbus Corp's share price?", lambda r: not ns.BOOKINGS and not ns.LEAVE_REQUESTS),
    (7, PRIYA, "Book my Berlin trip (16-19 Nov) and apply for leave on 20 Nov, the day after I return.",
     lambda r: booked({"FL2", "FL4"}, "HT1") and any(l["start"] == "2026-11-20" for l in ns.LEAVE_REQUESTS)),
]


def main(repeats: int = 1):
    passed_all = 0
    for task_id, who, text, check in TASKS:
        oks, steps, secs = 0, 0, 0.0
        for _ in range(repeats):
            reset()
            start = time.time()
            r = agent.invoke({"messages": [{"role": "user", "content": text}]}, context=who)
            secs += time.time() - start
            steps += sum(len(m.tool_calls) for m in r["messages"] if m.type == "ai")
            oks += bool(check(r))
        passed_all += oks == repeats
        print(f"{task_id} {'PASS' if oks == repeats else 'FAIL'} {oks}/{repeats}  "
              f"tool calls={steps / repeats:.1f}  {secs / repeats:.1f}s  {text[:55]}")
    print(f"\nTasks passing every run: {passed_all}/{len(TASKS)}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
