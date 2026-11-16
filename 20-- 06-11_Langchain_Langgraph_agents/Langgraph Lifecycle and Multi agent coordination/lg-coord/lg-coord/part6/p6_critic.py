"""Pattern 6 - Generator and critic: a writer drafts, a critic reviews against a style guide, repeat.
Run: python -m part6.p6_critic
"""
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from nimbus import systems as ns
from nimbus.model import get_model

STYLE_GUIDE = """Nimbus welcome emails must: greet by first name; state the start date and 10:00 orientation;
mention the IT ticket id; be under 120 words; end with 'The People Team'. No emojis."""
MAX_ROUNDS = 3                                         # stop even if the critic is never satisfied


class Review(BaseModel):
    approved: bool
    feedback: str = Field(description="Specific changes needed; empty if approved")


class EmailState(TypedDict):
    brief: str
    draft: str
    feedback: str
    rounds: int
    approved: bool
    sent: bool


writer = get_model(temperature=0.4)                    # some creativity for the writer
critic = get_model().with_structured_output(Review)    # a strict, structured judge


def write(state: EmailState) -> dict:
    prompt = f"Write a welcome email.\nBrief: {state['brief']}\nStyle guide: {STYLE_GUIDE}"
    if state.get("feedback"):
        prompt += f"\nPrevious draft:\n{state['draft']}\nFix exactly this feedback: {state['feedback']}"
    return {"draft": writer.invoke(prompt).content, "rounds": state.get("rounds", 0) + 1}


def review(state: EmailState) -> dict:
    r = critic.invoke(f"Check this email strictly against the style guide.\n{STYLE_GUIDE}\n\nEMAIL:\n{state['draft']}")
    return {"approved": r.approved, "feedback": r.feedback}


def next_step(state: EmailState) -> str:
    if state["approved"]:
        return "send"
    return "send" if state["rounds"] >= MAX_ROUNDS else "write"   # give up improving after MAX_ROUNDS


def send(state: EmailState) -> dict:
    ns.send_email("arjun@nimbus.example", "Welcome to Nimbus!", state["draft"])
    return {"sent": True}


g = StateGraph(EmailState)
g.add_node("write", write)
g.add_node("review", review)
g.add_node("send", send)
g.add_edge(START, "write")
g.add_edge("write", "review")
g.add_conditional_edges("review", next_step, ["write", "send"])   # the loop
g.add_edge("send", END)
email_loop = g.compile()

if __name__ == "__main__":
    r = email_loop.invoke({"brief": "Arjun Mehta, engineer, starts 2026-12-01, laptop ticket IT1."})
    print(r["rounds"], "rounds, approved:", r["approved"], "\n", r["draft"])
