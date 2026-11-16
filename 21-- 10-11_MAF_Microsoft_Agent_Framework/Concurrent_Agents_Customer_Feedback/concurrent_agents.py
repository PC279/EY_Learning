# feedback_agents.py
# ------------------------------------------------------------
# Three agents analyse the SAME customer feedback at the same time
# using Microsoft Agent Framework's ConcurrentBuilder (fan-out / fan-in).
# The LLM is accessed through OpenRouter.
# ------------------------------------------------------------

import asyncio
import json
import os
from pathlib import Path
from time import perf_counter                       # precise timer for measuring run time

from dotenv import load_dotenv
from agent_framework import Agent, AgentResponse
# OpenRouter speaks the OpenAI "Chat Completions" format, so we use the
# Chat Completions client and point it at OpenRouter's address.
from agent_framework.openai import OpenAIChatCompletionClient
from agent_framework.orchestrations import ConcurrentBuilder


HERE = Path(__file__).resolve().parent             # folder containing this file
load_dotenv(HERE / ".env")                          # load OPENROUTER_* variables from .env

# OpenRouter's OpenAI-compatible API address (same for every model)
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def load_feedback():
    """Load the same feedback records for every agent."""
    with (HERE / "feedback.json").open(encoding="utf-8") as file:
        records = json.load(file)
    if not isinstance(records, list) or not records:
        raise ValueError("feedback.json must be a non-empty JSON list")
    return records


async def main():
    # Read OpenRouter settings from .env
    api_key = os.getenv("OPENROUTER_API_KEY")
    model = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3.5-super-vl:free")

    # Fail early with a clear message if the key is missing
    if not api_key:
        raise SystemExit("Missing OPENROUTER_API_KEY. Add it to your .env file.")

    feedback = load_feedback()

    # One client shared by all three agents.
    # model    -> WHICH model (from OpenRouter's model page)
    # api_key  -> WHO you are (your OpenRouter key)
    # base_url -> WHERE to send requests (OpenRouter instead of OpenAI)
    client = OpenAIChatCompletionClient(
        model=model,
        api_key=api_key,
        base_url=OPENROUTER_BASE_URL,
    )

    # STEP 1: Three independent agents, each with a different responsibility.
    sentiment = Agent(
        client=client,
        name="SentimentAgent",
        instructions=(
            "You analyze customer sentiment. Using ONLY the given feedback JSON, "
            "count positive (ratings 4-5), neutral (rating 3), and negative "
            "(ratings 1-2) reviews. Cite 2-3 feedback IDs as examples. "
            "Give concise results. Do not invent reviews."
        ),
    )

    issues = Agent(
        client=client,
        name="IssueAgent",
        instructions=(
            "You identify recurring customer issues. Using ONLY the given "
            "feedback JSON, list the top three complaints, referencing the "
            "feedback IDs supporting each issue. Be concise. Do not infer "
            "numbers or issues not present in the data."
        ),
    )

    improvements = Agent(
        client=client,
        name="ImprovementAgent",
        instructions=(
            "You propose practical improvements to the service. Using ONLY "
            "the supplied feedback JSON, suggest three specific actions, "
            "each tied to one or more feedback IDs. Do not assume you have "
            "seen the other agents' answers. Be concise."
        ),
    )

    # STEP 2: Fan out the SAME input to all three agents concurrently.
    workflow = ConcurrentBuilder(
        participants=[sentiment, issues, improvements]
    ).build()

    # STEP 3: Run once, collect the three independent results (fan in).
    prompt = (
        "Analyze these fictional customer feedback records. "
        "Use the assigned role's instructions.\n\n"
        + json.dumps(feedback, ensure_ascii=False, indent=2)
    )

    print(f"Analyzing {len(feedback)} customer reviews with 3 concurrent agents ({model})...\n")
    started = perf_counter()
    result = await workflow.run(prompt)

    # Default aggregation returns one AgentResponse containing the agent messages.
    for output in result.get_outputs():
        if isinstance(output, AgentResponse):
            for message in output.messages:
                print(f"\n{'=' * 56}")
                print(f"{message.author_name or 'Agent'}")
                print("=" * 56)
                print(message.text or "(No text returned)")

    print(f"\nCompleted in {perf_counter() - started:.1f} seconds")


if __name__ == "__main__":
    asyncio.run(main())