"""
schemas.py - Pydantic models shared by the API (request and response shapes).
Person C's part is below. Persons A and B add their models to this same file.
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AISuggestionOut(BaseModel):
    # from_attributes lets FastAPI build this straight from the SQLAlchemy AISuggestion object
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    suggested_category: str
    suggested_priority: str
    priority_reason: str
    troubleshooting_steps: list[str]
    model_name: str
    created_at: datetime
