"""Part 3: a simple chat loop that keeps history itself. Run: python -m part3.chat"""
from nimbus.context import Employee
from part3.agent_v1 import agent

priya = Employee("E101", "india")
history = []
while (text := input("\nYou> ").strip()) not in {"", "exit", "quit"}:
    history.append({"role": "user", "content": text})
    result = agent.invoke({"messages": history}, context=priya)
    history = result["messages"]                 # keep everything, including tool calls
    print("Nimbus Assist>", history[-1].content)
