"""Part 9: serve Nimbus Assist over HTTP, with approvals. Run: uvicorn part9.app:app --reload"""
import sqlite3

from fastapi import FastAPI, HTTPException
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware, ModelCallLimitMiddleware
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from pydantic import BaseModel

from nimbus.context import Employee
from nimbus.model import get_model
from nimbus.prompts import SYSTEM_PROMPT
from nimbus.tools import ALL_TOOLS

agent = create_agent(                       # built ONCE at startup, shared by all requests
    model=get_model(), tools=ALL_TOOLS, system_prompt=SYSTEM_PROMPT, context_schema=Employee,
    middleware=[ModelCallLimitMiddleware(run_limit=12),
                HumanInTheLoopMiddleware(interrupt_on={"book_trip": True, "apply_leave": True,
                                                       "send_email": True})],
    checkpointer=SqliteSaver(sqlite3.connect("app_memory.db", check_same_thread=False)),
)
app = FastAPI(title="Nimbus Assist")

# In production the employee comes from your auth layer (e.g. a verified JWT), never from the body.
EMPLOYEES = {"E101": Employee("E101", "india"), "E202": Employee("E202", "germany")}


class ChatIn(BaseModel):
    employee_id: str
    thread_id: str
    message: str


class ResumeIn(BaseModel):
    employee_id: str
    thread_id: str
    decisions: list[dict]                   # [{"type": "approve"}, {"type": "reject", "message": "..."}]


def _respond(result: dict) -> dict:
    if "__interrupt__" in result:           # paused: the UI must show approval cards
        return {"status": "needs_approval",
                "actions": result["__interrupt__"][0].value["action_requests"]}
    return {"status": "done", "answer": result["messages"][-1].content}


def _employee(employee_id: str) -> Employee:
    if employee_id not in EMPLOYEES:
        raise HTTPException(403, "Unknown employee")
    return EMPLOYEES[employee_id]


@app.post("/chat")
def chat(body: ChatIn) -> dict:
    cfg = {"configurable": {"thread_id": f"{body.employee_id}:{body.thread_id}"}}   # per-user threads
    result = agent.invoke({"messages": [{"role": "user", "content": body.message}]}, cfg,
                          context=_employee(body.employee_id))
    return _respond(result)


@app.post("/resume")
def resume(body: ResumeIn) -> dict:
    cfg = {"configurable": {"thread_id": f"{body.employee_id}:{body.thread_id}"}}
    result = agent.invoke(Command(resume={"decisions": body.decisions}), cfg,
                          context=_employee(body.employee_id))
    return _respond(result)
