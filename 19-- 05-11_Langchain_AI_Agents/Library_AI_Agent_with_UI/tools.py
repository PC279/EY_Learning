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
def check_reservation(book_id, customer_name: str) -> dict:
    """Check if a reservation is possible WITHOUT saving anything.

    Used by reserve_book() below, and by server.py before it shows Confirm/Cancel.
    """
    customer_name = (customer_name or "").strip()
    if not customer_name:
        return {"ok": False, "reason": "Customer name is missing."}
    try:
        book_id = int(book_id)  # the model sometimes sends "101" instead of 101
    except (TypeError, ValueError):
        return {"ok": False, "reason": f"'{book_id}' is not a valid book ID."}

    book = next((b for b in load_json(BOOKS_PATH) if b["id"] == book_id), None)
    if book is None:
        return {"ok": False, "reason": f"No book found with ID {book_id}."}
    if book["available_copies"] <= 0:
        return {"ok": False, "reason": f"'{book['title']}' has no available copies."}
    return {"ok": True, "book": book, "customer_name": customer_name}


def reserve_book(book_id: int, customer_name: str, confirm: Callable[[str], str] = input) -> dict:
    """Reserve one copy of a book, but only after the human approves.

    `confirm` defaults to input() (terminal). The web server and tests pass their own answer.
    """
    # Check availability BEFORE asking, so we never ask to approve an impossible reservation.
    check = check_reservation(book_id, customer_name)
    if not check["ok"]:
        return {"reserved": False, "reason": check["reason"]}
    book_id, customer_name, title = check["book"]["id"], check["customer_name"], check["book"]["title"]

    # The approval step happens in Python, not in the AI, so the model cannot skip it.
    print("\n--- RESERVATION APPROVAL REQUIRED ---")
    print(f"Book    : {title} (ID {book_id})")
    print(f"Customer: {customer_name}")
    answer = confirm("Create this reservation? (y/n): ").strip().lower()
    if answer not in {"y", "yes"}:
        return {"reserved": False, "reason": "The user did not approve the reservation."}

    # Approved: reload fresh data (time may have passed while waiting), save, reduce copies.
    books = load_json(BOOKS_PATH)
    book = next(b for b in books if b["id"] == book_id)
    if book["available_copies"] <= 0:
        return {"reserved": False, "reason": f"'{title}' ran out of copies before approval."}
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
