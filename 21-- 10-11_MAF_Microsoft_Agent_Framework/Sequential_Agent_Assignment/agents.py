# agents.py
# ------------------------------------------------------------
# Creates the three specialised AI agents for the shopping assistant.
# Each agent = LLM client + name + instructions (+ optional tools).
# The LLM is NVIDIA Nemotron, accessed through OpenRouter.
# The orchestration (running them in order) lives in sequential.py.
# ------------------------------------------------------------

import os                                        # read environment variables
import asyncio                                   # needed only for the quick test at the bottom
from dotenv import load_dotenv                   # loads variables from the .env file
from agent_framework import Agent                # the agent class
# OpenRouter speaks the OpenAI "Chat Completions" format, so we use the
# Chat Completions client and simply point it at OpenRouter's address.
from agent_framework.openai import OpenAIChatCompletionClient

from tools import search_products, calculate_order_total  # our tested tools

# ============================================================
# STEP 1: Load configuration from .env
# ============================================================

# Reads .env and puts OPENROUTER_API_KEY / OPENROUTER_MODEL into os.environ
load_dotenv()

# OpenRouter's OpenAI-compatible API address (same for every model)
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

API_KEY = os.getenv("OPENROUTER_API_KEY")

# The model ID exactly as shown on the OpenRouter model page.
# Kept in .env so you can switch models without touching the code.
MODEL = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3.5-super-vl:free")

# Fail early with a clear message instead of a confusing error later
if not API_KEY:
    raise ValueError("OPENROUTER_API_KEY is missing. Add it to your .env file.")


# ============================================================
# STEP 2: Instructions for each agent
# Instructions = the agent's job description. Each one says:
#   - who the agent is and where it sits in the pipeline
#   - the steps to follow and which tool to use
#   - what NOT to do (stay in your lane)
#   - the exact output format (so the next agent can read it)
# ============================================================

INVENTORY_INSTRUCTIONS = """
You are the Inventory Agent, the FIRST of three agents in an e-commerce shopping assistant.

Your job:
1. Read the customer's request and identify: the product type or name, the quantity wanted,
   and the total budget in INR (write "not specified" if there is no budget).
2. Call the search_products tool with a single product keyword (for example "laptop").
   Use ONLY products returned by the tool. Never invent products, prices or stock.
3. For each product, set its availability for the requested quantity:
   AVAILABLE if stock >= quantity, LOW STOCK if stock is above 0 but below the quantity,
   OUT OF STOCK if stock is 0.
4. If the tool returns not_found, state that the product or category is not sold,
   and list the available_categories if the tool provided them.

Do NOT calculate order totals and do NOT recommend a product. Later agents do that.

Reply in exactly this format:
INVENTORY AGENT
Customer request: <product>, quantity <n>, budget ₹<amount or "not specified">
Matching products:
- <product_id> | <name> | ₹<price> each | stock: <stock> | rating: <rating> | <AVAILABLE / LOW STOCK / OUT OF STOCK>
"""

PRICING_INSTRUCTIONS = """
You are the Pricing Agent, the SECOND of three agents. The Inventory Agent's report is in the conversation above.

Your job:
1. Take the requested quantity and budget from the Inventory Agent's report.
2. For EVERY product the Inventory Agent listed, call the calculate_order_total tool with its
   product_id and the requested quantity. Never calculate totals yourself; always use the tool.
3. Budget check for each product:
   - WITHIN BUDGET if the tool status is ok and total <= budget
   - OVER BUDGET if the tool status is ok and total > budget
   - NOT FULFILLABLE if the tool status is out_of_stock, insufficient_stock or invalid_quantity (give the reason)
   - If the budget is "not specified", write BUDGET N/A instead of WITHIN/OVER BUDGET.
4. If the Inventory Agent found no products, say there is nothing to price.

Do NOT recommend a product. The next agent does that.

Reply in exactly this format:
PRICING AGENT
Quantity requested: <n> | Budget: ₹<amount or "not specified">
- <product_id> | <name> | ₹<unit price> x <n> = ₹<total> | <WITHIN BUDGET / OVER BUDGET / BUDGET N/A>
- <product_id> | <name> | NOT FULFILLABLE: <reason from the tool's message>
Affordable products: <product_ids that are WITHIN BUDGET, or "none">
"""

RECOMMENDATION_INSTRUCTIONS = """
You are the Recommendation Agent, the LAST of three agents. The Inventory Agent's and
Pricing Agent's reports are in the conversation above.

Rules for choosing:
1. Consider ONLY products the Pricing Agent marked WITHIN BUDGET
   (or BUDGET N/A, if the customer gave no budget, as long as stock is sufficient).
2. Choose the product with the highest customer rating.
3. If ratings are equal, choose the one with the lower total cost.
4. Never recommend a product that is out of stock, has insufficient stock or is over budget.
5. If nothing qualifies, do not recommend anything. Explain why (category not sold,
   not enough stock, or everything is over budget) and suggest a helpful next step,
   such as a smaller quantity, a higher budget, or one of the available categories.

Reply in exactly this format:
RECOMMENDATION AGENT
Recommended product: <name> (<product_id>)   [or "No recommendation"]
Price and quantity: ₹<unit price> each x <n> = ₹<total>
Customer rating: <rating>
Reason: <one or two sentences>
"""


# ============================================================
# STEP 3: Create the agents
# ============================================================

def create_agents() -> tuple[Agent, Agent, Agent]:
    """Create and return the Inventory, Pricing and Recommendation agents (in pipeline order)."""

    # One client (connection to OpenRouter) shared by all three agents.
    # base_url redirects the OpenAI-style requests to OpenRouter instead of OpenAI.
    client = OpenAIChatCompletionClient(
        model=MODEL,
        api_key=API_KEY,
        base_url=OPENROUTER_BASE_URL,
    )

    inventory_agent = Agent(
        client=client,
        name="InventoryAgent",                       # shown in the output; no spaces is safest
        description="Finds matching products and checks stock.",
        instructions=INVENTORY_INSTRUCTIONS,
        tools=[search_products],                     # can ONLY search
    )

    pricing_agent = Agent(
        client=client,
        name="PricingAgent",
        description="Calculates order totals and checks them against the budget.",
        instructions=PRICING_INSTRUCTIONS,
        tools=[calculate_order_total],               # can ONLY price
    )

    recommendation_agent = Agent(
        client=client,
        name="RecommendationAgent",
        description="Recommends the best affordable, in-stock product.",
        instructions=RECOMMENDATION_INSTRUCTIONS,
        # no tools: it only reasons over the previous agents' reports
    )

    return inventory_agent, pricing_agent, recommendation_agent


# ============================================================
# STEP 4: Quick test of ONE agent on its own
# (Testing a single agent here is fine. The full three-agent
#  pipeline must use SequentialBuilder in sequential.py.)
# ============================================================

async def _test_inventory_agent() -> None:
    inventory_agent, _, _ = create_agents()       # "_" means "we don't need these two here"
    result = await inventory_agent.run("Recommend 2 laptops within ₹1,20,000 total.")
    print(result.text)


if __name__ == "__main__":
    asyncio.run(_test_inventory_agent())