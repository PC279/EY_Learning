"""Mock versions of Nimbus Corp's company systems. In real life these are APIs;
here they are in-memory Python so you can run everything offline and inspect the state."""
from datetime import date, timedelta

TODAY = "2026-11-04"        # keep in sync with config.TODAY

EMPLOYEES = {
    "E101": {"name": "Priya Rao", "office": "india", "manager": "E150", "email": "priya@nimbus.example",
             "start_date": "2024-02-01"},
    "E202": {"name": "Lukas Becker", "office": "germany", "manager": "E250", "email": "lukas@nimbus.example",
             "start_date": "2026-09-01"},            # still on probation (6 months)
}
LEAVE_BALANCE = {"E101": 14, "E202": 9}             # working days left this year
LEAVE_TAKEN_IN_PROBATION = {"E202": 2}

FLIGHTS = [
    {"id": "FL1", "from": "BLR", "to": "BER", "date": "2026-11-16", "hours": 10.5, "class": "economy", "price_inr": 52000},
    {"id": "FL2", "from": "BLR", "to": "BER", "date": "2026-11-16", "hours": 10.5, "class": "premium_economy", "price_inr": 78000},
    {"id": "FL3", "from": "BLR", "to": "BER", "date": "2026-11-16", "hours": 10.5, "class": "business", "price_inr": 190000},
    {"id": "FL4", "from": "BER", "to": "BLR", "date": "2026-11-19", "hours": 9.5, "class": "premium_economy", "price_inr": 74000},
    {"id": "FL5", "from": "BER", "to": "BLR", "date": "2026-11-19", "hours": 9.5, "class": "economy", "price_inr": 50000},
]
HOTELS = [
    {"id": "HT1", "city": "BER", "name": "Spree Business Hotel", "price_per_night_eur": 135},
    {"id": "HT2", "city": "BER", "name": "Mitte Grand", "price_per_night_eur": 240},
    {"id": "HT3", "city": "BLR", "name": "Koramangala Suites", "price_per_night_inr": 6500},
]
TRAVEL_POLICY = {          # the same rules as the RAG doc's travel_policy.md
    "flight_class": "economy under 6 hours; premium_economy allowed for 6 hours or more; business never",
    "hotel_cap_per_night": {"BER": "EUR 150", "BLR": "INR 7,000"},
    "pre_approval_above": {"india": "INR 50,000 per trip", "germany": "EUR 800 per trip"},
    "per_diem": {"BER": "EUR 45", "BLR": "INR 2,500"},
}
EUR_TO_INR = 95            # fixed rate for the mock

BOOKINGS, LEAVE_REQUESTS, TICKETS, EMAILS, MEETINGS = [], [], [], [], []


def _working_days(start: str, end: str) -> int:
    d, e, n = date.fromisoformat(start), date.fromisoformat(end), 0
    while d <= e:
        n += d.weekday() < 5
        d += timedelta(days=1)
    return n


def _on_probation(emp_id: str) -> bool:
    start = date.fromisoformat(EMPLOYEES[emp_id]["start_date"])
    return date.fromisoformat(TODAY) < start + timedelta(days=182)


# ---------- read-only tools ----------
def get_employee(employee_id: str) -> dict:
    emp = EMPLOYEES.get(employee_id)
    if not emp:
        return {"error": f"No employee {employee_id}"}
    return {**emp, "employee_id": employee_id, "on_probation": _on_probation(employee_id)}


def get_leave_balance(employee_id: str) -> dict:
    return {"employee_id": employee_id, "days_left": LEAVE_BALANCE.get(employee_id, 0),
            "on_probation": _on_probation(employee_id),
            "probation_days_used": LEAVE_TAKEN_IN_PROBATION.get(employee_id, 0),
            "probation_limit": 5}


def search_hr_policies(query: str) -> dict:
    """Stand-in for the Ask HR RAG bot from the previous doc."""
    snippets = {
        "probation": "During the 6-month probation, employees may take at most 5 days of annual leave.",
        "carry": "India: carry forward up to 10 days; Germany: up to 5 days; use by 31 March.",
        "annual": "Annual leave: India 21 working days, Germany 28 working days.",
        "travel": "Flights: economy under 6 hours, premium economy for 6+ hours. Hotels: BER EUR 150, BLR INR 7,000.",
        "laptop": "Lost or stolen device: tell IT helpdesk (ext. 4357) within one hour.",
    }
    hits = [text for key, text in snippets.items() if key in query.lower()]
    return {"results": hits or ["No matching policy found."]}


def search_flights(origin: str, destination: str, date: str) -> dict:
    found = [f for f in FLIGHTS if f["from"] == origin.upper() and f["to"] == destination.upper()
             and f["date"] == date]
    return {"flights": found}


def search_hotels(city: str) -> dict:
    return {"hotels": [h for h in HOTELS if h["city"] == city.upper()]}


def get_travel_policy() -> dict:
    return TRAVEL_POLICY


# ---------- tools that change things (need care) ----------
def apply_leave(employee_id: str, start_date: str, end_date: str, reason: str = "") -> dict:
    days = _working_days(start_date, end_date)
    if days == 0:
        return {"status": "rejected", "reason": "No working days in that range."}
    if _on_probation(employee_id) and LEAVE_TAKEN_IN_PROBATION.get(employee_id, 0) + days > 5:
        return {"status": "rejected", "reason": f"Probation limit: max 5 days, {days} requested, "
                                                 f"{LEAVE_TAKEN_IN_PROBATION.get(employee_id, 0)} already used."}
    if days > LEAVE_BALANCE.get(employee_id, 0):
        return {"status": "rejected", "reason": "Not enough leave balance."}
    LEAVE_BALANCE[employee_id] -= days
    req = {"id": f"LR{len(LEAVE_REQUESTS) + 1}", "employee_id": employee_id, "start": start_date,
           "end": end_date, "working_days": days, "status": "submitted_to_manager"}
    LEAVE_REQUESTS.append(req)
    return req


def book_trip(employee_id: str, flight_ids: list[str], hotel_id: str, nights: int) -> dict:
    """Validates the booking against policy, so the agent cannot break the rules."""
    flights = [f for f in FLIGHTS if f["id"] in flight_ids]
    hotel = next((h for h in HOTELS if h["id"] == hotel_id), None)
    if len(flights) != len(flight_ids) or not hotel:
        return {"status": "rejected", "reason": "Unknown flight or hotel id."}
    for f in flights:
        allowed = "premium_economy" if f["hours"] >= 6 else "economy"
        if f["class"] == "business" or (f["class"] == "premium_economy" and allowed == "economy"):
            return {"status": "rejected", "reason": f"{f['id']} is {f['class']}, not allowed by policy."}
    if hotel["city"] == "BER" and hotel["price_per_night_eur"] > 150:
        return {"status": "rejected", "reason": "Hotel above the EUR 150 per night cap."}
    if hotel["city"] == "BLR" and hotel["price_per_night_inr"] > 7000:
        return {"status": "rejected", "reason": "Hotel above the INR 7,000 per night cap."}
    hotel_inr = nights * (hotel.get("price_per_night_inr") or hotel["price_per_night_eur"] * EUR_TO_INR)
    total_inr = sum(f["price_inr"] for f in flights) + hotel_inr
    office = EMPLOYEES[employee_id]["office"]
    limit_inr = 50000 if office == "india" else 800 * EUR_TO_INR
    status = "pending_manager_approval" if total_inr > limit_inr else "confirmed"
    booking = {"id": f"BK{len(BOOKINGS) + 1}", "employee_id": employee_id, "flights": flight_ids,
               "hotel": hotel_id, "nights": nights, "total_inr": total_inr, "status": status}
    BOOKINGS.append(booking)
    return booking


def create_it_ticket(employee_id: str, category: str, description: str, priority: str = "normal") -> dict:
    ticket = {"id": f"IT{len(TICKETS) + 1}", "employee_id": employee_id, "category": category,
              "description": description, "priority": priority, "status": "open"}
    TICKETS.append(ticket)
    return ticket


def send_email(to: str, subject: str, body: str) -> dict:
    EMAILS.append({"to": to, "subject": subject, "body": body})
    return {"status": "sent", "to": to}


def schedule_meeting(attendees: list[str], title: str, date: str, time: str) -> dict:
    MEETINGS.append({"attendees": attendees, "title": title, "date": date, "time": time})
    return {"status": "scheduled", "title": title, "date": date, "time": time}
