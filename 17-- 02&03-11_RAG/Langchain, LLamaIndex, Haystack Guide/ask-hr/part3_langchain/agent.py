"""Agentic Ask HR: the model decides when and what to search.
Run:  python -m part3_langchain.agent
"""
from langchain.agents import create_agent
from langchain_core.tools import tool

from part3_langchain.ask import format_docs, llm, vectorstore


@tool
def search_hr_documents(query: str, office: str = "") -> str:
    """Search Nimbus Corp HR policies. `office` may be 'india', 'germany' or '' for both."""
    flt = {"office": {"$in": [office, "all"]}} if office else None
    return format_docs(vectorstore.similarity_search(query, k=4, filter=flt))


agent = create_agent(
    model=llm,
    tools=[search_hr_documents],
    system_prompt=("You are Ask HR for Nimbus Corp. Use search_hr_documents for any policy "
                   "question, searching more than once if the question has several parts. "
                   "Answer only from what the tool returns and cite the sources."),
)

if __name__ == "__main__":
    question = "I'm on probation in Berlin. Can I take 7 days off, and how many days do I get per year?"
    result = agent.invoke({"messages": [{"role": "user", "content": question}]})
    for m in result["messages"]:
        print(f"--- {m.type}: {str(m.content)[:300]}")
