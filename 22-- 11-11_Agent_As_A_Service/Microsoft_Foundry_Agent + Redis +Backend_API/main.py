# =============================================================================
# Retail Support Agent API
# -----------------------------------------------------------------------------
# A small web API that lets a customer chat with an AI agent hosted in
# Azure AI Foundry. Redis is used as fast, short-term "session memory" so the
# API remembers which Foundry conversation belongs to which customer, and keeps
# a readable copy of the chat history.
#
# Request flow for POST /chat:
#   client -> FastAPI -> Redis (find this customer's conversation)
#                     -> Foundry agent (generate the reply)
#                     -> Redis (save the messages)  -> reply back to client
# =============================================================================

import os      # read environment variables (values loaded from the .env file)
import json    # turn Python dicts into JSON strings before storing in Redis

# UUID  = a type that validates "is this a proper unique ID?"
# uuid4 = a function that generates a brand-new random unique ID
from uuid import UUID, uuid4

import redis                      # Python client for talking to the Redis server
from dotenv import load_dotenv    # loads key=value pairs from .env into os.environ
from fastapi import FastAPI       # the web framework that exposes our API endpoints
from pydantic import BaseModel, Field  # used to define and validate request bodies

# DefaultAzureCredential tries several login methods in order (environment
# variables, managed identity, Azure CLI "az login", VS Code, etc.) and uses
# the first one that works. Locally, it normally picks up your "az login".
from azure.identity import DefaultAzureCredential

# AIProjectClient is the entry point to your Azure AI Foundry project.
from azure.ai.projects import AIProjectClient


# -----------------------------------------------------------------------------
# STEP 1: Load configuration
# -----------------------------------------------------------------------------
# Read the .env file in the project folder and put its values into the
# environment, so os.getenv("...") / os.environ["..."] can find them.
# This keeps secrets and URLs out of the source code.
load_dotenv()

# Create the FastAPI application. The title is what you see at the top of
# the auto-generated docs page (http://127.0.0.1:8000/docs).
app = FastAPI(title="Retail Store Agent API")

# How long (in seconds) a customer's session is remembered in Redis.
# After 1 hour of no activity, Redis deletes the keys automatically and the
# next message from that session_id starts a fresh conversation.
SESSION_TTL = 3600  # 1 hour


# -----------------------------------------------------------------------------
# STEP 2: Connect to Redis
# -----------------------------------------------------------------------------
# from_url() builds a connection from a URL of the form:
#   redis://<host>:<port>/<database-number>
# REDIS_URL comes from .env; if it's missing we fall back to the local
# Docker container (localhost, port 6379, database 0).
#
# decode_responses=True makes Redis return normal Python strings instead of
# raw bytes (b"..."), so we don't have to call .decode() everywhere.
#
# Note: this line doesn't actually connect yet. Redis connects lazily, on the
# first command (e.g. db.get). So if Redis is down, the error shows up on the
# first /chat request, not at startup.
db = redis.Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    decode_responses=True
)


# -----------------------------------------------------------------------------
# STEP 3: Connect to the existing Foundry agent
# -----------------------------------------------------------------------------
# Connect to your Azure AI Foundry project.
#   endpoint     -> your project's URL (required, so os.environ[...] is used:
#                   it crashes immediately with a KeyError if missing, which is
#                   better than failing silently later)
#   credential   -> who we are (your Azure login, via DefaultAzureCredential)
#   allow_preview-> opt in to preview features of the SDK
project = AIProjectClient(
    endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
    credential=DefaultAzureCredential(),
    allow_preview=True
)

# Get an OpenAI-compatible client that is linked to the agent you already
# created in the Foundry portal (looked up by its name). The agent's
# instructions, model and tools all live in Foundry, so this code only has to
# send messages to it. "RetailSupportAgent" is only a fallback used when
# FOUNDRY_AGENT_NAME is not set in .env.
agent = project.get_openai_client(
    agent_name=os.getenv("FOUNDRY_AGENT_NAME", "Retail-Store-Agent")
)


# -----------------------------------------------------------------------------
# STEP 4: Define the request structure
# -----------------------------------------------------------------------------
# Pydantic model describing what the JSON body of POST /chat must look like:
#   {
#     "message": "Where is my order?",
#     "session_id": "e202c7de-87b2-4d30-90f9-892e2f2e3d67"   <- optional
#   }
# FastAPI validates every request against this automatically and returns a
# 422 error if the body doesn't match, before our function even runs.
class ChatRequest(BaseModel):
    # The customer's message: must be between 1 and 2000 characters.
    # (Blocks empty messages and protects against huge inputs.)
    message: str = Field(min_length=1, max_length=2000)

    # Optional session ID.
    #   - First message: leave it out (None) and the server creates one.
    #   - Next messages: send back the session_id you received, so the agent
    #     continues the same conversation and remembers earlier messages.
    # Typing it as UUID means invalid IDs like "abc" are rejected with a 422.
    session_id: UUID | None = None


# -----------------------------------------------------------------------------
# STEP 5: Chat API  ->  POST /chat
# -----------------------------------------------------------------------------
# Receives a customer message, sends it to the Foundry agent inside the right
# conversation, stores the exchange in Redis, and returns the agent's reply.
#
# It's a plain "def" (not "async def"), so FastAPI runs it in a thread pool.
# That's the right choice here because the Redis and Azure calls are blocking.
@app.post("/chat")
def chat(request: ChatRequest):

    # Use the session_id the client sent, or create a new one for a new customer.
    # str() converts the UUID object to text so we can use it in Redis keys.
    session_id = str(request.session_id or uuid4())

    # Build the Redis key names for this session. The "retail:<id>:..."
    # naming is a common Redis convention (namespaces separated by colons)
    # that keeps keys organised and avoids clashes with other apps.
    conversation_key = f"retail:{session_id}:conversation"  # stores Foundry conversation ID
    history_key = f"retail:{session_id}:history"            # stores list of chat messages

    # Look up whether this session already has a Foundry conversation.
    # Returns the conversation ID string, or None if not found / expired.
    conversation_id = db.get(conversation_key)

    # No conversation yet (new customer, or the 1-hour TTL expired):
    # create a new conversation in Foundry.
    if not conversation_id:
        # A Foundry "conversation" is a container that stores all messages
        # server-side, so the agent automatically sees the earlier context
        # on every new message in the same conversation.
        conversation = agent.conversations.create()
        conversation_id = conversation.id

        # Remember the mapping  session_id -> conversation_id  in Redis.
        # ex=SESSION_TTL makes Redis delete the key automatically after 1 hour.
        db.set(
            conversation_key,
            conversation_id,
            ex=SESSION_TTL
        )

    # Send the customer's message to the Foundry agent, inside the right
    # conversation. The agent uses its instructions plus the earlier messages
    # of this conversation to produce a reply.
    response = agent.responses.create(
        conversation=conversation_id,
        input=request.message
    )

    # output_text gathers all the text parts of the agent's reply into one
    # string. "or ''" protects against a None value (e.g. if the reply had
    # no text), so we always store and return a string.
    answer = response.output_text or ""

    # Save the chat history in Redis.
    # A pipeline groups several Redis commands and sends them in ONE network
    # round trip, instead of one trip per command. By default redis-py also
    # wraps them in a transaction (MULTI/EXEC), so they run together.
    # "with" makes sure the pipeline is cleaned up afterwards.
    with db.pipeline() as pipe:
        # RPUSH appends values to the end (Right side) of a Redis list.
        # Redis stores plain strings, so each message dict is turned into a
        # JSON string first. Two entries are added: the user's message and
        # the assistant's reply, in chat order.
        pipe.rpush(
            history_key,
            json.dumps({
                "role": "user",
                "message": request.message
            }),
            json.dumps({
                "role": "assistant",
                "message": answer
            })
        )

        # Reset the 1-hour timer on both keys every time the customer chats.
        # So the session expires 1 hour after the LAST message, not the first
        # (a "sliding" expiry).
        pipe.expire(history_key, SESSION_TTL)
        pipe.expire(conversation_key, SESSION_TTL)

        # Actually send all the queued commands to Redis.
        # (Nothing above runs until execute() is called.)
        pipe.execute()

    # Send the reply back to the client. The client must keep session_id and
    # send it with the next message to continue the same conversation.
    return {
        "session_id": session_id,
        "reply": answer
    }


# -----------------------------------------------------------------------------
# STEP 6: Retrieve chat history  ->  GET /history/{session_id}
# -----------------------------------------------------------------------------
# Returns every message stored in Redis for one session.
# {session_id} in the path is read from the URL, and the ": UUID" type hint
# makes FastAPI reject anything that isn't a valid UUID (422 error).
@app.get("/history/{session_id}")
def get_history(session_id: UUID):

    # Same key format that /chat used when saving.
    history_key = f"retail:{session_id}:history"

    # LRANGE reads items from a list. 0 = first item, -1 = last item,
    # so 0..-1 means "the whole list". Returns a list of JSON strings,
    # or an empty list if the session doesn't exist or has expired.
    messages = db.lrange(history_key, 0, -1)

    # json.loads turns each stored JSON string back into a Python dict,
    # so the response is a clean list like:
    #   [{"role": "user", "message": "..."}, {"role": "assistant", ...}]
    return {
        "session_id": str(session_id),
        "messages": [
            json.loads(message)
            for message in messages
        ]
    }