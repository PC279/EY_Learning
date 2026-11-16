-- Saved business trips. Dates are ISO strings (YYYY-MM-DD), which SQLite compares correctly as text.
CREATE TABLE IF NOT EXISTS trips (
    trip_id     INTEGER PRIMARY KEY AUTOINCREMENT,   -- unique trip ID
    employee_id TEXT    NOT NULL,
    destination TEXT    NOT NULL,
    start_date  TEXT    NOT NULL,
    end_date    TEXT    NOT NULL,
    purpose     TEXT    NOT NULL,
    status      TEXT    NOT NULL DEFAULT 'planned'
                CHECK (status IN ('planned', 'completed', 'cancelled')),
    CHECK (end_date >= start_date)                   -- last line of defence behind API validation
);
