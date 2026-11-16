import os
import json
from uuid import UUID, uuid4

import redis
from dotenv import load_dotenv
from fastapi import FastAPI                     # package is "fastapi" (no underscore)
from openai import BadRequestError              # raised when a Foundry guardrail blocks a message
from pydantic import BaseModel, Field
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

# Load FOUNDRY_PROJECT_ENDPOINT, FOUNDRY_AGENT_NAME and REDIS_URL from .env
load_dotenv()

app = FastAPI(title="Employee Leave Agent API")

SESSION_TTL = 3600  # forget a session 1 hour after its last message

# Redis in Docker: leave-redis is on laptop port 6380 (retail-redis keeps 6379).
# decode_responses=True (with an "s") returns str instead of bytes.
db = redis.Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6380/0"),
    decode_responses=True
)

# Connect to the Foundry project, signed in with your "az login"
project = AIProjectClient(
    endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
    credential=DefaultAzureCredential(),
    allow_preview=True
)

# OpenAI-style client whose replies come from the EmployeeLeaveAgent in Foundry
agent = project.get_openai_client(
    agent_name=os.getenv("FOUNDRY_AGENT_NAME", "EmployeeLeaveAgent")
)


# Shape of the /chat request body; FastAPI rejects bad input with a 422
class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: UUID | None = None


@app.post("/chat")
def chat(request: ChatRequest):
    # Reuse the client's session_id, or create one for a new user
    session_id = str(request.session_id or uuid4())

    # Same "leave:" prefix and exact key names as GET /history, so both find the same data
    conversation_key = f"leave:{session_id}:conversation"
    history_key = f"leave:{session_id}:history"

    # Foundry conversation for this session (None if new or expired)
    conversation_id = db.get(conversation_key)

    # New session: create an empty Foundry conversation and remember it in Redis
    if not conversation_id:
        conversation = agent.conversations.create()
        conversation_id = conversation.id

        db.set(
            conversation_key,
            conversation_id,
            ex=SESSION_TTL
        )

    # Ask the agent inside this conversation, so it remembers earlier messages
    try:
        response = agent.responses.create(
            conversation=conversation_id,
            input=request.message
        )
        answer = response.output_text or ""
    except BadRequestError as error:
        # A guardrail block is expected behaviour: reply politely instead of a 500
        if error.code != "content_filter":
            raise
        answer = ("Sorry, I can't help with that message because it was blocked by our "
                  "safety guardrails. Please ask a question about Contoso employee leave.")

    # Save both messages and reset both 1-hour timers in one Redis round trip
    with db.pipeline() as pipe:
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

        pipe.expire(history_key, SESSION_TTL)
        pipe.expire(conversation_key, SESSION_TTL)

        pipe.execute()  # nothing is sent to Redis until here

    # Client keeps session_id and sends it with the next message
    return {
        "session_id": session_id,
        "reply": answer
    }


@app.get("/history/{session_id}")
def get_history(session_id: UUID):

    # Must match the key used in /chat exactly
    history_key = f"leave:{session_id}:history"

    # 0 to -1 = the whole list (empty if unknown or expired)
    messages = db.lrange(history_key, 0, -1)

    return {
        "session_id": str(session_id),
        "messages": [
            json.loads(message)
            for message in messages
        ]
    }