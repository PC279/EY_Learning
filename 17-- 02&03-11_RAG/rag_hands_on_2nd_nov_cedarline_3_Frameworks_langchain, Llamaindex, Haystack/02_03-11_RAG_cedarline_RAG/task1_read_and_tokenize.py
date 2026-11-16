"""
TASK 1 - Read and tokenize
--------------------------
1. Read both .txt files from the Documents folder.
2. Display each document.
3. Use tiktoken to show how many tokens each file has.
"""

from rag_helpers import load_documents, count_tokens


def main():
    documents = load_documents()
    print(f"Found {len(documents)} documents in the Documents folder.\n")

    total_tokens = 0
    for file_name, text in documents.items():
        tokens = count_tokens(text)
        total_tokens += tokens

        print("=" * 70)
        print(f"FILE: {file_name}")
        print("=" * 70)
        print(text.strip())
        print("-" * 70)
        print(f"Characters : {len(text)}")
        print(f"Words      : {len(text.split())}")
        print(f"Tokens     : {tokens}")
        print()

    print("=" * 70)
    print("TOKEN COUNT SUMMARY")
    print("=" * 70)
    for file_name, text in documents.items():
        print(f"{file_name:<35} {count_tokens(text):>5} tokens")
    print(f"{'TOTAL':<35} {total_tokens:>5} tokens")


if __name__ == "__main__":
    main()
