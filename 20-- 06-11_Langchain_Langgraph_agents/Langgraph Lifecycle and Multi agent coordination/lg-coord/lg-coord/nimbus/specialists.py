"""The Nimbus specialist agents, shared by every coordination pattern in Part 6."""
from langchain.agents import create_agent

from nimbus import tools as t
from nimbus.context import Employee
from nimbus.prompts import SYSTEM_PROMPT

REPORT_RULE = ("\nWork only on the task you are given. When finished, reply with a short factual report: "
               "what you did, ids created, and anything pending.")


def make_specialists(model) -> dict:
    """One create_agent per domain. Each sees only its own tools (smaller prompt, fewer mistakes)."""
    return {
        "travel": create_agent(model, [t.get_travel_policy, t.search_flights, t.search_hotels, t.book_trip],
                               system_prompt=SYSTEM_PROMPT + "\nYou are the TRAVEL specialist." + REPORT_RULE,
                               context_schema=Employee, name="travel"),
        "leave": create_agent(model, [t.get_leave_balance, t.search_hr_policies, t.apply_leave],
                              system_prompt=SYSTEM_PROMPT + "\nYou are the LEAVE specialist." + REPORT_RULE,
                              context_schema=Employee, name="leave"),
        "it": create_agent(model, [t.create_it_ticket],
                           system_prompt=SYSTEM_PROMPT + "\nYou are the IT specialist." + REPORT_RULE,
                           context_schema=Employee, name="it"),
        "comms": create_agent(model, [t.send_email, t.schedule_meeting],
                              system_prompt=SYSTEM_PROMPT + "\nYou are the COMMUNICATIONS specialist." + REPORT_RULE,
                              context_schema=Employee, name="comms"),
    }
