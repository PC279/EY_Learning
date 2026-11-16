# Retail Support Agent API: How It All Works

This is the complete guide to this project. It explains **what** each piece is, **where** it runs, **how** the pieces are connected, **why** each one is used, and **what happens step by step** when you send a message.

Every topic is explained in one place only. When a topic comes up again, the guide links back to its section instead of repeating it.

---

## Contents

1. [The project in 30 seconds](#1-the-project-in-30-seconds)
2. [Is my understanding right](#2-is-my-understanding-right)
3. [Where everything runs](#3-where-everything-runs)
4. [What each technology does and why](#4-what-each-technology-does-and-why)
5. [How the pieces connect](#5-how-the-pieces-connect)
6. [What happens step by step](#6-what-happens-step-by-step)
7. [Code map of main.py](#7-code-map-of-mainpy)
8. [Redis in depth](#8-redis-in-depth)
9. [Docker in depth](#9-docker-in-depth)
10. [Azure AI Foundry in depth](#10-azure-ai-foundry-in-depth)
11. [The class whiteboard reviewed](#11-the-class-whiteboard-reviewed)
12. [First-time setup](#12-first-time-setup)
13. [Daily start and stop](#13-daily-start-and-stop)
14. [Using the API in Swagger UI](#14-using-the-api-in-swagger-ui)
15. [Configuration and project files](#15-configuration-and-project-files)
16. [Troubleshooting](#16-troubleshooting)
17. [Keeping secrets out of GitHub](#17-keeping-secrets-out-of-github)
18. [Limitations and next steps](#18-limitations-and-next-steps)
19. [Glossary](#19-glossary)

---

## 1. The project in 30 seconds

A customer (or you, testing) sends a chat message to a small **web API** written in Python with **FastAPI**. The API forwards the message to an **AI agent** that lives in **Azure AI Foundry** and sends the agent's reply back.

To remember each customer's chat between messages, the API stores session information in **Redis**, a very fast in-memory data store that runs inside **Docker** on your laptop.

The API has two endpoints:

| Endpoint | What it does |
|---|---|
| `POST /chat` | Send a message, get the agent's reply and a `session_id` |
| `GET /history/{session_id}` | Read back every message of a session |

The slide from class shows the same idea:

![Foundry Agent + Backend API + Redis Memory: end-to-end flow (class slide)](images/architecture.png)

The slide calls the agent `RetailSupportAgent`. In this project the agent is named `Retail-Store-Agent` (set in `.env`, see [section 15](#15-configuration-and-project-files)).

---

## 2. Is my understanding right

> *"FastAPI is acting as a connection between the agent running in Foundry, called via Python, and the Redis server, and everything is running on the FastAPI server, whereas Redis is called using Docker."*

**Mostly right.** FastAPI really is the connector in the middle. Two parts need correcting:

| What you said | Verdict | Correct picture |
|---|---|---|
| FastAPI is the connection between the Foundry agent and Redis | ✅ Right | FastAPI is the **middle layer**. It calls Redis and it calls Foundry. Redis and Foundry **never talk to each other**. |
| The Foundry agent is called via Python | ✅ Right | Through the `azure-ai-projects` Python library, over **HTTPS on the internet**, using your `az login` identity. |
| Everything is running on the FastAPI server | ❌ Not quite | Only the code in `main.py` runs there. The pieces live in **three different places**: the API runs in a Python process on your laptop, Redis runs in a Docker container on your laptop, and the agent (the AI model itself) runs on **Microsoft's servers** in Azure. See [section 3](#3-where-everything-runs). |
| Redis is called using Docker | ⚠️ Partly | Docker only **hosts** Redis, like a box Redis lives in. FastAPI talks to Redis **directly**, using the `redis` Python library on `localhost:6379`. Docker is not involved in each call; it just forwards the port. You use Docker commands only to start and stop Redis. See [section 5.2](#52-fastapi-and-redis). |
| The FastAPI server | Small detail | **FastAPI** is the framework (your code's structure). **Uvicorn** is the actual server program that listens on port 8000 and runs that code. |

**Corrected sentence:**

> FastAPI (running in Uvicorn on my laptop) is the middle layer. For every request it talks to Redis (running in a Docker container on my laptop) to remember sessions, and to the Retail-Store-Agent (running in Azure AI Foundry in the cloud) to get the AI reply. Redis and Foundry never talk to each other directly.

---

## 3. Where everything runs

![Where everything runs and how the pieces connect](images/where_everything_runs.png)

| # | Piece | What it is | Where it runs | Address | How it starts |
|---|---|---|---|---|---|
| 1 | Client | Browser with Swagger UI, Postman, or any app | Your laptop | n/a | You open `http://127.0.0.1:8000/docs` |
| 2 | API | Uvicorn server running the FastAPI app in `main.py` | Your laptop, as a Python process inside `.venv` | `127.0.0.1:8000` | `python -m uvicorn main:app --reload` |
| 3 | Redis | Redis server, version 7 | Your laptop, inside the Docker container `retail-redis` | `localhost:6379` | `docker start retail-redis` |
| 4 | Agent | `Retail-Store-Agent`: model, instructions, knowledge, guardrails | Microsoft's servers (Azure cloud) | Your Foundry project endpoint | Always on; created once in the Foundry portal |

Supporting pieces:

| Piece | Role |
|---|---|
| Docker Desktop | The program that runs containers on Windows (needed for piece 3) |
| `.env` file | Holds settings that `main.py` reads at startup |
| `az login` | Your Azure sign-in; gives the API permission to call the agent |

If piece 2, 3 or 4 is unavailable, `/chat` fails. See [section 16](#16-troubleshooting) for each case.

---

## 4. What each technology does and why

| Technology | Its job in this project | Why it's used |
|---|---|---|
| **Python + `.venv`** | Language of the API. `.venv` is a private folder of installed packages for this project only. | Keeps this project's package versions separate from other projects. |
| **FastAPI** | Defines the endpoints (`/chat`, `/history`), validates input, and builds the docs page. | Very little code for a full API, automatic validation, free interactive docs. |
| **Uvicorn** | The web server: listens on port 8000, receives HTTP requests, hands them to FastAPI. | FastAPI needs a server to run in; Uvicorn is the standard one. `--reload` restarts it when code changes. |
| **Pydantic** | Checks the request body matches `ChatRequest` (message length, valid UUID). | Bad input is rejected automatically with a clear `422` error before your code runs. |
| **Swagger UI / OpenAPI** | The `/docs` page for trying the API in the browser. | Test without writing any client code. See [section 14](#14-using-the-api-in-swagger-ui). |
| **python-dotenv + `.env`** | Loads settings (endpoint, agent name, Redis URL) into environment variables. | Keeps secrets and machine-specific values out of the code. |
| **Redis** | Stores which Foundry conversation belongs to which session, plus a copy of the chat history. | Very fast, shared, survives API restarts, and can auto-delete old data. See [section 8](#8-redis-in-depth). |
| **redis** (Python library, also called redis-py) | The Python client that sends commands to the Redis server. | Official Redis client for Python. |
| **Docker / Docker Desktop** | Runs Redis in an isolated container. | One command gives a working Redis on Windows without installing it. See [section 9](#9-docker-in-depth). |
| **Azure AI Foundry** | Hosts the agent and stores its conversations. | The AI logic, policies and safety settings are managed in the portal, not in code. See [section 10](#10-azure-ai-foundry-in-depth). |
| **azure-ai-projects** | Python SDK to reach your Foundry project and agent. | Official way to call Foundry agents from Python. |
| **azure-identity** (`DefaultAzureCredential`) | Proves to Azure who you are. | Uses your `az login` locally and works unchanged on Azure later. No keys in code. |

---

## 5. How the pieces connect

There are four connections. Each uses a different "language" (protocol) and address.

### 5.1 Client and FastAPI

- **Protocol:** HTTP, with JSON bodies.
- **Address:** `127.0.0.1:8000`. `127.0.0.1` (also called `localhost`) means "this same computer", so only your laptop can reach it.
- **Who starts it:** Uvicorn listens on that port as soon as you run the `uvicorn` command.

### 5.2 FastAPI and Redis

- **Protocol:** the Redis protocol over TCP.
- **Library:** the `db` object in `main.py` (STEP 2), created from `REDIS_URL`.
- **The URL explained:** `redis://localhost:6379/0`

  | Part | Meaning |
  |---|---|
  | `redis://` | Use the Redis protocol |
  | `localhost` | Redis is on this computer |
  | `6379` | Redis's standard port |
  | `/0` | Use database number 0 (Redis has 16 numbered databases, 0–15, by default) |

- **The path of one command:** redis-py sends it to `localhost:6379` → Docker's **port mapping** forwards it into the container → the Redis server answers on the container's own port `6379`.
- **When it connects:** not at startup. redis-py connects on the **first command** (the first `/chat`). That's why the API starts fine even when Redis is down, and only fails when you send a message.

### 5.3 FastAPI and Foundry

- **Protocol:** HTTPS over the internet.
- **Objects in `main.py` (STEP 3):**
  - `project = AIProjectClient(endpoint, credential)`: connects to your Foundry project.
  - `agent = project.get_openai_client(agent_name=...)`: an OpenAI-style client whose calls are answered by your named agent.
- **Identity:** `DefaultAzureCredential` gets a token from your `az login` and attaches it to every call. Details in [section 10](#10-azure-ai-foundry-in-depth).
- **Calls made:** `agent.conversations.create()` and `agent.responses.create(...)`.

### 5.4 Redis and the disk

Redis keeps data in RAM and also writes every change to a file (`appendonly.aof`) on the Docker volume `retail_redis_data`. See [section 8.8](#88-what-survives-what).

### 5.5 What never connects

- The **client never talks to Redis or Foundry directly**. Everything goes through the API.
- **Redis and Foundry never talk to each other.** The API passes data between them.

---

## 6. What happens step by step

### 6.1 When Uvicorn starts

Everything at the top level of `main.py` runs **once**, when the server starts:

1. `load_dotenv()` reads `.env`.
2. `app = FastAPI(...)` creates the app.
3. `db = redis.Redis.from_url(...)` prepares the Redis client (no connection yet, see [5.2](#52-fastapi-and-redis)).
4. `project` and `agent` are created to talk to Foundry. If `FOUNDRY_PROJECT_ENDPOINT` is missing, startup fails here with a `KeyError`.
5. Uvicorn prints `Application startup complete` and waits for requests.

With `--reload`, you see **two processes** in the log: a *reloader* that watches your files, and the *server* that runs the app. Saving `main.py` makes the reloader restart the server, which runs these five steps again.

The code inside `chat()` and `get_history()` runs **once per request**.

### 6.2 One request, step by step

![Sequence of a POST /chat and a GET /history request](images/chat_request_sequence.png)

The numbers below match the numbered circles in the diagram.

| # | What happens | Code in `main.py` (STEP 5 or 6) |
|---|---|---|
| 1 | Client sends the message. Pydantic validates it; if there's no `session_id`, a new UUID is created. | `ChatRequest`, `request.session_id or uuid4()` |
| 2–3 | API asks Redis for this session's Foundry conversation ID. | `db.get(conversation_key)` |
| 4–6 | **Only for a new or expired session:** create a Foundry conversation and save its ID in Redis for 1 hour. | `agent.conversations.create()`, `db.set(..., ex=SESSION_TTL)` |
| 7–8 | Send the message to the agent inside that conversation; get the reply text. | `agent.responses.create(...)`, `response.output_text` |
| 9 | Append the user message and the reply to the history list, and reset both 1-hour timers, in one trip to Redis. | `db.pipeline()`, `rpush`, `expire`, `execute()` |
| 10 | Return `{session_id, reply}`. The client must send this `session_id` with the next message. | `return {...}` |
| 11–14 | `GET /history`: read the whole list from Redis, convert each JSON string back to a dict, return it. | `db.lrange(history_key, 0, -1)`, `json.loads` |

### 6.3 Three situations

| Situation | What the API does | Does the agent remember earlier messages? |
|---|---|---|
| First message (no `session_id`) | New `session_id` → new Foundry conversation → saved in Redis | Nothing to remember yet |
| Follow-up within 1 hour (same `session_id`) | Finds the conversation ID in Redis and reuses it | ✅ Yes |
| Same `session_id` after 1 hour of silence | Redis keys have expired → creates a **new** conversation | ❌ No, it starts fresh |

---

## 7. Code map of main.py

`main.py` is split into six numbered STEPs, and its comments explain each line. This table shows how the STEPs relate to the pieces:

| STEP | What it does | Runs | Talks to |
|---|---|---|---|
| 1 | Loads `.env`, creates the FastAPI app, sets `SESSION_TTL = 3600` | Once, at startup | `.env` file |
| 2 | Creates the Redis client `db` | Once, at startup | Redis (on first use) |
| 3 | Creates the Foundry clients `project` and `agent` | Once, at startup | Azure AI Foundry |
| 4 | Defines `ChatRequest`, the shape of the `/chat` body | Used on every `/chat` | — |
| 5 | `POST /chat` endpoint | Every chat request | Redis + Foundry |
| 6 | `GET /history/{session_id}` endpoint | Every history request | Redis only |

The endpoints are plain `def` functions (not `async def`). FastAPI runs them in a background thread pool, which suits the blocking Redis and Azure calls.

---

## 8. Redis in depth

### 8.1 What Redis is

Redis is a **key-value data store** that keeps its data in **RAM**, which makes it extremely fast (reads and writes usually take well under a millisecond). Think of it as a giant shared Python dictionary that lives in a separate program, so any number of API copies can use it and it survives API restarts.

Redis is a **server**: it runs on its own (here, in Docker) and waits for commands. Your code is a **client** that sends commands to it.

### 8.2 What this project stores

![What this project stores in Redis](images/redis_keys.png)

**Key naming:** `retail:{session_id}:conversation` and `retail:{session_id}:history`. Using colons to separate parts is a common Redis habit. It groups related keys (everything for one session shares a prefix) and avoids clashes with other apps using the same Redis.

### 8.3 Data types used

| Type | Used for | Think of it as |
|---|---|---|
| **String** | The Foundry conversation ID | One text value |
| **List** | The chat history | A Python list; new items added at the end |

Redis has other types this project doesn't use: **Hash** (a mini dictionary), **Set** (unique items), **Sorted Set** (items with scores, such as leaderboards), and **Stream** (an event log).

### 8.4 Commands used

| Redis command | Python call | What it does | Where |
|---|---|---|---|
| `GET` | `db.get(key)` | Read a String (or nothing if missing or expired) | STEP 5 |
| `SET ... EX 3600` | `db.set(key, value, ex=3600)` | Save a String that deletes itself after 3600 s | STEP 5 |
| `RPUSH` | `pipe.rpush(key, a, b)` | Add items to the **right** (end) of a List | STEP 5 |
| `EXPIRE` | `pipe.expire(key, 3600)` | Set or reset a key's timer | STEP 5 |
| `MULTI` / `EXEC` | `db.pipeline()` … `execute()` | Group commands and run them together | STEP 5 |
| `LRANGE key 0 -1` | `db.lrange(key, 0, -1)` | Read a List from first (`0`) to last (`-1`) | STEP 6 |

### 8.5 TTL and the sliding 1-hour timer

**TTL** (time to live) is a timer on a key. When it reaches zero, Redis deletes the key by itself.

Because every `/chat` call runs `EXPIRE` again, the timer **restarts on each message**. The session ends 1 hour after the **last** message, not the first:

| Time | Event | Session now expires at |
|---|---|---|
| 10:00 | First message | 11:00 |
| 10:40 | Another message | 11:40 |
| 11:40 | No more messages | Keys deleted |

The timer uses real clock time, so it keeps counting even while Redis is stopped.

### 8.6 Pipeline

Without a pipeline, the three history commands would need three separate trips to Redis. A **pipeline** queues them and sends them in **one trip**. In redis-py a pipeline is also a **transaction** by default (`MULTI` … `EXEC`), so the commands run together without other commands slipping in between. Nothing is sent until `execute()` is called.

### 8.7 decode_responses=True

Redis stores raw bytes. With `decode_responses=True`, redis-py turns them into normal Python strings (`"abc"` instead of `b"abc"`), so the code doesn't need `.decode()` everywhere.

### 8.8 What survives what

Redis keeps data in RAM, but this project also saves it to disk: `--appendonly yes` writes every change to `appendonly.aof`, and that file sits on the Docker volume `retail_redis_data` (see [section 9](#9-docker-in-depth)).

| Event | Redis data | Foundry conversations |
|---|---|---|
| Stop or restart Uvicorn (Ctrl+C, or `--reload`) | ✅ Kept | ✅ Kept |
| `docker stop` / `docker start retail-redis` | ✅ Kept (reloaded from the AOF file) | ✅ Kept |
| Restart PC or Docker Desktop | ✅ Kept | ✅ Kept |
| `docker rm -f retail-redis`, then `docker run` again with the same `-v` | ✅ Kept (the volume survives) | ✅ Kept |
| `docker volume rm retail_redis_data` | ❌ Gone | ✅ Kept in Azure, but no longer linked to any session |
| 1 hour without messages on a session | ❌ That session's keys deleted | ✅ Kept in Azure, but no longer linked |

Even with persistence, Redis here is treated as **short-term memory**, not a permanent database. The difference is explained in [section 11](#11-the-class-whiteboard-reviewed).

### 8.9 Look inside Redis yourself

Run these in a terminal while the container is running:

```powershell
# List every key this app created
docker exec retail-redis redis-cli --scan --pattern "retail:*"

# Show the type of a key (string / list)
docker exec retail-redis redis-cli TYPE retail:<session_id>:history

# Read the Foundry conversation ID for a session
docker exec retail-redis redis-cli GET retail:<session_id>:conversation

# Read the whole chat history list
docker exec retail-redis redis-cli LRANGE retail:<session_id>:history 0 -1

# Seconds left before a key expires (-2 = already gone, -1 = no timer)
docker exec retail-redis redis-cli TTL retail:<session_id>:history

# How many keys are in database 0
docker exec retail-redis redis-cli DBSIZE
```

**Best learning trick:** watch every command live while you use Swagger UI. Leave this running, send a `/chat` request, and you'll see the exact `GET`, `SET`, `RPUSH` and `EXPIRE` commands from [8.4](#84-commands-used) arrive. Press Ctrl+C to stop.

```powershell
# Prints every command Redis receives, in real time
docker exec -it retail-redis redis-cli MONITOR
```

---

## 9. Docker in depth

### 9.1 Key ideas

| Term | Meaning | In this project |
|---|---|---|
| **Image** | A ready-made, read-only package of a program and everything it needs | `redis:7-alpine` (Redis 7 on tiny Alpine Linux) |
| **Container** | A running (or stopped) copy of an image, isolated from your system | `retail-redis` |
| **Volume** | A storage area managed by Docker that outlives containers | `retail_redis_data`, mounted at `/data` |
| **Port mapping** | Forwards a port on your laptop into the container | Laptop `127.0.0.1:6379` → container `6379` |
| **Docker Desktop** | The Windows app that runs the Docker engine | Must show **Engine running** |
| **WSL 2** | Windows' built-in Linux support | Docker Desktop runs containers in a small Linux VM through WSL 2 |

### 9.2 The docker run command explained

`docker run` **creates** a new container. You run it only once (or after deleting the container).

```powershell
docker run -d --name retail-redis -p 127.0.0.1:6379:6379 -v retail_redis_data:/data redis:7-alpine redis-server --appendonly yes
```

| Part | Meaning |
|---|---|
| `docker run` | Create and start a new container |
| `-d` | Detached: run in the background and give the terminal back |
| `--name retail-redis` | A fixed name, so you can refer to it later |
| `-p 127.0.0.1:6379:6379` | Port mapping, as `laptop-IP:laptop-port:container-port`. Binding to `127.0.0.1` means only your own laptop can reach Redis, not other computers on the network. |
| `-v retail_redis_data:/data` | Attach the volume at `/data`, where Redis saves its files |
| `redis:7-alpine` | The image to use (downloaded automatically the first time) |
| `redis-server --appendonly yes` | The command run inside the container: start Redis with disk persistence on |

### 9.3 Everyday Docker commands

| Command | What it does |
|---|---|
| `docker start retail-redis` | Start the existing container (daily use) |
| `docker stop retail-redis` | Stop it (data is kept) |
| `docker ps` | List **running** containers |
| `docker ps -a` | List **all** containers, including stopped ones |
| `docker logs retail-redis` | Show Redis's own log messages |
| `docker exec retail-redis redis-cli ping` | Run a command inside the container; replies `PONG` if Redis is healthy |
| `docker rm -f retail-redis` | Delete the container (the volume and its data stay) |
| `docker volume ls` | List volumes |
| `docker volume inspect retail_redis_data` | Show where the volume lives |

### 9.4 Docker Desktop

![Docker Desktop showing the downloaded images and Engine running](images/docker_desktop.png)

What to look at:

- **Bottom-left, Engine running:** Docker is ready. If it isn't running, every `docker` command fails (see [section 16](#16-troubleshooting)).
- **Images:** `redis 7-alpine` is the downloaded image. The green dot means a container is using it.
- **Containers** tab (left menu): shows `retail-redis`, with start and stop buttons, as an alternative to the commands above.
- **Volumes** tab: shows `retail_redis_data`.

---

## 10. Azure AI Foundry in depth

### 10.1 The parts

| Part | Meaning |
|---|---|
| **Project** | Your workspace in Foundry, reached through `FOUNDRY_PROJECT_ENDPOINT` |
| **Agent** | `Retail-Store-Agent`: a model plus instructions (policies), knowledge (store policy) and guardrails (Responsible AI). Created and edited in the **Foundry portal**, not in this code. |
| **Conversation** | A container in Foundry holding all messages of one chat. The agent reads it to remember context. |
| **Response** | One agent answer, produced by `responses.create(conversation=..., input=...)` |

Because the agent lives in Foundry, you can improve its instructions in the portal and the API picks up the change without any code edits.

### 10.2 Why there are two memories

| | Foundry conversation | Redis history |
|---|---|---|
| Where | Azure cloud | Docker container on your laptop |
| Used by | The **agent**, for context when replying | The **API**, for `GET /history` |
| Lifetime | Stays in Azure | Deleted after 1 hour of inactivity |
| Linked by | — | `retail:{id}:conversation` holds the Foundry conversation ID |

Redis doesn't store the agent's memory. It stores the **link** to it, plus a quick-to-read copy of the messages.

### 10.3 Signing in (DefaultAzureCredential)

`DefaultAzureCredential` tries several sign-in sources in a fixed order and uses the first one that works. Examples include environment variables, a managed identity (when the code runs on Azure), and your Azure CLI login. On your laptop it uses the token saved by `az login`. No passwords or keys appear in the code. If you aren't signed in, or your account has no access to the Foundry project, the `/chat` call fails with an authentication error.

### 10.4 Agent name

The code reads the agent name from `FOUNDRY_AGENT_NAME` in `.env` (`Retail-Store-Agent`). `"RetailSupportAgent"` in the code is only a fallback used when `.env` doesn't set the name, and it must match a real agent in your project to work.

---

## 11. The class whiteboard reviewed

### 11.1 Original sketch from class

![Original whiteboard sketch from class](images/whiteboard_original.png)

The sketch shows a **general e-commerce system** (not this exact project): a client calls a server, and the server uses **PostgreSQL** (in Docker) for structured order information and **Redis** (in Docker) as "immediate memory" for things like the cart.

### 11.2 What's correct

- ✅ The client talks **only to the server**, never to the databases.
- ✅ **PostgreSQL** holds structured, permanent data such as orders.
- ✅ **Redis** is the fast "immediate memory" for short-lived data such as carts and sessions.
- ✅ Running both databases in **Docker** is a normal way to develop locally.

### 11.3 What to fix

| In the sketch | Fix | Why |
|---|---|---|
| One-way arrows | Make every arrow **two-way** | Each call sends a request **and** gets a response; the server both reads and writes. |
| "addresses" inside Redis | Saved addresses belong in **PostgreSQL**. Redis may keep a **cached copy** for speed. | Addresses must never be lost, so the permanent copy goes in the main database. |
| "Phonepe" inside the Redis area | Not a component | It was a real-world example of an app using this pattern, not part of the architecture. |

### 11.4 Corrected version

![Corrected whiteboard: client, server, PostgreSQL and Redis](images/whiteboard_corrected.png)

### 11.5 How it maps to this project

| Whiteboard | This project |
|---|---|
| Client | Swagger UI / Postman |
| Server | FastAPI running in Uvicorn |
| Redis in Docker | ✅ Same: `retail-redis`, holding short-lived session data |
| PostgreSQL in Docker | ❌ **Not used.** Its place is taken by the **Foundry agent in the cloud**, which provides the AI replies. |

If this project grew, PostgreSQL would be the place for permanent data such as customers, orders, or a long-term archive of chats that must outlive Redis's 1-hour timer.

---

## 12. First-time setup

**Prerequisites:**

- Python 3.10 or newer (this project uses 3.14; the code's `UUID | None` syntax needs 3.10+)
- Docker Desktop
- Azure CLI
- An Azure AI Foundry project with an agent already created

**Steps:**

1. **Create the environment and install packages** (packages explained in [section 15](#15-configuration-and-project-files)):

   ```powershell
   # Create a private package folder for this project
   python -m venv .venv
   # Switch this terminal to use it
   .venv\Scripts\Activate.ps1
   # Install everything listed in requirements.txt
   pip install -r requirements.txt
   ```

2. **Create `.env`** with your values (see [section 15](#15-configuration-and-project-files)).

3. **Sign in to Azure** (see [10.3](#103-signing-in-defaultazurecredential)):

   ```powershell
   az login
   ```

4. **Open Docker Desktop**, wait for **Engine running**, and create the Redis container once (the command is explained in [9.2](#92-the-docker-run-command-explained)):

   ```powershell
   docker run -d --name retail-redis -p 127.0.0.1:6379:6379 -v retail_redis_data:/data redis:7-alpine redis-server --appendonly yes
   ```

5. Continue with [section 13](#13-daily-start-and-stop) from step 3.

---

## 13. Daily start and stop

**Start**, in this order:

```powershell
# 1. Open Docker Desktop and wait for "Engine running"

# 2. Start the existing Redis container (NOT docker run, which would create a new one)
docker start retail-redis

# 3. Check Redis is healthy (should print PONG)
docker exec retail-redis redis-cli ping

# 4. Activate the virtual environment (PyCharm's terminal usually does this for you)
.venv\Scripts\Activate.ps1

# 5. Start the API
python -m uvicorn main:app --reload
```

Then open **http://127.0.0.1:8000/docs** (see [section 14](#14-using-the-api-in-swagger-ui)).

**Stop:**

- **API:** press **Ctrl+C** in the terminal running Uvicorn.
- **Redis (optional):** `docker stop retail-redis`. Data is kept, see [8.8](#88-what-survives-what).

---

## 14. Using the API in Swagger UI

### 14.1 The addresses

| URL | What it is |
|---|---|
| **http://127.0.0.1:8000/docs** | **Swagger UI**: try `POST /chat` and `GET /history` in the browser |
| http://127.0.0.1:8000/docs#/default/chat_chat_post | Opens Swagger UI directly at `POST /chat` |
| http://127.0.0.1:8000/docs#/default/get_history_history__session_id__get | Opens Swagger UI directly at `GET /history/{session_id}` |
| http://127.0.0.1:8000/redoc | The same documentation in a read-only layout |
| http://127.0.0.1:8000/openapi.json | The raw API description that both pages are built from |
| http://127.0.0.1:8000/ | Returns `404 Not Found`. That's normal, because the app has no route for `/`. |

**About the links:**

- The part after `#` jumps to one endpoint. It's built as `#/<group>/<operation id>`. The group is `default` because the endpoints have no tags. FastAPI makes the operation id from the function name, path and method, so `get_history` + `/history/{session_id}` + `GET` becomes `get_history_history__session_id__get`.
- If your copied link ends in `?utm_source=chatgpt.com`, that's a tracking tag added when the link was copied from ChatGPT. It does nothing here and can be removed.

![Swagger UI with POST /chat open](images/swagger_ui.png)

### 14.2 How to send a request

1. Open `/docs` and click an endpoint to expand it.
2. Click **Try it out**.
3. Fill in the body (for `/chat`) or the `session_id` (for `/history`).
4. Click **Execute**. The reply appears below, under **Responses**.

### 14.3 POST /chat

First message, without a `session_id`:

```json
{ "message": "What is your return policy?" }
```

Reply:

```json
{
  "session_id": "e202c7de-87b2-4d30-90f9-892e2f2e3d67",
  "reply": "You can return items within ..."
}
```

Follow-up message: copy the `session_id` from the reply into the body.

```json
{
  "message": "What about refunds?",
  "session_id": "e202c7de-87b2-4d30-90f9-892e2f2e3d67"
}
```

### 14.4 GET /history/{session_id}

Paste the `session_id` into the parameter box. Reply:

```json
{
  "session_id": "e202c7de-87b2-4d30-90f9-892e2f2e3d67",
  "messages": [
    { "role": "user", "message": "What is your return policy?" },
    { "role": "assistant", "message": "You can return items within ..." }
  ]
}
```

An unknown or expired session returns an empty `messages` list.

### 14.5 From PowerShell instead of the browser

```powershell
# Send a chat message; Invoke-RestMethod converts the JSON reply into an object
$r = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/chat `
       -ContentType "application/json" `
       -Body '{"message": "What is your return policy?"}'
$r.reply

# Use the returned session_id to read the history
Invoke-RestMethod -Uri "http://127.0.0.1:8000/history/$($r.session_id)"
```

### 14.6 Status codes you may see

| Code | Meaning here |
|---|---|
| `200 OK` | Worked |
| `404 Not Found` | That address doesn't exist (for example `/`) |
| `405 Method Not Allowed` | Wrong method, such as opening `/chat` in the browser (which sends `GET`; `/chat` only accepts `POST`) |
| `422 Unprocessable Entity` | The body failed validation: empty or too-long message (over 2000 characters), or an invalid UUID |
| `500 Internal Server Error` | Something failed inside, usually Redis is down or the Azure call failed. Check the Uvicorn terminal for the error. |

---

## 15. Configuration and project files

### 15.1 Project structure

```
Customer_Feedback_Concurrent_Agents/
├── .venv/                   # Installed packages for this project (not committed)
├── .env                     # Settings and secrets (not committed, see section 17)
├── images/                  # All pictures used in this guide
│   ├── architecture.png
│   ├── where_everything_runs.png
│   ├── chat_request_sequence.png
│   ├── redis_keys.png
│   ├── whiteboard_original.png
│   ├── whiteboard_corrected.png
│   ├── docker_desktop.png
│   └── swagger_ui.png
├── main.py                  # The whole API (STEPs 1–6, see section 7)
├── requirements.txt         # Python packages to install
├── README.md                # Short intro that points to this guide
└── HOW_IT_ALL_WORKS.md      # This guide
```

### 15.2 The .env file

```env
FOUNDRY_PROJECT_ENDPOINT=https://<your-resource>.services.ai.azure.com/api/projects/<your-project>
FOUNDRY_AGENT_NAME=Retail-Store-Agent

REDIS_URL=redis://localhost:6379/0
```

| Variable | Required | Meaning |
|---|---|---|
| `FOUNDRY_PROJECT_ENDPOINT` | Yes | Your Foundry project's address, from its overview page in the portal |
| `FOUNDRY_AGENT_NAME` | Recommended | The exact name of the agent in Foundry (see [10.4](#104-agent-name)) |
| `REDIS_URL` | Optional | Where Redis is (explained in [5.2](#52-fastapi-and-redis)); defaults to `redis://localhost:6379/0` |

### 15.3 requirements.txt

Installed versions at the time of writing are shown in brackets.

| Package | Role (details in [section 4](#4-what-each-technology-does-and-why)) |
|---|---|
| `fastapi` (0.162.4) | Web framework |
| `uvicorn` (0.54.0) | Web server |
| `redis` (8.1.0) | Redis client |
| `azure-ai-projects>=2.9.0` (2.10.0) | Foundry SDK |
| `azure-identity` (1.27.0) | Azure sign-in |
| `python-dotenv` (1.2.4) | Loads `.env` |

---

## 16. Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| `failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine` | Docker Desktop isn't running | Open Docker Desktop, wait for **Engine running**; confirm with `docker version` (it must show a `Server:` section) |
| `Conflict. The container name "/retail-redis" is already in use` | You ran `docker run` again, but the container already exists | Use `docker start retail-redis`. To rebuild it: `docker rm -f retail-redis`, then `docker run ...` (data stays in the volume) |
| `The term 'failed' is not recognized as the name of a cmdlet` | An error message was pasted into the terminal as if it were a command | Harmless; ignore it |
| `Unable to find image 'redis:7-alpine' locally`, then `Pull complete` | Docker didn't have the image yet, so it downloaded it | Normal; nothing to fix |
| `404 Not Found` on `http://127.0.0.1:8000/` | No route for `/` | Use `/docs` ([section 14](#14-using-the-api-in-swagger-ui)) |
| `KeyError: 'FOUNDRY_PROJECT_ENDPOINT'` when starting Uvicorn | `.env` missing, misnamed, or not in the project folder | Create `.env` ([15.2](#152-the-env-file)) |
| `/chat` returns `500`, terminal shows `redis.exceptions.ConnectionError` | Redis isn't running | `docker start retail-redis`, then check `PONG` |
| `/chat` returns `500`, terminal shows an authentication error (`ClientAuthenticationError`) | Not signed in, or no access to the project | `az login`; check your role on the Foundry project |
| Agent not found error | Name in `.env` doesn't match the agent in Foundry | Copy the exact name from the portal ([10.4](#104-agent-name)) |
| `422 Unprocessable Entity` | Bad request body | See [14.6](#146-status-codes-you-may-see) |
| Agent "forgot" the earlier chat | More than 1 hour passed, or a different `session_id` was sent | Expected behaviour ([6.3](#63-three-situations)) |
| PyCharm says the PSReadLine module is outdated | Old PowerShell add-on, unrelated to this project | Optional: `Install-Module PSReadLine -MinimumVersion 2.0.3 -Scope CurrentUser -Force` |

---

## 17. Keeping secrets out of GitHub

`.env` contains your Foundry endpoint and must not be pushed. Add a `.gitignore` file to the project folder:

```gitignore
# Settings and secrets
.env
# Installed packages (recreate with pip install -r requirements.txt)
.venv/
# Python's compiled-file cache
__pycache__/
```

If `.env` was committed before, stop tracking it. The file stays on your laptop:

```powershell
git rm --cached .env
```

---

## 18. Limitations and next steps

| Limitation | Possible improvement |
|---|---|
| No login or API key: anyone who can reach the API and knows a `session_id` can read that history | Add API keys or user authentication |
| Errors from Redis or Azure come back as a raw `500` | Catch them and return clear messages |
| Expired sessions leave their Foundry conversations unused in Azure | Delete the Foundry conversation when a session ends |
| Chat history lasts only 1 hour | Change `SESSION_TTL`, or archive chats to a database such as PostgreSQL ([11.5](#115-how-it-maps-to-this-project)) |
| Blocking calls in a thread pool | Use the async versions of the Redis and Azure clients for high traffic |
| Testing only through Swagger UI | Build a small web chat page that stores the `session_id` and calls `/chat` |

---

## 19. Glossary

| Term | Meaning |
|---|---|
| **API** | A set of addresses (endpoints) that programs call to get things done |
| **Endpoint** | One address + method, such as `POST /chat` |
| **HTTP / HTTPS** | The protocol of the web; HTTPS is the encrypted version |
| **JSON** | Text format for data, like `{"key": "value"}` |
| **Port** | A numbered "door" on a computer that a program listens on (8000 for the API, 6379 for Redis) |
| **localhost / 127.0.0.1** | "This same computer" |
| **UUID** | A random, practically unique ID, such as `e202c7de-87b2-...` |
| **Session** | One customer's ongoing chat, identified by `session_id` |
| **TTL** | Time to live: a timer after which Redis deletes a key ([8.5](#85-ttl-and-the-sliding-1-hour-timer)) |
| **Key-value store** | Storage where each value is found by its name (key), like a dictionary |
| **AOF** | Append-only file: Redis's log of every change, used to rebuild data after a restart |
| **Pipeline** | Several Redis commands sent in one trip ([8.6](#86-pipeline)) |
| **Image / Container / Volume** | See [9.1](#91-key-ideas) |
| **SDK** | A library that makes a service easy to call from code (e.g. `azure-ai-projects`) |
| **LLM** | Large language model: the AI model behind the agent |
| **Agent** | An LLM plus instructions, knowledge and guardrails, set up to do one job |
| **Conversation** | Foundry's stored record of one chat ([10.1](#101-the-parts)) |
| **OpenAPI** | Standard description of an API; FastAPI generates it and Swagger UI displays it |
| **Pydantic** | Library that validates data against a model like `ChatRequest` |
| **Uvicorn** | The server program that runs the FastAPI app |
| **Middle layer / orchestrator** | Code that sits between other services and coordinates them (the API's role here) |
