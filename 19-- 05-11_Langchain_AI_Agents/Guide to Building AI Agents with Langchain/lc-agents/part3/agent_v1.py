"""Part 3: Nimbus Assist v1 with create_agent. Run: python -m part3.agent_v1"""
from langchain.agents import create_agent

from nimbus.context import Employee
from nimbus.model import get_model
from nimbus.prompts import SYSTEM_PROMPT
from nimbus.tools import ALL_TOOLS

agent = create_agent(
    model=get_model(),
    tools=ALL_TOOLS,
    system_prompt=SYSTEM_PROMPT,
    context_schema=Employee,          # the type of the run-time context (Part 4.2)
)

if __name__ == "__main__":
    priya = Employee(employee_id="E101", office="india")
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "How many leave days do I have left?"}]},
        context=priya,
    )
    for message in result["messages"]:
        message.pretty_print()        # every step: human, AI (tool call), tool result, AI answer
