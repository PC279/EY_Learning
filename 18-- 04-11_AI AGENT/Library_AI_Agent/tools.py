"""The two Python tools the AI agent can choose from.

These are plain Python functions. The AI model never runs them itself:
agent.py reads the model's choice and calls them here.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

# Paths are built from this file's folder, so the app works from any working directory.
ROOT = Path(__file__).resolve().parent
BOOKS_PATH = ROOT / "books.json"
RESERVATIONS_PATH = ROOT / "reservations.json"

# Filler words removed from searches so "books related to Python" just searches "python".
STOP_WORDS = {
    "a", "an", "the", "and", "or", "of", "to", "for", "in", "on", "with", "about",
    "is", "are", "me", "show", "find", "book", "books", "related", "available",
}
# Short forms users often type, expanded to the words used in books.json.
SYNONYMS = {"ai": ["artificial", "intelligence"], "ml": ["machine", "learning"]}


def load_json(path: Path) -> list:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: list) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def keywords(text: str) -> set[str]:
    """Turn text into a set of lowercase search words (minus filler, plus synonyms)."""
    words = set(re.findall(r"[a-z0-9]+", text.lower())) - STOP_WORDS
    for short, expanded in SYNONYMS.items():
        if short in words:
            words.update(expanded)
    return words


# ---------------- Tool 1 ----------------
def search_books(query: str) -> dict:
    """Find books whose title, author or category share words with the query."""
    query_words = keywords(query)
    matches = []

    for book in load_json(BOOKS_PATH):
        book_words = keywords(f"{book['title']} {book['author']} {book['category']}")
        score = len(query_words & book_words)  # how many search words this book contains
        if score > 0:
            matches.append((score, book))

    matches.sort(key=lambda pair: -pair[0])  # best matches first
    results = [
        {**book, "is_available": book["available_copies"] > 0}
        for _, book in matches
    ]
    return {
        "query": query,
        "results": results,
        "message": "Matching books found." if results else "No books matched this search.",
    }


# ---------------- Tool 2 ----------------
def reserve_book(book_id: int, customer_name: str, confirm: Callable[[str], str] = input) -> dict:
    """Reserve one copy of a book, but only after the human types 'y' to approve.

    `confirm` defaults to input() (the keyboard). Tests pass a fake answer instead.
    """
    customer_name = customer_name.strip()
    if not customer_name:
        return {"reserved": False, "reason": "Customer name is missing."}

    books = load_json(BOOKS_PATH)
    book = next((b for b in books if b["id"] == int(book_id)), None)
    if book is None:
        return {"reserved": False, "reason": f"No book found with ID {book_id}."}

    # Check availability BEFORE asking, so we never ask to approve an impossible reservation.
    if book["available_copies"] <= 0:
        return {"reserved": False, "reason": f"'{book['title']}' has no available copies."}

    # The approval step happens in Python, not in the AI, so the model cannot skip it.
    print("\n--- RESERVATION APPROVAL REQUIRED ---")
    print(f"Book    : {book['title']} (ID {book['id']})")
    print(f"Customer: {customer_name}")
    answer = confirm("Create this reservation? (y/n): ").strip().lower()
    if answer not in {"y", "yes"}:
        return {"reserved": False, "reason": "The user did not approve the reservation."}

    # Approved: save the reservation and reduce the copy count.
    reservations = load_json(RESERVATIONS_PATH)
    reservation = {
        "reservation_id": f"R-{len(reservations) + 1:04d}",
        "book_id": book["id"],
        "title": book["title"],
        "customer_name": customer_name,
        "reserved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    reservations.append(reservation)
    book["available_copies"] -= 1  # `book` points into `books`, so this updates the list

    save_json(RESERVATIONS_PATH, reservations)
    save_json(BOOKS_PATH, books)
    return {"reserved": True, "reservation": reservation, "copies_left": book["available_copies"]}
