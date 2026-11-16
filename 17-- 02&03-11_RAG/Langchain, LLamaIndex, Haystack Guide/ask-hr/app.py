"""7.5 Serve Ask HR as an HTTP API.
pip install fastapi uvicorn ; run: uvicorn app:app --reload
"""
from fastapi import FastAPI
from pydantic import BaseModel

from part7_pro.ask_pro import ask

app = FastAPI()


class Question(BaseModel):
    question: str
    office: str | None = None


@app.post("/ask")
def ask_endpoint(q: Question):
    result = ask(q.question, q.office)
    return {"answer": result["answer"], "sources": sorted(set(result["sources"]))}
