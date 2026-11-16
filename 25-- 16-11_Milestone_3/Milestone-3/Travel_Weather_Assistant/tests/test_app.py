"""Self-checks for the required scenarios. No Redis, Ollama or internet needed: those three are faked here.

Run:  python -m pytest -q
"""
import os
import tempfile
from datetime import date, timedelta

os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test_trips.db")  # must be set before importing the app

import fakeredis
import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

import assistant
import memory
import weather
from main import app

client = TestClient(app)
TODAY = date.today()


class FakeModel(GenericFakeChatModel):
    """Replays scripted replies in order; bind_tools is a no-op so it can stand in for ChatOllama."""

    def bind_tools(self, tools, **kwargs):
        return self


def fake_open_meteo(url, params):
    """Canned Open-Meteo responses: Jaipur is known, every other city is not."""
    if "geocoding" in url:
        known = params["name"].lower() == "jaipur"
        return {"results": [{"name": "Jaipur", "country": "India", "latitude": 26.9, "longitude": 75.8}]} if known else {}
    days = (date.fromisoformat(params["end_date"]) - date.fromisoformat(params["start_date"])).days + 1
    when = [(date.fromisoformat(params["start_date"]) + timedelta(d)).isoformat() for d in range(days)]
    return {"daily": {"time": when, "weather_code": [61] * days, "temperature_2m_min": [14.0] * days,
                      "temperature_2m_max": [27.5] * days, "precipitation_sum": [2.5] * days,
                      "precipitation_probability_max": [70] * days}}


@pytest.fixture(autouse=True)
def fakes(monkeypatch):
    monkeypatch.setattr(memory, "client", fakeredis.FakeRedis(decode_responses=True))
    monkeypatch.setattr(weather, "_get", fake_open_meteo)


def new_trip(destination="Jaipur", employee="EMP104", start=2, end=4):
    body = {"employee_id": employee, "destination": destination, "purpose": "Client meeting",
            "start_date": str(TODAY + timedelta(start)), "end_date": str(TODAY + timedelta(end))}
    return client.post("/trips", json=body)


def test_trip_is_validated_saved_and_read_back():
    resp = new_trip()
    assert resp.status_code == 201
    trip = resp.json()
    assert trip["status"] == "planned"
    assert client.get(f"/trips/{trip['trip_id']}").json() == trip
    assert client.get("/trips/999999").status_code == 404


@pytest.mark.parametrize("start,end", [(4, 2), (-3, 1)])  # end before start; start in the past
def test_invalid_dates_are_rejected(start, end):
    assert new_trip(start=start, end=end).status_code == 422


def test_weather_failures_are_reported_not_invented():
    assert "only forecasts up to" in weather.get_forecast("Jaipur", TODAY + timedelta(30), TODAY + timedelta(32))["error"]
    assert "not found" in weather.get_forecast("Atlantis", TODAY, TODAY)["error"]
    partial = weather.get_forecast("Jaipur", TODAY + timedelta(14), TODAY + timedelta(20))
    assert partial["ok"] and len(partial["days"]) == 2 and "note" in partial  # clipped to the 16-day window


def test_conversation_uses_tools_and_remembers_the_trip(monkeypatch):
    trip_id = new_trip(employee="EMP900").json()["trip_id"]
    monkeypatch.setattr(assistant, "llm", FakeModel(messages=iter([
        AIMessage("", tool_calls=[{"name": "find_employee_trips", "id": "1",
                                   "args": {"employee_id": "EMP900", "destination": "Jaipur"}}]),
        AIMessage("Jaipur advisory"),
        AIMessage(""),  # follow-up: the model names no city, so the trip must come from Redis memory
        AIMessage("Yes, pack an umbrella."),
    ])))
    ask = {"session_id": "s1", "employee_id": "EMP900"}

    first = client.post("/ask", json={**ask, "question": "What weather should I expect for my Jaipur trip?"}).json()
    assert first["trip_id"] == trip_id
    assert [t["tool"] for t in first["tools_used"]] == ["find_employee_trips", "get_weather_forecast"]

    second = client.post("/ask", json={**ask, "question": "Should I pack an umbrella and light jacket?"}).json()
    assert second["trip_id"] == trip_id and "get_trip" in [t["tool"] for t in second["tools_used"]]
    assert second["answer"] == "Yes, pack an umbrella."


def test_sessions_are_isolated_and_unknown_trips_are_not_guessed(monkeypatch):
    new_trip(employee="EMP901")
    monkeypatch.setattr(assistant, "llm", FakeModel(messages=iter([AIMessage("")])))
    reply = client.post("/ask", json={"session_id": "brand-new", "employee_id": "EMP901",
                                      "question": "Will I need an umbrella there?"}).json()
    assert reply["trip_id"] is None and "not sure which trip" in reply["answer"]


def test_unknown_destination_gives_clear_message_without_the_model(monkeypatch):
    new_trip(destination="Qwertyville", employee="EMP902")
    monkeypatch.setattr(assistant, "llm", FakeModel(messages=iter([AIMessage("")])))  # only stage 1 may use it
    reply = client.post("/ask", json={"session_id": "s3", "employee_id": "EMP902",
                                      "question": "Weather for my Qwertyville trip?"}).json()
    assert "not found by the geocoding service" in reply["answer"] and "won't guess" in reply["answer"]
