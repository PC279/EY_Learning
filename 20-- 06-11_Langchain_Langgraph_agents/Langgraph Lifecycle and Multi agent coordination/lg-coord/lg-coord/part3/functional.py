"""Part 3.7: the Functional API - the same onboarding flow as Part 2, as plain Python functions.
Run: python -m part3.functional
"""
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.func import entrypoint, task

from nimbus import systems as ns


@task                                                     # a unit of work; its result is checkpointed
def laptop_ticket(name: str) -> str:
    return ns.create_it_ticket("HR", "hardware", f"Laptop for {name}")["id"]


@task
def access_ticket(name: str) -> str:
    return ns.create_it_ticket("HR", "access", f"GitHub access for {name}")["id"]


@task
def welcome_email(email: str, tickets: list[str]) -> str:
    return ns.send_email(email, "Welcome to Nimbus!", f"Your tickets: {tickets}")["status"]


@entrypoint(checkpointer=InMemorySaver())                 # the workflow; normal if/for/while control flow
def onboard(new_joiner: dict) -> dict:
    tickets = [laptop_ticket(new_joiner["name"])]         # calling a task returns a future
    if new_joiner["role"] == "engineer":
        tickets.append(access_ticket(new_joiner["name"]))
    ids = [t.result() for t in tickets]                   # .result() waits; tasks can run in parallel
    status = welcome_email(new_joiner["email"], ids).result()
    return {"tickets": ids, "email": status}


if __name__ == "__main__":
    cfg = {"configurable": {"thread_id": "onboard-arjun"}}
    print(onboard.invoke({"name": "Arjun", "email": "arjun@nimbus.example", "role": "engineer"}, cfg))
