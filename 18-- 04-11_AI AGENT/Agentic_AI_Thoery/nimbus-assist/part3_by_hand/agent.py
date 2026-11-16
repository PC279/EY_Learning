"""Nimbus Assist, built by hand: the agent loop in plain Python.
Run:  python -m part3_by_hand.agent --employee E101
"""
import argparse
import json

from openai import OpenAI

import config
from tools import RISKY_TOOLS, TOOL_FUNCTIONS, TOOL_SCHEMAS

client = OpenAI(api_key=config.OPENROUTER_API_KEY, base_url=config.OPENROUTER_BASE_URL)

SYSTEM_PROMPT = f"""You are Nimbus Assist, an HR and workplace agent for Nimbus Corp employees.
Today is {config.TODAY}. You are helping employee {{employee_id}}.

How to work:
1. Make a short plan, then use tools to gather facts before acting. Never guess ids, dates or prices.
2. Follow company policy. Check the travel policy before booking; check leave balance before applying.
3. Tools marked CHANGES DATA are checked with the employee before they run.
4. If a tool returns an error or a rejection, read the reason and adjust; do not repeat the same call.
5. If a request is not something your tools can do, say so plainly.
6. Finish with a short summary of what you did and anything still pending (e.g. manager approval)."""


def run_tool(name: str, args: dict, approve) -> dict:
    """Execute one tool call safely: unknown tools, bad arguments and refusals become messages."""
    if name not in TOOL_FUNCTIONS:
        return {"error": f"Unknown tool {name}"}
    if name in RISKY_TOOLS and not approve(name, args):
        return {"status": "cancelled", "reason": "The employee did not approve this action."}
    try:
        return TOOL_FUNCTIONS[name](**args)
    except TypeError as e:                      # wrong or missing arguments
        return {"error": f"Bad arguments for {name}: {e}"}


def run_agent(task: str, employee_id: str, approve=lambda name, args: True, verbose: bool = True) -> dict:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(employee_id=employee_id)},
        {"role": "user", "content": task},
    ]
    trace = []                                   # every tool call, for debugging and evaluation
    for step in range(1, config.MAX_STEPS + 1):
        response = client.chat.completions.create(
            model=config.CHAT_MODEL, messages=messages, tools=TOOL_SCHEMAS, temperature=0,
        )
        msg = response.choices[0].message

        if not msg.tool_calls:                   # no tool requested -> the agent is done
            return {"answer": msg.content, "steps": step, "trace": trace}

        # Record the assistant's request for tools exactly as the API expects it back
        messages.append({"role": "assistant", "content": msg.content or "", "tool_calls": [
            {"id": tc.id, "type": "function",
             "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
            for tc in msg.tool_calls]})

        for tc in msg.tool_calls:                # ACT, then OBSERVE
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args, result = {}, {"error": "Arguments were not valid JSON."}
            else:
                result = run_tool(tc.function.name, args, approve)
            trace.append({"step": step, "tool": tc.function.name, "args": args, "result": result})
            if verbose:
                print(f"  [{step}] {tc.function.name}({args}) -> {json.dumps(result)[:120]}")
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(result)})

    return {"answer": "I stopped after reaching the step limit. Please contact HR.",
            "steps": config.MAX_STEPS, "trace": trace}


def ask_human(name: str, args: dict) -> bool:
    return input(f"  Allow {name}({args})? [y/N] ").strip().lower() == "y"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--employee", default="E101")
    args = parser.parse_args()
    while (task := input("\nYou> ").strip()) not in {"", "exit", "quit"}:
        print("Nimbus Assist>", run_agent(task, args.employee, approve=ask_human)["answer"])
