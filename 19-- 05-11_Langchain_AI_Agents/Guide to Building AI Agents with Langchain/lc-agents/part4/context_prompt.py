"""Part 4.2-4.3: run-time context and a dynamic system prompt. Run: python -m part4.context_prompt"""
from langchain.agents import create_agent
from langchain.agents.middleware import ModelRequest, dynamic_prompt

from nimbus import systems as ns
from nimbus.context import Employee
from nimbus.model import get_model
from nimbus.prompts import SYSTEM_PROMPT
from nimbus.tools import ALL_TOOLS


@dynamic_prompt
def personalised_prompt(request: ModelRequest) -> str:
    """Rebuilt before every model call, from the run-time context."""
    who: Employee = request.runtime.context
    emp = ns.get_employee(who.employee_id)
    extra = (f"\nYou are helping {emp['name']} ({who.employee_id}) from the {who.office} office."
             f"\nOn probation: {emp['on_probation']}.")
    if who.office == "germany":
        extra += "\nUse EUR when talking about money."
    return SYSTEM_PROMPT + extra


agent = create_agent(model=get_model(), tools=ALL_TOOLS, middleware=[personalised_prompt],
                     context_schema=Employee)

if __name__ == "__main__":
    lukas = Employee(employee_id="E202", office="germany")
    result = agent.invoke({"messages": [{"role": "user", "content": "Can I take 7 days off from 23 Nov?"}]},
                          context=lukas)
    print(result["messages"][-1].content)
