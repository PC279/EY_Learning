# Step-by-step: run the Travel & Weather Assistant on Windows

You need four things running: **Ollama** (the AI model), **Redis** (session memory), the **FastAPI app**
(this project), and **Postman** (to send requests). SQLite needs no installation - it is built into Python.

Time needed: about 30 minutes, most of it waiting for the model download.

---

## Step 1 - Check Python

Open **PowerShell** and run:

```powershell
python --version
```

You need **3.11 or newer**. If the command is not found, install Python from https://www.python.org/downloads/
and tick **"Add python.exe to PATH"** on the first installer screen.

## Step 2 - Install Ollama and download the model

1. Go to https://ollama.com/download/windows and run **OllamaSetup.exe** (no admin rights needed).
2. When it finishes, Ollama runs in the background - you will see a llama icon in the system tray.
3. Open a **new** PowerShell window (so the `ollama` command is found) and run:

```powershell
ollama --version
ollama pull qwen2.5:3b                       # ~1.9 GB download, one time only
ollama run qwen2.5:3b "Say hello in one line" # quick test; should print a greeting
```

Ollama now listens on `http://localhost:11434`. You do **not** need to run `ollama serve`; the tray app does it.
If you see *"could not connect to ollama app"*, start **Ollama** from the Start menu.

## Step 3 - Start Redis

Pick **one** option.

**Option A - Docker Desktop (recommended if you already have Docker)**

```powershell
docker run -d --name travel-redis -p 6379:6379 redis:7   # first time only
docker exec -it travel-redis redis-cli ping              # should print PONG
```

Next time you restart the laptop: start Docker Desktop, then `docker start travel-redis`.
(The assessment only rules out *deploying the app* with Docker; using a local Redis container is fine.)

**Option B - Memurai (native Windows, Redis-compatible)**
Install the free *Memurai Developer* edition from https://www.memurai.com/get-memurai. It runs as a
Windows service on port 6379 automatically. Test with `memurai-cli ping` -> `PONG`.

**Option C - WSL (Ubuntu)**

```bash
sudo apt update && sudo apt install -y redis-server
sudo service redis-server start
redis-cli ping
```

## Step 4 - Open the project in PyCharm

1. Unzip `Travel_Weather_Assistant.zip`, e.g. to `C:\Users\<you>\PycharmProjects\travel_weather_assistant`.
2. PyCharm -> **File -> Open** -> select the `travel_weather_assistant` folder (the one containing `main.py`).
3. Create a virtual environment: **File -> Settings -> Project -> Python Interpreter -> Add Interpreter ->
   Add Local Interpreter -> Virtualenv Environment -> New**, base interpreter = your Python 3.11+, location
   `.venv` inside the project. Click OK.
4. Open PyCharm's **Terminal** tab (bottom). It activates `.venv` automatically - the prompt starts with `(.venv)`.

Using plain PowerShell instead of PyCharm?

```powershell
cd C:\Users\<you>\PycharmProjects\travel_weather_assistant
python -m venv .venv
.venv\Scripts\Activate.ps1
```

If PowerShell says *"running scripts is disabled"*, run this once and try again:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

## Step 5 - Install the Python packages

In the terminal with `(.venv)` active:

```powershell
pip install -r requirements.txt
```

## Step 6 - Create the settings file

```powershell
Copy-Item .env.example .env
```

The defaults already match Steps 2-3 (model `qwen2.5:3b`, Ollama on 11434, Redis on 6379). Nothing to edit
unless you changed a port.

## Step 7 - Create the database with sample trips

```powershell
python init_db.py
```

You should see three `saved:` lines (Mumbai, Bengaluru, London). This creates `trips.db` in the project
folder. Run it again any time you want a clean database - it resets the trips table.

## Step 8 - (Optional) Run the self-checks

```powershell
python -m pytest -q
```

Expected: `7 passed`. These tests fake Redis, Ollama and the weather API, so they pass even before
anything else is running. They prove the logic; Steps 9-10 prove the real services.

## Step 9 - Start the API

```powershell
uvicorn main:app --reload
```

Wait for `Application startup complete`, then open **http://127.0.0.1:8000/docs** in a browser - this is
the Swagger UI. Keep this terminal open: every tool call the assistant makes is logged here
(`assistant: tool call: ...`) - useful console evidence.

*PyCharm run button instead of the terminal:* **Run -> Edit Configurations -> + -> Python**. In the
*script* dropdown choose **module** and enter `uvicorn`; *Script parameters* `main:app --reload`;
*Working directory* = the project folder. Click Run.

## Step 10 - Test with Postman

1. Postman -> **Import** -> choose `postman/Travel_Weather_Assistant.postman_collection.json`.
2. Run requests **1 to 10 in order** (each has a description of the scenario it proves):

| # | Request | What you should see |
|---|---|---|
| 1 | Create trip (Jaipur) | `201` and the saved trip. Dates are auto-set to 2-4 days from today |
| 2 | Get trip by ID | The same trip read back from SQLite |
| 3 | Ask - Chat 1 | A weather advisory; `tools_used` lists `find_employee_trips` and `get_weather_forecast` |
| 4 | Ask - Chat 2 (same session) | Umbrella/jacket answer about Jaipur without naming Jaipur; same `trip_id` |
| 5 | Ask - new session | "I'm not sure which trip you mean..." - other sessions do not leak |
| 6 | Invalid dates | `422` - end date before start date |
| 7 | London trip | "I can't give a weather forecast ... I won't guess the conditions" |
| 8-9 | Unknown city | "Destination 'Qwertyville' was not found by the geocoding service" |
| 10 | Trip not found | `404` |

The first `/ask` can take 20-60 seconds while Ollama loads the model into memory; later ones are faster.

**Bonus failure demo:** stop Redis (`docker stop travel-redis`) and send request 3 -> `503 Session memory
unavailable`. Start it again with `docker start travel-redis`. Same idea with Ollama (quit it from the tray) ->
`503 Local model unavailable`.

## Step 11 - Save the submission evidence

Take screenshots (Postman or Swagger) of: request 1 (saved trip), request 3 (live forecast), request 4
(remembered follow-up) and request 7 or 9 (failure case), plus the uvicorn console showing `tool call` lines.
Put them in the `evidence/` folder - see `evidence/README.md`.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `503 Local model unavailable` | Ollama is not running - start it from the Start menu |
| `503 Ollama error ... model not found` | Run `ollama pull qwen2.5:3b` |
| `503 Session memory unavailable` | Redis is not running - `docker start travel-redis` (or start Memurai) |
| Answer says "Weather service unavailable" | No internet, or the office network/VPN blocks `open-meteo.com`. Try another network. If you need a proxy, set `HTTPS_PROXY` in `.env` |
| `422` on `/trips` | Read `msg` in the response: start date in the past, end before start, or a missing field |
| "I'm not sure which trip you mean" in a follow-up | You changed `session_id`, or the session expired (1 hour). Name the destination once |
| `ModuleNotFoundError` | The `.venv` is not active - look for `(.venv)` in the prompt, or select it as PyCharm's interpreter |
| Port 8000 already in use | `uvicorn main:app --reload --port 8001` and change `baseUrl` in Postman |
| Answers are slow | Normal on CPU (two model calls per question). Close heavy apps; the 3B model needs ~3 GB RAM |
