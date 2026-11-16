"""LangChain orchestration: three chained stages turn a question into a weather-grounded travel advisory.

Stage 1  resolve_trip    the model reads the question (+ session history) and calls the trip-search tool
Stage 2  fetch_weather   the weather tool gets the live forecast for that trip's city and dates
Stage 3  write_advisory  the model writes the answer using ONLY the facts gathered by the tools
"""
import json
import logging
from datetime import date

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableLambda
from langchain_core.tools import tool
from langchain_ollama import ChatOllama

import db
import memory
import weather
from config import OLLAMA_BASE_URL, OLLAMA_MODEL

log = logging.getLogger("assistant")
llm = ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL, temperature=0)  # deterministic answers


# ---------- Tools: the only source of facts (docstrings are what the model reads) ----------

@tool
def get_trip(trip_id: int) -> dict:
    """Read one saved business trip by its numeric trip ID."""
    return db.get_trip(trip_id) or {"error": f"Trip {trip_id} not found."}


@tool
def find_employee_trips(employee_id: str, destination: str = "") -> list[dict]:
    """Find an employee's saved trips. destination is the city named in the question (empty = all trips)."""
    return db.find_trips(employee_id, destination)


@tool
def get_weather_forecast(city: str, start_date: str, end_date: str) -> dict:
    """Live daily forecast (temperature, precipitation) for a city between two YYYY-MM-DD dates."""
    return weather.get_forecast(city, date.fromisoformat(start_date), date.fromisoformat(end_date))


def _use(tool_, args: dict, state: dict):
    """Run a tool and record the call; the record is returned to the client as evidence of tool use."""
    log.info("tool call: %s %s", tool_.name, args)
    state["tools_used"].append({"tool": tool_.name, "args": args})
    return tool_.invoke(args)


# ---------- Stage 1: interpret the question and find the trip ----------

RESOLVER_PROMPT = """You help employee {employee_id} with their saved business trips.
If the question or the conversation names a destination city, call find_employee_trips with that city.
If no city is named, do not call any tool."""


def resolve_trip(state: dict) -> dict:
    eid, question = state["employee_id"], state["question"]
    reply = llm.bind_tools([find_employee_trips]).invoke(
        [SystemMessage(RESOLVER_PROMPT.format(employee_id=eid)), *state["history"], HumanMessage(question)]
    )
    trips = []
    for call in reply.tool_calls:
        city = str(call["args"].get("destination", "")).strip()
        if call["name"] == "find_employee_trips" and city:
            # employee_id comes from the request, never from the model, so nobody can read another employee's trips
            trips = _use(find_employee_trips, {"employee_id": eid, "destination": city}, state)
            break
    if not trips:  # guard: small local models sometimes skip the call or pass a messy city name
        mine = _use(find_employee_trips, {"employee_id": eid, "destination": ""}, state)
        trips = [t for t in mine if t["destination"].lower() in question.lower()]
    if not trips and state["remembered_trip_id"]:  # follow-up such as "Will I need an umbrella there?"
        trip = _use(get_trip, {"trip_id": state["remembered_trip_id"]}, state)
        trips = [] if "error" in trip else [trip]
    # Ownership check: a session ID reused with another employee_id must not expose this trip
    trips = [t for t in trips if t["employee_id"].casefold() == eid.casefold()]
    state["trip"] = trips[0] if trips else None  # list is soonest-first, so duplicates resolve to the next trip
    return state


# ---------- Stage 2: live weather for the trip ----------

def fetch_weather(state: dict) -> dict:
    trip = state["trip"]
    if trip:  # city and dates come from SQLite, not from the model
        args = {"city": trip["destination"], "start_date": trip["start_date"], "end_date": trip["end_date"]}
        state["weather"] = _use(get_weather_forecast, args, state)
    return state


# ---------- Stage 3: write the advisory from the facts ----------

ADVISORY_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are a business-travel assistant. Use ONLY the FACTS (trip from the company database, forecast from "
     "Open-Meteo). Never invent or change weather numbers. Reply in under 160 words with:\n"
     "1. Destination and trip dates.\n"
     "2. Weather summary: temperature range in C and rain chance / precipitation.\n"
     "3. A direct answer to the employee's question.\n"
     "4. 3-4 short bullet points of packing or travel suggestions that fit this forecast and trip purpose.\n"
     "If the weather facts contain a 'note', mention it."),
    MessagesPlaceholder("history"),  # recent turns from Redis, so follow-ups make sense
    ("human", "FACTS:\n{facts}\n\nQUESTION: {question}"),
])


def _no_trip_message(employee_id: str) -> str:
    trips = db.find_trips(employee_id)
    if not trips:
        return f"I couldn't find any saved trips for {employee_id}. Please create one with POST /trips first."
    listing = "; ".join(f"trip {t['trip_id']}: {t['destination']} ({t['start_date']} to {t['end_date']})" for t in trips)
    return f"I'm not sure which trip you mean - please mention the destination. Your saved trips: {listing}."


def write_advisory(state: dict) -> dict:
    trip, forecast = state["trip"], state.get("weather")
    if trip is None:
        state["answer"] = _no_trip_message(state["employee_id"])
    elif not forecast["ok"]:
        # Fixed wording on purpose: the model never gets a chance to "fill in" weather we do not have
        state["answer"] = (
            f"I can't give a weather forecast for your {trip['destination']} trip (trip {trip['trip_id']}, "
            f"{trip['start_date']} to {trip['end_date']}). {forecast['error']} "
            "I won't guess the conditions - please try again later or check the trip details."
        )
    else:
        chain = ADVISORY_PROMPT | llm | StrOutputParser()
        facts = json.dumps({"trip": trip, "weather": forecast}, indent=1)
        state["answer"] = chain.invoke({"history": state["history"], "facts": facts, "question": state["question"]})
    return state


# The three stages chained with LangChain's pipe operator; each stage receives the previous stage's state
TRAVEL_PIPELINE = RunnableLambda(resolve_trip) | RunnableLambda(fetch_weather) | RunnableLambda(write_advisory)


def ask(session_id: str, employee_id: str, question: str) -> dict:
    history, remembered_trip_id = memory.load(session_id)
    state = TRAVEL_PIPELINE.invoke({
        "session_id": session_id, "employee_id": employee_id, "question": question,
        "history": history, "remembered_trip_id": remembered_trip_id, "tools_used": [],
    })
    trip_id = state["trip"]["trip_id"] if state["trip"] else None
    memory.save_turn(session_id, question, state["answer"], trip_id)
    return {"session_id": session_id, "trip_id": trip_id, "answer": state["answer"], "tools_used": state["tools_used"]}
