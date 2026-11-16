# AI-Powered Travel & Weather Advisory Assistant

A FastAPI service where an employee registers a business trip and asks weather questions about it.
LangChain + a free local Ollama model (`qwen2.5:3b`) read the question, call tools for the facts
(trip from **SQLite**, live forecast from **Open-Meteo**), and write a short advisory. **Redis** keeps
per-session conversation memory so follow-ups like *"Will I need an umbrella there?"* work.

```
Employee -> FastAPI (/ask) -> LangChain pipeline -> advisory
                               1. resolve_trip    (model calls find_employee_trips -> SQLite)
                               2. fetch_weather   (get_weather_forecast -> Open-Meteo)
                               3. write_advisory  (model writes the answer from those facts only)
            Redis: last 10 messages + current trip per session (1 hour TTL)
```

## Project files

| File | Purpose |
|---|---|
| `main.py` | FastAPI app: endpoints, input validation, error -> HTTP status mapping |
| `assistant.py` | LangChain tools and the 3-stage chain |
| `weather.py` | Open-Meteo geocoding + forecast, forecast-window checks |
| `memory.py` | Redis session memory |
| `db.py` / `schema.sql` | SQLite access and schema |
| `init_db.py` | Resets the database and loads 3 sample trips |
| `config.py` / `.env` | Settings (names only, no secrets) |
| `tests/test_app.py` | Self-checks for every required scenario (no Redis/Ollama/internet needed) |
| `postman/` | Postman collection with all demo requests in order |

## Install and run (Windows, PowerShell)

Prerequisites: Python 3.11+, [Ollama](https://ollama.com/download/windows), Redis on port 6379.
Full click-by-click instructions: **WINDOWS_SETUP_GUIDE.md**.

```powershell
ollama pull qwen2.5:3b                                   # once, ~1.9 GB
docker run -d --name travel-redis -p 6379:6379 redis:7   # once; later: docker start travel-redis

python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python init_db.py                 # creates trips.db with sample trips
python -m pytest -q               # optional self-check: 7 passed
uvicorn main:app --reload         # then open http://127.0.0.1:8000/docs
```

## API

| Method | Path | Body / purpose |
|---|---|---|
| POST | `/trips` | `{"employee_id","destination","start_date","end_date","purpose"}` -> 201 with the saved trip |
| GET | `/trips/{trip_id}` | Read a saved trip (404 if missing) |
| POST | `/ask` | `{"session_id","employee_id","question"}` -> `{"answer","trip_id","tools_used",...}` |

Example (dates must be within the next 16 days for a live forecast):

```json
POST /trips  {"employee_id":"EMP104","destination":"Jaipur","start_date":"2026-11-18","end_date":"2026-11-20","purpose":"Client meeting"}
POST /ask    {"session_id":"emp104-session-1","employee_id":"EMP104","question":"What weather should I expect for my Jaipur trip?"}
POST /ask    {"session_id":"emp104-session-1","employee_id":"EMP104","question":"Should I pack an umbrella and light jacket?"}
```

## Test scenarios (Postman collection, requests 1-10)

| Scenario | Request | Expected |
|---|---|---|
| New employee trip | 1 | 201, trip saved in SQLite |
| Existing trip lookup | 2 | Saved trip returned |
| Weather inquiry | 3 | Advisory + `tools_used` shows trip search and weather tool |
| Follow-up question | 4 | Same `trip_id` without naming Jaipur (Redis memory) |
| Session isolation | 5 | New session asks which trip instead of guessing |
| Invalid input | 6 | 422 - end date before start date |
| Unsupported forecast date | 7 | Sample London trip: "can't give a forecast ... won't guess" |
| Unknown destination | 8 + 9 | "not found by the geocoding service" |
| Missing trip | 10 | 404 |
| Service down | stop Redis or Ollama | 503 with a clear message |

Weather data by [Open-Meteo.com](https://open-meteo.com/) (CC BY 4.0, free tier for non-commercial use).
