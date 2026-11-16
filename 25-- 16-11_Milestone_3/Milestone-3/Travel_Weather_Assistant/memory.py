"""Per-session conversation memory in Redis. Every key contains the session ID, so sessions never mix."""
import json

import redis
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from config import REDIS_URL

MAX_MESSAGES = 10      # keep only the last 5 question/answer pairs
TTL_SECONDS = 60 * 60  # a session is forgotten after 1 hour of inactivity

client = redis.Redis.from_url(REDIS_URL, decode_responses=True)


def _keys(session_id: str) -> tuple[str, str]:
    return f"travel:session:{session_id}:messages", f"travel:session:{session_id}:trip_id"


def load(session_id: str) -> tuple[list[BaseMessage], int | None]:
    """Return the session's recent messages (as LangChain messages) and the trip it last talked about."""
    messages_key, trip_key = _keys(session_id)
    raw = client.lrange(messages_key, 0, -1)
    trip_id = client.get(trip_key)
    history = []
    for item in map(json.loads, raw):
        cls = HumanMessage if item["role"] == "human" else AIMessage
        history.append(cls(content=item["content"]))
    return history, int(trip_id) if trip_id else None


def save_turn(session_id: str, question: str, answer: str, trip_id: int | None) -> None:
    messages_key, trip_key = _keys(session_id)
    pipe = client.pipeline()  # one round trip, applied together
    pipe.rpush(messages_key, json.dumps({"role": "human", "content": question}),
               json.dumps({"role": "ai", "content": answer}))
    pipe.ltrim(messages_key, -MAX_MESSAGES, -1)
    pipe.expire(messages_key, TTL_SECONDS)
    if trip_id is not None:
        pipe.set(trip_key, trip_id, ex=TTL_SECONDS)
    else:
        pipe.expire(trip_key, TTL_SECONDS)  # keep the remembered trip alive alongside the messages
    pipe.execute()
