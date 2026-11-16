"""FastAPI entry point. Run with:  uvicorn main:app --reload   then open http://127.0.0.1:8000/docs"""
import logging
from datetime import date
from typing import Annotated

import httpx
import ollama
import redis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator

import assistant
import db
from config import OLLAMA_MODEL

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s: %(message)s")  # tool calls show in console
db.init_db()  # create the trips table on start-up if it is missing

app = FastAPI(title="Travel & Weather Advisory Assistant",
              description="Register business trips and ask weather-grounded travel questions.")

EmployeeId = Annotated[str, Field(min_length=1, max_length=20, pattern=r"^[A-Za-z0-9_-]+$", examples=["EMP104"])]


class TripIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)  # "  Jaipur " is stored as "Jaipur"

    employee_id: EmployeeId
    destination: str = Field(min_length=2, max_length=100, examples=["Jaipur"])
    start_date: date
    end_date: date
    purpose: str = Field(min_length=2, max_length=200, examples=["Client meeting"])

    @model_validator(mode="after")
    def check_dates(self):
        if self.start_date < date.today():
            raise ValueError("start_date cannot be in the past")
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class AskIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    # Restricted characters because the session ID becomes part of a Redis key
    session_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$", examples=["emp104-session-1"])
    employee_id: EmployeeId
    question: str = Field(min_length=2, max_length=500, examples=["What weather should I expect for my Jaipur trip?"])


@app.post("/trips", status_code=201)
def create_trip(trip: TripIn):
    """Validate and save a new trip in SQLite."""
    return db.create_trip(trip.employee_id, trip.destination, trip.start_date.isoformat(),
                          trip.end_date.isoformat(), trip.purpose)


@app.get("/trips/{trip_id}")
def read_trip(trip_id: int):
    """Read a saved trip by its ID."""
    trip = db.get_trip(trip_id)
    if trip is None:
        raise HTTPException(404, f"Trip {trip_id} not found")
    return trip


@app.post("/ask")
def ask(body: AskIn):
    """Ask the assistant; answers are grounded in the saved trip and the live forecast."""
    try:
        return assistant.ask(body.session_id, body.employee_id, body.question)
    except redis.RedisError as exc:
        raise HTTPException(503, f"Session memory unavailable - is Redis running? ({exc})")
    except (ConnectionError, httpx.ConnectError) as exc:
        raise HTTPException(503, f"Local model unavailable - is Ollama running? ({exc})")
    except ollama.ResponseError as exc:  # e.g. the model was never pulled
        raise HTTPException(503, f"Ollama error - did you run 'ollama pull {OLLAMA_MODEL}'? ({exc})")
