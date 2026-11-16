from typing import TypedDict, Optional


class ResearchResult(TypedDict):
    """One web search result produced by the Research Agent."""
    title: str
    url: str
    content: str


# total=False: the graph starts with only {"topic": ...}; each agent fills in its own keys.
class NewsState(TypedDict, total=False):

    # User input
    topic: str

    # Research Agent output
    research_results: list[ResearchResult]  # list of {title, url, content}, not a string

    # Summarizer Agent output
    summary_points: list[str]               # exactly 5 key points
    sources: list[str]                      # URLs behind the 5 points

    # Notifier Agent output
    email_text: str                         # the full email (LangGraph drops keys not listed here)
    output_file: str                        # path of the saved .txt file

    # Error handling
    error: Optional[str]