"""Nimbus Assist tools, LangChain style.

Identity comes from runtime.context (set by your app at login), NOT from the model's arguments,
so the model cannot act for someone else.
"""
from typing import Literal

from langchain.tools import ToolRuntime, tool
from pydantic import BaseModel, Field

from nimbus import systems as ns
from nimbus.context import Employee


# ---------- read-only tools ----------
@tool
def get_leave_balance(runtime: ToolRuntime[Employee]) -> dict:
    """Get the current employee's remaining annual leave days and probation limits."""
    return ns.get_leave_balance(runtime.context.employee_id)


@tool
def search_hr_policies(query: str) -> dict:
    """Search Nimbus HR policies: leave, probation, carry-forward, travel, IT security."""
    return ns.search_hr_policies(query)


@tool
def get_travel_policy() -> dict:
    """Get travel rules: allowed flight class by duration, hotel caps per city, approval limits."""
    return ns.get_travel_policy()


@tool
def search_flights(origin: Literal["BLR", "BER"], destination: Literal["BLR", "BER"], date: str) -> dict:
    """Find flights between Bengaluru (BLR) and Berlin (BER). date is YYYY-MM-DD."""
    return ns.search_flights(origin, destination, date)


@tool
def search_hotels(city: Literal["BLR", "BER"]) -> dict:
    """Find hotels in Bengaluru (BLR) or Berlin (BER) with nightly prices."""
    return ns.search_hotels(city)


# ---------- tools that change data ----------
class BookTripInput(BaseModel):
    """Arguments for book_trip. Field descriptions are shown to the model."""
    flight_ids: list[str] = Field(description="Flight ids from search_flights, e.g. ['FL2', 'FL4']")
    hotel_id: str = Field(description="Hotel id from search_hotels, e.g. 'HT1'")
    nights: int = Field(ge=1, le=30, description="Number of hotel nights")


@tool(args_schema=BookTripInput)
def book_trip(flight_ids: list[str], hotel_id: str, nights: int, runtime: ToolRuntime[Employee]) -> dict:
    """Book flights and a hotel for the current employee. The booking system enforces travel policy."""
    return ns.book_trip(runtime.context.employee_id, flight_ids, hotel_id, nights)


@tool
def apply_leave(start_date: str, end_date: str, runtime: ToolRuntime[Employee], reason: str = "") -> dict:
    """Submit an annual leave request for the current employee. Dates YYYY-MM-DD, inclusive."""
    return ns.apply_leave(runtime.context.employee_id, start_date, end_date, reason)


@tool
def create_it_ticket(category: Literal["hardware", "software", "access", "security"], description: str,
                     runtime: ToolRuntime[Employee],
                     priority: Literal["low", "normal", "high", "urgent"] = "normal") -> dict:
    """Open an IT support ticket for the current employee."""
    return ns.create_it_ticket(runtime.context.employee_id, category, description, priority)


@tool
def send_email(to: str, subject: str, body: str) -> dict:
    """Send an email from Nimbus Assist."""
    return ns.send_email(to, subject, body)


@tool
def schedule_meeting(attendees: list[str], title: str, date: str, time: str) -> dict:
    """Schedule a meeting. date YYYY-MM-DD, time HH:MM (24h)."""
    return ns.schedule_meeting(attendees, title, date, time)


READ_TOOLS = [get_leave_balance, search_hr_policies, get_travel_policy, search_flights, search_hotels]
WRITE_TOOLS = [book_trip, apply_leave, create_it_ticket, send_email, schedule_meeting]
ALL_TOOLS = READ_TOOLS + WRITE_TOOLS
