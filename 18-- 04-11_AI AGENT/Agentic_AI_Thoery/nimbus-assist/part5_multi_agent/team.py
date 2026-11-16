"""Multi-agent Nimbus Assist: a supervisor routes work to specialist agents.
Run:  python -m part5_multi_agent.team
"""
from typing import Literal

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, SystemMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.types import Command
from pydantic import BaseModel, Field

import config
from part4_langgraph import lc_tools as t
from part4_langgraph.model import llm

COMMON = (f"Today is {config.TODAY}. Use your tools; never guess ids, dates or prices. "
          "When finished, reply with a short factual summary of what you did and what is pending.")

SPECIALISTS = {
    "travel": create_agent(llm, [t.get_travel_policy, t.search_flights, t.search_hotels, t.book_trip],
                           system_prompt="You are the Nimbus travel agent. Book trips strictly within "
                                         "the travel policy. " + COMMON, name="travel"),
    "leave": create_agent(llm, [t.get_leave_balance, t.search_hr_policies, t.apply_leave],
                          system_prompt="You are the Nimbus leave agent. Check balances and probation "
                                        "rules before applying for leave. " + COMMON, name="leave"),
    "it": create_agent(llm, [t.create_it_ticket],
                       system_prompt="You are the Nimbus IT agent. Open clear, correctly categorised "
                                     "tickets. " + COMMON, name="it"),
    "comms": create_agent(llm, [t.get_employee, t.send_email, t.schedule_meeting],
                          system_prompt="You are the Nimbus communications agent. Write short, warm, "
                                        "professional emails and schedule meetings. " + COMMON, name="comms"),
}


class Route(BaseModel):
    """The supervisor's decision."""
    next: Literal["travel", "leave", "it", "comms", "FINISH"] = Field(
        description="Which specialist acts next, or FINISH when every part of the request is done.")
    instruction: str = Field(description="What that specialist should do now, in one or two sentences.")


SUPERVISOR_PROMPT = f"""You are the supervisor of the Nimbus Assist team. Today is {config.TODAY}.
Specialists: travel (flights, hotels, bookings), leave (balances, leave requests),
it (IT tickets), comms (emails, meetings, employee lookups).
Read the conversation, including the specialists' reports. Pick ONE specialist for the next piece of
work and give it a clear instruction, or FINISH when every part of the request is done.
Never send the same instruction twice."""


class TeamState(MessagesState):
    employee_id: str


def supervisor(state: TeamState) -> Command[Literal["travel", "leave", "it", "comms", "__end__"]]:
    decision = llm.with_structured_output(Route).invoke(
        [SystemMessage(SUPERVISOR_PROMPT + f"\nRequester: {state['employee_id']}")] + state["messages"])
    if decision.next == "FINISH":
        return Command(goto=END)
    return Command(goto=decision.next,
                   update={"messages": [AIMessage(f"[to {decision.next}] {decision.instruction}",
                                                  name="supervisor")]})


def make_worker(name: str):
    agent = SPECIALISTS[name]

    def worker(state: TeamState) -> Command[Literal["supervisor"]]:
        result = agent.invoke({"messages": state["messages"]})
        report = result["messages"][-1].content
        return Command(goto="supervisor",
                       update={"messages": [AIMessage(f"[{name} report] {report}", name=name)]})
    return worker


builder = StateGraph(TeamState)
builder.add_node("supervisor", supervisor)
for name in SPECIALISTS:
    builder.add_node(name, make_worker(name))
builder.add_edge(START, "supervisor")
team = builder.compile(checkpointer=InMemorySaver())


def run(task: str, employee_id: str, thread_id: str, approve=lambda req: "yes") -> str:
    cfg = {"configurable": {"thread_id": thread_id}, "recursion_limit": 30}
    result = team.invoke({"messages": [("user", task)], "employee_id": employee_id}, cfg)
    while "__interrupt__" in result:                          # risky actions wait for a human
        answers = {i.id: approve(i.value) for i in result["__interrupt__"]}
        result = team.invoke(Command(resume=answers), cfg)
    reports = [m.content for m in result["messages"] if getattr(m, "name", "") in SPECIALISTS]
    return "\n".join(reports)


if __name__ == "__main__":
    task = ("Onboard Arjun Mehta (arjun@nimbus.example), engineer, Bengaluru, starting 2026-12-01: "
            "laptop, welcome email, orientation meeting on his first day at 10:00.")
    print(run(task, "HR", thread_id="onboard-arjun",
              approve=lambda req: input(f"Allow {req['action']}({req['args']})? [y/N] ")))
