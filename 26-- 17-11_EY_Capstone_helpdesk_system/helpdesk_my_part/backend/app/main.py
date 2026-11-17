"""
TEMPORARY main.py for Person C's local testing only.
Do NOT push this file: Person B writes the real main.py (with CORS and all routers).
"""
import logging

from fastapi import FastAPI

from app.routers import ai

# Show the ai_service log lines (outcome, timing) in the terminal while testing
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Helpdesk API - Person C local test")
app.include_router(ai.router, prefix="/api")   # adds /api/tickets/{id}/ai-analysis and /ai-suggestions
