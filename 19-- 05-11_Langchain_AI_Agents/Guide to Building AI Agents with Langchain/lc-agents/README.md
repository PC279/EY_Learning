# lc-agents — companion code for "Building AI Agents with LangChain"

    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env          # add your OpenRouter key; choose models that support tool calling

Run from this folder as modules:

| Part | Command |
|---|---|
| 1 Models, messages, structured output | `python -m part1.p1_models`, `part1.p1_messages`, `part1.p1_structured` |
| 2 MCP tools | `python -m part2.mcp_client` (starts `part2.mcp_server` itself) |
| 3 First agent, chat loop | `python -m part3.agent_v1`, `python -m part3.chat` |
| 4 Structured output, context, dynamic prompt | `python -m part4.structured_agent`, `part4.context_prompt` |
| 5 Built-in and custom middleware | `python -m part5.custom` (see also `part5/builtin.py`) |
| 6 Memory | `python -m part6.memory`, `python -m part6.persistent` |
| 7 Approvals, streaming | `python -m part7.hitl`, `python -m part7.streaming` |
| 8 Subagents | `python -m part8.subagents` |
| 9 Tests, evaluation, API | `python -m pytest -q tests`, `python -m part9.run_tasks 3`, `uvicorn part9.app:app --reload` |

Mock company data: E101 Priya Rao (Bengaluru), E202 Lukas Becker (Berlin, on probation). "Today" is fixed at 2026-11-04.
