"""
main.py: Employee Leave Agent API (FastAPI + Redis)
===================================================

This is the web API that sits between a client (Swagger UI, Postman, an app)
and the EmployeeLeaveAgent in Microsoft Foundry.

    Client  --HTTP-->  FastAPI (this file)  --uses-->  LeaveAgentService (agent_service.py)  -->  Foundry agent
                              |
                              +--> Redis (Docker container "leave-redis"): session memory

What each piece does:
- FastAPI         : defines the endpoints and validates requests.
- LeaveAgentService: talks to the Foundry agent (see agent_service.py).
- Redis           : remembers, for each session_id,
                      1) which Foundry conversation it belongs to, and
                      2) a copy of the chat history (for GET /history).
                    Keys expire automatically after SESSION_TTL_SECONDS of inactivity.

Run it:  python -m uvicorn main:app --reload
Docs:    http://127.0.0.1:8000/docs
"""

import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Literal
from uuid import UUID, uuid4

import redis
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from agent_service import LeaveAgentService


# =============================================================================
# STEP 1: Configuration
# =============================================================================
# Read settings from .env into the environment.
load_dotenv()

# Where Redis is. Port 6380 on this laptop is mapped to the leave-redis container,
# so this project can run next to the Retail project's Redis on 6379.
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6380/0")

# How long a session is remembered after the LAST message (seconds). Default: 1 hour.
SESSION_TTL = int(os.getenv("SESSION_TTL_SECONDS", "3600"))

# Every Redis key this app creates starts with this prefix, e.g. "leave:<id>:history".
KEY_PREFIX = "leave"

# Simple logging, so errors show up clearly in the Uvicorn terminal.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("leave-api")


def redis_keys(session_id: str) -> tuple[str, str]:
    """Return the two Redis key names used for one session.

    conversation key -> holds the Foundry conversation ID (a String)
    history key      -> holds the chat messages (a List of JSON strings)
    """
    return (f"{KEY_PREFIX}:{session_id}:conversation",
            f"{KEY_PREFIX}:{session_id}:history")


# =============================================================================
# STEP 2: Start-up and shut-down (create and close the connections once)
# =============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once when the server starts (before 'yield') and once when it stops (after).

    Creating the clients here, instead of inside each request, means we connect
    once and reuse the same connections for every request.
    """
    # Redis client. It connects lazily, on the first command.
    # decode_responses=True returns normal str values instead of bytes.
    app.state.db = redis.Redis.from_url(REDIS_URL, decode_responses=True)

    # Our "agent as a service" from agent_service.py.
    app.state.agent = LeaveAgentService()
    logger.info("Connected to agent '%s'. Redis at %s", app.state.agent.agent_name, REDIS_URL)

    yield   # <- the API serves requests while paused here

    # Server is stopping: close the connections cleanly.
    app.state.agent.close()
    app.state.db.close()


app = FastAPI(
    title="Employee Leave Agent API",
    version="1.0.0",
    description="Ask Contoso leave-policy questions. Answers come from the "
                "EmployeeLeaveAgent in Microsoft Foundry; sessions are kept in Redis.",
    lifespan=lifespan,
)


# =============================================================================
# STEP 3: Request and response shapes (Pydantic models)
# =============================================================================
# FastAPI uses these to validate incoming JSON (bad input -> 422 error)
# and to show example bodies in Swagger UI.

class ChatRequest(BaseModel):
    # The employee's question: 1 to 2000 characters.
    message: str = Field(min_length=1, max_length=2000,
                         examples=["How many casual leave days am I entitled to?"])
    # Leave empty on the first message; send back the returned session_id after that.
    session_id: UUID | None = Field(default=None, examples=[None])


class ChatResponse(BaseModel):
    session_id: UUID     # keep this and send it with the next message
    reply: str           # the agent's answer
    blocked: bool        # True if a Foundry guardrail blocked the message


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    message: str
    blocked: bool = False


class HistoryResponse(BaseModel):
    session_id: UUID
    messages: list[HistoryMessage]


# =============================================================================
# STEP 4: Small helper endpoints
# =============================================================================
@app.get("/", tags=["info"])
def root():
    """Friendly landing response, so opening the base URL doesn't show 404."""
    return {"service": "Employee Leave Agent API", "docs": "/docs", "health": "/health"}


@app.get("/health", tags=["info"])
def health():
    """Check that the API is up and can reach Redis."""
    try:
        app.state.db.ping()   # Redis answers PONG if it's running
    except redis.exceptions.RedisError:
        raise HTTPException(status_code=503, detail="Redis is not reachable. Is the leave-redis container running?")
    return {"api": "ok", "redis": "ok", "agent": app.state.agent.agent_name}


# =============================================================================
# STEP 5: Chat endpoint  ->  POST /chat
# =============================================================================
# Plain "def" (not "async def"): Redis and Foundry calls are blocking,
# so FastAPI runs this function in a worker thread.
@app.post("/chat", response_model=ChatResponse, tags=["chat"])
def chat(request: ChatRequest):
    db, agent = app.state.db, app.state.agent

    # New customer? Create a session_id. Returning customer? Reuse theirs.
    session_id = str(request.session_id or uuid4())
    conversation_key, history_key = redis_keys(session_id)

    # 5a. Find this session's Foundry conversation in Redis (None if new or expired).
    try:
        conversation_id = db.get(conversation_key)
    except redis.exceptions.RedisError:
        raise HTTPException(status_code=503, detail="Redis is not reachable.")

    # 5b. Ask the agent. If conversation_id is None, ask() creates a new
    #     Foundry conversation and returns its ID in reply.conversation_id.
    try:
        reply = agent.ask(request.message, conversation_id)
    except Exception:
        # Guardrail blocks are already handled inside ask(); anything here is a
        # real failure (network, sign-in, wrong agent name...). Log the details
        # for us, return a short message to the client.
        logger.exception("Agent call failed")
        raise HTTPException(status_code=502, detail="The leave agent could not be reached. Please try again.")

    # 5c. Save to Redis in ONE round trip (a pipeline):
    #     - the session -> conversation link (with a fresh 1-hour timer)
    #     - the user message and the reply, appended to the history list
    #     - a fresh 1-hour timer on the history too
    try:
        with db.pipeline() as pipe:
            pipe.set(conversation_key, reply.conversation_id, ex=SESSION_TTL)
            pipe.rpush(
                history_key,
                json.dumps({"role": "user", "message": request.message, "blocked": reply.blocked}),
                json.dumps({"role": "assistant", "message": reply.text, "blocked": reply.blocked}),
            )
            pipe.expire(history_key, SESSION_TTL)
            pipe.execute()   # nothing is sent until here
    except redis.exceptions.RedisError:
        raise HTTPException(status_code=503, detail="Redis is not reachable.")

    return ChatResponse(session_id=session_id, reply=reply.text, blocked=reply.blocked)


# =============================================================================
# STEP 6: History endpoint  ->  GET /history/{session_id}
# =============================================================================
@app.get("/history/{session_id}", response_model=HistoryResponse, tags=["chat"])
def get_history(session_id: UUID):
    _, history_key = redis_keys(str(session_id))
    try:
        # LRANGE 0 -1 = the whole list, first to last. Empty list if unknown/expired.
        raw_messages = app.state.db.lrange(history_key, 0, -1)
    except redis.exceptions.RedisError:
        raise HTTPException(status_code=503, detail="Redis is not reachable.")

    # Each item was stored as a JSON string; turn it back into a dict.
    return HistoryResponse(session_id=session_id,
                           messages=[json.loads(item) for item in raw_messages])


# =============================================================================
# STEP 7: End a session  ->  DELETE /sessions/{session_id}
# =============================================================================
@app.delete("/sessions/{session_id}", tags=["chat"])
def end_session(session_id: UUID):
    """Forget a session: delete its Foundry conversation and its Redis keys."""
    db, agent = app.state.db, app.state.agent
    conversation_key, history_key = redis_keys(str(session_id))

    try:
        conversation_id = db.get(conversation_key)
        deleted_keys = db.delete(conversation_key, history_key)   # returns how many keys existed
    except redis.exceptions.RedisError:
        raise HTTPException(status_code=503, detail="Redis is not reachable.")

    # Also remove the conversation from Foundry, if we knew it.
    if conversation_id:
        try:
            agent.end_conversation(conversation_id)
        except Exception:
            logger.warning("Could not delete Foundry conversation %s", conversation_id)

    return {"session_id": str(session_id), "deleted": deleted_keys > 0}
