"""Part 4: watch one agent run go through its lifecycle, including a pause and a resume.
Run: python -m part4.lifecycle
"""
import time

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware, HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from nimbus.context import Employee
from nimbus.model import get_model
from nimbus.prompts import SYSTEM_PROMPT
from nimbus.tools import ALL_TOOLS

EVENTS: list[str] = []                      # the lifecycle, as it happens


def log(stage: str, detail: str = ""):
    EVENTS.append(f"{time.strftime('%H:%M:%S')}  {stage:<14} {detail}")


class LifecycleTracer(AgentMiddleware):
    """Records every lifecycle stage of a run. Each hook = one stage."""

    def before_agent(self, state, runtime):                     # 1. START: request received
        log("START", f"employee={runtime.context.employee_id}, {len(state['messages'])} messages")

    def before_model(self, state, runtime):                     # 2. PERCEIVE + 3. REASON begin
        log("THINK", f"model call with {len(state['messages'])} messages")

    def after_model(self, state, runtime):                      # 3. REASON ends: decision made
        calls = [tc["name"] for tc in state["messages"][-1].tool_calls]
        log("DECIDE", f"tools {calls}" if calls else "final answer")

    def wrap_tool_call(self, request, handler):                 # 4. ACT + 5. OBSERVE
        log("ACT", request.tool_call["name"])
        result = handler(request)
        log("OBSERVE", str(result.content)[:60])
        return result

    def after_agent(self, state, runtime):                      # 6. COMPLETE
        log("COMPLETE", f"{len(state['messages'])} messages in thread")


agent = create_agent(
    get_model(), ALL_TOOLS, system_prompt=SYSTEM_PROMPT, context_schema=Employee,
    middleware=[LifecycleTracer(),                               # first = outermost: sees everything
                HumanInTheLoopMiddleware(interrupt_on={"book_trip": True})],
    checkpointer=InMemorySaver(),                                # PERSIST: every step saved
)


def run_with_pause(task: str, employee: Employee, thread_id: str) -> str:
    cfg = {"configurable": {"thread_id": thread_id}}
    result = agent.invoke({"messages": [{"role": "user", "content": task}]}, cfg, context=employee)
    while "__interrupt__" in result:                             # PAUSE: waiting for a human
        log("PAUSED", f"waiting on {[a['name'] for a in result['__interrupt__'][0].value['action_requests']]}")
        log("RESUME", "human approved")
        result = agent.invoke(Command(resume={"decisions": [{"type": "approve"}]}), cfg, context=employee)
    return result["messages"][-1].content


if __name__ == "__main__":
    print(run_with_pause("Book me to Berlin 16-19 Nov within policy.", Employee("E101", "india"), "life-1"))
    print("\n".join(EVENTS))
