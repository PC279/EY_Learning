"""Conversational Ask HR: follow-up questions use the chat history.
Run:  python -m part3_langchain.chat
"""
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from part3_langchain.ask import llm, rag_chain

rephrase_prompt = ChatPromptTemplate.from_messages([
    ("system", "Rewrite the user's latest message as a complete, standalone question, "
               "using the chat history to fill in what it refers to. "
               "Return only the question. If it is already standalone, return it unchanged."),
    MessagesPlaceholder("history"),
    ("human", "{question}"),
])
rephrase_chain = rephrase_prompt | llm | StrOutputParser()


def chat():
    history = []
    while (q := input("\nYou> ").strip()) not in {"", "exit", "quit"}:
        standalone = rephrase_chain.invoke({"history": history, "question": q}) if history else q
        result = rag_chain.invoke({"question": standalone, "office": None})
        print(f"  (searched for: {standalone})\nAsk HR> {result['answer']}")
        history += [HumanMessage(q), AIMessage(result["answer"])]
        history = history[-6:]                           # keep the last 3 turns


if __name__ == "__main__":
    chat()
