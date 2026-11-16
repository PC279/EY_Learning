# Retail Support Agent API

A FastAPI backend that connects customers to a retail support AI agent in **Azure AI Foundry**, using **Redis** (running in Docker) to remember each chat session.

![Where everything runs](images/where_everything_runs.png)

**Quick start:** open Docker Desktop → `docker start retail-redis` → `python -m uvicorn main:app --reload` → open http://127.0.0.1:8000/docs

📘 **Everything else is in [HOW_IT_ALL_WORKS.md](HOW_IT_ALL_WORKS.md)**: what each piece does, where it runs, how they connect, a step-by-step request walkthrough, Redis and Docker in depth, setup, the Swagger UI, and troubleshooting.
