"""Unit tests for tools: fast, no model involved."""
from types import SimpleNamespace

from nimbus import systems as ns
from nimbus.context import Employee
from nimbus.tools import book_trip, get_travel_policy, search_flights

PRIYA = SimpleNamespace(context=Employee("E101", "india"))   # stands in for ToolRuntime


def test_search_flights_returns_both_classes():
    flights = search_flights.invoke({"origin": "BLR", "destination": "BER", "date": "2026-11-16"})["flights"]
    assert {f["class"] for f in flights} >= {"economy", "premium_economy"}


def test_model_never_sees_runtime_argument():
    assert "runtime" not in book_trip.tool_call_schema.model_json_schema()["properties"]


def test_book_trip_rejects_business_class():
    result = book_trip.func(flight_ids=["FL3", "FL4"], hotel_id="HT1", nights=3, runtime=PRIYA)
    assert result["status"] == "rejected" and not ns.BOOKINGS


def test_book_trip_uses_identity_from_context():
    result = book_trip.func(flight_ids=["FL2", "FL4"], hotel_id="HT1", nights=3, runtime=PRIYA)
    assert result["employee_id"] == "E101"
    assert result["status"] == "pending_manager_approval"


def test_travel_policy_has_hotel_caps():
    assert "BER" in get_travel_policy.invoke({})["hotel_cap_per_night"]
