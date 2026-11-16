"""Web API for the AI Library Assistant. The React app (frontend/) talks to this file.

It runs the same agent loop as agent.py, with one difference: reservations
pause and wait for the user's Confirm/Cancel click instead of a terminal input().

Endpoints:
  POST /api/chat     send a message, get the assistant's reply
  POST /api/confirm  answer Confirm/Cancel for a reservation waiting for approval
  GET  /api/health   check that the server is running and see the model name
"""

import json

import uvicorn
from fastapi import FastAPI, HTTPException
from openai import RateLimitError
from pydantic import BaseModel

# Reuse the model connection, tool descriptions and rules from the terminal agent.
from agent import MODEL, SYSTEM_PROMPT, TOOLS, client, run_tool
from tools import check_reservation, reserve_book

app = FastAPI(title="AI Library Assistant API")

# One conversation per browser tab, kept in memory (cleared when the server restarts).
# Each session: {"history": [...messages...], "pending": reservation waiting for approval or None}
sessions: dict[str, dict] = {}


# Shapes of the JSON the browser sends. FastAPI rejects requests that don't match.
class ChatRequest(BaseModel):
    session_id: str
    message: str


class ConfirmRequest(BaseModel):
    session_id: str
    approved: bool


def get_session(session_id: str) -> dict:
    if session_id not in sessions:
        sessions[session_id] = {"history": [{"role": "system", "content": SYSTEM_PROMPT}], "pending": None}
    return sessions[session_id]


def reply(text: str, tools_used: list[str], approval: dict | None = None) -> dict:
    """The JSON shape every endpoint returns to the browser."""
    return {"reply": text, "tools_used": list(dict.fromkeys(tools_used)), "approval": approval}


def add_tool_result(history: list[dict], call_id: str, result: dict) -> None:
    print(f"[TOOL RESULT] {json.dumps(result)[:500]}")
    history.append({"role": "tool", "tool_call_id": call_id, "content": json.dumps(result)})


def process_calls(session: dict, calls: list[dict], tools_used: list[str]) -> dict | None:
    """Run the model's tool calls in order.

    Returns approval details (and stops) if a reservation needs the user's click.
    Returns None when every call has run and has a result in the history.
    """
    for i, call in enumerate(calls):
        print(f"\n[AGENT CHOSE TOOL] {call['name']}  args={call['arguments']}")
        tools_used.append(call["name"])

        if call["name"] != "reserve_book":
            add_tool_result(session["history"], call["id"], run_tool(call["name"], call["arguments"]))
            continue

        # reserve_book: check first, save nothing yet.
        try:
            args = json.loads(call["arguments"] or "{}")
        except ValueError:
            args = {}
        check = check_reservation(args.get("book_id"), args.get("customer_name"))
        if not check["ok"]:  # e.g. no copies left: tell the model, never show buttons
            add_tool_result(session["history"], call["id"], {"reserved": False, "reason": check["reason"]})
            continue

        # Possible: pause here and remember exactly what to reserve. The browser only
        # ever sends back yes/no, so it can't change which book or name gets saved.
        approval = {
            "book_id": check["book"]["id"],
            "title": check["book"]["title"],
            "customer_name": check["customer_name"],
            "available_copies": check["book"]["available_copies"],
        }
        session["pending"] = {"call": call, "remaining": calls[i + 1:], **approval}
        return approval
    return None


def approval_reply(approval: dict, tools_used: list[str]) -> dict:
    text = (f"'{approval['title']}' is available. Please confirm the reservation "
            f"for {approval['customer_name']}.")
    return reply(text, tools_used, approval)


def run_agent(session: dict, tools_used: list[str]) -> dict:
    """Ask the model, run its tools, repeat until it answers or a reservation needs approval."""
    history = session["history"]
    for _ in range(5):  # safety limit, same as agent.py
        response = client.chat.completions.create(
            model=MODEL, messages=history, tools=TOOLS, tool_choice="auto", temperature=0
        )
        message = response.choices[0].message

        if not message.tool_calls:  # final answer
            answer = message.content or "(The model returned an empty answer.)"
            history.append({"role": "assistant", "content": answer})
            return reply(answer, tools_used)

        calls = [{"id": c.id, "name": c.function.name, "arguments": c.function.arguments}
                 for c in message.tool_calls]
        history.append({
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": [{"id": c["id"], "type": "function",
                            "function": {"name": c["name"], "arguments": c["arguments"]}} for c in calls],
        })
        approval = process_calls(session, calls, tools_used)
        if approval:
            return approval_reply(approval, tools_used)

    return reply("Stopped after too many tool calls. Please try a simpler request.", tools_used)


def close_pending(session: dict, result: dict) -> None:
    """Give the paused reservation (and any calls queued after it) a result, so the history stays valid."""
    pending = session["pending"]
    session["pending"] = None
    add_tool_result(session["history"], pending["call"]["id"], result)
    for call in pending["remaining"]:
        add_tool_result(session["history"], call["id"], {"error": "Skipped: the conversation moved on."})


def friendly_error(exc: Exception) -> HTTPException:
    if isinstance(exc, RateLimitError):
        return HTTPException(429, "The AI model is busy (rate limit). Wait a minute and try again.")
    return HTTPException(502, f"The AI service failed: {exc}")


@app.get("/api/health")
def health():
    return {"status": "ok", "model": MODEL}


@app.post("/api/chat")
def chat(req: ChatRequest):
    session = get_session(req.session_id)
    text = req.message.strip()
    if not text:
        raise HTTPException(400, "Type a message first.")

    # If a reservation was still waiting, treat a new message as "not approved".
    if session["pending"]:
        close_pending(session, {"reserved": False, "reason": "The user sent a new message instead of approving."})

    history = session["history"]
    turn_start = len(history)
    history.append({"role": "user", "content": text})
    try:
        return run_agent(session, [])
    except Exception as exc:
        # Nothing was saved in this turn (reservations always pause first), so undo it cleanly.
        del history[turn_start:]
        session["pending"] = None
        raise friendly_error(exc)


@app.post("/api/confirm")
def confirm(req: ConfirmRequest):
    session = get_session(req.session_id)
    pending = session["pending"]
    if not pending:
        raise HTTPException(409, "There is no reservation waiting for approval. Send your request again.")
    session["pending"] = None

    # Same reserve_book() as the terminal, but the "typed" answer comes from the button.
    answer = "y" if req.approved else "n"
    result = reserve_book(pending["book_id"], pending["customer_name"], confirm=lambda _: answer)
    add_tool_result(session["history"], pending["call"]["id"], result)

    tools_used = ["reserve_book"]
    try:
        approval = process_calls(session, pending["remaining"], tools_used)
        if approval:
            return approval_reply(approval, tools_used)
        return run_agent(session, tools_used)  # model writes the final message
    except Exception as exc:
        # The reservation step already happened, so report it truthfully instead of undoing.
        if result["reserved"]:
            outcome = (f"Reserved '{result['reservation']['title']}' for {pending['customer_name']} "
                       f"(reservation {result['reservation']['reservation_id']}).")
        else:
            outcome = f"No reservation was made: {result['reason']}"
        note = f"{outcome} The AI could not write a reply: {friendly_error(exc).detail}"
        session["history"].append({"role": "assistant", "content": note})
        return reply(note, tools_used)


if __name__ == "__main__":
    # `python server.py` (or PyCharm's Run button) starts the API on http://127.0.0.1:8000
    uvicorn.run(app, host="127.0.0.1", port=8000)
