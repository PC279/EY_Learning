"""2.4 A simple long-term memory: one JSON file of facts per employee."""
import json
from pathlib import Path

STORE = Path("memory.json")


def _load() -> dict:
    return json.loads(STORE.read_text()) if STORE.exists() else {}


def remember(employee_id: str, fact: str) -> dict:
    """Tool: save a lasting preference or fact the employee stated."""
    data = _load()
    facts = data.setdefault(employee_id, [])
    if fact not in facts:
        facts.append(fact)
    STORE.write_text(json.dumps(data, indent=2))
    return {"saved": fact}


def recall(employee_id: str) -> list[str]:
    """Read at the start of every task and added to the system prompt."""
    return _load().get(employee_id, [])
