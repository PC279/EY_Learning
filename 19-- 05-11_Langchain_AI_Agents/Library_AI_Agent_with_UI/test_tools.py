"""Free offline checks for tools.py. No API key needed, real JSON files are untouched."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import tools


class ToolTests(unittest.TestCase):
    def setUp(self):
        # Copy the data into a temporary folder so tests never change the real files.
        self.tmp = Path(tempfile.mkdtemp())
        self.books = self.tmp / "books.json"
        self.reservations = self.tmp / "reservations.json"
        shutil.copy(tools.BOOKS_PATH, self.books)
        self.reservations.write_text("[]", encoding="utf-8")
        self.patches = [
            patch.object(tools, "BOOKS_PATH", self.books),
            patch.object(tools, "RESERVATIONS_PATH", self.reservations),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        shutil.rmtree(self.tmp)

    def copies(self, book_id):
        return next(b for b in json.loads(self.books.read_text()) if b["id"] == book_id)["available_copies"]

    def test_search_python(self):
        ids = [b["id"] for b in tools.search_books("Python programming")["results"]]
        self.assertIn(101, ids)
        self.assertIn(102, ids)

    def test_search_ai_short_form(self):
        ids = [b["id"] for b in tools.search_books("AI")["results"]]
        self.assertEqual(set(ids), {104, 105, 106})

    def test_search_no_match(self):
        self.assertEqual(tools.search_books("cooking")["results"], [])

    def test_reserve_approved(self):
        result = tools.reserve_book(101, "Ahmed", confirm=lambda _: "y")
        self.assertTrue(result["reserved"])
        self.assertEqual(self.copies(101), 2)
        self.assertEqual(len(json.loads(self.reservations.read_text())), 1)

    def test_reserve_declined(self):
        result = tools.reserve_book(101, "Ahmed", confirm=lambda _: "n")
        self.assertFalse(result["reserved"])
        self.assertEqual(self.copies(101), 3)
        self.assertEqual(json.loads(self.reservations.read_text()), [])

    def test_reserve_no_copies_never_asks(self):
        def fail_if_asked(_):
            raise AssertionError("Should not ask for approval when no copies exist")
        result = tools.reserve_book(105, "Priya", confirm=fail_if_asked)
        self.assertFalse(result["reserved"])
        self.assertEqual(json.loads(self.reservations.read_text()), [])

    def test_check_reservation_saves_nothing(self):
        result = tools.check_reservation("101", "Ahmed")  # ID as text, like some models send
        self.assertTrue(result["ok"])
        self.assertEqual(self.copies(101), 3)
        self.assertEqual(json.loads(self.reservations.read_text()), [])
        self.assertFalse(tools.check_reservation(105, "Priya")["ok"])  # no copies
        self.assertFalse(tools.check_reservation(101, "  ")["ok"])     # no name

    def test_reserve_unknown_id(self):
        self.assertFalse(tools.reserve_book(999, "Ahmed", confirm=lambda _: "y")["reserved"])


if __name__ == "__main__":
    unittest.main()
