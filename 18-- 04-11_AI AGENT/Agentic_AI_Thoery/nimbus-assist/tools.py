"""Tool descriptions the LLM reads (JSON Schema), plus the Python function behind each."""
import nimbus_systems as ns


def fn(name, description, properties, required=None):
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": properties,
                       "required": required or list(properties)}}}


S = {"type": "string"}
TOOL_SCHEMAS = [
    fn("get_employee", "Look up an employee: name, office, manager, email, probation status.",
       {"employee_id": S}),
    fn("get_leave_balance", "Get remaining annual leave days and probation limits for an employee.",
       {"employee_id": S}),
    fn("search_hr_policies", "Search Nimbus HR policies (leave, probation, travel, IT security).",
       {"query": S}),
    fn("get_travel_policy", "Get the travel policy rules: flight class, hotel caps, approval limits.", {}),
    fn("search_flights", "Find flights. Airports: BLR (Bengaluru), BER (Berlin). Date YYYY-MM-DD.",
       {"origin": S, "destination": S, "date": S}),
    fn("search_hotels", "Find hotels in a city (BLR or BER) with nightly prices.", {"city": S}),
    fn("apply_leave", "Submit an annual leave request. Dates YYYY-MM-DD, inclusive. CHANGES DATA.",
       {"employee_id": S, "start_date": S, "end_date": S, "reason": S}, ["employee_id", "start_date", "end_date"]),
    fn("book_trip", "Book flights and a hotel for an employee. Validates policy. CHANGES DATA.",
       {"employee_id": S, "flight_ids": {"type": "array", "items": S}, "hotel_id": S,
        "nights": {"type": "integer"}}),
    fn("create_it_ticket", "Open an IT support ticket. category: hardware, software, access, security.",
       {"employee_id": S, "category": S, "description": S, "priority": {"type": "string",
        "enum": ["low", "normal", "high", "urgent"]}}, ["employee_id", "category", "description"]),
    fn("send_email", "Send an email. CHANGES DATA.", {"to": S, "subject": S, "body": S}),
    fn("schedule_meeting", "Put a meeting in calendars. CHANGES DATA.",
       {"attendees": {"type": "array", "items": S}, "title": S, "date": S, "time": S}),
]

TOOL_FUNCTIONS = {
    "get_employee": ns.get_employee, "get_leave_balance": ns.get_leave_balance,
    "search_hr_policies": ns.search_hr_policies, "get_travel_policy": ns.get_travel_policy,
    "search_flights": ns.search_flights, "search_hotels": ns.search_hotels,
    "apply_leave": ns.apply_leave, "book_trip": ns.book_trip,
    "create_it_ticket": ns.create_it_ticket, "send_email": ns.send_email,
    "schedule_meeting": ns.schedule_meeting,
}

RISKY_TOOLS = {"apply_leave", "book_trip", "send_email", "schedule_meeting"}   # need a human "yes"
