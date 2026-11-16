"""
TASK 4 - Get an AI answer
-------------------------
1. Retrieve the top 2 chunks from ChromaDB for a question.
2. Send the question and chunks to an AI model.
3. The AI must answer only from that context, or say it cannot find the answer.
4. Print the final response.

Run task3_store_and_search.py once before this file, so the database exists.
"""

import config
from rag_helpers import search
from ai_client import ask_ai


def answer_question(question):
    """The full RAG pipeline for one question: retrieve -> augment -> generate."""
    print("=" * 70)
    print(f"QUESTION: {question}")
    print("=" * 70)

    # 1. RETRIEVE: find the most relevant chunks
    chunks = search(question, top_k=config.TOP_K)
    print("Retrieved context:")
    for rank, c in enumerate(chunks, start=1):
        print(f"  {rank}. {c['source']} (chunk {c['chunk_index']})  distance = {c['distance']:.4f}")

    # 2 + 3. AUGMENT the prompt with the chunks and GENERATE an answer
    try:
        answer = ask_ai(question, chunks)
    except Exception as error:
        answer = f"[AI ERROR] {error}"

    print(f"\nAI ANSWER ({config.AI_PROVIDER} / {config.AI_MODEL}):")
    print(f"  {answer}\n")


def main():
    print(f"AI provider: {config.AI_PROVIDER}   model: {config.AI_MODEL}\n")

    while True:
        question = input(
            "Type a question, press Enter to run all 5 test questions, or type 'q' to quit\n> "
        ).strip()

        if question.lower() in ("q", "quit", "exit"):
            break
        if question:
            answer_question(question)
        else:
            for test_question in config.TEST_QUESTIONS:
                answer_question(test_question)

    print("Goodbye!")


if __name__ == "__main__":
    main()
