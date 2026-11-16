# Nimbus Assist — companion code

Code for the doc "Agentic AI from First Principles: Building Nimbus Assist".

    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env      # add your OpenRouter key; pick a model that supports tool calling

Run from this folder:

| Part | Command |
|---|---|
| 3 hand-built agent | `python -m part3_by_hand.agent --employee E101` |
| 4 LangGraph graph agent | `python -m part4_langgraph.graph_agent --employee E101` |
| 4 prebuilt agent (streaming) | `python -m part4_langgraph.prebuilt_agent` |
| 4 MCP server (stdio) | `python -m part4_langgraph.mcp_server` |
| 4 OpenAI Agents SDK version | `python -m part4_langgraph.openai_agents_version` (needs `openai-agents`) |
| 5 multi-agent team (onboarding) | `python -m part5_multi_agent.team` |
| 7 evaluate the 8 tasks | `python -m eval.run_tasks 3` |

Employees in the mock data: E101 Priya Rao (Bengaluru), E202 Lukas Becker (Berlin, on probation).
The company systems in `nimbus_systems.py` are in-memory mocks; "today" is fixed at 2026-11-04.
