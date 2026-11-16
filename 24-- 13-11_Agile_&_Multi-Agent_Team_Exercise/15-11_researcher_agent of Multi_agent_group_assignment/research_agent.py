"""Research Agent (Agent 1).

An LLM agent that uses a web search tool (Tavily) to find the latest
information on a topic. The LLM decides WHAT to search; the results
themselves are taken straight from the search tool, so every URL passed
to the Summarizer is real and never invented by the model.

LangGraph calls research_node(state). It reads state["topic"] and returns
only the NewsState keys it changes: {"topic", "research_results"} or {"error"}.
The shape of the state is defined in state.py.
"""

import json

from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware
from langchain_core.messages import ToolMessage
from langchain_tavily import TavilySearch

from config import get_llm
from state import NewsState, ResearchResult

MAX_TOPIC_LENGTH = 500   # longest topic a user may enter
MAX_SEARCHES = 3         # most web searches the LLM may run per topic
RESULTS_PER_SEARCH = 5   # results Tavily returns for each search
# shortcut: plain character cut, may end mid-sentence; switch to sentence-aware trimming if summaries suffer
MAX_CONTENT_CHARS = 1500

SYSTEM_PROMPT = f"""You are a research agent for a company newsletter.
Your job is to find the LATEST developments on the topic the user gives you.

Use the web_search tool. Run between 1 and {MAX_SEARCHES} searches, each from a
different angle (for example: the topic itself, recent news on it, key
companies or products involved). Do not repeat the same search.

When you have searched enough, reply with one short sentence saying you are done.
You do not need to summarise the results; another agent will do that."""


def validate_topic(topic: str) -> str | None:
    """Return an error message if the topic is not usable, otherwise None."""
    if not topic:
        return "Please enter a topic to research."
    if len(topic) > MAX_TOPIC_LENGTH:
        return f"The topic is too long ({len(topic)} characters). Please keep it under {MAX_TOPIC_LENGTH}."
    return None


def collect_results(messages: list) -> tuple[list[ResearchResult], str | None]:
    """Pull search results out of the agent's tool messages.

    Returns (results, last_tool_note):
      - results: unique ResearchResult dicts (title, url, content) from every search
      - last_tool_note: the last non-result text a search returned, such as
        "No search results found" or an API key error, used for the error message
    """
    results = []
    seen_urls = set()
    last_tool_note = None

    for message in messages:
        # Only tool messages hold search output; skip the user and AI messages.
        if not isinstance(message, ToolMessage):
            continue

        # Successful Tavily searches come back as JSON text.
        # Anything that is not JSON is an error or warning from the tool.
        try:
            data = json.loads(message.content)
        except (json.JSONDecodeError, TypeError):
            last_tool_note = str(message.content)
            continue

        for item in data.get("results", []):
            url = item.get("url")
            if not url or url in seen_urls:  # skip results with no link and duplicates across searches
                continue
            seen_urls.add(url)
            results.append({
                "title": item.get("title", ""),
                "url": url,
                "content": (item.get("content") or "")[:MAX_CONTENT_CHARS],
            })

    return results, last_tool_note


def research_node(state: NewsState) -> NewsState:
    """LangGraph node: research state["topic"] and return the findings."""
    topic = (state.get("topic") or "").strip()

    error = validate_topic(topic)
    if error:
        return {"error": error}

    try:
        # Tavily tool the LLM can call. topic="news" focuses on recent news articles.
        web_search = TavilySearch(max_results=RESULTS_PER_SEARCH, topic="news")

        agent = create_agent(
            get_llm(),
            tools=[web_search],
            system_prompt=SYSTEM_PROMPT,
            # Stop cleanly after MAX_SEARCHES searches, so a confused model cannot loop forever.
            middleware=[ToolCallLimitMiddleware(run_limit=MAX_SEARCHES, exit_behavior="end")],
        )

        result = agent.invoke(
            {"messages": [{"role": "user", "content": f"Research this topic: {topic}"}]},
            config={"recursion_limit": 15},  # backstop in case the model keeps going without searching
        )
    except Exception as e:  # missing key, network down, rate limit, model error, ...
        return {"error": f"Research Agent failed: {e}"}

    results, last_tool_note = collect_results(result["messages"])

    if results:
        # Return the cleaned topic too, so later agents use the trimmed version.
        return {"topic": topic, "research_results": results}

    # Case 1: the tool WAS called but returned no usable results
    # (no matches, invalid Tavily key, Tavily down, search limit reached).
    if last_tool_note:
        return {"error": f"No results found for '{topic}'. Search said: {last_tool_note[:300]}"}

    # Case 2: the model NEVER called the web_search tool. It answered on its own
    # instead of searching, so we have no real sources and must stop here.
    # Common causes: the free model ignored the tool, or the endpoint does not support tool calling right now.
    return {"error": (
        f"Research Agent error: the model did not call the web_search tool for '{topic}', "
        "so no web results were collected. Please run it again; if this keeps happening, "
        "the model may not support tool calling at the moment."
    )}


def _self_check() -> None:
    """Offline checks for the logic that needs no internet or API keys."""
    # Topic validation
    assert validate_topic("") is not None
    assert validate_topic("x" * (MAX_TOPIC_LENGTH + 1)) is not None
    assert validate_topic("x" * MAX_TOPIC_LENGTH) is None
    assert research_node({"topic": "   "}) == {"error": "Please enter a topic to research."}

    # Result collection: duplicates removed, errors noted, long content trimmed
    good = json.dumps({"results": [
        {"title": "A", "url": "https://a.com", "content": "x" * 5000},
        {"title": "B", "url": "https://b.com", "content": "b"},
    ]})
    duplicate = json.dumps({"results": [{"title": "A again", "url": "https://a.com", "content": "a"}]})
    messages = [
        ToolMessage(content=good, tool_call_id="1"),
        ToolMessage(content=duplicate, tool_call_id="2"),
        ToolMessage(content="No search results found for 'xyz'.", tool_call_id="3"),
    ]
    results, note = collect_results(messages)
    assert [r["url"] for r in results] == ["https://a.com", "https://b.com"]
    assert len(results[0]["content"]) == MAX_CONTENT_CHARS
    assert note.startswith("No search results found")

    print("Offline self-check passed.")


if __name__ == "__main__":
    # Usage (run from the project root):
    #   python -m agents.research_agent                 -> offline checks only
    #   python -m agents.research_agent "Generative AI" -> offline checks + a live run
    import sys

    _self_check()

    if len(sys.argv) > 1:
        output = research_node({"topic": " ".join(sys.argv[1:])})
        if "error" in output:
            print("ERROR:", output["error"])
        else:
            for i, r in enumerate(output["research_results"], 1):
                print(f"\n{i}. {r['title']}\n   {r['url']}\n   {r['content'][:200]}...")