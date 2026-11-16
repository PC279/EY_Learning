"""Part 8: a supervisor agent that uses specialist agents as tools. Run: python -m part8.subagents"""
from langchain.agents import create_agent
from langchain.tools import ToolRuntime, tool

from nimbus import tools as t
from nimbus.context import Employee
from nimbus.model import get_model
from nimbus.prompts import SYSTEM_PROMPT

model = get_model()

travel_agent = create_agent(model, [t.get_travel_policy, t.search_flights, t.search_hotels, t.book_trip],
                            system_prompt=SYSTEM_PROMPT + "\nYou only handle travel.",
                            context_schema=Employee, name="travel_agent")
leave_agent = create_agent(model, [t.get_leave_balance, t.search_hr_policies, t.apply_leave],
                           system_prompt=SYSTEM_PROMPT + "\nYou only handle leave.",
                           context_schema=Employee, name="leave_agent")
it_agent = create_agent(model, [t.create_it_ticket], system_prompt=SYSTEM_PROMPT + "\nYou only handle IT.",
                        context_schema=Employee, name="it_agent")


def _delegate(agent, task: str, runtime: ToolRuntime[Employee]) -> str:
    """Run a sub-agent on a self-contained task, with the same employee context."""
    result = agent.invoke({"messages": [{"role": "user", "content": task}]}, context=runtime.context)
    return result["messages"][-1].content          # only the final report goes back


@tool
def travel_specialist(task: str, runtime: ToolRuntime[Employee]) -> str:
    """Delegate a complete travel task (search, policy check, booking). Give full details: dates, cities."""
    return _delegate(travel_agent, task, runtime)


@tool
def leave_specialist(task: str, runtime: ToolRuntime[Employee]) -> str:
    """Delegate a complete leave task (balance, probation rules, applying). Give exact dates."""
    return _delegate(leave_agent, task, runtime)


@tool
def it_specialist(task: str, runtime: ToolRuntime[Employee]) -> str:
    """Delegate an IT support task, such as opening a ticket. Describe the problem fully."""
    return _delegate(it_agent, task, runtime)


supervisor = create_agent(
    model, [travel_specialist, leave_specialist, it_specialist],
    system_prompt=(SYSTEM_PROMPT + "\nYou coordinate specialists. Split the request into self-contained "
                   "tasks, delegate each to the right specialist, then summarise all results."),
    context_schema=Employee,
)

if __name__ == "__main__":
    r = supervisor.invoke({"messages": [{"role": "user", "content":
                          "Book my Berlin trip 16-19 Nov and apply for leave on 20 Nov."}]},
                          context=Employee("E101", "india"))
    print(r["messages"][-1].content)
