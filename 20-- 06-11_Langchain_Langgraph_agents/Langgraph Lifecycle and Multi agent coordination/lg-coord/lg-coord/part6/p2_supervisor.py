"""Pattern 2 - Supervisor: one manager agent routes work to specialists and decides when it's done.
Run: python -m part6.p2_supervisor
"""
from typing import Literal

from langchain_core.messages import AIMessage, SystemMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.types import Command
from pydantic import Field, create_model

from nimbus.context import Employee
from nimbus.model import get_model
from nimbus.specialists import make_specialists

MAX_ROUNDS = 6                                    # guard: the supervisor can't loop forever


class TeamState(MessagesState):
    rounds: int                                   # how many times the supervisor has delegated


def make_route(names: list[str]):
    """A structured-output schema whose 'next' can ONLY be one of these names or FINISH."""
    return create_model("Route",
                        next=(Literal[tuple(names + ["FINISH"])], ...),
                        instruction=(str, Field(description="A complete, self-contained task for that member")))


def build_supervisor_graph(members: dict, model, purpose: str) -> StateGraph:
    """Reusable: a supervisor over any {name: agent or compiled graph}. Pattern 3 reuses it."""
    names = list(members)
    router = model.with_structured_output(make_route(names))     # routing = structured output
    prompt = (f"You supervise a team: {', '.join(names)}. {purpose}\n"
              "Read the conversation and the members' reports. Choose ONE member for the next piece "
              "of work and give a complete instruction, or FINISH when every part of the request is done.")

    def supervisor(state: TeamState) -> Command:
        rounds = state.get("rounds", 0)
        if rounds >= MAX_ROUNDS:                                    # loop guard
            return Command(goto=END, update={"messages": [AIMessage("Stopped: too many rounds.", name="supervisor")]})
        decision = router.invoke([SystemMessage(prompt)] + state["messages"])
        if decision.next == "FINISH":
            return Command(goto=END)
        return Command(goto=decision.next, update={"rounds": rounds + 1, "messages": [
            AIMessage(f"[to {decision.next}] {decision.instruction}", name="supervisor")]})

    def make_worker(name: str):
        member = members[name]

        def worker(state: TeamState, runtime) -> Command:
            task = state["messages"][-1].content                    # ONLY the supervisor's instruction
            result = member.invoke({"messages": [{"role": "user", "content": task}]}, context=runtime.context)
            report = result["messages"][-1].content                 # ONLY the final report comes back
            return Command(goto="supervisor",
                           update={"messages": [AIMessage(f"[{name} report] {report}", name=name)]})
        return worker

    g = StateGraph(TeamState, context_schema=Employee)
    g.add_node("supervisor", supervisor, destinations=tuple(names) + (END,))   # for drawing the graph
    for n in names:
        g.add_node(n, make_worker(n), destinations=("supervisor",))
    g.add_edge(START, "supervisor")
    return g


model = get_model()
specialists = make_specialists(model)
team = build_supervisor_graph(specialists, model, "Nimbus HR, travel and IT requests.").compile(
    checkpointer=InMemorySaver())

if __name__ == "__main__":
    cfg = {"configurable": {"thread_id": "c2"}}
    r = team.invoke({"messages": [{"role": "user", "content":
                    "Book my Berlin trip 16-19 Nov and apply for leave on 20 Nov."}], "rounds": 0},
                    cfg, context=Employee("E101", "india"))
    for m in r["messages"]:
        print(getattr(m, "name", None) or m.type, ":", m.content[:100])
