"""SQLite persistence for trips: create the schema, save a trip, read trips back."""
import sqlite3
from contextlib import closing

from config import DB_PATH, PROJECT_DIR


def _connect() -> sqlite3.Connection:
    # A fresh connection per call keeps this safe under FastAPI's worker threads
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # rows behave like dicts
    return conn


def init_db() -> None:
    """Create the trips table if it does not exist yet (safe to call on every start-up)."""
    schema = (PROJECT_DIR / "schema.sql").read_text()
    with closing(_connect()) as conn:
        conn.executescript(schema)


def create_trip(employee_id: str, destination: str, start_date: str, end_date: str, purpose: str) -> dict:
    with closing(_connect()) as conn, conn:  # inner "conn" commits the transaction
        cur = conn.execute(
            "INSERT INTO trips (employee_id, destination, start_date, end_date, purpose) VALUES (?, ?, ?, ?, ?)",
            (employee_id, destination, start_date, end_date, purpose),
        )
    return get_trip(cur.lastrowid)


def get_trip(trip_id: int) -> dict | None:
    with closing(_connect()) as conn:
        row = conn.execute("SELECT * FROM trips WHERE trip_id = ?", (trip_id,)).fetchone()
    return dict(row) if row else None


def find_trips(employee_id: str, destination: str = "") -> list[dict]:
    """An employee's trips, soonest first; destination is a case-insensitive partial match."""
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT * FROM trips WHERE employee_id = ? COLLATE NOCASE AND destination LIKE '%' || ? || '%' ORDER BY start_date",
            (employee_id, destination),
        ).fetchall()
    return [dict(r) for r in rows]
