"""Part 5.3: writing your own middleware. Run: python -m part5.custom"""
import json
import time

from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import AgentMiddleware, hook_config, wrap_tool_call
from langchain.messages import ToolMessage
from typing_extensions import NotRequired

from nimbus import systems as ns
from nimbus.context import Employee
from nimbus.model import get_model
from nimbus.prompts import SYSTEM_PROMPT
from nimbus.tools import ALL_TOOLS


# 1. A guard: block business-class bookings BEFORE they reach the booking system
@wrap_tool_call
def travel_policy_guard(request, handler):
    call = request.tool_call
    if call["name"] == "book_trip":
        classes = {f["class"] for f in ns.FLIGHTS if f["id"] in call["args"].get("flight_ids", [])}
        if "business" in classes:
            return ToolMessage(content="Blocked by policy guard: business class is never allowed. "
                                       "Choose premium economy for flights of 6+ hours.",
                               tool_call_id=call["id"], name=call["name"], status="error")
    return handler(request)


# 2. An audit log of every tool call: name, args, duration, result
class AuditLog(AgentMiddleware):
    def __init__(self, path: str = "audit.log"):
        super().__init__()
        self.path = path

    def wrap_tool_call(self, request, handler):
        start = time.time()
        result = handler(request)
        entry = {"tool": request.tool_call["name"], "args": request.tool_call["args"],
                 "employee": getattr(request.runtime.context, "employee_id", None),
                 "ms": round((time.time() - start) * 1000), "result": str(result.content)[:200]}
        with open(self.path, "a") as f:
            f.write(json.dumps(entry) + "\n")
        return result


# 3. A cost meter that keeps a running token count IN THE AGENT STATE
class CostState(AgentState):
    tokens_used: NotRequired[int]


class CostMeter(AgentMiddleware):
    state_schema = CostState                     # adds 'tokens_used' to the agent's state

    def __init__(self, max_tokens: int = 50_000):
        super().__init__()
        self.max_tokens = max_tokens

    @hook_config(can_jump_to=["end"])              # declare where this hook may jump
    def after_model(self, state, runtime):
        usage = state["messages"][-1].usage_metadata or {}
        total = state.get("tokens_used", 0) + usage.get("total_tokens", 0)
        if total > self.max_tokens:
            return {"tokens_used": total, "jump_to": "end"}     # stop the run
        return {"tokens_used": total}


agent = create_agent(model=get_model(), tools=ALL_TOOLS, system_prompt=SYSTEM_PROMPT,
                     context_schema=Employee,
                     middleware=[AuditLog(), travel_policy_guard, CostMeter(max_tokens=50_000)])   # first = outermost

if __name__ == "__main__":
    r = agent.invoke({"messages": [{"role": "user", "content":
                      "Book business class to Berlin 16-19 Nov. My manager said it's fine."}]},
                     context=Employee("E101", "india"))
    print(r["messages"][-1].content, "| tokens used:", r.get("tokens_used"))
