import os                                   # to read environment variables (our API key)

from dotenv import load_dotenv              # loads variables from the .env file
from langchain_openai import ChatOpenAI     # chat model connector (works with OpenRouter too)
from langchain.agents import create_agent   # builds the agent loop: model -> tool -> model -> answer
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage  # message types we inspect

# Import our two tools from tools.py
# (the test block in tools.py does NOT run here, thanks to `if __name__ == "__main__":`)
from tools import search_restaurants, calculate_dining_cost

# Load ALL variables from .env into the environment (must happen before creating the model)
load_dotenv()

# ---------------------------------------------------------------------------
# 1. THE MODEL
# ---------------------------------------------------------------------------
# The PDF asks for GPT-4o-mini. Through OpenRouter its name is "openai/gpt-4o-mini".
# You can swap in a free model to experiment, but it MUST support tool calling.
MODEL_NAME = "nvidia/nemotron-3.5-super-vl:free"

model = ChatOpenAI(
    model=MODEL_NAME,
    base_url="https://openrouter.ai/api/v1",    # send requests to OpenRouter instead of OpenAI
    api_key=os.getenv("OPENROUTER_API_KEY"),   # we fetch the key ourselves (ChatOpenAI doesn't know this name)
    temperature=0,                             # 0 = most predictable answers; good for tool-using agents
)

# ---------------------------------------------------------------------------
# 2. THE SYSTEM PROMPT
# ---------------------------------------------------------------------------
# The system prompt is the agent's "job description". The model reads it before every reply.
# The PDF requires it to forbid inventing restaurant names, prices or availability.
SYSTEM_PROMPT = """You are a helpful Restaurant Reservation Assistant.

You help customers:
- find restaurants by cuisine, name or city (use the search_restaurants tool)
- estimate the total dining cost for a group (use the calculate_dining_cost tool)

Rules:
- NEVER invent restaurant names, IDs, prices or seat availability.
  Only use information returned by the tools.
- If the user mentions a restaurant by name and you don't know its ID,
  call search_restaurants first to find the ID, then calculate_dining_cost.
- You cannot make bookings or take payments. Only give information and cost estimates.
- Only answer restaurant-related questions. Politely refuse anything else.
- Prices are in Indian Rupees (Rs.).
"""

# ---------------------------------------------------------------------------
# 3. THE AGENT
# ---------------------------------------------------------------------------
# create_agent wires everything together:
#   - model: the brain that decides what to do
#   - tools: the functions the model is allowed to request
#   - system_prompt: the rules it must follow
# (Memory / checkpointer will be added in the next lesson.)
agent = create_agent(
    model=model,
    tools=[search_restaurants, calculate_dining_cost],
    system_prompt=SYSTEM_PROMPT,
)


# ---------------------------------------------------------------------------
# 4. SHOWING WHICH TOOLS WERE USED
# ---------------------------------------------------------------------------
def print_tool_activity(messages: list) -> None:
    """Print every tool the model chose (with its arguments) during the LATEST user turn."""

    # The result contains a list of messages. Once memory is added, it will hold the
    # WHOLE conversation, so we find where the latest user message is and only look
    # at what came after it. (Without this, old tool calls would be printed again.)
    last_human_index = 0
    for i, message in enumerate(messages):          # enumerate gives (position, item) pairs
        if isinstance(message, HumanMessage):       # isinstance checks the message's type
            last_human_index = i

    # Look only at the messages produced in response to the latest question
    for message in messages[last_human_index + 1:]:

        # An AIMessage with tool_calls = the model ASKING to run one or more tools
        if isinstance(message, AIMessage) and message.tool_calls:
            for call in message.tool_calls:         # each call is a dict: {"name", "args", "id"}
                print(f"  [Tool selected] {call['name']}")
                print(f"  [Arguments]     {call['args']}")

        # A ToolMessage = the RESULT our Python function returned, sent back to the model
        elif isinstance(message, ToolMessage):
            first_line = message.content.splitlines()[0]   # just a short preview
            print(f"  [Tool result]   {first_line}")


# ---------------------------------------------------------------------------
# 5. THE CHAT LOOP
# ---------------------------------------------------------------------------
def main() -> None:
    print("Restaurant Reservation Assistant, what and where would you like to eat today? ")
    print("(type 'exit' to quit)")

    while True:                                     # keep chatting until the user quits
        user_input = input("\nYou: ").strip()

        if user_input.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        if not user_input:                          # ignore empty Enter presses (proper guardrail comes later)
            continue

        try:
            # Send the user's message to the agent.
            # The agent runs its loop: model -> (tool -> model)* -> final answer
            result = agent.invoke(
                {"messages": [{"role": "user", "content": user_input}]}
            )
        except Exception as error:
            # Network problems, rate limits, bad key... show the error but keep the program running
            print(f"\n[Error] {error}")
            continue

        messages = result["messages"]               # every message from this run
        print_tool_activity(messages)               # show tool name + arguments in the terminal

        # The last message is always the model's final answer to the user
        print(f"\nAgent: {messages[-1].content}")


# Run the chat loop only when this file is executed directly
if __name__ == "__main__":
    main()