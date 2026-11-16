# lg-coord — companion code for "LangGraph, the Agent Lifecycle and Multi-Agent Coordination"

    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env          # add your OpenRouter key; choose a model that supports tool calling
    python -m pytest -q tests     # 14 tests, no API key or network needed

Run scripts from this folder as modules:

| Part | Command |
|---|---|
| 2 LangGraph from scratch | `python -m part2.onboarding_graph` |
| 3 Command and Send | `python -m part3.command_send` |
| 3 Subgraphs | `python -m part3.subgraph` |
| 3 Interrupts, retries, time travel | `python -m part3.persistence` |
| 3 Functional API | `python -m part3.functional` |
| 4 Run lifecycle | `python -m part4.lifecycle` |
| 6 Patterns 1-7 | `python -m part6.p1_sequential` ... `python -m part6.p7_blackboard` |
| 7 MCP | `python -m part7.mcp_client` (starts `part7.mcp_server` itself) |
| 8 Real-model coordination eval | `python -m part8.eval_coordination 3` |

Parts 2-3 need no model. Mock company data: E101 Priya Rao (Bengaluru), E202 Lukas Becker (Berlin, on probation).
