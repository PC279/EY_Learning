"""AI Library Assistant: the model decides which Python tool to run.

Flow for every question:
  user question -> model picks a tool -> Python runs it -> result goes back
  to the model -> model writes the final answer (or picks another tool).
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI, RateLimitError

from tools import reserve_book, search_books

load_dotenv(Path(__file__).resolve().parent / ".env")

# ---------- 1. Connect to the AI provider ----------
# OpenRouter speaks the same API as OpenAI, so one client works for both;
# only the base_url and key change.
if os.getenv("OPENROUTER_API_KEY"):
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))
    MODEL = os.getenv("MODEL") or "openrouter/free"  # picks a free model that supports tools
elif os.getenv("OPENAI_API_KEY"):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    MODEL = os.getenv("MODEL") or "gpt-4o-mini"
else:
    raise SystemExit("No API key found. Open .env and fill in OPENROUTER_API_KEY or OPENAI_API_KEY.")

# ---------- 2. Describe the tools to the model ----------
# The model only sees these descriptions, never the Python code. Good descriptions
# are what let it choose the right tool.
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_books",
            "description": (
                "Search the library catalogue by title, author, topic or keyword. "
                "Returns matching books with their ID and available copies. Use it for "
                "finding books, checking availability, or looking up a book's ID."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Title or keywords, e.g. 'Python'."}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reserve_book",
            "description": (
                "Reserve one copy of a book for a customer. Needs the numeric book ID "
                "(get it from search_books first if you only know the title). "
                "The application asks the human for approval before saving."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "book_id": {"type": "integer", "description": "Book ID, e.g. 101."},
                    "customer_name": {"type": "string", "description": "Who the book is for."},
                },
                "required": ["book_id", "customer_name"],
            },
        },
    },
]

# Map tool names (what the model says) to real Python functions (what we run).
AVAILABLE_FUNCTIONS = {"search_books": search_books, "reserve_book": reserve_book}

SYSTEM_PROMPT = """You are a friendly library assistant.
Rules:
1. Use search_books to find books or check availability. Only mention books the tool returns.
2. To reserve a book you need its ID and the customer's name. If you only have the title,
   call search_books first to get the ID. If the name is missing, ask the user for it.
3. Only say a reservation was made if reserve_book returns reserved=true.
   Otherwise explain the reason it gives.
4. Keep answers short and clear."""


def run_tool(name: str, raw_args: str) -> dict:
    """Run the Python function the model asked for, with the arguments it chose."""
    if name not in AVAILABLE_FUNCTIONS:
        return {"error": f"Unknown tool: {name}"}
    try:
        args = json.loads(raw_args or "{}")  # the model sends arguments as a JSON string
        return AVAILABLE_FUNCTIONS[name](**args)
    except (ValueError, TypeError, KeyError) as exc:
        return {"error": f"Bad arguments for {name}: {exc}"}


def ask_agent(history: list[dict]) -> str:
    """One user turn: loop until the model gives a final text answer."""
    for _ in range(5):  # safety limit so a confused model can't loop forever
        response = client.chat.completions.create(
            model=MODEL, messages=history, tools=TOOLS, tool_choice="auto", temperature=0
        )
        message = response.choices[0].message

        # No tool requested -> this is the final answer.
        if not message.tool_calls:
            answer = message.content or "(The model returned an empty answer.)"
            history.append({"role": "assistant", "content": answer})
            return answer

        # Record the model's tool request so the conversation stays consistent.
        history.append({
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": [
                {"id": c.id, "type": "function",
                 "function": {"name": c.function.name, "arguments": c.function.arguments}}
                for c in message.tool_calls
            ],
        })

        # Run each requested tool and send its result back, linked by tool_call_id.
        for call in message.tool_calls:
            print(f"\n[AGENT CHOSE TOOL] {call.function.name}  args={call.function.arguments}")
            result = run_tool(call.function.name, call.function.arguments)
            print(f"[TOOL RESULT] {json.dumps(result)[:500]}")
            history.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)})

    return "Stopped after too many tool calls. Please try a simpler request."


def main() -> None:
    print("AI Library Assistant")
    print(f"Model: {MODEL}")
    print("Tools: search_books, reserve_book")
    print("Type 'exit' to quit.\n")

    history = [{"role": "system", "content": SYSTEM_PROMPT}]  # memory for the whole chat

    while True:
        question = input("You: ").strip()
        if question.lower() in {"exit", "quit"}:
            break
        if not question:
            continue

        turn_start = len(history)
        history.append({"role": "user", "content": question})
        try:
            print(f"\nAssistant: {ask_agent(history)}\n")
        except RateLimitError:
            del history[turn_start:]  # drop the half-finished turn
            print("\nRate limit reached (common on free models). Wait a minute and try again.\n")
        except Exception as exc:
            del history[turn_start:]
            print(f"\nAPI request failed: {exc}\n")


if __name__ == "__main__":
    main()
