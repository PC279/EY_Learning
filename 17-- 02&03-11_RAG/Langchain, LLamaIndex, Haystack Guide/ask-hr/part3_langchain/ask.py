"""LangChain query pipeline, written in LCEL.
Run:  python -m part3_langchain.ask
"""
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_openai import ChatOpenAI

import config
from part2_by_hand.prompts import SYSTEM_PROMPT
from part3_langchain.store import get_vectorstore

vectorstore = get_vectorstore()

llm = ChatOpenAI(
    model=config.CHAT_MODEL,
    api_key=config.OPENROUTER_API_KEY,
    base_url=config.OPENROUTER_BASE_URL,      # OpenRouter speaks the OpenAI API
    temperature=0,
)

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "Employee's office: {office}\n\n"
              "Context passages:\n{context}\n\n"
              "Question: {question}"),
])


def retrieve(inputs: dict) -> list[Document]:
    office = inputs.get("office")
    flt = {"office": {"$in": [office, "all"]}} if office else None
    return vectorstore.similarity_search(inputs["question"], k=config.TOP_K, filter=flt)


def format_docs(docs: list[Document]) -> str:
    return "\n\n".join(f"[{i}] (source: {d.metadata['source']})\n{d.page_content}"
                       for i, d in enumerate(docs, start=1))


answer_chain = (
    RunnablePassthrough.assign(
        context=lambda x: format_docs(x["docs"]),
        office=lambda x: x.get("office") or "unknown",
    )
    | prompt
    | llm
    | StrOutputParser()
)

rag_chain = (
    RunnablePassthrough.assign(docs=RunnableLambda(retrieve))   # adds "docs"
    .assign(answer=answer_chain)                                # adds "answer"
)


def ask(question: str, office: str | None = None) -> dict:
    result = rag_chain.invoke({"question": question, "office": office})
    return {"answer": result["answer"],
            "sources": [d.metadata["source"] for d in result["docs"]]}


if __name__ == "__main__":
    while (q := input("\nAsk HR> ").strip()) not in {"", "exit", "quit"}:
        docs = retrieve({"question": q})
        for token in answer_chain.stream({"question": q, "docs": docs, "office": None}):
            print(token, end="", flush=True)               # streams word by word
        print()
