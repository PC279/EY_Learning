# sequential.py
# ------------------------------------------------------------
# Runs the three agents as ONE sequential workflow using
# Microsoft Agent Framework's SequentialBuilder:
#
#   Customer Request -> Inventory -> Pricing -> Recommendation -> Final Recommendation
#
# The workflow passes the full conversation (including tool calls
# and tool results) from each agent to the next automatically.
#
# Usage:
#   python sequential.py
#   Then type a request at the prompt. Type "exit" to stop.
# ------------------------------------------------------------

import asyncio                                         # run async code (the workflow is async)
from agent_framework.orchestrations import SequentialBuilder

from agents import create_agents                       # our three agents from agents.py


# Friendly display names for each agent (keys are the agents' "name" values)
DISPLAY_NAMES = {
    "InventoryAgent": "STEP 1/3 · Inventory Agent",
    "PricingAgent": "STEP 2/3 · Pricing Agent",
    "RecommendationAgent": "STEP 3/3 · Recommendation Agent",
}

# Words that stop the program (compared in lowercase)
EXIT_COMMANDS = {"exit"}


# ============================================================
# STEP 1: Build the sequential workflow
# ============================================================

def build_workflow(inventory_agent, pricing_agent, recommendation_agent):
    """Wire the three agents into a sequential workflow.

    participants             -> the agents, in the order they run
    output_from              -> which agent's reply is the FINAL output
    intermediate_output_from -> also report every other agent's reply
                                ("all_other") so we can display them
    """
    return SequentialBuilder(
        participants=[inventory_agent, pricing_agent, recommendation_agent],
        output_from=[recommendation_agent],
        intermediate_output_from="all_other",
    ).build()


# ============================================================
# STEP 2: Run ONE customer request through the workflow
# ============================================================

def print_banner(text: str, char: str = "=") -> None:
    """Print a line of text between two divider lines."""
    line = char * 70
    print(f"\n{line}\n{text}\n{line}")


async def handle_request(request: str, agents: tuple) -> None:
    """Run one customer request through all three agents and print the results."""

    print_banner(f"CUSTOMER REQUEST: {request}")

    # A NEW workflow for every request. A workflow remembers its conversation,
    # so reusing one would leak the previous customer's request into this one.
    workflow = build_workflow(*agents)   # *agents unpacks the tuple into 3 arguments

    # This single call runs Inventory -> Pricing -> Recommendation in order.
    # "await" pauses here until all three agents have finished.
    result = await workflow.run(request)

    # The result is a list of events, in the order they happened.
    # We only care about two event types:
    #   "intermediate" -> the Inventory and Pricing agents' replies
    #   "output"       -> the Recommendation agent's final reply
    for event in result:
        if event.type not in ("intermediate", "output"):
            continue   # skip status/bookkeeping events

        agent_name = DISPLAY_NAMES.get(event.executor_id, event.executor_id)
        print_banner(agent_name, char="-")
        print(event.data.text)   # event.data is the agent's response; .text is its reply

        if event.type == "output":
            print_banner("✅ FINAL RECOMMENDATION DELIVERED")


# ============================================================
# STEP 3: Main program - keep asking for requests until "exit"
# ============================================================

async def main() -> None:
    # Create the agents ONCE; they are reused for every request
    agents = create_agents()

    print_banner("🛒 E-commerce AI Shopping Assistant")
    print('Ask for a product recommendation, e.g. "Recommend 2 laptops within ₹1,20,000 total."')
    print('Type "exit" to stop.')

    # "while True" = loop forever; we leave it with "break"
    while True:
        try:
            # input() waits for the user to type. Running it with asyncio.to_thread
            # lets it wait without freezing the async event loop.
            request = await asyncio.to_thread(input, "\nYou: ")
        except (EOFError, KeyboardInterrupt):
            # Ctrl+C or Ctrl+D (or the input stream closing) also ends the program cleanly
            print()
            break

        request = request.strip()          # remove spaces/newlines around the text

        if not request:                    # user just pressed Enter
            continue                       # ask again

        if request.lower() in EXIT_COMMANDS:
            break                          # leave the loop -> program ends

        # try/except: if one request fails (e.g. a rate-limit error),
        # show the error and keep the assistant running for the next request.
        try:
            await handle_request(request, agents)
        except Exception as error:
            print(f"\n Request failed: {type(error).__name__}: {error}")
            print("Please try again (if this is a rate-limit error, wait a few seconds first).")

    print("👋 Goodbye!")


if __name__ == "__main__":
    # asyncio.run() starts the async main() function
    asyncio.run(main())