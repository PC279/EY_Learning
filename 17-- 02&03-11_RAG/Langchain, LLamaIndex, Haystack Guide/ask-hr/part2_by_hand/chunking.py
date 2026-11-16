"""Step 2 of indexing: cut long texts into overlapping chunks."""
import re

SEPARATORS = ["\n\n", "\n", ". ", " "]   # try the biggest natural break first


def _split(text: str, size: int, seps: list[str]) -> list[str]:
    """Recursively split text into pieces no longer than `size`."""
    if len(text) <= size:
        return [text]
    if not seps:                                   # no separator left: hard cut
        return [text[i:i + size] for i in range(0, len(text), size)]
    sep, rest = seps[0], seps[1:]
    pieces = []
    for part in text.split(sep):
        part = part + (sep if sep.strip() else "")  # keep '. ' as a full stop
        pieces.extend(_split(part, size, rest) if len(part) > size else [part])
    return pieces


def chunk_text(text: str, size: int = 800, overlap: int = 120) -> list[str]:
    """Pack small pieces into chunks of up to `size` chars, repeating ~`overlap` chars."""
    pieces = [p for p in _split(text, size, SEPARATORS) if p.strip()]
    chunks, current = [], ""
    for piece in pieces:
        joiner = "\n\n" if current else ""
        if len(current) + len(joiner) + len(piece) <= size:
            current += joiner + piece
            continue
        chunks.append(current.strip())
        tail = current[-overlap:]                  # the overlap carried forward
        tail = tail[tail.find(" ") + 1:] if " " in tail else tail   # start on a word
        current = (tail + "\n\n" + piece) if len(tail) + len(piece) + 2 <= size else piece
    if current.strip():
        chunks.append(current.strip())
    return chunks


def chunk_records(records: list[dict], size: int, overlap: int) -> list[dict]:
    """Chunk every loaded record; copy its metadata onto each chunk."""
    out = []
    for rec in records:
        if rec["metadata"].get("is_faq"):          # FAQ rows are already small
            pieces = [rec["text"]]
        else:
            pieces = chunk_text(rec["text"], size, overlap)
        for i, piece in enumerate(pieces):
            meta = dict(rec["metadata"], chunk=i)
            out.append({"text": piece, "metadata": meta})
    return out
