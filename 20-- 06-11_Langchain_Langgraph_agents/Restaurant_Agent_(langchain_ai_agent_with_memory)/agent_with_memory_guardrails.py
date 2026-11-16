import os                                   # to read environment variables (our API key)
import uuid                                 # generates unique IDs for each conversation (thread)

from dotenv import load_dotenv              # loads variables from the .env file
from langchain_openai import ChatOpenAI     # chat model connector (works with OpenRouter too)
from langchain.agents import create_agent   # builds the agent loop: model -> tool -> model -> answer
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage  # message types we inspect
from langgraph.checkpoint.memory import InMemorySaver  # stores conversation history in RAM

# Import our two tools from tools.py
# (the test block in tools.py does NOT run here, thanks to `if __name__ == "__main__":`)
from tools import search_restaurants, calculate_dining_cost

# Import the guardrails we use in the chat loop
from guardrails import check_input, detect_pii, redact_pii

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
- The restaurant data contains ONLY: name, cuisine, city, price per person and available seats.
  It has NO information about vegetarian options, ratings, menus or timings.
  If the user asks for these (e.g. "veg restaurants"), search using only the cuisine/city,
  and clearly say you can't confirm vegetarian options - never guess.

Using the conversation history:
- Remember the restaurant the user selected, the number of guests, and earlier cost results.
- If the user changes only one detail (e.g. "make that 6 people"), reuse the other details
  from earlier in the conversation and call calculate_dining_cost again.
- Short follow-ups like "yes", "no" or "6 people" refer to the previous messages.
"""

# ---------------------------------------------------------------------------
# 3. MEMORY
# ---------------------------------------------------------------------------
# A "checkpointer" saves the agent's messages after every turn.
# InMemorySaver keeps them in RAM (a Python dictionary), so they disappear
# when the program stops. Real apps would use a database-backed saver instead.
#
# The saved history is organised by "thread_id": one thread = one conversation.
# Same thread_id  -> the agent sees all earlier messages of that conversation.
# New thread_id   -> a blank conversation.

checkpointer = InMemorySaver()


def new_thread_id() -> str:
    """Create a unique ID for a fresh conversation."""
    return str(uuid.uuid4())   # e.g. "3f2b8c1e-..." - practically never repeats


# ---------------------------------------------------------------------------
# 4. THE AGENT
# ---------------------------------------------------------------------------
# create_agent wires everything together:
#   - model: the brain that decides what to do
#   - tools: the functions the model is allowed to request
#   - system_prompt: the rules it must follow
#   - checkpointer: where the conversation history is saved (memory)
agent = create_agent(
    model=model,
    tools=[search_restaurants, calculate_dining_cost],
    system_prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,
)


# ---------------------------------------------------------------------------
# 5. SHOWING WHICH TOOLS WERE USED (Task 4, point 6)
# ---------------------------------------------------------------------------
def print_tool_activity(messages: list) -> None:
    """Print every tool the model chose (with its arguments) during the LATEST user turn."""

    # With memory, the result holds the WHOLE conversation (every turn so far),
    # so we find where the latest user message is and only look at what came after it.
    # (Without this, old tool calls would be printed again on every turn.)
    last_human_index = 0
    for i, message in enumerate(messages):          # enumerate gives (position, item) pairs
        if isinstance(message, HumanMessage):       # isinstance checks the message's type
            last_human_index = i

    # Look only at the messages produced in response to the latest question.
    # The ":-1" at the end skips the very LAST message: that's the final answer,
    # which main() already prints as "Agent: ...", so we don't print it twice.
    for message in messages[last_human_index + 1 : -1]:

        # Every AIMessage = something the model produced. It can contain
        # text, tool calls, or both, so we check the two parts separately.
        if isinstance(message, AIMessage):

            # 1) Any text the model wrote along the way (often empty when it only calls tools).
            #    Some models return content as a list of blocks instead of a string,
            #    so we only print it when it's a non-empty string.
            if isinstance(message.content, str) and message.content.strip():
                print(f"  [AI message]    {message.content.strip()}")

            # 2) Any tools it asked for (an empty list is skipped automatically)
            for call in message.tool_calls:         # each call is a dict: {"name", "args", "id"}
                print(f"  [Tool selected] {call['name']}")
                print(f"  [Arguments]     {call['args']}")

        # A ToolMessage = the RESULT our Python function returned, sent back to the model
        elif isinstance(message, ToolMessage):
            first_line = message.content.splitlines()[0]   # just a short preview
            print(f"  [Tool result]   {first_line}")


# ---------------------------------------------------------------------------
# 6. THE CHAT LOOP
# ---------------------------------------------------------------------------
def main() -> None:
    print("Restaurant Reservation Assistant")
    print("Commands: /new = start a fresh conversation, exit = quit")

    thread_id = new_thread_id()                     # the current conversation's ID
    has_history = False                             # becomes True after the first successful reply

    while True:                                     # keep chatting until the user quits
        user_input = input("\nYou: ").strip()

        if user_input.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        # /new -> forget the old conversation and start a blank one
        if user_input.lower() == "/new":
            checkpointer.delete_thread(thread_id)   # actually erase the old history from memory
            thread_id = new_thread_id()             # switch to a brand-new conversation ID
            has_history = False                     # a lone "yes" is no longer a valid follow-up
            print("\n[New conversation started. Previous details are cleared.]")
            continue                                # don't send "/new" to the model

        # ---- INPUT GUARDRAIL: PII detection (runs first) ----
        # If the message contains an email or phone number, warn the user and
        # remove it BEFORE anything is sent to the model.
        pii_found = detect_pii(user_input)          # e.g. ["email address"]
        if pii_found:
            print(f"\n[Guardrail] Detected {' and '.join(pii_found)}. "
                  f"It has been removed and will not be sent to the assistant.")
            user_input = redact_pii(user_input)     # "My email is [EMAIL REDACTED]."

        # ---- INPUT GUARDRAILS: validation, domain restriction, follow-ups ----
        error = check_input(user_input, has_history)
        if error:
            if pii_found:
                # The message was mostly personal details - give a friendlier reply
                print("\nAgent: Thanks, but I don't need personal details. "
                      "I can help you search restaurants or estimate dining costs.")
            else:
                print(f"\n[Guardrail] {error}")
            continue                                # blocked: the model is never called

        # The config tells the agent WHICH conversation this message belongs to.
        # The checkpointer uses thread_id to load that conversation's history
        # before the model runs, and to save the new messages afterwards.
        config = {"configurable": {"thread_id": thread_id}}

        try:
            # Send ONLY the new message - the checkpointer adds the earlier ones automatically.
            # The agent runs its loop: model -> (tool -> model)* -> final answer
            result = agent.invoke(
                {"messages": [{"role": "user", "content": user_input}]},
                config=config,
            )
        except Exception as error:
            # Network problems, rate limits, bad key... show the error but keep the program running
            print(f"\n[Error] {error}")
            continue

        has_history = True                          # the conversation now has earlier messages

        messages = result["messages"]               # every message from this run
        print_tool_activity(messages)               # show tool name + arguments in the terminal

        # ---- OUTPUT GUARDRAIL: redact any email/phone number in the answer ----
        # The last message is always the model's final answer to the user
        safe_answer = redact_pii(messages[-1].content)
        print(f"\nAgent: {safe_answer}")


# Run the chat loop only when this file is executed directly
if __name__ == "__main__":
    main()