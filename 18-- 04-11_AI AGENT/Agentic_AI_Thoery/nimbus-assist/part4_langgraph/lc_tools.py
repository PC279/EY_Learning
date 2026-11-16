"""The Nimbus tools as LangChain tools. Risky ones pause the graph for human approval."""
from langchain_core.tools import tool
from langgraph.types import interrupt

import nimbus_systems as ns


def approved(action: str, args: dict) -> bool:
    """Pause the whole graph and wait for a human decision (resumed with Command(resume=...))."""
    decision = interrupt({"action": action, "args": args})
    return str(decision).strip().lower() in {"y", "yes", "approve"}


@tool
def get_employee(employee_id: str) -> dict:
    """Look up an employee: name, office, manager, email, probation status."""
    return ns.get_employee(employee_id)


@tool
def get_leave_balance(employee_id: str) -> dict:
    """Get remaining annual leave days and probation limits for an employee."""
    return ns.get_leave_balance(employee_id)


@tool
def search_hr_policies(query: str) -> dict:
    """Search Nimbus HR policies (leave, probation, travel, IT security)."""
    return ns.search_hr_policies(query)


@tool
def get_travel_policy() -> dict:
    """Get the travel policy rules: flight class, hotel caps, approval limits."""
    return ns.get_travel_policy()


@tool
def search_flights(origin: str, destination: str, date: str) -> dict:
    """Find flights. Airports: BLR (Bengaluru), BER (Berlin). Date YYYY-MM-DD."""
    return ns.search_flights(origin, destination, date)


@tool
def search_hotels(city: str) -> dict:
    """Find hotels in a city (BLR or BER) with nightly prices."""
    return ns.search_hotels(city)


@tool
def apply_leave(employee_id: str, start_date: str, end_date: str, reason: str = "") -> dict:
    """Submit an annual leave request. Dates YYYY-MM-DD, inclusive. CHANGES DATA."""
    args = {"employee_id": employee_id, "start_date": start_date, "end_date": end_date}
    if not approved("apply_leave", args):
        return {"status": "cancelled", "reason": "The employee did not approve this action."}
    return ns.apply_leave(employee_id, start_date, end_date, reason)


@tool
def book_trip(employee_id: str, flight_ids: list[str], hotel_id: str, nights: int) -> dict:
    """Book flights and a hotel for an employee. Validates policy. CHANGES DATA."""
    args = {"employee_id": employee_id, "flight_ids": flight_ids, "hotel_id": hotel_id, "nights": nights}
    if not approved("book_trip", args):
        return {"status": "cancelled", "reason": "The employee did not approve this action."}
    return ns.book_trip(employee_id, flight_ids, hotel_id, nights)


@tool
def create_it_ticket(employee_id: str, category: str, description: str, priority: str = "normal") -> dict:
    """Open an IT support ticket. category: hardware, software, access, security."""
    return ns.create_it_ticket(employee_id, category, description, priority)


@tool
def send_email(to: str, subject: str, body: str) -> dict:
    """Send an email. CHANGES DATA."""
    if not approved("send_email", {"to": to, "subject": subject}):
        return {"status": "cancelled", "reason": "Not approved."}
    return ns.send_email(to, subject, body)


@tool
def schedule_meeting(attendees: list[str], title: str, date: str, time: str) -> dict:
    """Put a meeting in calendars. Date YYYY-MM-DD, time HH:MM. CHANGES DATA."""
    if not approved("schedule_meeting", {"attendees": attendees, "title": title, "date": date}):
        return {"status": "cancelled", "reason": "Not approved."}
    return ns.schedule_meeting(attendees, title, date, time)


ALL_TOOLS = [get_employee, get_leave_balance, search_hr_policies, get_travel_policy, search_flights,
             search_hotels, apply_leave, book_trip, create_it_ticket, send_email, schedule_meeting]
