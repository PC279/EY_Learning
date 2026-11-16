"""Part 7.2: streaming progress, tokens and custom events. Run: python -m part7.streaming"""
from langchain.agents import create_agent
from langchain.tools import ToolRuntime, tool

from nimbus import systems as ns
from nimbus.context import Employee
from nimbus.model import get_model
from nimbus.prompts import SYSTEM_PROMPT
from nimbus.tools import ALL_TOOLS


@tool
def check_all_hotels(runtime: ToolRuntime[Employee]) -> list[dict]:
    """Check every hotel in both cities and return the ones within policy."""
    ok = []
    for h in ns.HOTELS:
        runtime.stream_writer({"progress": f"checking {h['name']}"})     # custom event
        within = h.get("price_per_night_eur", 0) <= 150 and h.get("price_per_night_inr", 0) <= 7000
        if within:
            ok.append(h)
    return ok


agent = create_agent(model=get_model(), tools=ALL_TOOLS + [check_all_hotels],
                     system_prompt=SYSTEM_PROMPT, context_schema=Employee)

if __name__ == "__main__":
    question = {"messages": [{"role": "user", "content": "Which hotels are within policy?"}]}
    priya = Employee("E101", "india")
    for mode, data in agent.stream(question, context=priya, stream_mode=["updates", "messages", "custom"]):
        if mode == "updates":                          # one entry per finished step
            for step, update in data.items():
                last = update["messages"][-1] if update and "messages" in update else None
                print(f"\n[step: {step}]", getattr(last, "tool_calls", "") or "")
        elif mode == "messages":                       # LLM tokens as they are generated
            token, meta = data
            if meta.get("langgraph_node") == "model" and token.content:
                print(token.content, end="", flush=True)
        elif mode == "custom":                         # our stream_writer events
            print(f"\n  ... {data['progress']}")
